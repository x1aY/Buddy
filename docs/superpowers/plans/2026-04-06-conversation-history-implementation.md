# 对话历史记忆功能 - 实现计划

## Context

为现有视频对话系统添加对话记忆功能，用户可以：
- 查看历史对话列表
- 点击切换到历史对话继续聊天
- 新建对话清空当前内容
- 删除不需要的历史对话
- 存储消息向量用于后续RAG检索增强

设计文档：`docs/superpowers/specs/2026-04-06-conversation-history-design.md`

## 技术选型

- **对话元数据和消息**：延续现有架构，使用 CSV 文件存储
- **向量存储**：ChromaDB 嵌入式向量数据库（纯Python，文件存储，零配置）
- **交互方式**：顶部下拉菜单，点击展开/收起
- **删除方式**：每条历史右侧显示删除图标，点击确认删除

## 后端实现步骤

### 1. 添加依赖

- **文件**：`backend/requirements.txt`
- **操作**：添加 `chromadb` 依赖

### 2. 创建数据模型

- **文件**：`backend/models/conversation.py`
- **内容**：
  - `Conversation` dataclass - 对话元数据
  - `Message` dataclass - 单条消息
  - Pydantic schemas 用于API请求响应

### 3. 创建CSV存储层

- **文件**：`backend/storage/conversation_storage.py`
- **内容**：
  - 遵循现有 `CSVStorage` 模式
  - `conversations.csv` 存储对话元数据
  - `messages.csv` 存储消息内容
  - 实现CRUD操作：
    - `list_conversations_for_user(user_id)` - 获取用户所有对话，按updated_at倒序
    - `get_conversation(id)` - 获取对话
    - `create_conversation(...)` - 创建新对话
    - `delete_conversation(id)` - 删除对话及所有消息
    - `add_message(...)` - 添加消息到对话

### 4. 创建向量存储客户端

- **文件**：`backend/vector_store/chroma_client.py`
- **内容**：
  - 初始化ChromaDB客户端，持久化到 `backend/data/chroma/`
  - 获取或创建集合 `conversation_messages`
  - 实现：
    - `add_message(message_id, conversation_id, role, content, embedding)` - 添加消息向量
    - `delete_message(message_id)` - 删除消息向量
    - `delete_conversation_vectors(conversation_id)` - 删除对话所有向量
    - `search_similar(query_embedding, limit)` - 相似度搜索（预留接口）

### 5. 创建API路由

- **文件**：`backend/api/conversations.py`
- **内容**：
  - JWT认证依赖（从Authorization header获取用户ID）
  - 实现以下端点：
    - `GET /api/conversations` - 获取对话列表
    - `GET /api/conversations/{id}` - 获取对话完整消息
    - `POST /api/conversations` - 创建新对话
    - `POST /api/conversations/{id}/messages` - 添加消息（同时生成向量存入Chroma）
    - `PUT /api/conversations/{id}` - 更新对话标题
    - `DELETE /api/conversations/{id}` - 删除对话
- **注册**：在 `backend/main.py` 注册路由

### 6. 向量生成集成

- 复用现有LLM配置（OpenAI/Anthropic）
- 在添加消息时调用对应嵌入API生成向量
- 配置选择：使用现有 `settings.llm_provider` 决定用哪个嵌入模型

## 前端实现步骤

### 1. 创建API客户端

- **文件**：`frontend/src/api/conversations.ts`
- **内容**：
  - 封装所有对话API调用
  - 类型定义与后端对应

### 2. 修改 VideoCallPage.vue

- **文件**：`frontend/src/components/VideoCallPage.vue`
- **修改内容**：

  1. **添加"历史"按钮**：
     - 放在右上角，退出登录按钮左侧
     - 样式与其他按钮保持一致

  2. **添加下拉菜单**：
     - 点击"历史"按钮展开/收起
     - 点击外部自动收起
     - 显示结构：
       - 当前对话（高亮）
       - 分隔线
       - 历史对话列表（每条右侧带删除垃圾桶图标）
       - 分隔线
       - 新建对话按钮

  3. **状态管理新增**：
     - `currentConversationId` ref - 当前对话ID
     - `historyDropdownOpen` ref - 下拉菜单展开状态
     - `conversationList` ref - 对话列表缓存

  4. **集成现有流程修改**：
     - 页面加载时：如果没有当前对话，自动创建一个空对话
     - 用户发送新消息时：保存到后端API
     - 切换对话：加载选中对话消息替换本地 `conversationMessages`
     - 新建对话：保存当前（如果有消息）→ 创建新对话 → 清空本地
     - 删除对话：确认 → 删除API → 刷新列表 → 如果删除当前则新建

  5. **样式**：使用TailwindCSS，保持现有设计风格

### 3. 更新类型定义（如果需要）

- **文件**：`frontend/shared/src/types.ts`
- 可能需要添加Conversation和Message相关类型

## 数据流向

```
页面加载
  → 如果没有 currentConversationId，自动 POST /api/conversations 创建空对话

用户发送消息
  → 追加到本地 conversationMessages
  → POST /api/conversations/{id}/messages 保存到后端
  → 后端生成向量存入Chroma

用户点击历史菜单项
  → GET /api/conversations/{id} 获取完整消息列表
  → 替换本地 conversationMessages
  → 更新 currentConversationId
  → 收起下拉菜单

用户点击新建对话
  → 如果当前对话有消息，保持现有
  → POST /api/conversations 创建新对话
  → 清空 conversationMessages
  → 更新 currentConversationId
  → 收起下拉菜单

用户点击删除对话
  → 弹出确认框
  → DELETE /api/conversations/{id}
  → 重新加载对话列表
  → 如果删除的是当前，自动新建对话
```

## 关键文件修改清单

| 操作 | 文件 | 类型 |
|------|------|------|
| 添加依赖 | `backend/requirements.txt` | 修改 |
| 新增数据模型 | `backend/models/conversation.py` | 新增 |
| 新增CSV存储 | `backend/storage/conversation_storage.py` | 新增 |
| 新增向量存储 | `backend/vector_store/chroma_client.py` | 新增 |
| 新增API路由 | `backend/api/conversations.py` | 新增 |
| 注册路由 | `backend/main.py` | 修改 |
| 新增API客户端 | `frontend/src/api/conversations.ts` | 新增 |
| 添加UI和逻辑 | `frontend/src/components/VideoCallPage.vue` | 修改 |

总计：**新增4个文件，修改3个文件** - 在合理范围内。

## 认证处理

- 所有对话API需要JWT认证，从 `Authorization: Bearer {token}` 获取
- 验证token后从payload获取 `userId`，只返回对应用户的对话
- 遵循现有认证代码模式

## 测试验证

### 功能测试点

1. **新建对话**：点击新建对话，确认创建成功，清空界面
2. **发送消息**：发送消息后，确认保存到后端
3. **历史列表**：展开历史，确认能看到刚才的对话
4. **切换对话**：点击历史对话，确认加载正确消息
5. **删除对话**：点击删除，确认从列表消失
6. **向量存储**：发送消息后，确认ChromaDB中存有向量

### 运行测试

完成后运行：
```bash
# 后端
cd backend && pip install -r requirements.txt
cd backend && uvicorn main:app --reload --port 8000

# 前端
cd frontend && npm install
cd frontend && npm run dev
```

打开浏览器，测试完整流程。

## 风险和注意事项

- CSV存储是全量加载，对话太多会变慢，但对于当前项目规模可接受
- ChromaDB嵌入式运行，不需要额外服务，符合当前极简架构
- 每条消息都生成向量会增加LLM调用成本，这是功能需求本身决定的
- 删除对话需要同步删除CSV中消息和Chroma中向量，要注意事务一致性（如果其中一个失败，需要回滚提示错误）
