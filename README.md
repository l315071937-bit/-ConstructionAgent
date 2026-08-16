# ConstructionAgent

建筑工程智能 Agent 系统（V0.1 骨架 + 第一条垂直主链路）。

- 文档基准：docs/00_PROJECT_CONTEXT.md / 01_ARCHITECTURE.md（§52 冻结决策表）/ 02_AGENT_SPEC.md / 03_API_SPEC.md
- 第一条主链路：登录 → 项目 → 上传 PDF → 解析切片 → BGE-M3 向量化 → Milvus → 混合检索 → Evidence → LLM 回答（带 [En] 引用）→ SSE 流式 → 前端对话页

## 快速启动

1. 起基础设施：`docker compose up -d`（PostgreSQL + Redis + Milvus standalone）
2. 后端：`cd backend && pip install -r ../requirements.txt && cp ../.env.example ../.env`
   编辑 .env 填入 EMBEDDING_API_KEY / LLM_API_KEY 后：`uvicorn main:app --reload --port 8000`
3. 前端：`cd frontend && npm install && npm run dev`（Vite 已代理 /api 到 8000）

## V0.1 已知限制（诚实清单）

- 词法通道（LexicalRetriever）仅接口占位，Dense 先行；三候选实现待 evaluation/ 实验定案
- Reranker 为 dense score 占位；bge-reranker-v2-m3 为默认实现档
- 扫描件 OCR / 复杂版面 MinerU 兜底未接入（DocumentParserRouter 已预留）
- 规范查询 / 方案编制接口返回 501（03 §7，后续阶段增量）
- 回答 token 级流式待 V0.2（当前 done 事件一次返回完整回答）
- 数据库表结构由 create_all 自动创建，Alembic 迁移后续接入
