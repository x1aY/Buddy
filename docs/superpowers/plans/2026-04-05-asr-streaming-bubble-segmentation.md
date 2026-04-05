# ASR 流式气泡分段识别实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现ASR实时流式识别，文字在正式气泡中持续蹦出显示，用户停顿超过分段超时后自动开启新气泡，提升用户体验。

**Architecture:** 采用前后端协同方案，后端维护分段状态，分离分段超时（700ms）和LLM处理超时（2000ms）。新增 `user_transcript_ongoing` 和 `user_transcript_segment_end` 消息类型，前端直接在对话列表中更新正在识别的气泡，实现蹦字效果。

**Tech Stack:** Python FastAPI (backend), Vue 3 TypeScript (frontend), Pydantic models.

---

## 文件修改概览

| 文件 | 操作 | 说明 |
|-----|------|------|
| `backend/models/schemas.py` | Modify | 新增两个消息类型，加入ServerMessage联合类型 |
| `backend/services/stream_processor.py` | Modify | 添加分段状态管理，修改partial结果处理 |
| `frontend/shared/src/types.ts` | Modify | 新增TypeScript类型定义 |
| `frontend/src/components/VideoCallPage.vue` | Modify | 修改消息处理逻辑，移除partialUserTranscript，直接更新conversationMessages |
| `frontend/src/components/SubtitleDisplay.vue` | No change | 已支持渲染多消息，无需修改 |

---

## Task 1: 后端 - 新增消息类型到schemas

**Files:**
- Modify: `backend/models/schemas.py`

- [ ] **Step 1: 添加两个新的消息类**

Add after line 82 (`UserTranscriptPartialMessage` definition):

```python
class UserTranscriptOngoingMessage(BaseModel):
    type: Literal['user_transcript_ongoing'] = 'user_transcript_ongoing'
    message_id: str  # 当前分段唯一ID
    text: str        # 当前分段完整识别文本


class UserTranscriptSegmentEndMessage(BaseModel):
    type: Literal['user_transcript_segment_end'] = 'user_transcript_segment_end'
    message_id: str  # 结束的分段ID
```

- [ ] **Step 2: 将新消息类型添加到ServerMessage union**

Modify line 113-122, update the ServerMessage union:

```python
ServerMessage = Union[
    UserTranscriptMessage,
    UserTranscriptPartialMessage,
    UserTranscriptOngoingMessage,
    UserTranscriptSegmentEndMessage,
    ModelStartMessage,
    ModelTokenMessage,
    ModelAudioMessage,
    ModelEndMessage,
    PongMessage,
    ErrorMessage
]
```

- [ ] **Step 3: 验证语法正确**

```bash
cd backend && python -m pytest tests/ -xvs
```

Expected: No syntax errors.

- [ ] **Step 4: Commit**

```bash
git add backend/models/schemas.py
git commit -m "feat: add user_transcript_ongoing and segment_end message types"
```

---

## Task 2: 后端 - StreamProcessor添加分段状态管理

**Files:**
- Modify: `backend/services/stream_processor.py`
- Test: `backend/tests/test_services/test_stream_processor.py` (if exists)

- [ ] **Step 1: 在__init__添加新的状态变量**

Modify line 48-56, after `_pending_audio_buffer: list[bytes] = []`:

```python
        # Streaming ASR segmentation - for multiple bubbles
        self._current_segment_id: Optional[str] = None
        self._segment_silence_timer: Optional[asyncio.Task] = None
        self._segment_timeout_ms: int = 700  # Segment silence timeout (ms)
        self._finished_segments: list[str] = []  # Completed segment texts
```

- [ ] **Step 2: 修改on_partial回调处理**

Modify line 134-138, replace the existing `on_partial`:

```python
        def on_partial(text: str):
            """Called by streaming ASR when partial result available.
            Create new segment if none active, update text, send to frontend.
            """
            global segment_timeout
            if not self._result_callback:
                return

            # Create new segment if none active
            if self._current_segment_id is None:
                segment_id = str(int(asyncio.get_event_loop().time() * 1000))
                self._current_segment_id = segment_id
            else:
                segment_id = self._current_segment_id

            # Reset segment silence timer
            if self._segment_silence_timer:
                self._segment_silence_timer.cancel()

            # Schedule new segment timeout
            self._segment_silence_timer = asyncio.create_task(
                self._segment_silence_timeout(segment_id, text)
            )

            # Send ongoing update to frontend for real-time display
            if self._result_callback:
                self._result_callback(UserTranscriptOngoingMessage(
                    message_id=segment_id,
                    text=text
                ))
```

- [ ] **Step 3: 添加_segment_silence_timeout方法**

Add after line 147 (`_on_final_result`) before line 149 (`_silence_timeout_process`):

```python
    async def _segment_silence_timeout(self, segment_id: str, final_text: str) -> None:
        """Called after segment silence timeout - finish this segment.
        Next speech will start a new bubble.
        """
        await asyncio.sleep(self._segment_timeout_ms / 1000)

        # Save to finished segments
        if final_text.strip():
            self._finished_segments.append(final_text.strip())

        # Notify frontend segment ended
        if self._result_callback:
            self._result_callback(UserTranscriptSegmentEndMessage(
                message_id=segment_id
            ))

        # Clear current segment - next speech starts new bubble
        self._current_segment_id = None
```

- [ ] **Step 4: 修改_silence_timeout_process合并所有分段文本**

Modify line 149-164, update the method:

Original line 155: `final_text = self.streaming_asr.get_current_text().strip()`

Replace with:

```python
        # Combine all finished segments + any current ongoing segment
        final_parts = self._finished_segments.copy()
        if self.streaming_asr:
            current_text = self.streaming_asr.get_current_text().strip()
            if current_text:
                final_parts.append(current_text)

        final_text = " ".join(final_parts).strip()
        if not final_text:
            return
```

- [ ] **Step 5: 修改_stop_streaming_asr清空分段状态**

Modify line 175-184, add clearing of segment state:

```python
    async def _stop_streaming_asr(self) -> None:
        """Stop current streaming ASR session"""
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None
        if self._segment_silence_timer:
            self._segment_silence_timer.cancel()
            self._segment_silence_timer = None
        if self.streaming_asr:
            await self.streaming_asr.close()
            self.streaming_asr = None
        # Clear pending buffer and segment state for next connection
        self._pending_audio_buffer.clear()
        self._finished_segments.clear()
        self._current_segment_id = None
```

- [ ] **Step 6: 运行测试检查不破坏现有功能**

```bash
cd backend && python -m pytest tests/ -xvs
```

Expected: All existing tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/services/stream_processor.py
git commit -m "feat: add segment management to StreamProcessor"
```

---

## Task 3: 前端 - 添加TypeScript类型定义

**Files:**
- Modify: `frontend/shared/src/types.ts`

- [ ] **Step 1: 更新ServerMessage类型添加新消息**

Modify line 13-21, add new cases to `ServerMessage`:

```typescript
// Server -> Client messages
export type ServerMessage =
  | { type: 'user_transcript'; text: string } // ASR final result for user
  | { type: 'user_transcript_partial'; text: string } // Partial ASR result (streaming) - deprecated
  | { type: 'user_transcript_ongoing'; message_id: string; text: string } // Ongoing ASR segment (streaming bubble)
  | { type: 'user_transcript_segment_end'; message_id: string } // ASR segment finished
  | { type: 'model_start'; sessionId: string } // Model starts responding
  | { type: 'model_token'; token: string } // Streaming token from model
  | { type: 'model_audio'; data: string } // base64 encoded TTS audio
  | { type: 'model_end' } // Model finished responding
  | { type: 'pong' }
  | { type: 'error'; message: string };
```

- [ ] **Step 2: 验证TypeScript编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/shared/src/types.ts
git commit -m "feat: add types for user_transcript_ongoing messages"
```

---

## Task 4: 前端 - VideoCallPage修改消息处理逻辑

**Files:**
- Modify: `frontend/src/components/VideoCallPage.vue`

- [ ] **Step 1: 移除partialUserTranscript ref**

Line 136: `const partialUserTranscript = ref('');` → 移除这行。

- [ ] **Step 2: 添加handleUserTranscriptOngoing处理**

In `handleServerMessage` function (line 209-268), add new case:

```typescript
function handleServerMessage(message: ServerMessage) {
  switch (message.type) {
    case 'user_transcript_ongoing':
      // Real-time update of ongoing segment in conversation list
      const { message_id, text } = message;
      // Find if this segment already exists
      const existingIndex = conversationMessages.value.findIndex(
        m => m.id === message_id
      );
      if (existingIndex >= 0) {
        // Update existing bubble
        conversationMessages.value[existingIndex].text = text;
      } else {
        // Add new bubble for new segment
        conversationMessages.value.push({
          id: message_id,
          role: 'user',
          text: text,
          timestamp: Date.now()
        });
      }
      break;

    case 'user_transcript_segment_end':
      // Nothing to do - segment already ended, next will be new bubble
      break;

    case 'user_transcript_partial':
      // Deprecated - keep for backward compatibility temporarily
      // partialUserTranscript.value = message.text || '';
      break;
```

*(Keep the existing `user_transcript` case, it's still needed for the final LLM trigger)*

- [ ] **Step 3: 更新SubtitleDisplay组件属性**

Line 61 in template: `:partial-text="partialUserTranscript"` → 改为 `:partial-text="''"` (or remove prop and make optional default).

Actually, need to update SubtitleDisplay props to make partialText optional. Let's do that:

Modify `frontend/src/components/SubtitleDisplay.vue`, change:

```typescript
interface Props {
  messages: ConversationMessage[];
  cameraEnabled: boolean;
  partialText?: string;
}
```

And in template, the partial div becomes:

```html
<div v-if="partialText" class="flex justify-end mt-2">
```

Then in VideoCallPage.vue template, you can omit the prop or pass undefined.

- [ ] **Step 4: 移除对partialUserTranscript的所有引用**

Search the file for `partialUserTranscript` and remove dead code. The only references should be:
- Already removed from ref
- In `case 'user_transcript':` line 227: `partialUserTranscript.value = '';` → remove this line

- [ ] **Step 5: 更新aiOrbState计算属性**

Line 146: `if (partialUserTranscript.value)` → change to:

```typescript
// If we have any ongoing user message being transcribed, we're listening
const hasOngoingTranscript = conversationMessages.value.some(
  m => m.role === 'user' && Date.now() - m.timestamp < 2000
);
if (hasOngoingTranscript) {
  return "listening";
}
```

- [ ] **Step 6: 验证代码编译**

```bash
cd frontend && npm run lint
```

Expected: No lint errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/VideoCallPage.vue frontend/src/components/SubtitleDisplay.vue
git commit -m "feat: update frontend message handling for streaming bubbles"
```

---

## Task 5: 测试验证

**Files:**
- Test manually by running the application

- [ ] **Step 1: Start backend**

```bash
cd backend && uvicorn main:app --reload --port 8000
```

Expected: Backend starts successfully.

- [ ] **Step 2: Start frontend dev server**

```bash
cd frontend && npm run dev
```

Expected: Frontend starts successfully.

- [ ] **Step 3: Manual testing**

Test cases:
1. Open page, enable audio, start speaking → first bubble appears immediately, words increment (蹦字效果)
2. Pause for ~1 second → segment ends
3. Speak again → new bubble appears
4. Pause for ~2 seconds → LLM gets all segments combined, generates response
5. Verify response is correct with all text

- [ ] **Step 4: Commit if any fixes needed from testing**

If bugs found and fixed during testing, commit them.

---

## Self-Review

- ✅ Spec coverage: All requirements from design spec are covered (new messages, segment timeout, LLM timeout separation, real-time bubbles)
- ✅ No placeholders: All code changes shown, all commands exact
- ✅ Type consistency: Message types match between backend Pydantic and frontend TypeScript
- ✅ Bite-sized tasks: Each task is independent, can be committed separately
