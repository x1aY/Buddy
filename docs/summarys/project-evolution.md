# 项目演进总结 - Buddy 全栈AI对话系统

## 项目概述

Buddy 是一个**基于大语言模型的多模态实时对话系统**。用户可以通过摄像头和麦克风与AI面对面交流，AI能够"看见"你展示的东西，听懂你说的话，并且可以联网搜索实时信息，用语音回复你。这本质上是一个移动端AI助手的Web原型。

**技术栈：**
- 后端: Python FastAPI + Uvicorn + WebSocket
- 前端: Vue 3 + TypeScript + Vite + Pinia + TailwindCSS
- AI 服务: 阿里云 ASR/TTS + 多LLM提供商支持 (Anthropic Claude / OpenAI / 火山引擎豆包)
- 认证: JWT + OAuth 2.0 (华为/微信) + 访客模式
- 监控: Prometheus
- 日志: Structlog 结构化日志

---

## 开发演进时间线

### 2026-03-28: UI 美化与数据传输日志增强

#### 完成内容
1. **机器人图标替换和自动隐藏**
   - 替换为新设计渐变色简约线条SVG
   - 仅当摄像头关闭 AND 字幕关闭时显示，开启任一功能自动隐藏

2. **页面图标科技感简约化改造**
   - 5个组件共10个图标从Unicode表情替换为内联SVG
   - 使用 `fill="currentColor"` 自动继承颜色
   - **不引入任何外部依赖**，保持项目简约架构

3. **数据传输日志增强**
   - 后端结构化日志记录音频和摄像头数据接收
   - 前端使用日志采样（音频每10个chunk记录一次），避免日志刷屏

**经验：** SVG适合少量定制图标，不引入图标库；高频数据传输需要日志采样。

---

### 2026-03-31: 项目架构探索

成功完成了全面架构探索，生成了完整的[架构文档](../architecture/architecture.md)。

**架构优势：**
1. **代码组织清晰** - 后端分层，前端组件化+组合式函数
2. **前后端类型一致** - 共享类型定义在 `frontend/shared/`
3. **实时交互设计合理** - WebSocket全双工，ASR支持部分结果，LLM流式响应
4. **可靠性设计** - WebSocket自动重连，心跳检测，静默检测
5. **可观测性** - Prometheus指标 + 结构化日志 + 健康检查

**后续建议：** 保持模块化架构，新增LLM/ASR/TTS提供商遵循现有模式。

---

### 2026-03-31: 阿里云实时语音识别demo修复

**问题：** 分步操作导致连接建立后空闲超时断开
```
Gateway:IDLE_TIMEOUT:Websocket session is idle for too long time
```

**解决方案：** 调整执行顺序，完全消除空闲时间：
```
用户点击 → 获取麦克风权限 → 建立连接 → 立即发送StartTranscription → 立即发送音频
```
这样间隔 < 100ms，从根源解决问题。

**经验：** 阿里云对WebSocket空闲超时限制严格，连接建立后必须尽快发送数据。

---

### 2026-04-01: 双文件日志系统实现

**需求：** 原单一日志太乱，分离完整日志和关键日志。

**实现方案：** Python logging 标准库多handler + 过滤器
- `logs/log_full.log`: JSON结构化，DEBUG+，每周轮转保留1周
- `logs/log_main.log`: 纯文本人类可读，INFO+，每周轮转保留2周

**关键日志过滤：** 连接状态变化、ASR状态、Token过期、数据统计、开关事件、WARNING+自动保留

**增强改进：** 自动将布尔 `enabled` 转换为"开启/关闭"中文文字，便于阅读。

---

### 2026-04-01: 流式ASR效率评审

对 `streaming_asr.py` 效率评审：
- **发现：** 每个消息都在WARNING级别记录完整数据 → 生产日志过大（中等问题）
- **总体：** 设计高效，正确的双缓冲解决竞争，全程异步，职责分离清晰

---

### 2026-04-05: 从 SeeWorldUI 移植完整UI到前端

**任务：** 将全新UI设计从 React 移植到 Vue 3，全换Tailwind CSS，保留所有业务逻辑。

**完成内容：**
1. 安装 Tailwind CSS v3（v4有兼容性问题降级）
2. 新增 `AIOrb.vue` 动态AI状态球体（三种状态动画）
3. 完全重写 `LoginPage.vue` 和 `VideoCallPage.vue`
4. 后续简化：抽取 `BaseToggleButton.vue` 消除重复，统一使用 `lucide-vue-next`

**经验教训：**
- 优先选稳定版本，减少兼容性问题
- Vue scoped样式中定义的类名不能用在template元素上
- Vue模板不要用 `条件 && 文本` 写法，会输出布尔值

---

### 2026-04-12: 服务目录重构 - 统一架构改造

**背景：** 扁平目录不利于维护，按功能分组，统一架构模式。

**新目录结构：**
```
backend/services/
├── __init__.py          # 向后兼容重新导出
├── llm/                 # 大语言模型模块
│   ├── base.py          # BaseLLMService 抽象基类
│   ├── factory.py       # 统一 LLM 工厂
│   ├── pipeline.py      # LlmPipeline 工具调用循环
│   └── providers/       # 具体 LLM 实现
├── speech/              # 语音处理模块 (ASR + TTS)
│   ├── base.py          # 抽象基类
│   ├── factory.py       # ASR/TTS 统一工厂
│   ├── asr_stream_processor.py  # ASR 流式处理
│   └── providers/       # 具体语音实现
├── auth/                # 第三方 OAuth 认证
└── chat_session.py      # 原名 stream_processor.py - WebSocket 会话协调器
```

**统一架构模式：** 抽象基类 + 工厂 + 提供者
- 添加新实现不需要修改上层代码
- 符合依赖倒置原则
- 通过重新导出保持向后兼容

**验证：** 全部81个测试通过。

---

### 2026-04-16: 项目重命名 SeeWorldWeb → Buddy

- 全文搜索确认无残留
- 修改网页标题、登录页标题
- 修复 tsconfig 添加 `@buddy/shared` 路径映射
- 重新安装依赖
- 前后端都能正常启动

---

## 关键架构原则总结

1. **模块化** - 每个模块职责单一，上层依赖抽象不依赖具体实现
2. **类型安全** - 后端Pydantic + 前端TypeScript，减少运行时错误
3. **可扩展** - 添加新LLM/ASR提供者只需要加新文件，不需要改上层
4. **可观测** - 结构化日志分离 + Prometheus指标，便于问题定位
5. **向后兼容** - 重构通过重新导出保持兼容，不中断现有代码
