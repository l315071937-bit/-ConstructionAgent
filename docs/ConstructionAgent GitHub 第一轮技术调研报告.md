# ConstructionAgent GitHub 第一轮技术调研报告

> 调研日期：2026-08-15
> 调研方式：GitHub REST API 实时数据抓取（36 个仓库元数据 + 4 组专项搜索 + 8 个重点仓库目录树验证 + 垂直项目 README 深度阅读）
> 数据说明：Star 数、最后推送时间、License 均为抓取当日实时值，非训练数据
> 调研范围：Agent 架构 / RAG / 工程文档理解 / 工程图纸理解 / HITL / 工程化
> 调研结论：**第一轮只做筛选与推荐，不开始实现 ConstructionAgent**

---

## 一、总体结论（TL;DR）

1. **垂直领域开源生态极其薄弱**。GitHub 全站搜索 "engineering drawing OCR" 仅 58 个结果、"construction drawing" 421 个结果，且绝大多数是课程作业和学术 Demo；中文关键词"工程图纸"搜索基本被无关仓库污染。结论：**建筑图纸 AI 没有现成可抄的开源方案，只能自建，第一轮的价值在于锁定"能力积木"而非"完整方案"**。
2. **通用 RAG 平台的"文档理解深度"已经成熟**。RAGFlow 的 DeepDoc（版面识别 + 模板化切片）、MinerU（PDF→Markdown/JSON）、PaddleOCR 的 PP-Structure（表格/版面/KIE）三家已经覆盖了中文工程文档解析的 90% 需求，ConstructionAgent 的知识库解析层应该"站在它们肩膀上"，而不是自己从头写解析器。
3. **Agent 编排层的最优解与冻结文档一致**。LangGraph 在 2026 年的生态地位已经无法绕开：Checkpointer（HITL 任务恢复）、interrupt()（人机协同）、Supervisor 库（路由）恰好一一对应 02_AGENT_SPEC 中 Orchestrator + 三 Agent + Task Resume 的全部需求。CrewAI/AutoGen 等"全家桶"框架反而是风险项（抽象过重、行为黑盒）。
4. **图纸理解方向发现了三个值得跟踪的年轻项目**（ConstructDrawingAI / cad-ai-agent / OpenTakeoff），Star 都在两位数，但设计思想（Canonical Intermediate Representation、意图分类路由、可审计量算 MCP 工具）与 ConstructionAgent 的 Evidence-First 理念高度共振，应纳入 V2 技术储备而非 V1。
5. **License 是本次调研最重要的隐性结论**：QAnything（AGPL-3.0，且已停滞 17 个月）、Dify（自定义商业受限 License）、MinerU（自定义 License）、DocLayout-YOLO（AGPL-3.0）——凡是要"抄代码"或"内嵌部署"的项目，商用前必须逐一过法务。

---

## 二、GitHub 项目排行榜 Top 15

评分维度与权重（按任务文档要求）：业务匹配度 25% / Agent 架构参考价值 20% / RAG 技术参考价值 20% / 文档图纸处理能力 15% / 工程化程度 10% / 活跃度 5% / 文档完整度 5%。

| 排名 | 项目 | 类别 | Stars | 最后更新 | License | 业务 25 | Agent 20 | RAG 20 | 文档 15 | 工程 10 | 活跃 5 | 文档 5 | 总分 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | RAGFlow | A | 88.5k | 2026-08-14 | Apache-2.0 | 22 | 16 | 19 | 15 | 8 | 5 | 5 | **90** |
| 2 | Dify | B | 152.5k | 2026-08-15 | 自定义受限 | 18 | 17 | 16 | 8 | 9 | 5 | 5 | **78** |
| 3 | LlamaIndex | B | 51.6k | 2026-08-14 | MIT | 12 | 17 | 19 | 10 | 9 | 5 | 5 | **77** |
| 4 | Haystack | B | 26.2k | 2026-08-15 | Apache-2.0 | 12 | 15 | 18 | 9 | 9 | 5 | 5 | **73** |
| 5 | LangGraph | B | 39.7k | 2026-08-14 | MIT | 10 | 20 | 12 | 3 | 10 | 5 | 5 | **65** |
| 6 | CrewAI | B | 57.1k | 2026-08-15 | MIT | 10 | 18 | 12 | 5 | 9 | 5 | 5 | **64** |
| 7 | QAnything | A | 14.1k | 2025-03-24 | AGPL-3.0 | 18 | 8 | 14 | 11 | 7 | 2 | 4 | **64** |
| 8 | ConstructDrawingAI | A | 27 | 2026-07-14 | 自定义 | 22 | 10 | 6 | 12 | 3 | 3 | 3 | **59** |
| 9 | cad-ai-agent | A | 22 | 2026-07-10 | MIT | 21 | 12 | 5 | 10 | 5 | 3 | 3 | **59** |
| 10 | OpenTakeoff | A | 80 | 2026-08-14 | Apache-2.0 | 20 | 12 | 5 | 8 | 6 | 4 | 4 | **59** |
| 11 | MinerU | C | 77.7k | 2026-08-14 | 自定义 | 15 | 2 | 8 | 15 | 7 | 5 | 4 | **56** |
| 12 | PaddleOCR | C | 87.7k | 2026-07-22 | Apache-2.0 | 15 | 2 | 6 | 15 | 8 | 5 | 5 | **56** |
| 13 | ColPali | C | 2.7k | 2026-08-03 | MIT | 13 | 2 | 15 | 12 | 4 | 4 | 3 | **53** |
| 14 | Letta | B | 24.3k | 2026-08-14 | Apache-2.0 | 8 | 16 | 8 | 3 | 8 | 5 | 5 | **53** |
| 15 | Milvus | C | 45.6k | 2026-08-15 | Apache-2.0 | 12 | 2 | 17 | 2 | 9 | 5 | 5 | **52** |

**第 16~20 名（仅简评）**：Docling（52，IBM 文档转换，英文强中文弱）｜OpenHands（52，事件流 Agent 工程化范本）｜Qdrant（51，Milvus 轻量替代）｜AutoGen（51，已并入 Microsoft Agent Framework，生态动荡）｜MetaGPT（48，SOP 流水线思想可借鉴，活跃度下降）。

> 注意：评分反映"对 ConstructionAgent 的参考价值"，不是项目本身优劣。例如 LangGraph 排第 5，是因为它没有业务和文档解析能力；但它是**唯一"必须采用"的底座框架**——见第八节。


---

## 三、A 类：直接参考项目详细分析（5 个）

### A-1 RAGFlow（infiniflow/ragflow）

- GitHub：https://github.com/infiniflow/ragflow
- Stars：88,493 ｜ 最后更新：2026-08-14 ｜ License：Apache-2.0

**1. 解决什么问题？**
企业级"深度文档理解"RAG 平台。核心卖点是文档解析不靠"一刀切"，而是先做版面识别（Layout Detection）、再按文档类型套用模板化切片（Template-based Chunking），支持 PDF/Word/Excel/图片/扫描件，内置表格结构识别（TSR）和 OCR。2025 年起增加 Agent 画布（agent/ 模块）、GraphRAG（graphrag/ 模块）和 Memory（memory/ 模块），已从"RAG 引擎"演化为"RAG + Agent 平台"。与 ConstructionAgent 的"企业资料 + 规范 + 模板检索"场景重叠度最高。

**2. 技术栈**
Go（后端任务执行/API）+ Python（RAG 与解析核心）+ React（web/）+ Elasticsearch/Infinity（全文）+ 自研/外接向量库（ES、Milvus、Qdrant 等）+ DeepDoc 解析模型（自研 Layout/TSR 模型）。

**3. 架构（数据流）**
```
文档上传 → deepdoc/（版面识别 → 表格/OCR → 按模板切片：论文/手册/书籍/法律/工程类模板）
→ 切片写入全文索引 + 向量索引（带 page/position 元数据）
→ 用户提问 → 检索（关键词+向量混合、加权、Rerank）→ 引用标注（Citation）
→ LLM 生成（引用自动关联到原文位置）→ 前端可点击引用跳转原文
→ （2025+）Agent 模块可编排检索/生成/GPT-4V 看图等节点工作流
```

**4. 哪些代码值得 ConstructionAgent 借鉴？**
- `deepdoc/` 目录：文档解析器的分层设计（layout → table → ocr → chunk 模板），特别是**工程类文档如何按"章节标题 + 图 + 表"切片**——这是我们解析《建筑电气工程施工方案.doc》这类文档的直接范本；
- `rag/` 目录：检索-重排-引用的完整 pipeline，Citation 数据结构与我们的 Evidence 结构高度同构（chunk_id + page + position + file）；
- `agent/` 目录：画布式 Agent 编排（节点 = 检索/生成/条件分支），可作为 Orchestrator 路由的可视化参考；
- `memory/` 目录：对话记忆与共享记忆的落地方式，对应我们 Task State + Conversation Context 的设计。

**5. ConstructionAgent 可以借鉴什么？**
- 直接参考：DeepDoc 的解析管线设计、模板化切片思想、Citation/Evidence 映射关系；
- 可以改造：把它的"通用知识库"改成我们"项目库 / 规范库 / 企业库"三类知识库 + tenant/project 过滤；
- 不建议采用：整套平台部署太重（ES + 多个微服务），Agent 画布是自研 DSL，无法把 LangGraph 图直接迁入。

**6. 存在什么问题？**
平台级复杂度（V1 部署成本高）；Go+Python 双栈维护难；Agent 模块较新、成熟度低于其 RAG 核心；深绑定其自研 DSL，若采用等于放弃 LangGraph 编排的自由度。

---

### A-2 QAnything（netease-youdao/QAnything）

- GitHub：https://github.com/netease-youdao/QAnything
- Stars：14,072 ｜ 最后更新：2025-03-24 ｜ License：AGPL-3.0

**1. 解决什么问题？**
网易有道推出的企业知识库问答系统，主打"两段式检索"（先 Embedding 粗召回、再 Rerank 精排）和本地私有化部署，中文场景优化好，支持 Word/PDF/PPT/Excel/图片多格式，内置 OCR 与多模态能力。

**2. 技术栈**
Python + FastAPI + Vue + 自研 BCEmbedding（bce-embedding / bce-reranker）+ PaddleOCR + Milvus/自研检索引擎。

**3. 架构（数据流）**
```
文档上传 → 解析（OCR/版面）→ 切片 → Embedding 入库
用户问题 → Embedding 检索（粗召回 TopN）→ Reranker 精排（两段式）
→ LLM 生成（引用标注）→ 前端展示答案 + 来源文件
```

**4. 哪些代码值得借鉴？**
- `qanything_kernel/` 中两段式检索（embedding → rerank）的实现与延迟优化；
- Rerank 在中文工程术语上的策略（BCEmbedding 是中文 Rerank 最早的成熟实践之一）；
- 本地化部署方案（docker-compose 一键起）的工程结构。

**5. 可以借鉴什么？**
- 直接参考：两段式检索 + Rerank 的参数与阈值设计；
- 可以改造：其"知识库/文件管理"交互设计（对应我们的项目文件管理）；
- 不建议采用：**整个项目**。理由见下。

**6. 存在什么问题？**
**开发已停滞 17 个月**（最后推送 2025-03-24），社区 issue 大量无人回复；AGPL-3.0 对商业内嵌部署是硬约束（衍生服务必须开源）；与 RAGFlow 相比文档解析深度明显落后。结论：**参考设计可以，抄代码不行，直接用更不行**。

---

### A-3 ConstructDrawingAI（A-SHOJAEI/ConstructDrawingAI）

- GitHub：https://github.com/A-SHOJAEI/ConstructDrawingAI
- Stars：27 ｜ 最后更新：2026-07-14 ｜ License：自定义（需确认条款）

**1. 解决什么问题？**
把 2D 施工图（电气/建筑/P&ID）转成"结构化、可决策的数据"：符号与构件检测、连接关系图提取、工程量统计、自然语言问答、RFI 草稿——所有提取值都带置信度并可回溯到"源实体 + 图号"。这是极少数**以真实图纸基准测试成绩说话**的开源项目（见 README 基准表：电气检测 DELP/SkeySpot 0.847 mAP@50 超过 SOTA；P&ID 检测 PID2Graph OPEN100 0.926；连接边提取 0.752 edge AP 逼近 Relationformer 0.755）。

**2. 技术栈**
Python + 检测模型（YOLO 系）+ 关系提取模型（Relationformer 类）+ 图结构 + LLM（L4 问答层）。

**3. 架构（数据流）——五层管线，全部读写同一个中间表示 CIR**
```
L0 Ingest：PDF / DWG-DXF / IFC / 图片 → 千兆像素级切片（gigapixel tiling）→ CIR
L1 Perception：符号/构件检测 + 连接图提取
L2 Grounding：检测结果映射到 IFC 类别 + MasterFormat/UniFormat 编码
L3 Engines：工程量提取（数量/面积/长度）
L4 Agent：基于 CIR 的自然语言问答 + RFI 草稿生成
每个提取值：{值, 置信度, 来源实体, 图号页码}
```

**4. 哪些代码值得借鉴？**
- **CIR（Canonical Intermediate Representation）单一 Schema 设计**——五层管线全部读写同一结构，这是它最值得抄的思想，与我们 Evidence 统一结构的设计哲学完全一致；
- L0 的 gigapixel tiling：大图纸必须切片后送检测，否则分辨率崩塌——这是图纸处理的工程难点解法；
- L2 Grounding：检测结果映射到行业编码体系（IFC/MasterFormat），对应我们"证据 → 专业/区域元数据"的过滤体系；
- `docs/BENCHMARKS.md`：如何用公开基准（DELP/SkeySpot/FloorPlanCAD/CubiCasa5K/PID2Graph）做可复现评估。

**5. 可以借鉴什么？**
- 直接参考：CIR 分层数据流、基准测试方法（第二轮可沿这些基准搜索）；
- 可以改造：L4 的问答 Agent 换成我们的 LangGraph + Evidence 体系；
- 不建议采用：V1 集成（冻结文档明确 V1 不做 CAD 几何推理）。

**6. 存在什么问题？**
研究级项目（README 自述以基准评估为核心），无部署文档、无测试基础设施；仅 27 Star，作者单一，可持续性存疑；License 非标准。**定性：V2 图纸方向的"思想供应商"，不是"代码供应商"。**

---

### A-4 cad-ai-agent / cad-dxf-agent（jeremylongshore/cad-ai-agent）

- GitHub：https://github.com/jeremylongshore/cad-ai-agent
- Stars：22 ｜ 最后更新：2026-07-10 ｜ License：MIT

**1. 解决什么问题？**
"上传 DXF/PDF/DWG，用自然语言下达指令"的图纸智能平台：结构化编辑、合规检查（ADA/IBC/自定义规则）、图纸健康报告（图层卫生/实体统计）、工程量提取、图纸摘要、RFI 生成、封闭区域检测（房间/面积计算）。特点是"AI 永不改动你的原始文件"。

**2. 技术栈**
Python（v0.12.0）+ DXF 解析（ezdxf 类库）+ 意图分类 + 多管线（每条能力一条 pipeline）+ LLM。

**3. 架构（数据流）**
```
上传 DXF/PDF/DWG → 解析为实体模型
用户自然语言指令 → Intent Classifier（编辑？合规？量算？摘要？）
→ 选择对应 Processing Pipeline（确定性工具为主，LLM 只做意图与叙述）
→ 结构化结果（含来源实体引用）→ 输出
```

**4. 哪些代码值得借鉴？**
- **意图分类 → 管线选择**：与我们的 Orchestrator"识别任务 → 选择 Agent"是同一个模式，且它的实现克制（分类器 + 规则优先，不滥用 LLM）；
- 每条能力的"确定性工具优先、LLM 只做胶水"原则，对应 02_AGENT_SPEC 的 RULE-006（Agent 通过 Service/Tool 获取能力）；
- 合规检查的"规则引擎 + 发现项 + 整改指引"输出结构，对应我们规范检查的 Evidence 输出格式。

**5. 可以借鉴什么？**
- 直接参考：意图分类路由设计、确定性工具优先原则；
- 可以改造：合规检查规则引擎 → 替换为我们的 Standard Evidence 比对；
- 不建议采用：V1 集成（同样属于 CAD 方向）。

**6. 存在什么问题？**
单人项目、DXF 为主（DWG 依赖转换）、无生产案例；Star 22 但代码工程素质（CI、版本化文档、能力矩阵）明显高于同类。**定性：V2 CAD Agent 的原型级参考。**

---

### A-5 OpenTakeoff（Kentucky-ai/opentakeoff）

- GitHub：https://github.com/Kentucky-ai/opentakeoff
- Stars：80 ｜ 最后更新：2026-08-14 ｜ License：Apache-2.0

**1. 解决什么问题？**
"建筑图纸工程量提取引擎"——同一套引擎上提供两条通道：给 Agent 用的 **40 个 MCP 工具**（量长度/面积/计数/比例尺校准），给估算师用的浏览器画布。**每次测量都记录：比例尺、方法、操作者**——输出天然可审计，也就是天然可当训练数据。

**2. 技术栈**
TypeScript + npm 包（opentakeoff-mcp，已发布 MCP 官方 registry）+ 浏览器 Canvas 前端。

**3. 架构（数据流）**
```
PDF 图纸 → 画布/Agent 工具（flood fill 测量、比例尺门控）
→ 每次测量写记录：{数值, 比例尺, 方法, 操作者}
→ 同一套数学保证 Agent 与人工结果一致 → 可审计记录 → 训练数据沉淀
```

**4. 哪些代码值得借鉴？**
- **"同一引擎、双通道（Agent MCP / 人工画布）"** 的产品架构：AI 和人工共用同一计算内核，结果可比、可审计——这正是我们"AI 检索 + 人工确认"想要的状态；
- **测量记录携带"方法+比例尺+人"**：对应我们的 Evidence 携带"版本+页码+来源"——元数据自证可信度；
- MCP 工具包的工程化实践（registry 发布、npm 包、demo 部署），是评估"MCP 在建筑领域是否成立"的现成案例。

**5. 可以借鉴什么？**
- 直接参考：可审计测量的数据契约设计、双通道产品架构；
- 可以改造：MCP 工具清单（40 个量算工具）可映射为我们 V2 的 Tool 设计；
- 不建议采用：V1 集成（量算不是 V1 场景）。

**6. 存在什么问题？**
项目 2026-06 才创建，非常年轻；TypeScript 技术栈与我们 Python 后端不同；工程量提取的精度上限取决于图纸质量，未见大规模生产验证。**定性：V2 量算方向的种子选手，持续跟踪。**

---

## 四、B 类：架构参考项目详细分析（6 个）

### B-1 LangGraph（langchain-ai/langgraph）

- GitHub：https://github.com/langchain-ai/langgraph
- Stars：39,707 ｜ 最后更新：2026-08-14 ｜ License：MIT

**1. 解决什么问题？**
用"图 + 状态机"建模 Agent 工作流：StateGraph（状态驱动编排）、Checkpointer（状态持久化/断点续跑）、interrupt()（人机协同暂停-恢复）、Subgraph（子图复用）、prebuilt（现成 Agent 模式）。解决的是"多步骤、多分支、可恢复、可人审"的 Agent 编排问题——**与 02_AGENT_SPEC 中三个 Agent 的 Graph 定义、HITL 挂起、Task Resume 需求一一对应**。

**2. 技术栈**
Python（libs/ 核心）+ JS 版本 + LangSmith（可选观测平台）。

**3. 架构（数据流）**
```
StateGraph(State Schema) → 添加 Node（检索/生成/检查）+ 条件边（置信度路由）
→ compile(checkpointer=PostgresCheckpointer)
→ 运行中 interrupt() 挂起 → 状态写入 Checkpointer → 前端提交人工决策
→ Command(resume=...) 恢复执行（从挂起点继续，不重跑）
```

**4. 哪些代码值得借鉴？**
- `libs/checkpoint-postgres`（或 checkpoint-redis）：HITL 任务恢复的持久化方案——冻结文档第 40 条"恢复 LangGraph 继续执行"的直接实现；
- `libs/langgraph` 中 `interrupt()` / `Command` 机制：4 个人工确认点（模板/目录/参数冲突/终审）的标准写法；
- `libs/prebuilt` 中 create_react_agent + ToolNode：Agent Tool 调用的工程化封装；
- `examples/` 中的 agent-with-supervisor 示例：Orchestrator 路由的官方参考写法。

**5. 可以借鉴什么？**
- 直接参考：**全部**。三个 Agent = 三张子图，Orchestrator = 路由层，与冻结架构完全兼容；
- 可以改造：把它的示例 State 换成我们的 ProjectRetrievalState / StandardQueryState / ConstructionPlanState；
- 不建议采用：LangSmith（商业观测平台）作为硬依赖——自建日志即可（对应 02_AGENT_SPEC §22 Observability）。

**6. 存在什么问题？**
API 演进快（版本间迁移成本）；官方示例多为 Demo 深度，生产级编排经验需要自己积累；对"三个 Agent + 统一 Service 层"这类企业架构没有官方模板，需要自建——**这正是我们三份冻结文档的价值所在**。

---

### B-2 Dify（langgenius/dify）

- GitHub：https://github.com/langgenius/dify
- Stars：152,475 ｜ 最后更新：2026-08-15 ｜ License：自定义（Dify Open Source License，商用受限）

**1. 解决什么问题？**
"LLM 应用开发平台"：可视化 Workflow/Agent/Chatflow、知识库（切片/混合检索/Rerank）、模型网关（上百模型接入）、API/SSE 输出、多租户、工作流内嵌**人工审核节点**。它是 150k Star 级项目里唯一把 HITL 做成"平台标准功能"的。

**2. 技术栈**
Python + Flask/Celery + PostgreSQL + Redis + 向量库插件（Weaviate/Qdrant/Milvus/等）+ React 前端。

**3. 架构（数据流）**
```
用户搭建 Workflow（节点：检索/LLM/工具/条件/人工审核）
→ 运行时：触发 → 节点依次执行 → 遇"人工审核节点"挂起任务
→ 审核人通过/驳回（带意见）→ 任务恢复继续
→ 全程任务状态可查 + SSE 推送 + 日志
```

**4. 哪些代码值得借鉴？**
- `api/` 中任务生命周期管理（Task 创建/查询/恢复/事件流）——对应我们 TaskService 设计；
- Workflow 中**人工审核节点的挂起-恢复实现**：审核超时、驳回带原因、多人审批——比 LangGraph 原生 interrupt 更接近企业场景；
- 知识库管理（数据集切片预览、检索命中测试页）的产品交互——对应我们前端"上传文件 → 查看切片效果"的工程体验；
- 模型网关的 provider 抽象（统一封装 DeepSeek/Qwen/OpenAI）——对应我们 LLMFactory 设计。

**5. 可以借鉴什么？**
- 直接参考：HITL 的产品交互与任务挂起-恢复 API 设计；LLMFactory 的多 provider 抽象；
- 可以改造：其知识库+工作流组合模式 → 替换为我们的三 Agent + Service 架构；
- 不建议采用：**平台本体**。理由见下。

**6. 存在什么问题？**
它是平台不是库——要把我们的三 Agent LangGraph 架构塞进它的 DSL，等于放弃 02_AGENT_SPEC 全部 Graph 设计；License 是"源代码可得"而非开源（多租户场景受限，商用需购买授权）；自建平台与它直接竞争。**定性：产品设计与 HITL UX 的参考范本，不是技术底座。**

---

### B-3 LlamaIndex（run-llama/llama_index）

- GitHub：https://github.com/run-llama/llama_index
- Stars：51,649 ｜ 最后更新：2026-08-14 ｜ License：MIT

**1. 解决什么问题？**
"数据框架"：把企业数据（文件/数据库/API）组织成 LLM 可消费的结构，并提供最丰富的检索模式与 Agent 抽象。RAG 模式覆盖：Sentence-Window、Auto-Merging、Parent-Child、Hybrid、Query Pipeline、Sub-Question 分解等——任务文档里点名的"Parent-Child Retrieval、Multi Query"基本都源于 LlamaIndex 生态。

**2. 技术栈**
Python + 各类向量库集成（Milvus/Qdrant/PG/ES 全覆盖）+ Workflows（事件驱动）+ AgentWorkflow（多 Agent 交接）。

**3. 架构（数据流）**
```
文档 → Ingestion Pipeline（解析/切片/索引，可挂 MetadataFilter）
查询 → Query Pipeline（改写 → 混合检索 → 重排 → 合成）
或 AgentWorkflow：FunctionAgent 之间 handoff（一个 Agent 把控制权交给下一个）
```

**4. 哪些代码值得借鉴？**
- `llama-index-core` 的 NodeWithScore / MetadataFilters：**文档级元数据过滤**是它的强项（对应我们 tenant/project 过滤）；
- Query Pipeline 的"改写→检索→重排→合成"模块化拼装：与我们 Project Retrieval Graph 的节点划分几乎一致；
- AgentWorkflow 的 handoff 机制：多 Agent 交接的轻量实现（可作为 Orchestrator 混合问题路由的备选参考）；
- 与 Milvus 的集成代码（milvus 索引的 partition/filter 用法）。

**5. 可以借鉴什么？**
- 直接参考：检索模式的命名与实现思路（Parent-Child 应对"表格与正文分离"场景，对工程文档有效）；
- 可以改造：把它的 Query Pipeline 用 LangGraph 重实现（我们已锁定 LangGraph，避免双框架）；
- 不建议采用：与 LangGraph 混用两套 Agent 框架（状态模型、checkpointer 不互通，维护成本翻倍）。

**6. 存在什么问题？**
抽象层次多（Workflows 与 AgentWorkflow 两套并存，学习曲线陡）；中文工程文档优化不如国内项目；与 LangGraph 生态重叠，同时引入会带来概念混乱。**定性：检索模式百科全书 + 元数据过滤参考，不进主框架。**

---

### B-4 Haystack（deepset-ai/haystack）

- GitHub：https://github.com/deepset-ai/haystack
- Stars：26,214 ｜ 最后更新：2026-08-15 ｜ License：Apache-2.0

**1. 解决什么问题？**
"生产级 RAG 管线框架"：Pipelines 2.0（组件化拼装）+ BM25/Embedding 双路检索器 + Ranker + Agent 组件 + 深度集成评测（Ragas）。它是最早把 BM25 + Vector 混合检索工程化的框架之一，文档质量在同类中一流。

**2. 技术栈**
Python + 组件系统（Component/Connection）+ 多种 DocumentStore（Elasticsearch/OpenSearch/Qdrant/自研内存版）+ 可插拔 Embedder/Ranker。

**3. 架构（数据流）**
```
文档 → Converters（PDF/Word/TXT）→ Preprocessors（清洗/切片）
→ DocumentStore（BM25 倒排 + 向量双索引）
查询 → Retriever（BM25 + Embedding 双路）→ Join → Ranker → Generator
→ 整条 Pipeline 可序列化部署（hayhooks）
```

**4. 哪些代码值得借鉴？**
- BM25 + Embedding 双路检索器的**生产级实现**（分数归一化、双路合并策略）：对应我们 merge_results 节点的具体算法；
- Pipeline 的可序列化/版本化部署：企业内"方案模板"式的 RAG 配置管理；
- 评测集成（Pipeline 内嵌评估节点）：对应我们 Retrieval Evaluation 需求。

**5. 可以借鉴什么？**
- 直接参考：混合检索的合并与归一化策略、文档预处理链；
- 可以改造：它的 Pipeline 概念 → 我们的 LangGraph Node；
- 不建议采用：作为主框架（与 LangGraph 二选一，我们已选 LangGraph；且它对中文与多模态支持弱）。

**6. 存在什么问题？**
社区以欧美为主，中文工程文档实践少；Agent 能力弱于 LangGraph；多模态检索（图纸）几乎空白。**定性：混合检索工程实现的参考书。**

---

### B-5 CrewAI（crewAIInc/crewAI）

- GitHub：https://github.com/crewAIInc/crewAI
- Stars：57,090 ｜ 最后更新：2026-08-15 ｜ License：MIT

**1. 解决什么问题？**
"角色扮演式多 Agent 框架"：定义 Crew（一组角色 Agent）、Task（带上下文的作业）、Process（顺序/层级执行）、Flow（事件驱动）。内置 HITL（human_input 标记）、Memory、Knowledge、RAG 管线（2025 年新增知识模块）。

**2. 技术栈**
Python（lib/crewai 核心 + flows）+ 商业化平台（CrewAI Studio）。

**3. 架构（数据流）**
```
定义 Agent(role/goal/backstory/tools) + Task(description/expected_output/human_input)
→ Crew 编排：Sequential 顺序执行 / Hierarchical 管理者分派
→ 任务间共享上下文 → human_input=True 时暂停等待人工输入 → 继续
```

**4. 哪些代码值得借鉴？**
- Role/Goal/Task 的**结构化 Agent 定义方式**：让 Agent 职责边界显式化（对应我们三个 Agent 的职责冻结，但用代码而非仅文档表达）；
- `human_input` 的 HITL 最小实现（挂起点、输入回填、继续执行）——比 LangGraph interrupt 更"产品化"；
- 事件流（Agent/Task 生命周期事件）→ 前端"正在检索项目资料"进度展示的实现方式。

**5. 可以借鉴什么？**
- 直接参考：Agent 职责的显式声明模式、HITL 交互范式；
- 可以改造：把 Crew 换成 LangGraph 图（保留其角色定义思想）；
- 不建议采用：**框架本体**。理由见下。

**6. 存在什么问题？**
"魔法"过多（内部 Prompt 拼装黑盒，难调试难审计）——与我们"确定性优先、Prompt 显式冻结"的工程文化冲突；记忆/知识模块为后加功能，与专业 RAG 栈差距明显；平台商业导向，开源版与付费版能力分化。**定性：产品形态参考 > 技术底座参考。**

---

### B-6 Letta（letta-ai/letta）

- GitHub：https://github.com/letta-ai/letta
- Stars：24,250 ｜ 最后更新：2026-08-14 ｜ License：Apache-2.0

**1. 解决什么问题？**
"记忆优先的 Agent 服务器"（原 MemGPT）：把 Agent 状态拆成 Memory Blocks（in-context 块 / archival 块），所有状态持久化，Agent 可跨会话恢复"它记得什么"。附带 Agent Server（REST API 暴露 Agent 会话）、沙箱、ADE（Agent 开发环境）。

**2. 技术栈**
Python + SQLite/PostgreSQL（记忆存储）+ REST Server + Docker。

**3. 架构（数据流）**
```
Agent 运行中 → 上下文超限时把信息"归档"到 archival block（向量检索）
→ 需要时从记忆库召回 → 会话结束状态持久化
→ 下次会话从持久化状态恢复（Agent 不"失忆"）
```

**4. 哪些代码值得借鉴？**
- **Memory Blocks 的显式记忆分层**：in-context（当前任务上下文）/ archival（长期可检索记忆）——对应我们 Redis 短期上下文 + PostgreSQL 长期任务状态的分层；
- Agent Server 的 REST 会话模型（create/step/resume）：对应我们 Task 化长任务的 API 形态；
- 状态持久化与恢复的工程实现（checkpoint 语义）。

**5. 可以借鉴什么？**
- 直接参考：记忆分层的命名与边界设计；
- 可以改造：它的"记忆优先" → 我们的"Evidence 优先"（V1 冻结文档明确不做复杂长期记忆，Letta 的完整记忆系统留给 V2）；
- 不建议采用：V1 引入完整 Letta（与 LangGraph Checkpointer 职责重叠，增加双份状态管理）。

**6. 存在什么问题？**
"记忆优先"范式对 V1 过重（我们 V1 只有 Conversation Context + Task State）；框架较年轻，API 变动频繁。**定性：Task/会话持久化的参考实现，V2 再评估。**

---

## 五、C 类：专项技术参考项目（10 个，其中 4 个详析）

### C-1 MinerU（opendatalab/MinerU）

- GitHub：https://github.com/opendatalab/MinerU
- Stars：77,668 ｜ 最后更新：2026-08-14 ｜ License：自定义（非标准 SPDX，商用需审阅）

**1. 解决什么问题？**
把 PDF（含扫描件）高质量转成 Markdown/JSON：版面分析 → 公式识别 → 表格识别 → OCR → 按阅读顺序输出。**中文文档解析质量在开源界第一梯队**，学术论文与工程手册类效果尤佳。

**2. 技术栈**
Python + 自研版面/公式/表格模型（HuggingFace 发布）+ VLM 管线（2.x 起）+ GPU 加速。

**3. 架构（数据流）**
```
PDF → 版面检测（区分正文/表格/公式/图）→ 各区域路由到专项模型
→ 表格结构识别 → OCR/公式识别 → 阅读顺序组装 → Markdown/JSON（含坐标）
```

**4. 哪些代码值得借鉴？**
- `mineru/` 核心管线：区域级"检测-路由-专项处理-组装"的解析器分层；
- 输出的**坐标与页码元数据**（块级 bbox）：与我们的 Evidence 需携带 page/bbox 的需求完全对口；
- Docker 化部署与服务化封装（`projects/` 下的 web 服务）。

**5. 可以借鉴什么？**
- 直接参考：扫描件/复杂版式 PDF 的解析兜底方案（配合 PyMuPDF 处理文本型 PDF）；
- 可以改造：输出 JSON 直接映射为我们的 Chunk 结构（带 page/bbox）；
- 不建议采用：作为唯一解析器（对文字型 PDF 性能浪费大，且 GPU 资源消耗高）。

**6. 存在什么问题？**
高质量输出依赖 GPU；License 非标准（须法务审阅后商用）；模型更新快（版本间行为有差异）。**定性：解析管线中的"重武器"，按需启用。**

---

### C-2 PaddleOCR / PP-Structure（PaddlePaddle/PaddleOCR）

- GitHub：https://github.com/PaddlePaddle/PaddleOCR
- Stars：87,675 ｜ 最后更新：2026-07-22 ｜ License：Apache-2.0

**1. 解决什么问题？**
百度开源的 OCR + 文档结构化全家桶：PP-OCRv4/v5（文本检测识别）、PP-StructureV3（版面分析/表格识别 SLANet/公式识别/关键信息提取 KIE）、PaddleOCR-VL（VLM 版 OCR）、表格恢复、多语言（中文最强）。还提供 `langchain-paddleocr` 集成与 `mcp_server`。

**2. 技术栈**
Python（PaddlePaddle 框架）+ PaddleServing/Triton 部署 + JS 版。

**3. 架构（数据流）**
```
图片/PDF 页 → PP-DocLayout 版面检测 → 文本区域 OCR / 表格区域 SLANet 结构识别
→ 阅读顺序组装 → 结构化输出（文本+表格 HTML/Excel+坐标）
→ 可挂 LangChain DocumentLoader 或 MCP 工具直接进 RAG
```

**4. 哪些代码值得借鉴？**
- `ppstructure/` 目录：**表格识别与版面分析的完整实现**——工程文档（材料表、参数表、图纸标题栏）解析的核心能力；
- `langchain-paddleocr/`：OCR → Document 的现成桥接（我们可仿照写 LangGraph Tool）；
- `mcp_server/`：文档解析的 MCP 化实践（V2 可参考）；
- `deploy/`：服务化部署方案（PaddleServing）。

**5. 可以借鉴什么？**
- 直接参考：**表格识别 + 版面分析 + OCR** 三大件直接作为我们的文档解析服务；
- 可以改造：输出映射到我们的 Chunk + Evidence（带 bbox/page）；
- 不建议采用：PaddlePaddle 框架之外的部分（训练脚本等与 V1 无关）。

**6. 存在什么问题？**
PaddlePaddle 框架依赖（与 PyTorch 生态并存增加部署复杂度）；模型/API 版本多（v2→v3 结构变动）；表格跨页与合并单元格场景仍需兜底。**定性：中文工程文档解析的主力军。**

---

### C-3 ColPali（illuin-tech/colpali）

- GitHub：https://github.com/illuin-tech/colpali
- Stars：2,736 ｜ 最后更新：2026-08-03 ｜ License：MIT

**1. 解决什么问题？**
"视觉检索"：用 VLM（PaliGemma 系）对 PDF 页面图像直接打 patch 级向量，检索时**不需要 OCR**，直接按页面图像语义匹配（Late Interaction / ColBERT 式）。对扫描件、图纸、复杂版式（OCR 会丢失视觉信息的场景）检索效果显著优于"OCR 后再向量化"。

**2. 技术栈**
Python + PaliGemma VLM + Qdrant/Vespa/自研检索后端 + GPU。

**3. 架构（数据流）**
```
PDF 页 → 渲染为图像 → 切成 patches → VLM 编码为多向量（每 patch 一向量）
查询（文本/图片）→ 同样编码 → MaxSim 晚交互打分 → 命中页面（可定位到 patch 区域）
```

**4. 哪些代码值得借鉴？**
- `colpali_engine/`：patch 级编码与 MaxSim 检索的实现——**图纸页级检索（"这个节点在哪张图上"）的最佳开源实践**；
- 与 Qdrant 的集成代码：多向量（multivector）索引的工程用法；
- 评测脚本（ViDoRe 基准）：视觉检索的可复现评估方法。

**5. 可以借鉴什么？**
- 直接参考：**图集/图纸/扫描件的页级检索**——正好补上"OCR 对图纸失效"的短板；
- 可以改造：命中 page + patch 区域 → 我们的 Evidence（page + bbox + 缩略图）；
- 不建议采用：V1 主体检索（延迟高于文本向量检索，且 V1 以文本型文档为主）。

**6. 存在什么问题？**
研究级工程（部署组件需自己拼）；索引与查询都吃 GPU；patch 级匹配偏"外观相似"而非"语义理解"（对跨图纸的构件语义检索有限）。**定性：V1 末/V2 图纸检索的核心候选，V1 可在图集知识库上先做 POC。**

---

### C-4 Milvus（milvus-io/milvus）

- GitHub：https://github.com/milvus-io/milvus
- Stars：45,643 ｜ 最后更新：2026-08-15 ｜ License：Apache-2.0

**1. 解决什么问题？**
分布式向量数据库。对 ConstructionAgent 的三个关键能力：① 2.5+ 内置全文检索（BM25）——**混合检索（dense + sparse）一个库全搞定**；② Partition Key——**按 tenant_id/project_id 做物理隔离过滤**（对应我们 Permission First 原则，比 Python 层过滤安全得多）；③ milvus-lite——本地开发无需完整集群。

**2. 技术栈**
Go + C++ + etcd/Pulsar/MinIO（分布式模式依赖）。

**3. 架构（数据流）**
```
写入：Chunk → Dense 向量（BGE-M3）+ Sparse 向量（BM25）→ 集合（带 partition key）
查询：Metadata 过滤（project_id=1001）→ Dense/Sparse 双路打分 → Hybrid 融合 → TopK
```

**4. 哪些代码值得借鉴？**
- `pymilvus` 的 HybridSearch / AnnSearchRequest：混合检索官方用法；
- Partition Key 与标量索引的实践：多租户过滤的正确姿势（对应冻结文档 01 §25 的"先 Metadata Filter 再检索"）；
- 其 Full-Text Search（tantivy 内核）的 schema 设计：BM25 的字段级配置。

**5. 可以借鉴什么？**
- 直接参考：**按冻结架构采用**（01 文档已锁定 Milvus，本调研验证其可行性：内置 BM25 可省掉独立 ES，Partition Key 满足多租户隔离）；
- 可以改造：milvus-lite 用于本地开发，standalone 模式用于单机部署，集群模式留给多租户生产；
- 不建议采用：分布式集群模式作为 V1 默认（运维过重）。

**6. 存在什么问题？**
完整集群运维成本高（etcd/Pulsar/MinIO）；内存占用大；对 8G 内存开发机构成压力。**缓解：V1 用 standalone/milvus-lite。备选：Qdrant（51 分，轻量但偏离冻结架构，需走变更评审）。**

---

### C-5~C-10 专项项目简评表

| 项目 | Stars/更新 | License | 定位 | 对 ConstructionAgent 的判断 |
| --- | --- | --- | --- | --- |
| FlagEmbedding（BGE） | 12.1k / 2026-08 | MIT | BGE-M3 嵌入 + bge-reranker 重排 | **采用**：冻结架构的 Embedding/Reranker 来源；BGE-M3 同时输出 dense+sparse，与 Milvus 混合检索天然配对 |
| DocLayout-YOLO | 2.2k / 2025-04 | AGPL-3.0 | 轻量版面检测 | 参考论文/权重用法；AGPL 约束 + 更新放缓，生产可改用 PaddleOCR 的 PP-DocLayout |
| bm25s | 1.8k / 2026-07 | MIT | 纯 Python BM25 | 备选：若 Milvus 全文检索不满足（如中文分词定制），用它自建 BM25 层；依赖少、毫秒级 |
| Ragas | 15.3k / 2026-02 | Apache-2.0 | RAG 评测（忠实性/上下文精度） | **采用（评估期）**：检索评估与测试集生成，对应 02_AGENT_SPEC 的 Agent 测试要求；注意指标本身有争议，仅作参考信号 |
| CRAG | 468 / 2024-10 | 无 License | Corrective RAG 论文实现 | 思想参考：其 Retrieval Evaluator ≈ 我们的 check_confidence 节点；**代码不可抄（无 License）**；Web Search 回退不适用（我们回退是人工兜底） |
| self-rag | 2.4k / 2024-05 | MIT | Self-RAG 论文实现（反思 token） | 思想参考：生成时自检 + 按需检索；实现停留在 Llama2 时代，**定性为学术 Demo，不采用** |

**其余已调研未入榜**：Qwen2.5-VL（19.8k，图纸/文档 VLM 解析候选，V2 重点）、marker（38.8k，PDF→MD，英文强中文一般）、surya（21.3k，OCR 工具包）、olmOCR（19.3k，大规模扫描件 OCR，部署重）、Docling（64.8k，IBM 文档转换，中文弱于国产方案）、deepdoctection（3.2k，管线编排式解析，活跃度一般）、ezdxf（1.4k，DXF 解析，V2 CAD 基础库）、IfcOpenShell（2.7k，IFC/BIM，V2 储备）、AutoGen（60.4k，已并入 Microsoft Agent Framework，生态动荡不建议）、MetaGPT（69.8k，SOP 流水线思想可借鉴，活跃度下降）、OpenHands（84.1k，事件流+沙箱的工程化范本，V2 参考）、engineering-drawing-extractor（93★，2023 年停滞，仅标题栏提取）、YOLOplan（21★，MEP 符号检测，太早期）。

---

## 六、ConstructionAgent 技术能力矩阵

| 能力 | RAGFlow | Dify | LlamaIndex | Haystack | LangGraph | CrewAI | MinerU | PaddleOCR | ColPali | Milvus | 是否值得采用 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Multi-Agent 编排 | ✓ | ✓ | ✓ | ◐ | ✓✓ | ✓ | - | - | - | - | ✓（LangGraph） |
| Supervisor/Router | ◐ | ✓ | ✓ | - | ✓ | ✓ | - | - | - | - | ✓ |
| HITL（挂起/恢复） | ◐ | ✓✓ | ◐ | - | ✓✓ | ✓ | - | - | - | - | ✓ |
| Hybrid 检索（BM25+向量） | ✓ | ✓ | ✓ | ✓✓ | - | ◐ | - | - | - | ✓✓ | ✓ |
| Reranker | ✓ | ✓ | ✓ | ✓ | - | ◐ | - | - | - | - | ✓（BGE） |
| Query Rewrite | ✓ | ✓ | ✓ | ◐ | ◐ | ◐ | - | - | - | - | ✓ |
| Parent-Child 检索 | ✓ | ◐ | ✓✓ | - | - | - | - | - | - | - | ◐（工程表格场景评估） |
| 多租户过滤（partition） | ✓ | ✓ | ✓ | ◐ | - | - | - | - | - | ✓✓ | ✓（Milvus partition key） |
| 引用/来源追踪 | ✓✓ | ✓ | ✓ | ✓ | - | ◐ | ✓(bbox) | ✓(bbox) | ✓(patch) | - | ✓ |
| PDF 文本解析 | ✓ | ✓ | ✓ | ✓ | - | ◐ | ✓✓ | ✓ | - | - | ✓（PyMuPDF+兜底） |
| 版面分析 | ✓✓ | ◐ | ◐ | - | - | - | ✓✓ | ✓✓ | - | - | ✓ |
| 表格识别 | ✓✓ | ◐ | ◐ | - | - | - | ✓ | ✓✓ | - | - | ✓ |
| 中文 OCR | ✓ | ✓ | ◐ | ◐ | - | - | ◐ | ✓✓ | - | - | ✓ |
| 图纸页级视觉检索 | - | - | - | - | - | - | - | - | ✓✓ | - | V2 重点研究 |
| 图纸符号检测 | - | - | - | - | - | - | - | - | - | - | V2（ConstructDrawingAI 等） |
| CAD/DXF 原生解析 | - | - | - | - | - | - | - | - | - | - | V2（ezdxf/cad-ai-agent） |
| RAG 评测 | ◐ | ◐ | ✓ | ✓✓ | - | - | - | - | ✓ | - | ✓（Ragas） |
| 生产部署/观测 | ✓ | ✓✓ | ✓ | ✓✓ | ◐ | ◐ | ◐ | ✓ | ◐ | ✓✓ | ✓ |

（✓✓ = 该能力的第一梯队；✓ = 支持；◐ = 部分/一般；- = 无）

---

## 七、技术方案候选

### 7.1 Agent 架构候选

**方案 A（推荐）：LangGraph 自建 Orchestrator + 三 Agent 子图**
Orchestrator 路由层（意图分类 → 单 Agent / 混合链路）+ 三个独立 StateGraph 子图 + PostgresCheckpointer 持久化 + interrupt() 实现 4 个人工确认点。完全遵循 02_AGENT_SPEC 的 Graph/State/Node 设计与 20 条强制规则。参考源码：langgraph `libs/checkpoint-postgres`、`examples/` 中 supervisor 示例、langgraph-supervisor-py 的路由写法（★1.6k，MIT，活跃，可作为轻量起步参考，但最终自建以适配三 Agent 职责）。

**方案 B：Dify 平台承载**
把三 Agent 拆成平台内 Workflow。优点：HITL/多租户/观测开箱即用；缺点：DSL 绑定、LangGraph 图全部重写、License 受限、与自建产品定位冲突。**否决。**

**方案 C：CrewAI/AutoGen 全家桶**
CrewAI 角色式或 AutoGen 群聊式。优点：上手快；缺点：行为黑盒、Prompt 不可审计、定制深度不足——与"Evidence First、确定性优先"的文化冲突。**否决（保留其 HITL 交互与角色声明思想）。**

### 7.2 RAG 架构候选

**方案 A（推荐）：Milvus（dense+sparse 全文混合 + partition key 过滤）+ BGE-M3 + bge-reranker**
与冻结架构一致。Milvus 2.5+ 内置 BM25 省掉独立全文引擎；partition key 保证 tenant/project 物理隔离；V1 开发用 milvus-lite/standalone。风险：内存与运维成本，用 standalone 模式缓解。

**方案 B：轻量自建（bm25s + pgvector/Qdrant）**
部署最简、成本最低，适合原型验证；但偏离 Architecture Freeze（Milvus），需要变更评审，且后期数据量大后仍需迁移。**仅作降级预案。**

**方案 C：RAGFlow 全家桶（Infinity/ES + DeepDoc + GraphRAG）**
能力最强但引入完整平台依赖与 Go 栈，与自研架构重叠。**不采用本体；分阶段借鉴：DeepDoc 解析管线（V1）、GraphRAG（V2 规范关联图谱）。**

### 7.3 文档/图纸处理候选

**方案 A（推荐）：分层解析管线**
文字型 PDF → PyMuPDF 文本抽取（快、页码精确）；扫描件/复杂版式 → PaddleOCR PP-Structure（版面+表格+中文 OCR）；版式极端复杂/公式密集 → MinerU 兜底。全部输出统一 Chunk Schema（text + page + bbox + source_type）。`.doc/.docx/.xls` 统一先转 PDF 再进管线（LibreOffice headless）。

**方案 B：MinerU 全量**
质量高但 GPU 消耗大、License 需审阅，对简单文字型 PDF 是杀鸡用牛刀。**不推荐全量，保留为兜底。**

**方案 C：Docling（IBM）**
英文生态强、代码质量高，但中文工程文档效果弱于方案 A 组合。**备选，用于英文资料。**

**图纸方向（V2 储备，V1 不实现）**：ColPali 页级视觉检索（POC 优先）→ ConstructDrawingAI 的 CIR 分层管线（L0 切片 → L1 检测 → L2 行业编码映射）→ cad-ai-agent 的意图路由 + ezdxf CAD 原生解析 → OpenTakeoff 的可审计量算契约。

---

## 八、最终推荐

### 必须采用（与冻结文档一致，且本调研验证可行）

1. **LangGraph**：编排底座（Checkpointer + interrupt + Subgraph），02_AGENT_SPEC 三张图直接落地；
2. **Milvus**：向量库（2.5+ 全文检索 + partition key），开发用 milvus-lite/standalone；
3. **BGE-M3 + bge-reranker（FlagEmbedding）**：中文嵌入与重排的第一选择；
4. **PaddleOCR / PP-Structure**：中文工程文档的 OCR/版面/表格主力；
5. **PyMuPDF**：文字型 PDF 的页码级文本抽取（Evidence 的 page 定位基础）；
6. **FastAPI + PostgreSQL + Redis + Docker**（冻结架构既定，调研无反对证据）。

### 强烈推荐

1. **RAGFlow 的 DeepDoc 设计**作为解析管线架构参考（不部署其平台）；
2. **MinerU** 作为复杂版式兜底解析器（先做法务 License 审阅）；
3. **Ragas** 纳入检索评估阶段（对应"第三阶段知识库"的验收标准）；
4. **bm25s** 作为 BM25 轻量备胎（Milvus 中文分词定制不满足时启用）；
5. **Dify 的 HITL 交互设计**作为前端"人工确认点"的产品参考（模板选择、目录确认、终审 UI）。

### 可以考虑

1. langgraph-supervisor-py：Orchestrator 起步的轻量参考（最终自建）；
2. Letta 的记忆分层思想（V2 再评估）；
3. Haystack 的双路检索合并策略；
4. LlamaIndex 的 Parent-Child 检索（工程表格与正文分离场景，先 POC）；
5. Qwen2.5-VL 作为 V2 图纸 VLM 解析的模型候选；
6. Qdrant 作为 Milvus 降级预案（需变更评审才可启用）。

### 暂时不要做

1. **V1 集成任何图纸/CAD 能力**（ConstructDrawingAI、cad-ai-agent、OpenTakeoff、ColPali 全部进 V2 技术储备清单，不进入 V1 开发）；ColPali 例外——若 V1 图集检索质量不达标，可在 V1.5 以 POC 形式评估；
2. Dify/CrewAI/AutoGen 框架本体（理由见方案候选）；
3. RAGFlow 平台部署（与自研架构重叠）；
4. CRAG/self-rag 的代码（无 License/学术过时，只吸收思想）；
5. MCP 生态（冻结文档已明确 V1 不做；OpenTakeoff 是 V2 再评估 MCP 价值的案例）。

---

## 九、第二轮 GitHub 搜索关键词

基于第一轮发现的"垂直生态薄弱但积木齐全"格局，第二轮建议沿以下关键词深挖：

**图纸理解（V2 核心）**
1. PID2Graph / DELP / SkeySpot / FloorPlanCAD / CubiCasa5K —— 图纸检测基准与配套实现（ConstructDrawingAI 的评测底座）
2. drawing symbol detection YOLO / construction blueprint dataset
3. gigapixel image tiling inference（千兆像素图纸切片推理）
4. vision-language model CAD / DXF text extraction LLM

**视觉检索与多模态（V1.5~V2）**
5. ColPali fine-tuning construction / visual document retrieval benchmark ViDoRe
6. late interaction retrieval multilingual

**文档解析深度（V1 知识库阶段）**
7. table structure recognition benchmark / SLANet alternative（表格识别上限）
8. OmniDocBench / document parsing benchmark Chinese（中文解析评测）
9. PDF page thumbnail annotation（Evidence 缩略图生成与高亮定位）

**Agent 工程化（贯穿）**
10. langgraph checkpoint postgres production / langgraph interrupt human review（HITL 生产实践）
11. agent observability open source / agent trace evaluation（自建观测参考，替代 LangSmith）
12. agent memory hierarchical / mem0（记忆分层的独立实现，V2 评估）

**建筑垂直（持续监控）**
13. construction takeoff MCP / AEC AI agent / construction document RAG
14. IFC extraction knowledge graph / BIM LLM（V2 BIM 方向）
15. 图纸识别 / 表格识别 / 文档版面分析（中文社区项目，注意区分广告仓库）

> 搜索技巧提示：第一轮已证实中文关键词污染严重，第二轮建议以英文专业术语 + 基准名称为主，中文搜索仅作补充并重点看"有真实基准成绩/生产案例"的项目。

---

## 十、调研对现有冻结文档的印证与三个补充建议

**印证**：01/02 文档锁定的 LangGraph + Milvus + BGE + FastAPI 技术栈，经 36 个仓库横评，没有发现更好的替代组合；三 Agent 职责划分与业界 Supervisor/Router 最佳实践一致；Evidence 结构设计领先于绝大多数开源项目（多数项目只有 Citation，没有 page/bbox/version 的完整证据链）。

**补充建议 1（架构级，需讨论）**：建议在 01 文档的"检索技术"一节明确写入 **Milvus Partition Key = tenant/project 物理隔离**的实现要求——调研确认这是多租户安全的关键，且 Milvus 原生支持，应在开发前冻结该决策。

**补充建议 2（License 清单，需法务）**：本轮发现 4 个"想抄但 License 有坑"的项目（QAnything AGPL、Dify 受限、MinerU 自定义、DocLayout-YOLO AGPL），建议在 06_CLAUDE_DEVELOPMENT_RULES.md 中增加一条规则：**引入第三方代码前必须核对 License 白名单**。

**补充建议 3（知识库解析管线）**：建议将本文档 7.3 方案 A 的"分层解析管线（PyMuPDF → PP-Structure → MinerU 兜底）"作为 03/04 文档中 DocumentService 的设计输入，避免三个 Agent 各自解析文档。

---

*本轮调研数据均为 2026-08-15 从 GitHub API 实时抓取（36 仓库 + 4 组搜索 + 8 目录树 + 3 README 深读），评分与推荐仅代表第一轮结论；第二轮将按第九节关键词继续深挖。*
