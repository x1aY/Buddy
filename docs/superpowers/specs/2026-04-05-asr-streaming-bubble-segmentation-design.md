# ASR 流式识别气泡分段设计

## 问题背景

当前阿里云实时流式ASR识别结果都直接返回前端，但是：
- 识别过程中结果只显示在临时半透明气泡中
- 需要等到静音超时（2秒）结束后才会创建正式气泡
- 用户体验不够流畅，不能看到文字实时在正式气泡中"蹦出"
- 用户希望：实现不断蹦字效果，一段时间没说话之后，自动另起一个新气泡表示新的识别结果

## 设计目标

1. 实现"蹦字"效果：说话开始就创建正式气泡，识别文字实时更新
2. 自动分段：用户停顿一段时间后自动结束当前气泡，再次说话自动开始新气泡
3. 分离两个超时概念：
   - **分段超时**: 判断何时开启新气泡（较短，如700ms）
   - **LLM处理超时**: 判断何时将完整文本交给LLM处理（保持现有2秒）

## 方案选择

选择 **方案B：前后端协同**：
- 后端新增消息类型维护分段状态
- 分段超时和LLM超时分离配置
- 协议清晰，易于维护

## 详细设计

### 新增消息类型

#### 1. `UserTranscriptOngoing` (服务端 → 客户端)
正在进行中的识别结果，用于实时更新当前气泡文字。

**后端 schema**:
```python
class UserTranscriptOngoingMessage(BaseModel):
    type: Literal['user_transcript_ongoing'] = 'user_transcript_ongoing'
    message_id: str  # 当前分段的唯一ID
    text: str        # 当前分段完整识别文本
```

**前端 TypeScript**:
```typescript
| { type: 'user_transcript_ongoing'; message_id: string; text: string }
```

#### 2. `UserTranscriptSegmentEnd` (服务端 → 客户端)
通知客户端当前分段已结束。

**后端 schema**:
```python
class UserTranscriptSegmentEndMessage(BaseModel):
    type: Literal['user_transcript_segment_end'] = 'user_transcript_segment_end'
    message_id: str  # 结束的分段ID
```

**前端 TypeScript**:
```typescript
| { type: 'user_transcript_segment_end'; message_id: string }
```

### 后端状态管理 (`StreamProcessor`)

新增成员变量:

```python
# Streaming ASR segmentation
_current_segment_id: Optional[str] = None
_segment_silence_timer: Optional[asyncio.Task] = None
_segment_timeout_ms: int = 700  # 分段超时毫秒数
_finished_segments: List[str] = []  # 已完成分段文本
```

### 处理流程

1. **音频块到达**:
   - 重置分段静音定时器
   - 如果没有当前分段ID → 创建新分段ID

2. **ASR partial 结果回调**:
   - 更新当前分段文本
   - 发送 `user_transcript_ongoing` 消息给前端
   - 前端：如果message_id存在则更新文本，不存在则新增气泡到conversationMessages

3. **分段超时触发** (700ms无新音频):
   - 将当前分段文本添加到 `_finished_segments`
   - 发送 `user_transcript_segment_end` 给前端
   - 清空 `_current_segment_id`

4. **LLM 超时触发** (2000ms无新音频，原有逻辑):
   - 合并 `_finished_segments` + 当前分段文本（如果存在）得到完整用户输入
   - 清空所有分段状态
   - 送入LLM处理流程

### 可配置参数

| 参数 | 默认值 | 说明 |
|-----|--------|------|
| `_segment_timeout_ms` | 700ms | 分段超时：多久没说话开启新气泡 |
| `_silence_timeout_ms` (原有) | 2000ms | LLM处理超时：多久没说话交给LLM处理 |

### 文件修改清单

**后端**:
1. `backend/models/schemas.py` - 新增两个消息类型，加入ServerMessage union
2. `backend/services/stream_processor.py` - 添加分段状态管理，修改on_partial回调处理

**前端**:
1. `frontend/shared/src/types.ts` - 新增TypeScript类型定义
2. `frontend/src/components/VideoCallPage.vue` - 修改消息处理逻辑，不再使用 `partialUserTranscript`，改为直接在 `conversationMessages` 中更新正在进行的分段

**不需要修改**:
- `backend/api/websocket.py` - 已有泛化消息处理，不需要改
- `frontend/src/components/SubtitleDisplay.vue` - 已遍历 `messages`，不需要改

## 兼容性

- 新增消息类型不影响现有协议
- 原有 `user_transcript_partial` 和 `user_transcript` 可以保留兼容（或者废弃，看实现选择）
- 本设计选择：替换原有partial处理方式，移除不再使用的代码

## 测试点

1. 短时间说话 → 一个气泡，文字蹦出 → 分段结束 → 再说话 → 新气泡
2. 连续不停说话 → 一个气泡持续更新，直到停顿超过700ms才结束
3. 停顿300ms继续说 → 同一个气泡（不触发分段超时）
4. 停顿800ms → 分段结束，继续说话新开气泡
5. 停顿2秒 → 所有分段合并送给LLM
6. 验证LLM能正确得到完整对话文本
