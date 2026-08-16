```
# 建筑工程智能 Agent 系统
# 02_AGENT_SPEC.md

> Version: V1.0
> Status: Agent Design Freeze
> Purpose: Claude Code 开发基准文档
>
> 本文档定义 ConstructionAgent 三个核心 Agent 的职责、State、Graph、Node、
> Tool、Service、Prompt、路由、错误处理、Evidence、HITL 以及 Agent 之间的调用关系。
>
> Claude Code 必须按照本文档实现。
> 不允许为了追求“多 Agent”而增加没有实际业务价值的 Agent。

---

# 1. 三 Agent 总览

系统 V1 只有三个核心业务 Agent：

​```text
┌──────────────────────────────────────────────┐
│                 Orchestrator                 │
│                统一任务编排层                 │
└──────────────────┬───────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
┌────────────┐ ┌────────────┐ ┌─────────────────┐
│ Project    │ │ Standard   │ │ Construction    │
│ Retrieval  │ │ Query      │ │ Plan            │
│ Agent      │ │ Agent      │ │ Agent           │
└────────────┘ └────────────┘ └─────────────────┘
```

三个 Agent 的核心问题分别是：

```
Project Retrieval Agent
    ↓
“项目里是什么？”

Standard Query Agent
    ↓
“规范怎么规定？”

Construction Plan Agent
    ↓
“结合项目和规范，方案怎么做？”
```

------

# 2. Agent 职责边界

## 2.1 Project Retrieval Agent

负责项目知识检索。

输入：

```
用户问题
project_id
conversation_context
```

数据来源：

```
项目图纸
项目文档
设计说明
施工图
竣工图
表格
图片
OCR
项目内部资料
```

输出：

```
Answer
Evidence[]
Confidence
Conflict[]
```

------

## 2.2 Standard Query Agent

负责工程规范、标准和图集查询。

输入：

```
用户问题
地区
专业
项目上下文
```

数据来源：

```
国家标准
行业标准
地方标准
地方规范
标准图集
企业标准
```

输出：

```
Answer
Standard Evidence[]
Confidence
Applicability
Version Information
```

------

## 2.3 Construction Plan Agent

负责施工方案辅助编制。

输入：

```
施工任务
项目上下文
项目 Evidence
规范 Evidence
企业模板
```

输出：

```
Plan Outline
Plan Content
Project Evidence[]
Standard Evidence[]
Warnings[]
Human Review Items[]
Generated Document
```

------

# 3. Agent 设计原则

所有 Agent 必须遵循：

```
State Driven
+
Evidence First
+
Retrieval First
+
Deterministic Tools
+
LLM Generation
+
Human Review
```

Agent 不应该成为一个：

```
巨大 Prompt
+
一个 LLM Call
```

而应该：

```
Input
 ↓
Analysis
 ↓
Retrieval
 ↓
Validation
 ↓
Generation
 ↓
Verification
 ↓
Output
```

------

# 4. Agent 目录结构

```
backend/
└── agents/
    │
    ├── project_retrieval/
    │   ├── __init__.py
    │   ├── graph.py
    │   ├── state.py
    │   ├── nodes.py
    │   ├── tools.py
    │   ├── prompts.py
    │   └── schemas.py
    │
    ├── standard_query/
    │   ├── __init__.py
    │   ├── graph.py
    │   ├── state.py
    │   ├── nodes.py
    │   ├── tools.py
    │   ├── prompts.py
    │   └── schemas.py
    │
    └── construction_plan/
        ├── __init__.py
        ├── graph.py
        ├── state.py
        ├── nodes.py
        ├── tools.py
        ├── prompts.py
        └── schemas.py
```

------

# 5. Agent State 总体原则

每个 Agent 使用独立 State。

不要：

```
三个 Agent 共用一个巨大 State
```

推荐：

```
ProjectRetrievalState
StandardQueryState
ConstructionPlanState
```

------

# 6. Project Retrieval Agent

# 6.1 业务目标

解决：

> “项目资料里面到底是什么？”

例如：

```
深圳市政消防道路做法是怎么样的？

3号楼卫生间防水高度是多少？

A-205 图纸中这个构造是什么？

这个区域的材料规格是什么？

项目里有没有关于消防道路的说明？
```

------

# 6.2 Project Retrieval State

建议：

```
class ProjectRetrievalState(TypedDict, total=False):

    # Request
    request_id: str
    user_id: int
    tenant_id: int
    project_id: int

    # Query
    original_query: str
    rewritten_query: str
    query_type: str

    # Retrieval
    filters: dict
    bm25_results: list
    vector_results: list
    merged_results: list
    reranked_results: list

    # Evidence
    evidences: list
    conflicts: list

    # LLM
    answer: str

    # Quality
    confidence: float
    retrieval_status: str

    # Control
    retry_count: int
    fallback_level: int

    # HITL
    human_required: bool
    human_reason: str

    # Error
    error: str | None
```

------

# 6.3 Project Retrieval Graph

```
START
  ↓
validate_input
  ↓
analyze_query
  ↓
build_filters
  ↓
parallel_retrieval
  ├──────────────┐
  ↓              ↓
BM25          Vector
  │              │
  └──────┬───────┘
         ↓
merge_results
         ↓
rerank
         ↓
build_evidence
         ↓
detect_conflict
         ↓
check_confidence
         │
    ┌────┼───────────────┐
    │    │               │
    ▼    ▼               ▼
  High  Low           Conflict
    │    │               │
    │    ▼               ▼
    │  query_rewrite    HITL
    │    │
    │    ▼
    │  retrieve_again
    │
    ▼
generate_answer
    ↓
validate_answer
    ↓
END
```

------

# 6.4 Node：validate_input

职责：

```
验证：
user_id
tenant_id
project_id
query
```

检查：

```
query 是否为空
project_id 是否存在
用户是否有项目权限
```

失败：

```
直接返回业务错误
```

------

# 6.5 Node：analyze_query

职责：

识别用户问题特点。

输出：

```
query_type
```

例如：

```
DIMENSION
MATERIAL
DRAWING
LOCATION
PROCESS
PROJECT_SPEC
GENERAL_PROJECT_QUERY
```

同时识别：

```
图号
楼栋
楼层
专业
材料
构件
区域
编号
```

例如：

```
“3号楼二层卫生间防水高度是多少？”

解析：

building = 3#
floor = 2F
discipline = architecture
topic = waterproofing
query_type = DIMENSION
```

------

# 6.6 Node：build_filters

将 query 转成检索 Metadata Filter。

例如：

```
{
    "project_id": 1001,
    "building": "3#",
    "floor": "2F",
    "discipline": "architecture"
}
```

注意：

> project_id 必须作为强制过滤条件。

------

# 6.7 Node：parallel_retrieval

执行：

```
BM25
+
Vector Search
```

可以使用 asyncio 并发。

伪代码：

```
bm25_task = bm25_search(...)
vector_task = vector_search(...)

bm25_results, vector_results = await asyncio.gather(
    bm25_task,
    vector_task
)
```

------

# 6.8 Tool：BM25 Search

```
async def search_bm25(
    query: str,
    filters: dict,
    top_k: int = 20
):
    ...
```

适合：

```
图号
编号
尺寸
材料
规范编号
专业术语
精确短语
```

------

# 6.9 Tool：Vector Search

```
async def search_vector(
    query: str,
    filters: dict,
    top_k: int = 20
):
    ...
```

适合：

```
自然语言
语义表达
描述性问题
相似表达
```

------

# 6.10 Node：merge_results

将：

```
BM25 Top 20
+
Vector Top 20
```

合并。

要求：

```
去重
保留来源
保留原始 score
保留 retrieval_method
```

例如：

```
{
    "chunk_id": "chunk_001",
    "bm25_score": 12.4,
    "vector_score": 0.81,
    "retrieval_methods": [
        "bm25",
        "vector"
    ]
}
```

------

# 6.11 Node：rerank

调用：

```
BGE-Reranker
```

输入：

```
query
+
merged_results
```

输出：

```
Top 5~10
```

如果 Reranker 失败：

```
fallback_level += 1

使用 merged_results
```

不能因为 Reranker 失败直接终止整个任务。

------

# 6.12 Node：build_evidence

将检索结果转换成统一 Evidence。

必须包含：

```
evidence_id
file_id
file_name
page
content
score
thumbnail_url
source_type
version
metadata
```

------

# 6.13 Node：detect_conflict

检测：

```
多个 Evidence 是否表达不同事实
```

例如：

```
Evidence A
防水高度 = 1800mm

Evidence B
防水高度 = 1500mm
```

判断：

```
conflict = true
```

输出：

```
{
    "conflict_type": "VALUE_CONFLICT",
    "field": "waterproof_height",
    "evidence_ids": [
        "ev_001",
        "ev_002"
    ]
}
```

------

# 6.14 Conflict 处理

如果发现高风险冲突：

```
detect_conflict
       ↓
human_required = true
       ↓
WAITING_HUMAN
```

前端展示：

```
⚠ 项目资料存在冲突

A-205：
1800mm

A-312：
1500mm

请确认采用哪一个资料。
```

------

# 6.15 Node：check_confidence

建议初始规则：

```
High:
Top evidence score >= threshold
AND
至少 2 个高质量 Evidence
AND
无冲突

Medium:
有 Evidence
但证据较弱

Low:
没有可靠 Evidence
```

V1 不要求复杂机器学习 Confidence Model。

先使用：

```
规则 + Retrieval Score
```

------

# 6.16 Low Confidence

如果：

```
confidence == LOW
```

进入：

```
query_rewrite
```

------

# 6.17 Node：query_rewrite

例如：

原问题：

```
消防道路怎么做？
```

Rewrite：

```
深圳市政项目
消防车道
消防道路
路面结构做法
路面材料
设计说明
标准图集
```

然后：

```
retrieve_again
```

最多：

```
V1：1~2 次
```

禁止无限循环。

------

# 6.18 第三层兜底

如果：

```
第一次检索失败
+
Rewrite 失败
+
第二次检索仍失败
```

不要编造答案。

返回：

```
未找到足够项目依据。

推荐人工查看：

1. A-205
2. A-312
3. S-102

[查看文件]
```

------

# 6.19 Node：generate_answer

Prompt 必须要求：

```
只能依据 Evidence
不能补充项目中不存在的事实
不能伪造图号
不能伪造页码
不能伪造尺寸
```

输出：

```
answer
+
evidence_ids
```

------

# 6.20 Node：validate_answer

检查：

```
回答中的数字
回答中的图号
回答中的材料
回答中的规范
```

是否能够在 Evidence 中找到。

如果：

```
Answer 提到 1800mm
```

但 Evidence 没有：

```
FAIL
```

重新生成或降级。

------

# 7. Standard Query Agent

# 7.1 业务目标

解决：

> “规范到底怎么规定？”

例如：

```
深圳市政消防道路有什么要求？

消防车道宽度规范要求是多少？

这个施工做法有什么规范依据？

这个做法对应哪本标准图集？
```

------

# 7.2 Standard Query State

```
class StandardQueryState(TypedDict, total=False):

    request_id: str
    user_id: int
    tenant_id: int
    project_id: int | None

    original_query: str
    rewritten_query: str

    region: str | None
    discipline: str | None
    standard_type: str | None

    filters: dict

    bm25_results: list
    vector_results: list
    merged_results: list
    reranked_results: list

    evidences: list

    applicability: dict
    version_info: dict

    answer: str

    confidence: float

    retry_count: int
    fallback_level: int

    human_required: bool
    human_reason: str

    error: str | None
```

------

# 7.3 Standard Query Graph

```
START
  ↓
validate_input
  ↓
analyze_standard_query
  ↓
identify_region
  ↓
identify_discipline
  ↓
build_standard_filters
  ↓
parallel_retrieval
  ├───────────────┐
  ↓               ↓
BM25            Vector
  │               │
  └───────┬───────┘
          ↓
merge
          ↓
rerank
          ↓
version_check
          ↓
applicability_check
          ↓
build_evidence
          ↓
confidence
          │
     ┌────┴─────┐
     ▼          ▼
   High       Low
     │          │
     │      query_rewrite
     │          │
     ▼          ▼
generate_answer
     ↓
validate_answer
     ↓
END
```

------

# 7.4 Node：analyze_standard_query

识别：

```
地区
专业
标准类型
主题
规范编号
```

例如：

```
“深圳市政消防道路有什么要求？”

region = 深圳
discipline = 市政
topic = 消防道路
```

------

# 7.5 地区优先级

标准查询必须考虑地区。

推荐过滤顺序：

```
项目指定地区
    ↓
地方标准
    ↓
行业标准
    ↓
国家标准
```

例如项目位于深圳：

```
深圳地方标准
>
广东地方标准
>
国家标准
```

但不是绝对覆盖关系。

最终仍然需要根据：

```
适用范围
发布日期
有效状态
```

判断。

------

# 7.6 标准版本检查

必须检查：

```
standard_code
standard_name
version
publish_date
effective_date
status
```

例如：

```
GB/T XXXXX-2020
```

需要确认：

```
现行
废止
替代
即将实施
```

V1 如果知识库中无法确认状态：

```
明确告诉用户：

“当前知识库无法确认该标准最新有效状态。”
```

禁止：

```
LLM 猜测“这是现行标准”。
```

------

# 7.7 Applicability Check

判断：

```
该规范
+
当前地区
+
当前专业
+
当前工程场景
```

是否匹配。

例如：

```
建筑工程
```

不能因为搜索到：

```
道路交通规范
```

就直接认为适用。

------

# 7.8 Standard Evidence

必须保存：

```
standard_code
standard_name
article
page
content
version
status
effective_date
```

例如：

```
{
    "standard_code": "GB XXXXX",
    "standard_name": "XXXX标准",
    "article": "5.2.3",
    "page": 34,
    "content": "......",
    "version": "2025",
    "status": "active"
}
```

------

# 7.9 Standard Answer

输出结构建议：

```
结论

根据：
《XXXX》
第 X.X.X 条

要求：
XXXX。

适用范围：
XXXX。

注意：
XXXX。

Evidence：
[规范 PDF 第 34 页]
```

------

# 7.10 Standard Agent 禁止事项

禁止：

```
编造规范编号
编造条款
编造页码
编造规范名称
编造标准版本
把推荐值说成强制值
把项目做法说成国家标准
```

------

# 8. Construction Plan Agent

# 8.1 业务目标

负责：

> “基于真实项目资料和规范生成施工方案。”

------

# 8.2 输入

```
用户任务
+
project_id
+
project_context
+
enterprise_template
```

------

# 8.3 输出

```
Plan
+
Project Evidence
+
Standard Evidence
+
Warnings
+
Human Review
```

------

# 8.4 Construction Plan State

```
class ConstructionPlanState(TypedDict, total=False):

    # Request
    request_id: str
    user_id: int
    tenant_id: int
    project_id: int

    # Task
    original_request: str
    task_type: str

    # Project
    project_context: dict
    project_evidences: list

    # Standard
    standard_query: str
    standard_evidences: list

    # Template
    template_id: str | None
    template_name: str | None
    template_content: str | None

    # Plan
    outline: list
    plan_facts: dict            # 已定事实表：生成各章节前注入、章节生成后回写、四查时跨章一致性校验
    current_section: str
    generated_sections: list

    # Validation
    fact_check_results: list
    standard_check_results: list
    completeness_results: list
    risk_results: list

    # Human
    human_required: bool
    human_reason: str
    human_decision: dict

    # Output
    final_content: str
    document_id: str | None
    download_url: str | None

    # Control
    retry_count: int
    fallback_level: int

    # Error
    error: str | None
```

------

# 8.5 Construction Plan Graph

```
START
  ↓
validate_request
  ↓
analyze_plan_task
  ↓
retrieve_template
  ↓
template_check
  │
  ├── no template → human_confirm
  │
  └── template found
           ↓
      human_confirm_template
           ↓
      generate_outline
           ↓
      human_confirm_outline
           ↓
      retrieve_reference_plans
           ↓
      retrieve_project_context
           ↓
      retrieve_standard_context
           ↓
      generate_plan_sections
           ↓
      fact_check
           ↓
      standard_check
           ↓
      completeness_check
           ↓
      risk_check
           ↓
      final_review
           ↓
      generate_document
           ↓
          END
```

------

# 8.6 Node：analyze_plan_task

识别：

```
施工专业
施工对象
施工阶段
施工范围
```

例如：

```
“编制地下室防水施工方案”

task_type = waterproofing
discipline = architecture
object = basement
```

------

# 8.7 Node：retrieve_template

查询：

```
Enterprise Template Knowledge Base
```

例如：

```
地下室防水施工方案模板
```

如果：

```
Top 1
```

置信度足够：

```
进入模板确认
```

------

# 8.8 Node：human_confirm_template

前端：

```
检测到以下企业模板：

《XX公司地下室防水施工方案模板》

版本：2025

是否使用？

[使用该模板]
[选择其他模板]
[不使用模板]
```

状态：

```
WAITING_HUMAN
```

------

# 8.9 Node：generate_outline

根据：

```
企业模板
+
项目任务
+
工程规范
```

生成：

```
1. 工程概况
2. 编制依据
3. 施工准备
4. 材料要求
5. 施工工艺
6. 质量控制
7. 安全措施
8. 成品保护
9. 验收要求
10. 应急措施
```

注意：

> 以上只是示例，不允许写死为所有方案固定结构。

应优先遵循企业模板。

------

# 8.10 Node：human_confirm_outline

用户可以：

```
确认
修改
删除章节
增加章节
调整顺序
```

然后继续。

------

# 8.10.1 Node：retrieve_reference_plans

在目录确认之后，检索企业知识库中的**历史优秀方案**（与 task_type 相同的同专业方案）。

输出：

```
reference_plans
```

用途：

1. 作为分章节生成时的**结构/措辞参考**（真实业务中技术员编方案的第一动作是"找上一份同专业旧方案改"，本节点是把这一工作习惯 AI 化）；
2. 不直接复制历史方案内容——历史方案中的工程参数可能与本项目冲突，只作风格与工艺组织参考；
3. 检索不到历史方案时**不阻塞流程**（跳过，仅使用模板 + 规范 + 项目资料）。

---

# 8.11 Node：retrieve_project_context

项目 Agent 不需要重新启动完整 Graph。

Construction Plan Agent 调用：

```
ProjectRetrievalService
```

获取：

```
项目名称
建筑面积
楼栋
施工范围
结构
材料
工程参数
相关图纸
```

输出：

```
project_evidences
```

------

# 8.12 Node：retrieve_standard_context

调用：

```
StandardRetrievalService
```

获取：

```
规范
标准
图集
验收要求
质量要求
安全要求
```

输出：

```
standard_evidences
```

------

# 8.13 Agent 间调用原则

Construction Plan Agent：

```
不直接调用：
ProjectRetrievalAgent.graph()
```

也不：

```
StandardQueryAgent.graph()
```

而是：

```
Construction Plan
       ↓
ProjectRetrievalService
       ↓
Knowledge Retrieval
```

以及：

```
Construction Plan
       ↓
StandardRetrievalService
       ↓
Knowledge Retrieval
```

这样：

```
Agent = Workflow
Service = Capability
```

------

# 8.14 Node：generate_plan_sections

每个章节独立生成。

例如：

```
工程概况
施工准备
施工工艺
质量控制
安全措施
```

不要：

```
一个 Prompt 一次生成整篇 10000 字方案。
```

推荐：

```
Outline
 ↓
Section 1
 ↓
Section 2
 ↓
Section 3
 ...
```

好处：

```
更稳定
更容易重试
更容易检查
更容易修改
```

同时必须遵守**已定事实表机制**：

```
生成每个章节前
    ↓
把 plan_facts（已锁定工程参数）注入该章节 Prompt
    ↓
章节生成后
    ↓
提取本章新出现的工程事实（参数/材料/做法）
    ↓
与 plan_facts 比对：
  - 一致 → 保留
  - 缺失 → 回写 plan_facts
  - 冲突 → 标记 conflict，按事实检查规则处理
```

> 目的：防止分章节生成导致跨章矛盾（如第 3 章 C30 混凝土、第 6 章写成 C25）。
> 这是长文档一致性的必要条件（2026-08-15 可行性体检结论）。

------

# 8.15 Section State

每个章节可以记录：

```
{
    "section_id": "section_01",
    "title": "工程概况",
    "status": "COMPLETED",
    "content": "...",
    "evidence_ids": [
        "ev_001",
        "ev_002"
    ]
}
```

------

# 8.16 Fact Check

检查：

```
项目名称
建筑面积
楼栋
层数
尺寸
材料
施工范围
工程参数
```

必须能够映射到：

```
Project Evidence
```

如果无法映射：

```
[待人工确认]
```

同时必须执行**跨章一致性检查**：

```
各章节生成的工程事实
        ↓
与 plan_facts（已定事实表）逐条比对
        ↓
发现不一致（如章节 A 与章节 B 同一参数不同值）
        ↓
标记 conflict + 回写修正 + 进入终审风险清单
```

> 2026-08-15 补充：事实检查从「单章对照 Project Evidence」扩展为
> 「单章对照 Evidence + 跨章对照 plan_facts」双重校验。

------

# 8.17 Standard Check

检查：

```
规范编号
规范名称
条款
技术要求
验收要求
```

必须能够映射到：

```
Standard Evidence
```

------

# 8.18 Completeness Check

检查方案是否缺失：

```
施工准备
材料
机械
人员
施工工艺
质量
安全
环保
成品保护
验收
```

具体检查项根据：

```
企业模板
+
施工类型
```

动态生成。

------

# 8.19 Risk Check

重点检查：

```
危险作业
高处作业
临电
机械
消防
基坑
吊装
防护
应急
```

V1：

```
规则检查
+
LLM 辅助检查
```

不能宣称：

```
“方案已完全满足安全要求”
```

只能：

```
“AI 初步检查发现以下风险项，请专业人员审核。”
```

**危大工程特别规则**（2026-08-15 补充）：

```
当 task_type 命中危大工程范围
（脚手架、模板支撑、深基坑、起重吊装、拆除工程等）时：

1. 生成结果必须显式标注：
   「本方案为 AI 辅助起草，须经专家论证后方可实施」；
2. 风险检查强制升级：
   逐条对照危大工程专项规范清单执行检查，不因篇幅跳过；
3. 终审 HITL 的提示文案升级为红色警示样式。
```

> 依据：住建部危大工程管理制度（专家论证制度）。
> 这是产品安全定位问题：AI 辅助结构/危大专业方案时，不标注即埋雷。

------

# 8.20 Final Review

最终：

```
Project Evidence
+
Standard Evidence
+
Generated Plan
+
Validation Result
```

进入：

```
WAITING_HUMAN
```

用户确认：

```
[通过]
[返回修改]
```

------

# 8.21 Document Generation

最终输出：

```
DOCX
PDF
```

保存：

```
MinIO
```

数据库：

```
generated_documents
```

记录：

```
document_id
task_id
project_id
file_name
object_key
version
created_by
created_at
```

------

# 9. 三 Agent 协作场景

## 场景一：普通项目查询

用户：

```
深圳市政消防道路做法是怎么样的？
```

Orchestrator 判断：

```
主要是项目资料查询
```

调用：

```
Project Retrieval Agent
```

如果用户继续：

```
这个做法符合规范吗？
```

调用：

```
Standard Query Agent
```

------

# 10. 场景二：方案编制

用户：

```
帮我编制消防道路施工方案。
```

Orchestrator：

```
Construction Plan Agent
```

内部：

```
Plan Agent
 ↓
ProjectRetrievalService
 ↓
获取项目道路资料
```

然后：

```
Plan Agent
 ↓
StandardRetrievalService
 ↓
获取消防道路规范
```

最后：

```
Project Evidence
+
Standard Evidence
+
Enterprise Template
 ↓
Construction Plan
```

------

# 11. 场景三：混合问题

用户：

```
我们这个项目消防道路现在设计的是4米，
这个尺寸是否符合深圳规范？
```

这是：

```
Project Fact
+
Standard Validation
```

推荐流程：

```
Orchestrator
       ↓
Project Retrieval Agent
       ↓
确认项目设计值 = 4m
       ↓
Standard Query Agent
       ↓
查询规范要求
       ↓
Comparison
       ↓
Answer
```

最终：

```
项目设计值：
4m

规范要求：
XXXX

判断：
XXXX

Evidence：
项目图纸 + 规范条款
```

------

# 12. Comparison 机制

对于：

```
项目值
vs
规范值
```

不要单纯让 LLM 判断。

应该：

```
Project Evidence
+
Standard Evidence
        ↓
Structured Comparison
        ↓
LLM Explanation
```

例如：

```
{
    "project_value": 4.0,
    "standard_min_value": 4.0,
    "unit": "m",
    "result": "PASS"
}
```

如果是：

```
3.5m
```

则：

```
result = "FAIL"
```

------

# 13. Orchestrator 与 Agent 的关系

Orchestrator：

```
决定“调用谁”
```

Agent：

```
决定“怎么完成任务”
```

Service：

```
提供“能力”
```

Knowledge：

```
提供“数据”
```

LLM：

```
提供“推理和生成”
```

------

# 14. 标准化 Agent Interface

每个 Agent 应提供：

```
class BaseAgent:

    async def run(
        self,
        input_data: dict
    ) -> dict:
        ...
```

但每个 Agent 使用自己的 State。

例如：

```
ProjectRetrievalAgent.run()
StandardQueryAgent.run()
ConstructionPlanAgent.run()
```

统一返回：

```
{
    "task_id": "task_001",
    "status": "COMPLETED",
    "answer": "...",
    "evidences": [],
    "warnings": [],
    "human_required": false
}
```

------

# 15. Agent Output Schema

统一：

```
class AgentResult(BaseModel):

    task_id: str

    status: str

    answer: str | None

    evidences: list[Evidence]

    warnings: list[str]

    confidence: float | None

    human_required: bool

    human_reason: str | None
```

施工方案额外：

```
class PlanAgentResult(AgentResult):

    outline: list
    document_id: str | None
```

------

# 16. Prompt 设计原则

Prompt 分为：

```
System Prompt
+
Task Prompt
+
Evidence Context
+
Output Schema
```

不要把：

```
项目资料
规范
用户问题
系统规则
```

全部拼成一个超长 Prompt。

------

# 17. Evidence 注入

推荐：

```
用户问题

↓

项目 Evidence

[EV001]
文件：A-205.pdf
页码：12
内容：...

[EV002]
文件：A-312.pdf
页码：8
内容：...

↓

LLM
```

要求：

```
回答必须引用 Evidence ID。
```

------

# 18. Prompt 核心规则

所有 Agent 都需要：

```
1. 不得编造事实
2. 不得编造 Evidence
3. 不得伪造页码
4. 不得伪造图号
5. 不得伪造规范条款
6. 证据不足时明确说明
7. 存在冲突时不得自行选择
8. 需要人工确认时必须暂停
```

------

# 19. Agent Retry

每个 Node 不应该无限 Retry。

建议：

```
max_retry = 2
```

流程：

```
失败
 ↓
Retry 1
 ↓
Retry 2
 ↓
Fallback
```

------

# 20. Agent Failure Classification

错误分为：

```
TRANSIENT
RETRIEVAL
LLM
VALIDATION
BUSINESS
PERMISSION
HUMAN_REQUIRED
```

例如：

```
LLM API Timeout
→ TRANSIENT

没有检索结果
→ RETRIEVAL

用户没有项目权限
→ PERMISSION

发现图纸冲突
→ HUMAN_REQUIRED
```

------

# 21. 三层兜底

统一：

```
Layer 1
Retry
    ↓
Layer 2
Agent / Retrieval Degradation
    ↓
Layer 3
Human / Manual Search
```

------

# 22. Agent Observability

每个 Agent Task 至少记录：

```
task_id
agent_name
node_name
start_time
end_time
duration
status
error
retry_count
token_usage
```

用于：

```
性能分析
错误排查
成本分析
Agent 调试
```

------

# 23. Node 日志

示例：

```
task=task_001
agent=project_retrieval
node=rerank
status=completed
duration=0.82s
result_count=8
```

禁止日志输出：

```
用户密码
JWT
敏感 Token
完整私有文档
```

------

# 24. Agent 性能目标

V1 初始目标：

## Project Retrieval

```
普通查询：
< 5 秒

复杂查询：
< 10 秒
```

------

## Standard Query

```
普通查询：
< 5 秒
```

------

## Construction Plan

由于属于长任务：

```
异步 Task
+
SSE
```

不要求同步 HTTP 等待。

------

# 25. Agent 测试

每个 Agent 至少需要：

```
正常问题
无结果问题
低置信问题
冲突问题
权限问题
LLM 失败
Reranker 失败
BM25 失败
Vector 失败
HITL
```

------

# 26. Project Agent Test Cases

例如：

```
TC-P-001
问题：
3号楼二层卫生间防水高度是多少？

预期：
找到对应图纸
返回页码
返回 Evidence
TC-P-002
问题：
项目里有没有消防道路设计？

预期：
返回相关图纸 / 文档
TC-P-003
问题：
XXX项目不存在的参数是多少？

预期：
不能编造
TC-P-004
存在两个不同尺寸

预期：
Conflict
+
HITL
```

------

# 27. Standard Agent Test Cases

```
TC-S-001
查询某标准具体条款
TC-S-002
查询地方规范
TC-S-003
查询已经废止的标准
TC-S-004
规范库中不存在
TC-S-005
多个规范存在冲突
```

预期：

```
明确 Evidence
+
版本
+
适用性
```

------

# 28. Construction Plan Test Cases

```
TC-C-001
存在企业模板
TC-C-002
多个模板
TC-C-003
不存在模板
TC-C-004
项目资料不足
TC-C-005
规范资料不足
TC-C-006
生成后存在事实错误
TC-C-007
用户中途修改方案结构

TC-C-008
企业知识库存在/不存在历史同专业方案

预期：
存在 → 检索到并作为风格参考；不存在 → 不阻塞流程

TC-C-009
分章节生成后出现跨章参数不一致
（第 3 章 C30 / 第 6 章 C25）

预期：
plan_facts 比对发现 conflict → 回写修正 → 进入终审风险清单

TC-C-010
task_type 命中危大工程（如模板支撑）

预期：
生成结果显式标注「须经专家论证」+ 风险检查强制升级 + 终审红色警示
```

------

# 29. Agent 开发优先级

必须按照：

```
P0
Project Retrieval Agent
```

然后：

```
P1
Standard Query Agent
```

最后：

```
P2
Construction Plan Agent
```

原因：

施工方案 Agent 依赖：

```
项目检索
+
规范检索
+
Evidence
```

所以必须先把底层能力做好。

------

# 30. 开发顺序

Claude Code：

```
Phase 1
Project Retrieval State

Phase 2
Project Retrieval Tools

Phase 3
BM25

Phase 4
Vector Search

Phase 5
Reranker

Phase 6
Evidence

Phase 7
Conflict

Phase 8
Confidence

Phase 9
Project Retrieval Graph

Phase 10
Standard Query Agent

Phase 11
Construction Plan Agent
```

------

# 31. 最重要的 Agent 架构

最终：

```
                       User
                         │
                         ▼
                  Orchestrator
                         │
             ┌───────────┼───────────┐
             │           │           │
             ▼           ▼           ▼
          Project      Standard    Construction
          Retrieval      Query        Plan
             │           │           │
             │           │           │
             ▼           ▼           ▼
          Evidence    Evidence    Evidence
             │           │           │
             └───────────┼───────────┘
                         ▼
                    Validation
                         │
                    ┌────┴────┐
                    ▼         ▼
                 Answer      HITL
                              │
                              ▼
                         Final Output
```

------

# 32. 最终设计结论

ConstructionAgent V1 的核心不是：

```
“有三个 Agent”
```

而是：

```
三个 Agent
+
统一 Orchestrator
+
统一 Evidence
+
统一 Service
+
统一 Task
+
统一 HITL
+
统一 Retry/Fallback
```

三个 Agent 分别承担：

```
Project Retrieval Agent
=
项目事实

Standard Query Agent
=
规范依据

Construction Plan Agent
=
工程方案
```

最终形成：

```
项目事实
    +
规范依据
    +
企业模板
    ↓
施工方案
```

------

# 33. Claude Code 强制规则

开发三个 Agent 时：

```
RULE-001
Agent 必须使用 LangGraph。

RULE-002
每个 Agent 必须有独立 State。

RULE-003
Agent 不得直接访问数据库。

RULE-004
Agent 不得直接操作 Milvus。

RULE-005
Agent 不得直接操作 MinIO。

RULE-006
Agent 必须通过 Service / Tool 获取能力。

RULE-007
所有工程事实必须尽可能绑定 Evidence。

RULE-008
Evidence 不足不得编造。

RULE-009
发现关键数据冲突必须进入 HITL。

RULE-010
Retry 不得无限循环。

RULE-011
检索失败必须执行降级策略。

RULE-012
Construction Plan Agent 不得直接 import
Project Retrieval Agent 或 Standard Query Agent。

RULE-013
Construction Plan Agent 必须通过 Service 获取项目和规范 Evidence。

RULE-014
长任务必须 Task 化。

RULE-015
HITL 必须支持任务恢复。

RULE-016
所有 Agent 必须可以独立测试。

RULE-017
所有 Agent 必须记录运行日志。

RULE-018
不要为了展示 Multi-Agent 而增加无意义 Agent。

RULE-019
不要把所有业务逻辑写进 Prompt。

RULE-020
任何架构级修改必须先报告，不得自行修改 Architecture Freeze。
```

------

# 34. Agent Definition of Done

一个 Agent 只有同时满足以下条件，才算开发完成：

```
[ ] State 完成
[ ] Graph 完成
[ ] Node 完成
[ ] Tool 完成
[ ] Service 调用完成
[ ] Prompt 完成
[ ] Schema 完成
[ ] Evidence 完成
[ ] Retry 完成
[ ] Fallback 完成
[ ] Error Handling 完成
[ ] HITL 完成
[ ] Logging 完成
[ ] Unit Test 完成
[ ] Integration Test 完成
[ ] SSE Task 状态完成
```

------

# 35. V1 Agent 最终闭环

```
                     用户问题
                         │
                         ▼
                    Orchestrator
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          项目查询      规范查询      方案编制
             │           │           │
             ▼           ▼           ▼
          Project      Standard    Construction
           Agent        Agent        Agent
             │           │           │
             └───────────┼───────────┘
                         ▼
                      Evidence
                         │
                  Conflict Detection
                         │
                  Confidence Check
                         │
                  ┌──────┴──────┐
                  ▼             ▼
                Answer         HITL
                                │
                                ▼
                         Human Confirmation
                                │
                                ▼
                           Final Output
```

------

# 36. 核心理念

> **Agent 不负责“知道答案”，Agent 负责“找到证据、组织证据、验证证据，并在证据不足时停止生成”。**

对于建筑工程场景：

```
真实项目资料
        ↓
项目 Evidence
        ↓
规范 Evidence
        ↓
AI 推理
        ↓
人工确认
        ↓
工程输出
```

这才是 ConstructionAgent V1 的核心 Agent 架构。

```
### 这份和 `01_ARCHITECTURE.md` 的关系

现在两份文档已经形成上下级关系：

​```text
01_ARCHITECTURE.md
        │
        │ 定义整个系统怎么搭
        ▼
02_AGENT_SPEC.md
        │
        │ 定义三个 Agent 怎么实现
        ▼
┌─────────────────────────────────────┐
│ Project Retrieval Agent             │
│                                     │
│ State → Node → Retrieval → Evidence │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Standard Query Agent                │
│                                     │
│ State → Node → Retrieval → Evidence │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Construction Plan Agent             │
│                                     │
│ State → Project → Standard → Plan   │
└─────────────────────────────────────┘
```

**这里有一个非常关键的设计我建议保留：**

> `Construction Plan Agent` **不直接调用另外两个 Agent 的 Graph**，而是调用 `ProjectRetrievalService` 和 `StandardRetrievalService`。

这样以后 Claude 写代码时不会变成：

```
PlanAgent
   ↓
ProjectAgent
   ↓
StandardAgent
   ↓
又启动一个 Graph
   ↓
又启动一个 Agent
```

最后变成复杂的 **Agent 套 Agent**。

而是：

```
ConstructionPlanAgent
       │
       ├── ProjectRetrievalService
       │        ↓
       │     Evidence
       │
       └── StandardRetrievalService
                ↓
             Evidence
```