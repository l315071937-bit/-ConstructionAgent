# ConstructionAgent GitHub 第一轮技术调研任务

你现在不是让我直接写代码，而是作为我的「AI Agent 技术架构研究助手」，先帮我在 GitHub 上筛选适合 ConstructionAgent 的优秀开源项目。

## 一、项目背景

我要开发一个面向中国建筑/施工领域的 ConstructionAgent。

核心目标是：

1. 项目知识检索 Agent
2. 规范查询 Agent
3. 施工方案编制 Agent

系统需要支持企业内部项目资料、施工图纸、规范、图集、施工方案、Word/PDF/Excel 等工程资料的统一检索，并通过 Agent 根据用户问题决定调用检索、规范查询、方案编制等能力。

系统不是简单的 ChatGPT + RAG，而是希望做成一个具有真实工程化能力的 Multi-Agent / Agentic RAG 系统。

------

## 二、目前暂定技术方向

以下技术只是候选方案，不要默认必须使用，请通过 GitHub 项目调研判断是否合理：

- Python
- FastAPI
- LangGraph
- LangChain
- BGE-M3
- Milvus
- PostgreSQL
- Redis
- PyMuPDF
- OCR
- Docker
- DeepSeek / Qwen 等 LLM

------

## 三、核心技术需求

### 1. Agent 架构

重点寻找：

- Multi-Agent
- Supervisor Agent
- Router Agent
- LangGraph
- Tool Calling
- Agent State
- Agent Memory
- Human-in-the-loop
- Agent Workflow
- 条件路由
- Agent 失败重试
- Agent 降级

重点关注项目是否真正解决了 Agent 编排问题，而不是简单把多个 Prompt 放在一起。

------

### 2. RAG

重点寻找：

- Advanced RAG
- Agentic RAG
- Hybrid Search
- BM25 + Vector Search
- Reranker
- Query Rewrite
- Query Expansion
- Multi Query
- Parent-Child Retrieval
- Self-RAG
- Corrective RAG
- Adaptive RAG
- Retrieval Evaluation
- Citation / Source Tracking

尤其关注：

「检索不到 → 查询改写 → 再检索 → 判断是否可信 → 最终回答」

这种闭环设计。

------

### 3. 工程文档理解

重点寻找：

- PDF RAG
- Document AI
- OCR
- Layout Understanding
- Table Extraction
- Word / Excel / PDF
- 多模态 RAG
- 文档页码定位
- 文档引用
- 图片/文本联合检索

因为 ConstructionAgent 后续需要处理：

- 施工图纸
- 规范
- 图集
- 施工方案
- 企业标准
- Word
- Excel
- PDF
- 扫描件

------

### 4. 工程图纸理解

这是重点研究方向。

重点寻找：

- Engineering Drawing AI
- CAD Drawing AI
- Construction Drawing AI
- Blueprint AI
- Technical Drawing Understanding
- Drawing OCR
- Drawing Object Detection
- Multimodal RAG for Drawings
- Drawing Knowledge Graph

重点关注：

图纸 → OCR / Vision → 结构化信息 → 检索 → RAG → Agent

这一类完整链路。

------

### 5. Human-in-the-loop

重点寻找：

- Human in the Loop
- Approval
- Review
- Agent interrupt
- Human feedback
- Workflow checkpoint

因为 ConstructionAgent 中有几个关键节点不能让 LLM 自动决定：

例如：

企业已有施工方案模板
→ 检索
→ 判断是否存在适用模板
→ 人工确认
→ 决定是否按照企业模板编制

以及：

施工方案生成
→ 人工审核
→ 通过 → 下一阶段
→ 不通过 → 修改/重新生成

------

### 6. 工程化能力

重点关注：

- FastAPI
- Docker
- PostgreSQL
- Redis
- Celery / Async
- API Design
- Logging
- Monitoring
- Testing
- Configuration
- Exception Handling
- Retry
- Idempotency

不要只找 Demo，要特别判断哪些项目值得作为工程化参考。

------

# 四、GitHub 筛选标准

请不要只按照 Star 数量排序。

建立以下评分体系：

| 维度                            | 权重 |
| ------------------------------- | ---- |
| 与 ConstructionAgent 业务匹配度 | 25%  |
| Agent 架构参考价值              | 20%  |
| RAG 技术参考价值                | 20%  |
| 文档/图纸处理能力               | 15%  |
| 工程化程度                      | 10%  |
| 活跃度                          | 5%   |
| 文档完整度                      | 5%   |

总分 100 分。

------

# 五、第一轮筛选目标

从 GitHub 中筛选：

### A 类：直接参考

与 ConstructionAgent 非常接近。

例如：

- 工程图纸 AI
- 工程文档 RAG
- 企业知识库 Agent
- Multi-Agent RAG

目标：3~5 个。

### B 类：架构参考

业务不一定是建筑，但 Agent/RAG 架构非常优秀。

例如：

- LangGraph Multi-Agent
- Agentic RAG
- Adaptive RAG
- Self-RAG
- Human-in-the-loop

目标：5~8 个。

### C 类：专项技术参考

只解决某一个关键问题。

例如：

- PDF 多模态解析
- OCR
- 图纸理解
- 表格解析
- 文档定位
- 多模态检索

目标：5~10 个。

------

# 六、每个 GitHub 项目必须输出

不要只给我项目名称和链接。

每个项目按照下面格式分析：

## 项目名称

GitHub：

Stars：

最后更新时间：

License：

### 1. 解决什么问题？

### 2. 技术栈

### 3. 架构

用文字描述完整数据流：

用户问题
→ ...
→ ...
→ 最终答案

### 4. 哪些代码值得 ConstructionAgent 借鉴？

必须指出具体：

- 哪个目录
- 哪个模块
- 哪个 Agent
- 哪个 RAG Pipeline
- 哪个设计模式

不要只说“架构值得参考”。

### 5. ConstructionAgent 可以借鉴什么？

明确列出：

- 可以直接参考
- 可以改造
- 不建议采用

### 6. 存在什么问题？

例如：

- Demo 性质太强
- 代码不完整
- Star 很高但架构过时
- 没有测试
- 没有生产部署
- 文档不完整
- 依赖版本老旧
- 业务场景不匹配

------

# 七、最终不要直接写代码

第一轮任务的最终输出必须是：

## 1. GitHub 项目排行榜

给出 Top 15。

## 2. ConstructionAgent 技术能力矩阵

例如：

| 能力        | 项目A | 项目B | 项目C | 是否值得采用 |
| ----------- | ----- | ----- | ----- | ------------ |
| Multi-Agent | ✓     | ✓     |       | ✓            |
| Hybrid RAG  | ✓     |       | ✓     | ✓            |
| Reranker    | ✓     | ✓     |       | ✓            |
| HITL        |       | ✓     |       | ✓            |
| PDF解析     | ✓     |       | ✓     | ✓            |
| 图纸理解    |       | ✓     |       | 重点研究     |

## 3. 技术方案候选

分别给出：

### Agent 架构候选

方案 A：
方案 B：
方案 C：

### RAG 架构候选

方案 A：
方案 B：
方案 C：

### 文档/图纸处理候选

方案 A：
方案 B：
方案 C：

## 4. 最终推荐

不要直接决定全部技术栈。

请明确区分：

- 必须采用
- 强烈推荐
- 可以考虑
- 暂时不要做

## 5. 第二轮 GitHub 搜索关键词

根据第一轮结果，自动总结下一轮应该继续搜索的关键词。

------

# 八、重要要求

不要为了凑数量推荐项目。

如果一个项目只有 Demo 价值，就明确标记为 Demo。

如果项目与 ConstructionAgent 非常匹配，即使 Star 很少，也可以进入推荐。

优先关注：

「代码质量 + 架构思想 + 与 ConstructionAgent 的匹配程度」

而不是单纯 Star 数量。

第一轮只做技术调研和项目筛选。

**不要开始实现 ConstructionAgent。**