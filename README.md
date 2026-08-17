# ConstructionAgent

建筑工程智能 Agent 系统（项目资料检索 + 工程规范查询 + 施工方案辅助编制）。

- 文档基准：docs/00_PROJECT_CONTEXT.md / 01_ARCHITECTURE.md（§52 冻结决策表）/ 02_AGENT_SPEC.md / 03_API_SPEC.md
- 第一条主链路：登录 → 项目 → 上传 PDF → 解析切片 → BGE-M3 向量化 → Milvus → 混合检索 → Evidence → LLM 回答（带 [En] 引用）→ SSE 流式 → 前端对话页
- 第二条主链路：规范元数据 + 文件入库 → 条款切片 → 独立规范向量库 → 地区/版本/状态检查 → Standard Evidence → 带引用回答
- 第三条主链路：企业模板确认 → 目录确认 → 项目/正式规范 Evidence → 分章节生成与四类检查 → 人工终审 → DOCX/PDF

## 快速启动

1. 起基础设施：`docker compose up -d`（PostgreSQL + Redis + Milvus standalone）
2. 后端：`cd backend && pip install -r ../requirements.txt && cp ../.env.example ../.env`
   编辑 .env 填入 EMBEDDING_API_KEY / LLM_API_KEY 后：`uvicorn main:app --reload --port 8000`
3. 前端：`cd frontend && npm install && npm run dev`（Vite 已代理 /api 到 8000）

## V0.1 已知限制（诚实清单）

- 词法通道（LexicalRetriever）仅接口占位，Dense 先行；三候选实现待 evaluation/ 实验定案
- Reranker 为 dense score 占位；bge-reranker-v2-m3 为默认实现档
- 扫描件 OCR / 复杂版面 MinerU 兜底未接入（DocumentParserRouter 已预留）
- 施工方案使用后台 Task + SQL checkpoint；当前未接入外部分布式任务队列，单机进程内执行生成步骤
- 企业模板和历史优秀方案通过 `/api/v1/enterprise/plan-documents` 由管理员维护，尚无批量导入界面
- 规范有效状态以入库元数据为准；状态未知时回答必须明确提示，系统不联网猜测
- 回答 token 级流式待 V0.2（当前 done 事件一次返回完整回答）
- 数据库表结构由 create_all 自动创建，Alembic 迁移后续接入
