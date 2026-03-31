# SeeWorldWeb 项目架构文档

## 1. 项目概述

SeeWorldWeb 是一个基于 AI 的实时音视频对话系统，结合了语音识别（ASR）、大语言模型（LLM）和文本转语音（TTS）技术，实现了自然的人机交互体验。项目支持多种 OAuth 登录方式，并提供了完整的前端界面和后端服务架构。

---

## 2. 整体目录结构

```
SeeWorldWeb/
├── backend/                 # FastAPI 后端服务
│   ├── api/                 # API 端点（认证、监控、WebSocket）
│   ├── services/            # 核心业务服务（LLM、ASR、TTS、OAuth）
│   ├── models/              # 数据模型和 schema 定义
│   ├── utils/               # 工具函数（日志、JWT、OpenAI 接口）
│   ├── storage/             # 存储模块
│   ├── tests/               # 测试代码
│   ├── data/                # 数据目录
│   ├── config.py            # 全局配置和设置
│   ├── main.py              # FastAPI 应用入口
│   ├── requirements.txt     # Python 依赖
│   └── .env.example         # 环境变量示例
├── frontend/                # Vue 3 + TypeScript 前端
│   ├── src/
│   │   ├── components/      # Vue 组件（登录、视频通话、控件）
│   │   ├── composables/     # Vue 组合式函数（音频、摄像头、WebSocket）
│   │   ├── stores/          # Pinia 状态管理（认证）
│   │   ├── router/          # Vue Router 配置
│   │   ├── utils/           # 工具函数
│   │   ├── styles/          # 全局样式
│   │   ├── App.vue          # 根组件
│   │   └── main.ts          # 应用入口
│   ├── shared/              # 共享类型和常量（前后端通用）
│   ├── public/              # 静态资源
│   ├── index.html           # HTML 模板
│   ├── package.json         # 依赖配置
│   ├── vite.config.ts       # Vite 配置
│   ├── vitest.config.ts     # Vitest 配置
│   └── tsconfig.json        # TypeScript 配置
├── docs/                    # 文档目录
├── logs/                    # 日志文件
└── CLAUDE.md                # 项目说明文档
```

---

## 3. 后端架构

### 3.1 核心技术栈
- **框架**: FastAPI（高性能异步 API 框架）
- **ASGI 服务器**: Uvicorn
- **认证**: JWT（JSON Web Token）+ OAuth 2.0（华为、微信）
- **实时通信**: WebSocket（双向通信）
- **API 文档**: 自动生成的 OpenAPI 文档
- **监控**: Prometheus + Grafana（内置指标）
- **日志**: Structlog（结构化日志）
- **环境管理**: Pydantic Settings（环境变量管理）

### 3.2 主要模块

#### 3.2.1 入口文件 (`main.py`)
```python
# 核心功能：
- 初始化 FastAPI 应用
- 配置 CORS 中间件
- 注册路由（认证、监控、WebSocket）
- 启用 Prometheus 指标收集
- 配置日志系统
```

**关键路由**:
- `GET /`: 健康检查和版本信息
- `GET /health`: 详细健康状态
- `GET /metrics`: Prometheus 监控指标
- `GET /auth/*`: OAuth 认证相关接口
- `WS /ws`: WebSocket 实时通信端点

#### 3.2.2 配置模块 (`config.py`)
```python
# 核心配置：
- 服务器设置（端口、主机、调试模式）
- CORS 配置（允许的来源）
- JWT 配置（密钥、算法）
- OAuth 提供商配置（华为、微信）
- 阿里云服务配置（ASR、TTS、LLM）
- 火山引擎配置（代码生成服务）
- 豆包 LLM 配置
```

**版本**: 1.0.0

#### 3.2.3 API 路由层 (`api/`)

**auth.py** - OAuth 认证接口
```python
- GET /auth/huawei: 重定向到华为 OAuth 登录页面
- GET /auth/huawei/callback: 华为 OAuth 回调处理
- GET /auth/wechat: 重定向到微信 OAuth 登录页面
- GET /auth/wechat/callback: 微信 OAuth 回调处理
```

**monitoring.py** - 监控和健康检查
```python
- GET /health: 返回详细的健康状态
- 包括系统信息、依赖状态检查
```

**websocket.py** - 实时通信端点
```python
- WS /ws: 处理音视频流的双向通信
- 支持音频流、摄像头帧、控制指令
- 支持访客模式（无 token）和认证模式
- 集成 StreamProcessor 处理媒体流
```

#### 3.2.4 服务层 (`services/`)

**StreamProcessor.py** - 媒体流处理核心
```python
功能：
- 管理对话状态
- 处理音频流（ASR）
- 处理摄像头帧（视觉上下文）
- 调度 LLM 处理和 TTS 合成
- 支持音频/摄像头/字幕的开关控制
- 会话历史管理（最多 50 条消息）

关键特性：
- 实时部分结果回调（用户可看到打字效果）
- 静默超时检测（2 秒无音频结束识别）
- 支持 Vision-LLM（图像 + 文本输入）
- TTS 合成与播放
```

**streaming_asr.py** - 阿里云实时 ASR
```python
功能：
- 与阿里云实时语音识别服务通信
- 流式识别音频数据
- 提供部分结果和最终结果回调
- 自动重连和错误处理

协议：WebSocket（Alibaba Cloud NLS）
采样率：16kHz
音频格式：PCM（16-bit 单声道）
```

**doubao_llm.py** - 豆包大语言模型
```python
功能：
- 与字节跳动豆包 LLM 通信
- 支持流式响应
- 处理多模态消息（文本 + 图像）
- 会话管理

接口：OpenAI 兼容的 API
```

**volcano_coding.py** - 火山引擎代码生成
```python
功能：
- 提供代码生成服务
- 支持流式响应
- 作为 LLM 替代方案（当配置了火山引擎时）
```

**tts.py** - 阿里云 TTS
```python
功能：
- 文本转语音合成
- 返回 MP3 格式音频
- 支持多语言和发音人配置
```

**huawei_oauth.py** - 华为 OAuth 2.0
**wechat_oauth.py** - 微信 OAuth 2.0
**Aliyun_token.py** - 阿里云服务令牌管理

#### 3.2.5 模型层 (`models/schemas.py`)

**数据类型定义**:
```python
# WebSocket 消息类型
- ClientMessage: 客户端 → 服务器（音频块、摄像头帧、控制指令）
- ServerMessage: 服务器 → 客户端（转录结果、模型响应、音频）

# 对话类型
- ConversationMessage: 历史消息
- UserTranscript/Partial: ASR 结果

# 认证类型
- UserInfo: 用户信息（ID、姓名、头像、提供商）
- JwtPayload: JWT 令牌载荷
- LoginResponse: 登录响应

# LLM 类型
- LLMMessage: LLM 消息（支持文本和图像）
- LLMContentPart: 内容部分（文本或图像）
- LLMCompletionRequest: 完成请求

# ASR/TTS 类型
- ASRResult: 语音识别结果
- TTSResult: 语音合成结果
```

#### 3.2.6 工具层 (`utils/`)

**logger.py** - 结构化日志系统
- 使用 Structlog 实现
- 支持上下文绑定
- 控制台和文件输出

**jwt.py** - JWT 令牌管理
- 创建和验证 JWT 令牌
- 支持过期时间和用户信息

**openai_stream.py** - OpenAI 接口封装
- 处理流式响应
- 支持 SSE（Server-Sent Events）

---

## 4. 前端架构

### 4.1 核心技术栈
- **框架**: Vue 3（Composition API）
- **语言**: TypeScript
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **测试**: Vitest + Vue Test Utils
- **通信**: WebSocket（ReconnectingWebSocket 模式）

### 4.2 主要目录结构

#### 4.2.1 组件层 (`components/`)

**VideoCallPage.vue** - 视频通话主页面
```vue
功能：
- 显示摄像头预览（可选）
- 控制音频/摄像头/字幕开关
- 显示实时字幕
- 管理 WebSocket 连接
- 显示机器人状态和连接信息
```

**LoginPage.vue** - 登录页面
```vue
功能：
- 提供 OAuth 登录按钮（华为、微信）
- 支持访客模式登录
- 处理 OAuth 回调和 token 管理
```

**AudioToggle.vue** - 音频开关控件
**CameraToggle.vue** - 摄像头开关控件
**CameraPreview.vue** - 摄像头预览组件
**SubtitleToggle.vue** - 字幕开关控件
**SubtitleDisplay.vue** - 字幕显示组件

#### 4.2.2 组合式函数 (`composables/`)

**use-websocket-client.ts** - WebSocket 客户端
```typescript
功能：
- 建立和管理 WebSocket 连接
- 自动重连机制（3 秒延迟）
- 心跳检测（30 秒间隔）
- 消息发送和接收处理
- 事件回调注册

API：
- connect(): WebSocket
- send(message: ClientMessage): void
- onMessage(handler): void
- offMessage(handler): void
- disconnect(): void
```

**use-audio-capture.ts** - 音频捕获
```typescript
功能：
- 访问用户麦克风
- 音频处理和重采样（浏览器采样率 → 16kHz）
- 音频编码（PCM → base64）
- 流式发送音频块（100ms 间隔）
- 支持暂停/恢复

参数：
- 目标采样率：16kHz（Alibaba ASR 要求）
- 缓冲大小：2048 样本
```

**use-camera-capture.ts** - 摄像头捕获
```typescript
功能：
- 访问用户摄像头
- 视频帧捕获和编码（JPEG）
- 控制帧率（1fps）
- 图像质量控制（0.8）
- 发送 base64 编码的帧数据
```

#### 4.2.3 状态管理 (`stores/auth.ts`)

```typescript
功能：
- 管理用户认证状态
- 存储 token 和用户信息
- 支持访客模式
- 本地存储持久化
- 提供 login/guest/logout 方法

状态：
- token: string | null
- user: UserInfo | null
- isGuest: boolean
- isAuthenticated: computed
```

#### 4.2.4 路由配置 (`router/index.ts`)

```typescript
路由：
- /login: 登录页面（无认证要求）
- /call: 视频通话页面（需要认证或访客模式）
- /: 根路由（自动重定向到 /call 或 /login）

守卫：
- 路由导航前检查认证状态
- 未认证用户重定向到登录页
```

---

## 5. 共享类型和配置

### 5.1 共享类型定义 (`frontend/shared/src/types.ts`)

```typescript
// WebSocket 消息类型（与后端 models/schemas.py 对应）
type ClientMessage = 
  | { type: 'audio_chunk'; data: string }      // 音频块（base64）
  | { type: 'camera_frame'; data: string }     // 摄像头帧（base64）
  | { type: 'toggle_audio'; enabled: boolean }
  | { type: 'toggle_camera'; enabled: boolean }
  | { type: 'toggle_subtitle'; enabled: boolean }
  | { type: 'ping' };

type ServerMessage = 
  | { type: 'user_transcript'; text: string }           // 最终转录结果
  | { type: 'user_transcript_partial'; text: string }   // 部分转录结果
  | { type: 'model_start'; sessionId: string }          // 模型开始响应
  | { type: 'model_token'; token: string }              // 模型流式响应
  | { type: 'model_audio'; data: string }                // TTS 音频（base64）
  | { type: 'model_end' }                               // 响应结束
  | { type: 'pong' }
  | { type: 'error'; message: string };

// 对话消息
interface ConversationMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: number;
}

// 用户信息
interface UserInfo {
  id: string;
  name: string;
  avatar?: string;
  provider: 'huawei' | 'wechat';
}
```

### 5.2 共享常量 (`frontend/shared/src/constants.ts`)

```typescript
// UI 默认状态
export const DEFAULT_AUDIO_ENABLED = false;
export const DEFAULT_CAMERA_ENABLED = false;
export const DEFAULT_SUBTITLE_ENABLED = false;

// 摄像头捕获设置
export const CAMERA_FRAME_INTERVAL_MS = 1000;      // 1fps
export const CAMERA_FRAME_QUALITY = 0.8;          // JPEG 质量
export const CAMERA_FRAME_MAX_WIDTH = 1280;        // 最大宽度

// 音频捕获设置
export const AUDIO_CHUNK_INTERVAL_MS = 100;        // 100ms 间隔
export const AUDIO_MIME_TYPE = 'audio/webm; codecs=opus';

// WebSocket 设置
export const WEBSOCKET_RECONNECT_DELAY_MS = 3000;  // 重连延迟
export const WEBSOCKET_PING_INTERVAL_MS = 30000;   // 心跳间隔

// LLM 设置
export const LLM_MAX_HISTORY = 20;                 // 最大历史消息数
```

---

## 6. 核心功能特性

### 6.1 实时音视频对话

**流程**:
```
用户语音 → 麦克风捕获 → 音频编码（PCM 16kHz）→ WebSocket 发送 → 
后端 ASR 识别 → 部分结果实时返回 → 静默检测 → 最终结果 → LLM 处理 →
TTS 合成 → 音频返回 → 前端播放
```

**关键特性**:
- 实时部分结果显示（打字效果）
- 静默超时检测（2 秒无音频结束识别）
- 字幕显示（可选）
- 音频/摄像头/字幕开关控制

### 6.2 多模态交互

**支持的输入**:
- 语音（ASR）
- 图像（摄像头捕获）
- 文本（未来支持）

**LLM 处理**:
```python
# 构建多模态消息
messages = [
    SystemPrompt(),
    UserMessage(
        content=[
            TextPart("描述这个图片"),
            ImagePart(base64_data)
        ]
    )
]
```

### 6.3 认证系统

**支持的登录方式**:
1. **华为 OAuth 2.0**: 完整的 OAuth 流程
2. **微信 OAuth 2.0**: 完整的 OAuth 流程  
3. **访客模式**: 无需认证，直接使用

**认证流程**:
```
1. 用户选择登录方式
2. 重定向到 OAuth 提供商
3. 用户授权后回调
4. 获取用户信息
5. 生成 JWT 令牌
6. 前端存储 token 和用户信息（localStorage）
7. 后续请求携带 token（WebSocket 查询参数）
```

**JWT 令牌**:
```python
# 结构
{
  "userId": "user123",
  "userName": "张三",
  "provider": "huawei",
  "iat": 1234567890,
  "exp": 1234567890 + 7 * 24 * 3600  # 7 天有效期
}
```

### 6.4 会话管理

**特性**:
- 每个 WebSocket 连接创建一个会话
- 会话历史最多保留 50 条消息
- 支持跨设备登录（token 存储在 localStorage）
- 会话超时和自动重连

---

## 7. API 端点和 WebSocket 交互

### 7.1 HTTP API 端点

**认证相关**:
- `GET /auth/huawei`: 重定向到华为登录页面
- `GET /auth/huawei/callback?code=<code>`: 华为 OAuth 回调
- `GET /auth/wechat`: 重定向到微信登录页面
- `GET /auth/wechat/callback?code=<code>`: 微信 OAuth 回调

**监控相关**:
- `GET /`: 返回服务状态和版本
- `GET /health`: 详细健康检查
- `GET /metrics`: Prometheus 监控指标

### 7.2 WebSocket 端点

**地址**: `ws://<host>:<port>/ws?token=<jwt_token>`

**消息类型**:

**客户端 → 服务器**:
```typescript
// 音频块
{
  type: 'audio_chunk',
  data: 'base64_encoded_pcm'
}

// 摄像头帧
{
  type: 'camera_frame',
  data: 'base64_encoded_jpeg'
}

// 控制指令
{
  type: 'toggle_audio',
  enabled: true
}

{
  type: 'toggle_camera',
  enabled: false
}

{
  type: 'toggle_subtitle',
  enabled: true
}

// 心跳
{
  type: 'ping'
}
```

**服务器 → 客户端**:
```typescript
// 最终转录结果
{
  type: 'user_transcript',
  text: '你好，我想了解这个功能'
}

// 部分转录结果（实时）
{
  type: 'user_transcript_partial',
  text: '你好，我'
}

// 模型开始响应
{
  type: 'model_start',
  sessionId: '12345'
}

// 模型流式响应
{
  type: 'model_token',
  token: '你'
}

// TTS 音频
{
  type: 'model_audio',
  data: 'base64_encoded_mp3'
}

// 响应结束
{
  type: 'model_end'
}

// 心跳响应
{
  type: 'pong'
}

// 错误
{
  type: 'error',
  message: '无效的消息类型'
}
```

---

## 8. 关键依赖

### 8.1 后端依赖 (requirements.txt)
```
fastapi                    # API 框架
uvicorn[standard]          # ASGI 服务器
python-multipart           # 表单处理
pydantic[email]            # 数据验证
pyjwt                      # JWT 处理
httpx                      # HTTP 客户端
python-dotenv              # 环境变量
pydantic-settings          # 配置管理
websockets                 # WebSocket 支持
pytest                     # 测试框架
pytest-asyncio             # 异步测试
structlog                  # 日志系统
prometheus-fastapi-instrumentator  # Prometheus 指标
```

### 8.2 前端依赖 (package.json)
```json
{
  "dependencies": {
    "vue": "^3.4.19",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.7"
  }
}
```

---

## 9. 部署和运行

### 9.1 后端启动
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 文件，填入配置信息
uvicorn main:app --reload --port 8000
```

### 9.2 前端启动
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### 9.3 环境变量配置

**必需变量**:
```env
# JWT 密钥（生产环境必须修改）
JWT_SECRET=your-secret-key-change-in-production

# OAuth 配置
HUAWEI_CLIENT_ID=your-huawei-client-id
HUAWEI_CLIENT_SECRET=your-huawei-client-secret
HUAWEI_REDIRECT_URI=http://localhost:8000/auth/huawei/callback

WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
WECHAT_REDIRECT_URI=http://localhost:8000/auth/wechat/callback

# 阿里云服务
ALIBABA_ASR_APPKEY=your-alibaba-asr-appkey
ALIBABA_ASR_TOKEN=your-alibaba-asr-token

ALIBABA_TTS_APPKEY=your-alibaba-tts-appkey
ALIBABA_TTS_TOKEN=your-alibaba-tts-token

# 豆包 LLM
DOUBAO_API_KEY=your-doubao-api-key
DOUBAO_ENDPOINT=https://aquasearch.doubao.com/api/v1/chat/completions

# 火山引擎
VOLCANO_ACCESS_KEY=your-volcano-access-key
VOLCANO_SECRET_KEY=your-volcano-secret-key
VOLCANO_REGION=cn-beijing
```

---

## 10. 监控和日志

### 10.1 Prometheus 指标
- `/metrics`: 暴露 Prometheus 格式的指标
- 包括请求计数、响应时间、WebSocket 连接数等

### 10.2 日志
- 存储位置: `./logs/`
- 格式: JSON（结构化）
- 级别: INFO, WARNING, ERROR, DEBUG
- 包含请求 ID、会话 ID、用户信息等上下文

---

## 11. 测试

### 11.1 后端测试
```bash
cd backend
pytest tests/ -v
```

### 11.2 前端测试
```bash
cd frontend
npm run test
```

---

## 12. 未来改进建议

1. **安全性增强**:
   - 实现 refresh token 机制
   - 增加 rate limiting
   - 改进 CORS 配置

2. **性能优化**:
   - 音频压缩（Opus 编码）
   - 图像压缩（WebP 格式）
   - 消息批处理

3. **功能扩展**:
   - 支持文本输入
   - 支持文件上传
   - 支持多语言
   - 支持对话历史记录

4. **可靠性**:
   - 更强大的重连机制
   - 消息确认和重试
   - 服务降级策略

---

## 总结

SeeWorldWeb 是一个架构完整、功能强大的 AI 音视频对话系统。它采用了现代的技术栈，结合了多个云服务提供商的 API，提供了自然的人机交互体验。项目代码结构清晰，模块职责明确，易于扩展和维护。
