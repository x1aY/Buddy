# Buddy (巴迪)

> 你的个人 AI 管家，世界信息的入口

## 简介

Buddy 是一个全栈个人网站项目，定位为你的**个人 AI 管家**：
- 作为个人知识库的入口，帮你整理和检索信息
- 后续可扩展让 AI 获取信息、整理知识、甚至操作本地机器
- 基于 vibe-coding 实战开发，持续迭代中

## 技术架构

### 后端
- **框架**: FastAPI (异步 Python Web 框架)
- **服务器**: Uvicorn (ASGI 服务器)
- **数据验证**: Pydantic + pydantic-settings
- **认证**: JWT (PyJWT)
- **向量数据库**: ChromaDB (用于知识库存储和检索)
- **实时通信**: WebSockets
- **监控**: Prometheus 指标 + Structlog 结构化日志
- **测试**: pytest + pytest-asyncio

### 前端
- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **样式**: Tailwind CSS
- **图标**: Lucide Vue Next
- **测试**: Vitest + Vue Test Utils

## 项目特色

- 🚀 **现代化全栈架构** - FastAPI + Vue 3，开发体验流畅
- ⚡ **实时通信** - WebSocket 支持双向实时对话
- 🧠 **原生 LLM 支持** - 集成 OpenAI 等大语言模型，支持工具调用
- 📚 **向量数据库** - ChromaDB 内置，支持知识库检索
- 🔒 **类型安全** - 后端 Pydantic 验证 + 前端 TypeScript
- 📊 **可观测性** - Prometheus 监控 + 结构化日志
- 🏗️ **清晰架构** - 按功能模块划分，易于扩展

## 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+

### 安装依赖

```bash
# 安装后端依赖
cd backend && pip install -r requirements.txt

# 安装前端依赖
cd ../frontend && npm install
```

### 本地开发

```bash
# 启动后端 (端口 8000)
cd backend && uvicorn main:app --reload --port 8000

# 启动前端开发服务器 (另开终端)
cd frontend && npm run dev
```

### 构建预览

```bash
# 构建前端
cd frontend && npm run build

# 预览生产版本
cd frontend && npm run preview
```

## 构建你自己的个人网站

Buddy 是一个基础项目框架，你可以：
1. Fork 这个项目
2. 根据你的需求修改前端 UI 和后端功能
3. 添加你自己的知识库内容
4. 扩展 AI 能力让它帮你管理个人信息

详细开发命令参考 `CLAUDE.md`。

## 项目结构

```
├── backend/          # Python FastAPI 后端
├── frontend/         # Vue 3 + TypeScript 前端
├── docs/             # 项目文档
├── logs/             # 日志文件
└── CLAUDE.md         # Claude 开发指南
```

## 愿景

> 让 AI 成为你的个人管家，帮你看见世界，整理知识，提升效率。
