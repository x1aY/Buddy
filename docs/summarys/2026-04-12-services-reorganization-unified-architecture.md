# 服务目录重构总结 - 统一架构改造

## 完成时间
2026-04-12

## 重构背景
原始 `backend/services/` 目录下文件过多，都是扁平存放，没有按功能分组，不利于维护和扩展。需要：
1. 按功能分组整理
2. 对 LLM 和语音模块都应用统一的架构模式（抽象基类 + 工厂 + 提供者）
3. 上层只依赖抽象，不依赖具体实现，便于后续添加新提供者

## 重构内容

### 1. 新目录结构
```
backend/services/
├── __init__.py          # 保持向后兼容，重新导出所有类
├── llm/                 # 大语言模型模块
│   ├── __init__.py
│   ├── base.py          # BaseLLMService 抽象基类
│   ├── factory.py       # 统一 LLM 工厂
│   ├── pipeline.py      # LlmPipeline 工具调用循环
│   ├── conversation_history.py  # 对话历史管理
│   ├── embedding.py     # Embedding 服务
│   └── providers/       # 具体 LLM 实现
│       ├── __init__.py
│       ├── anthropic.py
│       ├── openai.py
│       └── volcengine.py
├── speech/              # 语音处理模块 (ASR + TTS)
│   ├── __init__.py
│   ├── base.py          # BaseASRService, BaseTTSService 抽象基类
│   ├── factory.py       # ASR/TTS 统一工厂
│   ├── asr_stream_processor.py  # ASR 流式处理
│   └── providers/       # 具体语音实现
│       ├── __init__.py
│       ├── aliyun_token.py
│       ├── aliyun_asr.py
│       ├── aliyun_tts.py
│       └── aliyun_streaming_asr.py
├── auth/                # 第三方 OAuth 认证
│   ├── __init__.py
│   ├── huawei_oauth.py
│   └── wechat_oauth.py
└── chat_session.py      # 原名 stream_processor.py - WebSocket 会话协调器
```

### 2. 统一架构模式
**所有功能模块都遵循相同的架构模式：**
1. **抽象基类** (`base.py`) - 定义统一接口
2. **工厂** (`factory.py`) - 根据环境配置自动选择已配置的实现
3. **提供者** (`providers/`) - 具体实现，每个提供者一个文件

优点：
- 添加新实现只需要添加新文件，不需要修改上层代码
- 上层调用方只依赖抽象，不关心具体是哪个厂商
- 符合依赖倒置原则 (DIP)

### 3. 关键改动

| 原始文件 | 新位置 | 说明 |
|---------|--------|------|
| `stream_processor.py` | `chat_session.py` | 重命名，更准确反映其作用：协调整个聊天会话（文本 + 音频流 + 摄像头） |
| `anthropic_llm.py` | `llm/providers/anthropic.py` | LLM 提供者移到子目录 |
| `openai_llm.py` | `llm/providers/openai.py` | LLM 提供者移到子目录 |
| `volcengine_llm.py` | `llm/providers/volcengine.py` | LLM 提供者移到子目录 |
| `asr.py` | `speech/providers/aliyun_asr.py` | 重命名 + 继承 BaseASRService |
| `tts.py` | `speech/providers/aliyun_tts.py` | 重命名 + 继承 BaseTTSService |
| `Aliyun_token.py` | `speech/providers/aliyun_token.py` | 小写命名，只有阿里云实现使用，放在 providers 内 |
| `huawei_oauth.py` | `auth/huawei_oauth.py` | 分组到认证模块 |
| `wechat_oauth.py` | `auth/wechat_oauth.py` | 分组到认证模块 |

### 4. 向后兼容
- `services/__init__.py` 保留了所有原始导出
- 现有导入方式 `from services import XXX` 继续正常工作
- 同时也支持新的分组导入 `from services.llm import BaseLLMService`

## 验证
- 全部 81 个测试通过 ✔
- 功能完全保留，没有破坏性变更
- 流式响应、工具调用、ASR 流式识别都正常工作

## 经验总结
1. **保持向后兼容非常重要** - 通过重新导出可以让现有代码不中断
2. **相同架构模式应用到多个模块** - 让项目更一致，容易理解
3. **重命名要更新所有引用** - 特别是测试文件中的 patch 路径
4. **逐步迁移 + 持续测试** - 每一步都运行测试确保不引入 bug

## 后续可扩展性
现在添加新的 LLM 提供者只需要：
1. 在 `llm/providers/` 添加新文件，继承 `BaseLLMService`
2. 在 `llm/factory.py` 添加选择逻辑
3. 不需要修改任何上层代码

添加新的 ASR/TTS 提供者同理。
