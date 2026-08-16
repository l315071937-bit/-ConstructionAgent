# ConstructionAgent 第二轮：GitHub 技术调研反向验证

## 你的身份

你现在不是项目开发助手，也不是继续推荐 GitHub 项目的助手。

你现在是 ConstructionAgent 的「技术尽调 / 反向验证工程师」。

上一轮你已经生成了一份：
《ConstructionAgent GitHub 第一轮技术调研报告》

本轮任务不是扩充项目数量，而是：

> 对第一轮报告中的关键技术结论逐条提出质疑，并通过 GitHub 源码、官方文档、Issue / Release 等证据进行验证。

最终目标：

把第一轮的“推荐意见”，变成可以支撑 ConstructionAgent V1 技术选型的“证据”。

---

# 一、第一轮报告

请先读取上一轮生成的：

《ConstructionAgent GitHub 第一轮技术调研报告》

不要重新从零开始。

如果报告文件位置不明确，先搜索当前项目目录，找到该报告。

---

# 二、核心原则

本轮必须遵守：

1. 不要默认第一轮结论正确。
2. 不要因为 GitHub Star 高就认为适合。
3. 不要因为项目 README 写了某个技术，就认定源码真正实现了。
4. 必须尽可能查看源码。
5. 必须优先使用官方 GitHub Repository、官方 Documentation、官方 Release。
6. 对无法验证的结论明确标记“证据不足”。
7. 不允许为了得到明确结论而猜测。
8. 区分：
   - 事实
   - 推断
   - 推荐
9. 如果第一轮结论错误，要明确推翻，而不是维护原结论。
10. 不要开始写 ConstructionAgent 代码。

---

# 三、第一轮项目重新分类

不要继续使用单纯 Star / 综合评分作为最终依据。

重新将项目分为：

### A：业务高度相关

真正和 Construction / Engineering / Drawing / Enterprise Knowledge / Document AI 高度相关。

### B：Agent / RAG 架构参考

业务不一定是建筑，但 Agent、RAG、Workflow、HITL 等值得学习。

### C：专项技术参考

例如：

- PDF
- OCR
- Layout
- Table
- CAD
- Drawing
- Multimodal
- Citation

### D：不建议继续研究

与 ConstructionAgent 实际需求关系弱，或者项目质量/活跃度不足。

每个项目必须给出分类理由。

---

# 四、重点验证以下 10 个核心结论

## 结论 1：LangGraph 是否真的应该作为 V1 Agent 编排框架？

第一轮报告如果认为：

“LangGraph 是 ConstructionAgent 必须采用的底座”

本轮必须反向验证。

比较：

- LangGraph
- 普通 Python Workflow
- LlamaIndex Workflow
- Haystack Pipeline
- CrewAI（如果第一轮涉及）

重点回答：

### A

ConstructionAgent 当前只有：

- 项目知识检索 Agent
- 规范查询 Agent
- 施工方案 Agent

是否真的需要 LangGraph？

### B

LangGraph 的哪些能力是真正解决 ConstructionAgent 问题的？

重点验证：

- State
- Conditional Routing
- Checkpoint
- Interrupt
- Resume
- Human-in-the-loop
- Subgraph

### C

必须找到 GitHub 源码中的实际实现位置。

输出：

Repository
→ 文件
→ 类 / 函数
→ 具体作用

### D

最终结论只能是：

- 必须采用
- 强烈推荐
- 可以采用
- 暂时不需要

并说明原因。

---

# 五、结论 2：Milvus 是否真的适合作为 ConstructionAgent V1 Vector Store？

重点验证：

- Dense Vector
- Sparse Vector
- BM25
- Hybrid Search
- Metadata Filter
- Partition Key
- Multi-tenant / Multi-project
- Rerank

特别验证：

### 1

第一轮报告说 Milvus 支持 BM25。

请查官方文档和源码，确认：

- 哪个版本开始支持
- 如何实现
- 是 Milvus 内部能力还是外部组件
- 是否适合中文建筑规范检索

### 2

验证：

“Partition Key = 项目数据物理安全隔离”

这个说法是否准确。

必须区分：

- 查询路由
- 性能优化
- 数据隔离
- 权限控制
- 安全边界

如果 Partition Key 不能作为真正的权限安全边界，必须明确指出。

### 3

比较：

Milvus
vs
Qdrant
vs
Elasticsearch / OpenSearch

只比较 ConstructionAgent V1 真正需要的能力。

不要为了比较而比较。

---

# 六、结论 3：BGE-M3 + Reranker 是否真的适合中文建筑规范？

验证：

- BGE-M3 dense embedding
- BGE-M3 sparse / lexical ability
- BM25
- bge-reranker

重点考虑 ConstructionAgent 的真实查询：

例如：

“剪力墙水平分布筋最小配筋率是多少？”

“框架梁箍筋加密区长度如何确定？”

“地下室外墙防水做法有哪些？”

“GB 55037 第 X 条要求是什么？”

“施工方案中模板支撑体系有什么要求？”

分析：

### Dense Search

适合什么？

### BM25

适合什么？

### Sparse

适合什么？

### Reranker

解决什么？

最后判断 V1 推荐：

方案 A：

BGE-M3 Dense
+
BM25
+
Reranker

还是：

BGE-M3 Dense
+
BGE-M3 Sparse
+
Reranker

还是其他方案。

不要默认第一轮答案。

---

# 七、结论 4：PyMuPDF + PaddleOCR + MinerU 的分层解析方案是否合理？

验证第一轮报告中的：

PDF
↓
PyMuPDF
↓
PaddleOCR
↓
MinerU

重点研究：

### 文本型 PDF

应该使用什么？

### 扫描 PDF

应该使用什么？

### 复杂版面

应该使用什么？

### 表格

应该使用什么？

### 图片 + 文字混排

应该使用什么？

### Word / Excel

是否应该使用完全不同的解析器？

最终形成：

DocumentParser Router

例如：

文件
↓
类型识别
↓
Parser Router
├── PyMuPDF
├── PaddleOCR
├── MinerU
├── python-docx
└── openpyxl

请验证这个设计，而不是默认它正确。

---

# 八、结论 5：RAGFlow 是否真的值得作为源码教材？

第一轮可能认为：

“RAGFlow 不部署，只学习 DeepDoc。”

请验证：

### 1

DeepDoc 当前代码结构。

### 2

哪些模块与 ConstructionAgent 真正相关：

- PDF parsing
- OCR
- Layout
- Table
- Chunking
- Metadata
- Retrieval
- Citation

### 3

哪些模块不应该学习 / 不适合直接复制？

### 4

必须给出具体 GitHub 路径。

最终输出：

| RAGFlow模块 | 是否研究 | 原因 |
| ----------- | -------- | ---- |
| DeepDoc     |          |      |
| OCR         |          |      |
| Layout      |          |      |
| Table       |          |      |
| Chunking    |          |      |
| Retrieval   |          |      |
| Citation    |          |      |

---

# 九、结论 6：建筑图纸视觉理解是否应该放到 V2？

验证第一轮关于：

- CAD
- Drawing
- Blueprint
- Multimodal
- OCR
- Object Detection
- 图纸理解

的结论。

重点不是问：

“有没有技术可以做？”

而是：

> ConstructionAgent V1 是否有必要做？

从以下角度判断：

- 实现成本
- GPU需求
- 数据集
- 标注成本
- 准确率风险
- 工程价值
- 是否影响 V1 主链路

最终明确：

V1：

做什么？

不做什么？

V2：

再加入什么？

---

# 十、结论 7：Human-in-the-loop 应该放在哪些节点？

验证第一轮报告中的 HITL 设计。

结合 ConstructionAgent：

## 场景 A

检索到企业已有施工方案模板

↓

需要人工确认：

“是否按照企业模板编制？”

## 场景 B

施工方案生成

↓

人工审核

↓

通过 / 驳回

## 场景 C

规范检索结果置信度不足

↓

是否需要人工介入？

## 场景 D

检索不到资料

↓

是否提示用户人工查看具体图号 / 文件？

请判断：

哪些必须 HITL？

哪些不应该 HITL？

否则容易变成：

“每一步都让人点确认”。

最终形成：

HITL 节点设计表。

---

# 十一、结论 8：三 Agent 架构是否合理？

当前：

1. 项目知识检索 Agent
2. 规范查询 Agent
3. 施工方案 Agent

请反向验证：

### 为什么不是一个 Agent？

### 为什么不是更多 Agent？

### 三个 Agent 的边界在哪里？

特别检查：

“项目知识检索 Agent”和“规范查询 Agent”是否真的应该拆开。

例如：

用户：

“这个项目地下室防水应该怎么做？”

可能需要：

项目资料
+
规范
+
企业标准

这时候应该：

一个 Agent？

还是：

Router
→ Project Retrieval
→ Standard Retrieval
→ Synthesis

请根据实际代码架构和 Agent 设计经验分析。

不要为了 Multi-Agent 而 Multi-Agent。

---

# 十二、结论 9：第一轮是否存在过度设计？

这是本轮最重要的检查之一。

检查第一轮是否引入了：

- GraphRAG
- Knowledge Graph
- Self-RAG
- CRAG
- Reflection
- Memory Agent
- Planner Agent
- Critic Agent
- 多模态
- CAD
- MCP
- 多数据库
- 多模型

如果没有明确业务需求，标记：

“V1 不建议”。

最终形成：

## V1 必须

## V1 推荐

## V1 暂缓

## V2 再考虑

---

# 十三、结论 10：重新审查第一轮 Top 15

每个项目必须重新检查：

1. GitHub 地址是否正确
2. License
3. 最近更新时间
4. Star
5. Fork
6. 是否仍在维护
7. README 是否和源码一致
8. 核心技术是否真的存在
9. 是否只是 Demo
10. 是否值得 ConstructionAgent 学习

重点：

不要只看 README。

至少针对排名靠前的项目：

- 查看目录结构
- 查看关键代码
- 查看 requirements / pyproject
- 查看 GitHub release
- 查看 issue
- 查看 commit

如果无法查看源码，明确：

“本结论只能作为 README 级别判断”。

---

# 十四、建立“证据等级”

所有结论必须标记证据等级：

### S级

官方源码 + 官方文档双重验证

### A级

官方源码验证

### B级

官方文档验证

### C级

README / 项目描述

### D级

第三方文章 / Blog

### E级

推测

最终技术选型：

优先使用 S / A / B 级证据。

---

# 十五、最终输出

不要再输出一篇很长的普通报告。

最终必须输出以下 6 个结果。

---

## 结果 1：第一轮结论审判

| 第一轮结论             | 是否成立 | 证据等级 | 修改意见 |
| ---------------------- | -------- | -------- | -------- |
| LangGraph 必须采用     |          |          |          |
| Milvus 最适合          |          |          |          |
| BGE-M3 + Reranker      |          |          |          |
| PyMuPDF + OCR + MinerU |          |          |          |
| RAGFlow 只学 DeepDoc   |          |          |          |
| 图纸视觉 V2            |          |          |          |
| 三 Agent               |          |          |          |
| HITL                   |          |          |          |

---

## 结果 2：GitHub 项目最终分类

### 🟢 必须研究

最多 5 个。

### 🟡 值得参考

最多 8 个。

### ⚪ 了解即可

最多 5 个。

### 🔴 淘汰

说明原因。

---

## 结果 3：ConstructionAgent V1 技术选型

严格使用：

| 技术领域   | 最终选择 | 备选 | 为什么 |
| ---------- | -------- | ---- | ------ |
| Agent      |          |      |        |
| Workflow   |          |      |        |
| Embedding  |          |      |        |
| Vector DB  |          |      |        |
| Sparse     |          |      |        |
| Reranker   |          |      |        |
| PDF        |          |      |        |
| OCR        |          |      |        |
| Word       |          |      |        |
| Excel      |          |      |        |
| Redis      |          |      |        |
| PostgreSQL |          |      |        |
| LLM        |          |      |        |

---

## 结果 4：V1 / V2 边界

### V1 必须实现

列出不超过 10 项。

### V1 暂时不做

列出不超过 10 项。

### V2 再研究

列出候选能力。

---

## 结果 5：最终架构草案

用 Mermaid 输出：

用户
→ Router
→ Agent
→ Tool / Retrieval
→ Evidence
→ Answer
→ HITL

同时说明：

State 如何流转。

---

## 结果 6：仍然无法确定的问题

这是最重要的。

列出：

> 即使进行了第二轮验证，目前仍无法确定的技术问题。

并告诉我：

- 需要做什么实验
- 需要 Benchmark 什么
- 需要什么数据

不要强行给答案。

---

# 十六、最终禁止事项

本轮禁止：

❌ 开始写 ConstructionAgent 代码

❌ 创建项目目录

❌ 自动安装依赖

❌ 为了证明第一轮正确而选择性寻找证据

❌ 因为 GitHub Star 高就推荐

❌ 把“README 宣称支持”当成“源码已经实现”

❌ 为了让架构看起来高级而增加 Agent

本轮唯一任务：

> **验证第一轮报告，推翻错误结论，保留有证据支持的结论，最终形成 ConstructionAgent V1 的可靠技术选型。**