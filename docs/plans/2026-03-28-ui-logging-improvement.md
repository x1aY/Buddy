# 实现计划：UI 美化与数据传输日志增强

## Context

当前项目存在三个需要改进的问题：
1. **前端页面中心机器人图标**：设计老旧不够美观，需要替换，并且需要在开启摄像头或开启字幕时自动隐藏
2. **页面图标**：当前使用 Unicode 表情符号，显示效果不一致，缺乏科技感和简约风格
3. **数据传输日志**：音频数据和摄像头预览流数据传输时，日志中没有记录传输情况，不利于调试

本计划解决这三个问题，保持项目原有的简约架构（不引入额外依赖）。

## 问题 1：机器人图标替换和自动隐藏

### 解决方案
- 修改显示条件：只有当「摄像头关闭 **AND** 字幕关闭」时才显示
- 替换为新设计的简约科技风格 SVG 图标
- 不引入额外依赖，保持 SVG 矢量格式

### 需要修改的文件
1. [`frontend/public/robot-icon.svg`](../../frontend/public/robot-icon.svg) - 替换图标内容
2. [`frontend/src/components/VideoCallPage.vue`](../../frontend/src/components/VideoCallPage.vue) - 修改显示条件（第 18 行）

### 实现步骤
1. 在 `VideoCallPage.vue` 中，将 `v-if="!subtitleEnabled"` 改为 `v-if="!subtitleEnabled && !cameraEnabled"`
2. 用新设计的 SVG 替换现有 `robot-icon.svg` 内容：
   - 保持 200x200 viewBox 尺寸不变
   - 采用渐变色+简约线条设计，增加科技感
   - 参考设计：神经网络灵感的圆形背景+简约机器人轮廓

### 验证方法
| 状态 | 预期结果 |
|------|----------|
| 摄像头关闭 && 字幕关闭 | 机器人图标显示 |
| 摄像头开启 && 字幕关闭 | 机器人图标隐藏 |
| 摄像头关闭 && 字幕开启 | 机器人图标隐藏 |
| 摄像头开启 && 字幕开启 | 机器人图标隐藏 |

---

## 问题 2：页面图标科技感简约化改造

### 解决方案
- **方案选择**：使用内联 SVG 图标替换现有的 Unicode 表情符号
- **原因**：不引入任何外部图标库依赖，保持项目简约架构；SVG 体积小，显示一致，可精确控制样式

### 需要修改的文件
| 文件路径 | 需要替换图标数量 |
|----------|-----------------|
| [`frontend/src/components/LoginPage.vue`](../../frontend/src/components/LoginPage.vue) | 3 个（手机、对话气泡、访客） |
| [`frontend/src/components/AudioToggle.vue`](../../frontend/src/components/AudioToggle.vue) | 2 个（音量开/关） |
| [`frontend/src/components/CameraToggle.vue`](../../frontend/src/components/CameraToggle.vue) | 2 个（摄像头开/关） |
| [`frontend/src/components/SubtitleToggle.vue`](../../frontend/src/components/SubtitleToggle.vue) | 2 个（字幕开/关） |
| [`frontend/src/components/VideoCallPage.vue`](../../frontend/src/components/VideoCallPage.vue) | 1 个（退出登录） |

**总计：10 个图标，5 个文件**

### 实现步骤
1. 对每个组件，将 emoji 替换为内联 SVG 图标
2. 使用 `fill="currentColor"` 让图标自动继承父元素文字颜色，保持原有配色方案
3. 保持现有 CSS `.icon` 类不变，图标尺寸自适应
4. 每个图标设计为 24x24 viewBox，简约线条风格

**图标替换清单：**
- `AudioToggle`：🔊 → 扬声器 SVG；🔇 → 扬声器加斜杠 SVG
- `CameraToggle`：📹 → 摄像机 SVG；🚫 → 摄像机加斜杠 SVG
- `SubtitleToggle`：📖 → 字幕文本 SVG；📝 → 关闭字幕 SVG
- `LoginPage`：📱 → 手机 SVG；💬 → 对话气泡 SVG；👁️ → 访客眼睛 SVG
- `VideoCallPage`：🚪 → 退出登出 SVG

### 验证方法
- 所有页面所有按钮图标显示正常
- 图标颜色正确继承按钮的不同状态颜色（开启/关闭）
- 在不同浏览器显示一致（相比 emoji 改进）
- 点击功能正常，图标不影响交互

---

## 问题 3：数据传输日志增强

### 解决方案
- **后端**：在 `websocket.py` 中使用现有的 `structlog` 记录接收到的数据
- **前端**：在发送数据时添加采样日志，避免日志刷屏
- **原因**：复用现有日志基础设施，不改变架构；采用限流策略避免日志爆炸

### 需要修改的文件
**后端：**
1. [`backend/api/websocket.py`](../../backend/api/websocket.py) - 添加接收数据日志

**前端：**
2. [`frontend/src/composables/use-audio-capture.ts`](../../frontend/src/composables/use-audio-capture.ts) - 添加音频发送采样日志
3. [`frontend/src/composables/use-camera-capture.ts`](../../frontend/src/composables/use-camera-capture.ts) - 添加摄像头帧发送日志

### 实现步骤

**后端：**
1. 在文件顶部导入 `get_logger` 创建 `logger`
2. 在处理 `audio_chunk` 消息时添加日志：`logger.info("audio_chunk_received", data_length=len(msg.data))`
3. 在处理 `camera_frame` 消息时添加日志：`logger.info("camera_frame_received", data_length=len(msg.data))`

**前端：**
1. `use-audio-capture.ts`：添加计数器，每 10 个 chunk 记录一次日志，避免刷屏
   ```typescript
   audioChunkCounter++;
   if (audioChunkCounter % LOG_INTERVAL === 0) {
     console.log(`[Audio] Sent ${audioChunkCounter} chunks total, last chunk size: ${base64.length} bytes`);
   }
   ```

2. `use-camera-capture.ts`：摄像头默认 1fps，每一帧发送后记录日志
   ```typescript
   console.log(`[Camera] Sent frame, size: ${base64.length} bytes`);
   ```

### 验证方法
**后端：**
- 启动后查看控制台和 `logs/app.log` 文件
- 开启音频说话，确认日志出现 `audio_chunk_received`
- 开启摄像头，确认日志出现 `camera_frame_received`
- 检查日志为结构化 JSON，包含 `data_length` 字段

**前端：**
- 打开浏览器控制台
- 开启音频，确认每 N 个 chunk 输出一条日志
- 开启摄像头，确认每秒输出一条日志
- 确认不会过度刷屏

---

## 实施顺序

1. **问题 1** - 改动最小，先做容易验证
2. **问题 2** - 多处图标替换，纯 UI 改动
3. **问题 3** - 日志功能，不影响显示，最后做

## 影响评估

| 问题 | 文件修改数 | 风险 | 依赖变化 |
|------|------------|------|----------|
| 问题 1 | 2 | 低 | 无 |
| 问题 2 | 5 | 低 | 无（不引入新依赖） |
| 问题 3 | 3 | 低 | 无（复用现有日志） |
| **总计** | **10 个文件** | **低** | **无新增依赖** |

总改动约 150 行代码，不影响项目原有简约架构，保持零额外图标库/CSS 框架依赖。

## 验收标准

1. ✓ 机器人图标美观，且在摄像头或字幕开启时正确隐藏
2. ✓ 所有图标风格统一，简约有科技感，显示一致
3. ✓ 音频和摄像头数据传输时，前后端日志都有记录
4. ✓ 不引入任何新的外部依赖
5. ✓ 原有功能全部正常工作
