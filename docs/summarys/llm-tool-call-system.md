# LLM 工具调用系统开发总结

## 架构概述

Buddy 使用**统一LLM架构**，支持多种LLM提供商，完整实现了ReAct-style工具调用循环，允许LLM在对话过程中调用工具获取实时信息（如联网搜索）。

### 统一架构设计

#### 核心组件

**`base.py` - `BaseLLMService` 抽象基类**  
定义统一接口，所有LLM提供商必须实现：
```python
- is_configured() -> bool
- chat_stream(messages: List[LLMMessage], tools: Optional[List[ToolDefinition]]) -> AsyncGenerator[str, None]
```

**`factory.py` - 统一LLM工厂**  
根据环境配置自动选择LLM服务，选择优先级：  
**VolcEngine (if configured) → Anthropic → OpenAI**

**`pipeline.py` - `LlmPipeline` 工具调用循环**  
管理完整的工具调用闭环：
1. 调用LLM，带上工具定义和对话上下文
2. 如果LLM返回纯文本，结束循环，输出结果
3. 如果LLM返回工具调用，执行工具获取结果
4. 将工具结果添加到对话上下文
5. 重复调用LLM，直到LLM给出最终答案或达到最大迭代次数（5次）

#### 支持的提供商

| 提供商 | 文件 | 协议 | 工具调用支持 |
|--------|------|------|-------------|
| Anthropic Claude | `llm/providers/anthropic.py` | Anthropic Messages API | ✅ 原生支持 |
| OpenAI / 豆包 | `llm/providers/openai.py` | OpenAI Chat Completions API | ✅ 流式解析支持 |
| 火山引擎 | `llm/providers/volcengine.py` | Anthropic 兼容协议 | ✅ 完整支持 |

---

## 开发迭代总结

### LLM Pipeline 检查与修复

#### 第一轮检查发现的问题
1. **消息格式不规范** - 工具调用时消息格式不符合LLM服务要求
2. **循环逻辑缺陷** - 多工具调用后上下文维护不正确
3. **OpenAI流解析鲁棒性不足** - 缺少异常处理
4. **测试覆盖不完整** - 缺少端到端完整循环测试

#### 修复后验证
所有问题已修复，实现完全符合需求：
- ✅ 完整工具调用循环，最大5次迭代保护
- ✅ 正确构建LLM消息
- ✅ 正确处理文本响应和工具调用
- ✅ 正确执行工具调用并维护上下文
- ✅ 所有17个LLM Pipeline测试通过
- ✅ 全部81个后端测试通过

---

### Anthropic LLM 工具调用实现

#### 主要功能
1. **接受工具参数** - `chat_stream` 添加 `tools` 可选参数，保持向后兼容
2. **格式转换** - 内部 `ToolDefinition` → Anthropic 格式
3. **流式解析** - 检测 `tool_use` 事件，累积工具输入，输出 `[TOOL_CALL]:{json}`
4. **保持兼容** - 无工具时保持原有纯文本流式行为

**测试覆盖：** 6个测试全部通过。

---

### OpenAI LLM 工具调用实现验证

| 需求 | 状态 |
|------|------|
| 添加 `tools` 可选参数 | ✅ 已实现 |
| 内部格式转OpenAI格式 | ✅ 已实现 |
| 请求中包含工具 | ✅ 已实现 |
| 扩展流解析器检测工具调用 | ✅ 已实现 |
| 生成标准 `[TOOL_CALL]:{json}` 格式 | ✅ 已实现 |
| 保持向后兼容 | ✅ 已实现 |
| 完整测试覆盖 | ✅ 5个测试全部通过 |

**额外优化：** 支持多模态图片输入、完整异常处理、分块参数累积解析。

---

### 火山引擎支持集成

1. 在 `config.py` 添加三个配置项
2. 创建 `VolcengineLLMService` 实现 `BaseLLMService`
3. 在工厂添加选择逻辑
4. 更新 `llm_pipeline.py` 接受统一接口

**验证：** 所有测试通过，功能完整保留。

---

### Open-WebSearch MCP 配置检查

验证项目已正确实现 `open-websearch` 配置：
- ✅ `config.py` 已包含三个配置项
- ✅ `.env.example` 已添加文档
- ✅ SPECS 合规

---

## 工具调用循环设计

```
用户语音 → ASR识别 → 文本用户消息 → LlmPipeline
                                     ↓
                              调用LLM（带工具定义）
                                     ↓
                        ↙是否有工具调用?↘
                     是                否
                     ↓                ↓
              执行工具获取结果       输出文本给用户
              将结果添加到上下文
                     ↓
                 重复调用LLM
```

**关键设计：**
- 最大迭代5次防止无限循环
- `working_messages` 保存当前轮次中间消息
- 工具调用以 `[TOOL_CALL]:{json}` 格式输出

---

## 经验总结

1. **适配层设计解决协议不兼容** - 不同厂商协议差异大，通过适配层转换，对外保持统一接口，符合开闭原则
2. **循环抽离独立 `LlmPipeline`** - 整个流程职责清晰，每个步骤单一职责，好调试好扩展
3. **充分测试覆盖** - 每个提供商都有完整测试套件，修改后快速验证
4. **配置驱动选择** - 通过环境变量选择LLM提供商，不需要修改代码，便于部署
