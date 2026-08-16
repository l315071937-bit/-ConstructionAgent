# 建筑工程智能 Agent 系统
# 01_ARCHITECTURE.md

> Version: V1.0
> Status: Architecture Freeze
> Purpose: Claude Code 开发基准文档
> Language: Python + FastAPI + LangGraph + Vue3
>
> 本文档定义系统总体技术架构、模块职责、数据流、Agent 编排方式以及核心设计原则。
> Claude Code 在开发过程中不得擅自改变本文档定义的核心架构。

---

# 1. 项目概述

## 1.1 项目名称

ConstructionAgent

## 1.2 项目定位

ConstructionAgent 是一个面向建筑工程项目的 AI Agent 系统。

系统通过项目图纸、设计文件、规范、标准图集、企业施工模板等工程资料建立项目知识库，并通过三个专业 Agent 为工程人员提供：

1. 项目知识检索
2. 工程规范查询
3. 施工方案辅助编制

系统重点解决传统工程信息查询中的：

- 图纸资料分散
- 图纸与表格信息难以关联
- 规范查询效率低
- 项目资料检索困难
- 同一位置多个文件数据冲突
- AI 无法准确定位原始证据
- 施工方案编制重复劳动
- AI 生成内容缺乏工程依据

---

# 2. V1 核心目标

V1 不追求“大而全”，必须首先完成以下核心闭环：

```text
用户登录
    ↓
创建 / 进入项目
    ↓
上传项目资料
    ↓
文档解析
    ↓
建立项目知识库
    ↓
用户提出工程问题
    ↓
Project Retrieval Agent
    ↓
检索项目资料
    ↓
生成 Evidence
    ↓
回答问题
    ↓
右侧显示图纸 / 图集 / 规范缩略图
    ↓
点击 Evidence
    ↓
跳转原始文件对应页
    ↓
Standard Query Agent
    ↓
查询规范依据
    ↓
Construction Plan Agent
    ↓
项目资料 + 规范 + 企业模板
    ↓
生成施工方案
    ↓
人工确认
    ↓
导出 Word / PDF
```

如果上述闭环没有稳定运行：

> 不进入高级 Agent 能力开发。

------

# 3. 三个核心 Agent

系统最终只保留三个核心业务 Agent。

```
┌──────────────────────────────────────┐
│            Orchestrator              │
│          Agent 统一编排层             │
└────────────────┬─────────────────────┘
                 │
        ┌────────┼─────────┐
        ▼        ▼         ▼
┌────────────┐ ┌────────────┐ ┌───────────────┐
│ Project    │ │ Standard   │ │ Construction  │
│ Retrieval  │ │ Query      │ │ Plan          │
│ Agent      │ │ Agent      │ │ Agent         │
└────────────┘ └────────────┘ └───────────────┘
```

------

# 4. Agent 职责边界

## 4.1 Project Retrieval Agent

负责：

> “项目里有什么？”

典型问题：

```
3号楼二层卫生间防水高度是多少？

A-205图纸里面这个位置怎么做？

这个区域的墙面材料是什么？

项目消防道路采用什么做法？

这个构件的尺寸是多少？
```

数据来源：

```
项目图纸
设计说明
施工图
竣工图
项目表格
项目文档
项目图片
OCR 内容
CAD / PDF 提取内容
```

禁止：

- 凭 LLM 常识编造项目事实
- 不经过 Evidence 就回答具体项目参数
- 跨项目检索
- 忽略文件版本
- 遇到冲突自行猜测

------

# 4.2 Standard Query Agent

负责：

> “规范怎么规定？”

典型问题：

```
深圳市政消防道路有什么要求？

这个施工做法符合什么规范？

这个尺寸有没有规范依据？

这个做法对应哪本图集？

某规范目前是否有效？
```

数据来源：

```
国家标准
行业标准
地方标准
地方规范
标准图集
企业规范
项目指定规范
```

禁止：

- 编造规范编号
- 编造条款
- 使用无法确认版本的规范
- 用模型知识替代知识库中的规范 Evidence
- 忽略地区适用性
- 忽略规范有效状态

------

# 4.3 Construction Plan Agent

负责：

> “结合项目资料和规范，施工方案怎么编？”

输入：

```
用户任务
+
项目资料
+
规范资料
+
企业施工模板
```

典型任务：

```
编制地下室防水施工方案

编制外墙保温施工方案

编制消防道路施工方案

编制土方开挖施工方案
```

输出：

```
施工方案结构
+
施工方案正文
+
项目依据
+
规范依据
+
风险检查
+
待人工确认项
```

------

# 5. 总体技术架构

```
┌───────────────────────────────────────────────────────────────┐
│                       Frontend                               │
│                                                               │
│             Vue3 + TypeScript + Element Plus                 │
│                                                               │
│  项目管理 │ 智能问答 │ Evidence │ 图纸预览 │ 方案编制 │ 任务中心 │
└───────────────────────────────┬───────────────────────────────┘
                                │
                         HTTP / SSE
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                       FastAPI API Layer                       │
│                                                               │
│ auth │ projects │ documents │ retrieval │ standards │ plans   │
│                         │                                     │
│                     tasks / SSE                                │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                         │
│                                                               │
│  Authentication Context                                       │
│  Agent Routing                                                │
│  Task Lifecycle                                               │
│  HITL                                                         │
│  Retry / Fallback                                              │
└───────────────┬──────────────────┬─────────────────────────────┘
                │                  │
        ┌───────┴────────┐ ┌──────┴──────────┐
        ▼                ▼ ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐
│ Project      │ │ Standard     │ │ Construction Plan   │
│ Retrieval    │ │ Query        │ │ Agent               │
│ Agent        │ │ Agent        │ │                     │
└──────┬───────┘ └──────┬───────┘ └──────────┬──────────┘
       │                 │                    │
       └─────────────────┼────────────────────┘
                         ▼
┌───────────────────────────────────────────────────────────────┐
│                    Service Layer                              │
│                                                               │
│ ProjectService                                               │
│ DocumentService                                              │
│ RetrievalService                                             │
│ StandardService                                              │
│ TemplateService                                              │
│ EvidenceService                                              │
│ TaskService                                                  │
│ DocumentPreviewService                                       │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    AI Infrastructure                          │
│                                                               │
│ LLMFactory                                                    │
│ Embedding                                                     │
│ BM25                                                         │
│ Reranker                                                      │
│ Query Classifier                                              │
│ Memory                                                        │
│ Retry                                                         │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                       Data Layer                              │
│                                                               │
│ PostgreSQL │ Redis │ Milvus │ MinIO │ Model / LLM API        │
└───────────────────────────────────────────────────────────────┘
```

------

# 6. 分层架构

## 6.1 Frontend Layer

技术：

```
Vue 3
TypeScript
Element Plus
Axios
SSE
Pinia
Vue Router
```

主要职责：

```
用户登录
项目管理
文件上传
聊天
Evidence 展示
图纸预览
HITL
施工方案编制
任务状态
```

前端不得包含：

```
LLM Prompt
RAG 核心逻辑
数据库逻辑
Agent Workflow
```

------

# 7. API Layer

技术：

```
FastAPI
Pydantic
JWT
bcrypt
```

API 层职责：

```
HTTP 参数接收
参数校验
Authentication
Authorization
调用 Service
返回 Response
SSE
异常转换
```

API 层不负责：

```
直接执行 Milvus 查询
直接调用 LLM
编写 Prompt
执行 Agent Node
处理复杂业务逻辑
```

推荐：

```
API
 ↓
Service
 ↓
Agent / Knowledge
```

------

# 8. Authentication Architecture

登录流程：

```
Frontend
    │
    │ POST /auth/login
    ▼
FastAPI
    │
    ▼
查询 users
    │
    ▼
bcrypt.verify()
    │
    ├── fail → 401
    │
    ▼
生成 JWT
    │
    ▼
返回 Token
```

JWT Payload：

```
{
    "user_id": 10001,
    "role": "engineer",
    "tenant_id": 1,
    "exp": 1780000000
}
```

后续请求：

```
Authorization: Bearer <JWT>
```

FastAPI：

```
get_current_user()
        ↓
解析 JWT
        ↓
验证签名
        ↓
验证 exp
        ↓
获取 user
        ↓
Authorization
```

密码：

```
禁止明文存储

password
   ↓
bcrypt
   ↓
password_hash
```

数据库只保存：

```
password_hash
```

------

# 9. Dependency Injection

统一使用 FastAPI Dependency。

例如：

```
async def get_db():
    ...

async def get_current_user():
    ...

async def get_current_project():
    ...
```

接口：

```
@router.post("/projects/{project_id}/query")
async def query_project(
    project_id: str,
    user = Depends(get_current_user),
    project = Depends(get_current_project),
):
    ...
```

权限链：

```
JWT
 ↓
User
 ↓
Tenant
 ↓
Project Membership
 ↓
Project Access
```

任何项目知识检索必须验证：

```
tenant_id
+
project_id
+
user permission
```

------

# 10. Orchestrator

Orchestrator 是整个 Agent 系统的统一编排入口。

职责：

```
识别任务
选择 Agent
创建 Task
管理状态
调用 Agent
处理 HITL
处理失败
恢复任务
返回最终结果
```

不负责：

```
具体 BM25
具体 Vector Search
具体 Prompt
具体数据库 SQL
```

------

# 11. Agent 路由

用户：

```
深圳市政消防道路有什么要求？
```

路由：

```
Orchestrator
      ↓
判断：
规范查询
      ↓
Standard Query Agent
```

用户：

```
3号楼卫生间防水高度是多少？
```

路由：

```
Orchestrator
      ↓
项目资料查询
      ↓
Project Retrieval Agent
```

用户：

```
帮我编制地下室防水施工方案
```

路由：

```
Orchestrator
      ↓
施工方案任务
      ↓
Construction Plan Agent
```

------

# 12. Agent 协同原则

三个 Agent 不允许直接相互 import。

错误：

```
ConstructionPlanAgent
        ↓
ProjectAgent.graph()
```

错误：

```
ProjectAgent
        ↓
StandardAgent
```

正确：

```
                 Orchestrator
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Project      Standard      Plan
        Agent        Agent        Agent
```

施工方案 Agent 如果需要项目资料：

```
Construction Plan Agent
        ↓
ProjectRetrievalService
        ↓
Project Knowledge Base
```

需要规范：

```
Construction Plan Agent
        ↓
StandardRetrievalService
        ↓
Standard Knowledge Base
```

这样可以保证：

```
Agent
Service
Knowledge
```

职责解耦。

------

# 13. Knowledge Architecture

系统采用：

```
Metadata Filter
+
BM25
+
Vector Search
+
Reranker
```

而不是单一向量搜索。

------

# 14. 项目知识检索流程

```
User Query
    ↓
Query Parse
    ↓
Project Filter
    ↓
Metadata Filter
    ↓
┌───────────────┐
│               │
▼               ▼
BM25           Vector
│               │
└───────┬───────┘
        ▼
    Merge Results
        ↓
      Rerank
        ↓
    Evidence
        ↓
 Conflict Detection
        ↓
 Confidence Check
        ↓
      Answer
```

------

# 15. BM25 的定位

BM25 主要解决：

```
图号
编号
尺寸
专业名词
材料名称
精确短语
```

例如：

```
A-205
DN100
1800mm
聚氨酯防水
```

------

# 16. Vector Search 的定位

Vector Search 主要解决：

```
自然语言表达
语义相似
描述性问题
不同表达方式
```

例如：

```
卫生间墙面防水需要做到多高？

厕所墙面防水上翻高度是多少？
```

语义相近，但文字不完全相同。

------

# 17. Reranker

推荐：

```
BGE-Reranker
```

流程：

```
BM25 Top 20
+
Vector Top 20
        ↓
Merge
        ↓
Top 30
        ↓
Reranker
        ↓
Top 5~10
```

最终回答只能主要依赖：

```
Reranked Evidence
```

------

# 18. Evidence Architecture

Evidence 是整个系统的核心数据结构。

统一结构：

```
class Evidence:
    evidence_id: str

    project_id: str | None

    file_id: str
    file_name: str

    source_type: str

    page: int | None

    content: str

    score: float

    thumbnail_url: str | None

    bbox: list | None

    version: str | None

    metadata: dict
```

------

# 19. Evidence Source Type

可能包括：

```
PROJECT_DRAWING
PROJECT_DOCUMENT
PROJECT_TABLE
PROJECT_IMAGE

STANDARD
STANDARD_ATLAS
LOCAL_STANDARD
ENTERPRISE_STANDARD

ENTERPRISE_TEMPLATE
```

------

# 20. Evidence 为什么重要

传统 RAG：

```
检索
 ↓
LLM
 ↓
答案
```

本系统：

```
检索
 ↓
Evidence
 ↓
LLM
 ↓
答案
 +
Evidence
```

用户可以看到：

```
AI回答：

卫生间防水高度为 XXX。

依据：
A-205.pdf
第12页
```

右侧：

```
┌────────────────────┐
│     图纸缩略图       │
│                    │
│       PAGE 12      │
└────────────────────┘

A-205.pdf
第12页

[查看原图]
```

------

# 21. PDF 定位

Evidence 必须至少保存：

```
file_id
page
```

例如：

```
{
    "file_id": "doc_001",
    "page": 12
}
```

前端：

```
点击 Evidence
      ↓
PDF Viewer
      ↓
跳转 Page 12
```

未来支持：

```
bbox
```

例如：

```
{
    "page": 12,
    "bbox": [100, 200, 800, 700]
}
```

用于：

```
页面内高亮
```

------

# 22. 前端右侧 Evidence Explorer

核心布局：

```
┌───────────────────────────────────────────────────────┐
│                    ConstructionAgent                 │
├───────────────────────────────┬───────────────────────┤
│                               │                       │
│          Chat                 │   Evidence Explorer   │
│                               │                       │
│ 用户问题                       │ ┌───────────────────┐ │
│                               │ │                   │ │
│ AI回答                        │ │    图纸缩略图      │ │
│                               │ │                   │ │
│ [Evidence 1]                  │ │      Page 12      │ │
│ [Evidence 2]                  │ └───────────────────┘ │
│                               │                       │
│                               │ A-205.pdf             │
│                               │ 第12页                │
│                               │                       │
│                               │ [查看原图]             │
│                               │                       │
├───────────────────────────────┴───────────────────────┤
│                  输入问题                              │
└───────────────────────────────────────────────────────┘
```

Evidence Explorer 可以展示：

```
图纸
规范
标准图集
项目文件
表格
```

------

# 23. Document Storage

采用：

```
MinIO
```

保存：

```
原始 PDF
Office
图片
CAD
缩略图
生成文档
```

数据库只保存：

```
object_key
metadata
```

不要把大文件直接存 PostgreSQL。

------

# 24. PostgreSQL

负责：

```
用户
租户
项目
项目成员
文件
文件版本
页面
Chunk
规范 Metadata
Task
Task Event
HITL
Conversation
Message
Generated Document
```

------

# 25. Milvus

负责：

```
Vector Search
```

至少建立：

```
project_knowledge
standard_knowledge
```

必须携带：

```
chunk_id
project_id
document_id
page
```

检索时必须：

```
先 Metadata Filter
 ↓
再 Vector Search
```

禁止：

```
全库 Vector Search
 ↓
Python 再过滤 project_id
```

因为这样存在：

```
数据越权风险
+
性能问题
```

------

# 26. Redis

Redis V1 主要负责：

```
Task 临时状态
SSE 状态
缓存
短期 Conversation Context
分布式锁
```

不要把 Redis 作为唯一业务数据库。

需要长期保存的数据：

```
PostgreSQL
```

------

# 27. LLMFactory

所有 LLM 调用必须经过：

```
LLMFactory
```

禁止 Agent 中直接：

```
OpenAI(...)
```

或者：

```
DeepSeek(...)
```

应该：

```
llm = LLMFactory.get("default")
```

这样以后可以替换：

```
DeepSeek
OpenAI
Qwen
本地模型
```

而不修改 Agent。

------

# 28. Retry / Fallback

系统采用三层兜底。

## 第一层：Retry

```
LLM / Embedding / Reranker / DB
        ↓
失败
        ↓
Retry
```

适用于：

```
网络异常
超时
临时服务异常
```

------

## 第二层：Agent 降级

例如：

```
Reranker失败
    ↓
使用原始召回结果
```

或者：

```
Vector Search失败
    ↓
BM25继续工作
```

------

## 第三层：人工兜底

例如：

```
检索不到
+
多次 Query Rewrite 仍失败
        ↓
告诉用户：
未找到足够证据
        ↓
提供：
可能相关的文件
+
图号
+
人工查询入口
```

------

# 29. 检索不到时的最终策略

绝不能：

```
没有找到
 ↓
LLM 自己编答案
```

应该：

```
第一次检索
 ↓
Query Rewrite
 ↓
第二次检索
 ↓
仍无结果
 ↓
扩大检索范围
 ↓
仍无结果
 ↓
返回低置信结果 / 推荐文件
 ↓
人工确认
```

例如：

```
当前未找到足够证据。

建议人工查看：

A-205 建筑平面图
A-312 防水节点详图
S-102 设计说明

[查看文件]
```

------

# 30. 冲突处理

工程项目中可能存在：

```
图纸 A：1800mm

图纸 B：1500mm
```

不能让 LLM：

```
“我认为应该是1800mm”
```

必须：

```
Evidence A
+
Evidence B
        ↓
Conflict Detection
        ↓
HITL
```

前端：

```
发现项目资料存在冲突：

A-205：1800mm
A-312：1500mm

请选择：
[采用 A-205]
[采用 A-312]
[人工查看]
```

------

# 31. HITL 设计原则

不是每一步都人工确认。

只有关键节点进入 HITL。

V1 主要包括：

```
1. 企业模板选择
2. 方案结构确认
3. 工程数据冲突
4. 最终方案审核
```

------

# 32. Construction Plan Agent 调用关系

```
用户
 ↓
Construction Plan Agent
 ↓
任务解析
 ↓
企业模板检索
 ↓
模板选择
 ↓
HITL
 ↓
生成方案结构
 ↓
HITL
 ↓
历史方案检索
 ↓
Project Retrieval
 ↓
Standard Query
 ↓
方案章节生成
 ↓
事实检查
 ↓
规范检查
 ↓
完整性检查
 ↓
风险检查
 ↓
最终人工审核
 ↓
Word / PDF
```

------

# 33. 企业模板规则

如果找到：

```
模板 A
模板 B
模板 C
```

进入：

```
WAITING_HUMAN
```

用户选择后：

```
selected_template
```

才能继续。

如果没有：

```
未找到匹配的企业模板。
```

然后：

```
询问用户是否允许使用：
项目资料 + 规范
生成通用方案结构。
```

必须得到用户确认。

------

# 34. Construction Plan 的事实来源

方案中的：

```
项目名称
建筑面积
楼栋数量
施工范围
结构形式
材料规格
尺寸
工程数量
```

只能来自：

```
Project Evidence
```

------

# 35. Construction Plan 的规范来源

方案中的：

```
技术要求
施工要求
验收要求
质量标准
安全要求
```

主要来自：

```
Standard Evidence
```

------

# 36. Construction Plan 的格式来源

方案：

```
章节结构
企业格式
封面
目录
章节顺序
模板语言
```

来自：

```
Enterprise Template
```

------

# 37. 不确定信息处理

如果无法确认：

```
[待人工确认]
```

禁止：

```
模型猜测
```

------

# 38. SSE

AI 任务采用：

```
HTTP
+
SSE
```

事件：

```
task_started
node_started
node_completed
token
evidence
conflict
human_required
task_completed
error
```

前端可以实时显示：

```
正在分析问题
正在检索项目资料
正在核对规范
正在生成方案
```

但是不直接显示内部 Node 名称。

错误：

```
vector_search_node
merge_results_node
```

正确：

```
正在检索项目资料
```

------

# 39. Task Architecture

长任务必须 Task 化。

例如：

```
POST /plans/create
```

返回：

```
{
    "task_id": "task_001",
    "status": "RUNNING"
}
```

之后：

```
GET /tasks/task_001
```

查询：

```
状态
进度
当前阶段
Evidence
HITL
错误
```

------

# 40. HITL Task Resume

例如：

```
Construction Plan
        ↓
Template Selection
        ↓
WAITING_HUMAN
```

用户：

```
选择模板 A
```

前端：

```
POST /tasks/task_001/resume
```

后端：

```
恢复 LangGraph
        ↓
继续执行
```

因此：

> HITL 不能简单设计成前端弹窗后丢失 Agent 状态。

------

# 41. Memory

V1 不做复杂长期记忆。

主要使用：

```
Conversation Context
+
Task State
```

短期对话：

```
Redis
```

长期业务数据：

```
PostgreSQL
```

Agent State：

```
Task.state_json
```

------

# 42. MCP

V1 不强制使用 MCP。

原因：

目前三个 Agent 所需的数据主要来自：

```
自己的 Knowledge Base
自己的 Service
自己的 Database
```

直接 Service 调用更简单。

V2 如果需要：

```
企业 ERP
企业 OA
BIM
外部规范系统
Web Search
第三方工程平台
```

再考虑 MCP。

因此：

> 不为了“Agent 项目必须有 MCP”而强行增加 MCP。

------

# 43. 目录架构

最终建议：

```
ConstructionAgent/
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── docs/
│   ├── 01_ARCHITECTURE.md
│   ├── 02_AGENT_SPEC.md
│   ├── 03_API_SPEC.md
│   ├── 04_DATABASE_SPEC.md
│   ├── 05_FRONTEND_SPEC.md
│   └── 06_CLAUDE_DEVELOPMENT_RULES.md
│
├── scripts/
│   ├── init_db.sql
│   ├── init_milvus.py
│   ├── build_knowledge_base.py
│   ├── seed_data.py
│   └── verify_env.py
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   │
│   ├── core/
│   │   ├── logger.py
│   │   ├── exceptions.py
│   │   ├── llm_factory.py
│   │   ├── retry.py
│   │   ├── knowledge_base.py
│   │   ├── reranker.py
│   │   ├── query_classifier.py
│   │   └── memory.py
│   │
│   ├── db/
│   │   ├── session.py
│   │   ├── models.py
│   │   └── migrations.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── projects.py
│   │       ├── documents.py
│   │       ├── retrieval.py
│   │       ├── standards.py
│   │       ├── plans.py
│   │       └── tasks.py
│   │
│   ├── services/
│   │   ├── project_service.py
│   │   ├── document_service.py
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Retriever 抽象接口（真实可替换）
│   │   │   ├── dense_retriever.py # BGE-M3 向量检索（V0.1 实现）
│   │   │   ├── lexical_retriever.py # 词法通道接口（V0.1 占位，实现待实验）
│   │   │   └── reranker.py        # Reranker 封装（V0.1 按 dense score 占位）
│   │   ├── standard_service.py
│   │   ├── template_service.py
│   │   ├── evidence_service.py
│   │   ├── task_service.py
│   │   └── preview_service.py
│   │
│   ├── evaluation/                  # 检索与答案评估（V0.1 仅骨架，不阻塞主链路）
│   │   ├── __init__.py
│   │   ├── metrics/
│   │   │   ├── recall_at_k.py
│   │   │   ├── mrr.py
│   │   │   ├── ndcg.py
│   │   │   ├── citation_accuracy.py
│   │   │   └── answer_accuracy.py
│   │   ├── datasets/                # 查询集 + qrels（建筑领域评测数据）
│   │   └── runner.py
│   │
│   └── agents/
│       ├── project_retrieval/
│       │   ├── graph.py
│       │   ├── state.py
│       │   ├── nodes.py
│       │   ├── tools.py
│       │   ├── prompts.py
│       │   └── schemas.py
│       │
│       ├── standard_query/
│       │   ├── graph.py
│       │   ├── state.py
│       │   ├── nodes.py
│       │   ├── tools.py
│       │   ├── prompts.py
│       │   └── schemas.py
│       │
│       └── construction_plan/
│           ├── graph.py
│           ├── state.py
│           ├── nodes.py
│           ├── tools.py
│           ├── prompts.py
│           └── schemas.py
│
└── frontend/
    ├── src/
    │   ├── api/
    │   ├── components/
    │   ├── views/
    │   ├── stores/
    │   ├── router/
    │   └── types/
    └── package.json
```

------

# 44. 核心数据流

## 44.1 项目问答

```
User
 ↓
POST /retrieval/query
 ↓
Auth
 ↓
Project Permission
 ↓
Orchestrator
 ↓
Project Retrieval Agent
 ↓
Query Parse
 ↓
Metadata Filter
 ↓
BM25 + Vector
 ↓
Merge
 ↓
Rerank
 ↓
Evidence
 ↓
Conflict Detection
 ↓
Confidence
 ↓
LLM
 ↓
Answer + Evidence
 ↓
Frontend
 ↓
Evidence Explorer
```

------

# 45. 规范查询

```
User
 ↓
POST /standards/query
 ↓
Orchestrator
 ↓
Standard Query Agent
 ↓
Region / Discipline / Topic
 ↓
Metadata Filter
 ↓
BM25 + Vector
 ↓
Rerank
 ↓
Version Check
 ↓
Applicability Check
 ↓
Evidence
 ↓
LLM
 ↓
Answer + Standard Evidence
```

------

# 46. 施工方案

```
User
 ↓
POST /plans/create
 ↓
Construction Plan Agent
 ↓
Parse Task
 ↓
Search Enterprise Template
 ↓
HITL
 ↓
Generate Outline
 ↓
HITL
 ↓
Project Retrieval
 ↓
Standard Query
 ↓
Generate Chapters
 ↓
Fact Check
 ↓
Standard Check
 ↓
Completeness Check
 ↓
Risk Check
 ↓
Final HITL
 ↓
Generate Document
 ↓
MinIO
```

------

# 47. 核心设计原则

## 原则 1：Evidence First

任何工程事实都应该尽可能有 Evidence。

------

## 原则 2：Retrieval First

具体项目事实和规范条款：

```
先检索
后生成
```

不是：

```
先让 LLM 回答
再找依据
```

------

## 原则 3：Conflict First

工程资料存在冲突时：

```
发现冲突
 ↓
展示证据
 ↓
人工确认
```

而不是：

```
LLM 猜测
```

------

## 原则 4：Permission First

所有项目数据访问：

```
User
 ↓
Tenant
 ↓
Project
 ↓
Permission
 ↓
Retrieval
```

------

## 原则 5：Agent 与基础设施解耦

Agent 不直接管理：

```
数据库连接
Milvus
Redis
MinIO
HTTP
```

统一通过 Service / Infrastructure。

------

## 原则 6：V1 优先稳定闭环

不要因为：

```
MCP
Multi-Agent
复杂 Memory
复杂 Planning
```

而增加无必要复杂度。

------

# 48. V1 明确不做

以下功能暂不作为 V1 必需：

```
复杂多 Agent 自主协商
自动 BIM 修改
自动 CAD 修改
复杂长期 Memory
自动规范联网实时更新
复杂 MCP Ecosystem
自动替代工程师签字
自动生成完全无需审核的施工方案
```

------

# 49. V2 可扩展方向

未来可以增加：

```
BIM Agent
CAD Agent
进度 Agent
造价 Agent
质量检查 Agent
安全检查 Agent
材料 Agent
规范联网更新
企业 OA / ERP
MCP
多模态视觉模型
图纸 OCR / Layout Model
CAD 图元检索
BIM 属性检索
```

但是 V2 不得破坏 V1：

```
Orchestrator
+
Service
+
Evidence
+
Knowledge
```

的核心架构。

------

# 50. Architecture Freeze

从本文档开始，以下内容视为 V1 Architecture Freeze：

```
1. 三 Agent 架构
2. Orchestrator
3. Service Layer
4. Evidence Architecture
5. BM25 + Vector + Reranker
6. PostgreSQL
7. Redis
8. Milvus
9. MinIO
10. FastAPI
11. Vue3 + TypeScript + Element Plus
12. JWT + bcrypt
13. SSE
14. HITL
15. Task State
16. 三层 Retry / Fallback
```

Claude Code 在后续开发过程中：

> 如果发现需要修改以上核心架构，必须先停止当前开发并说明修改原因，不得自行修改 Architecture Freeze 内容。

> 本节的冻结语义由第 52 节细化：冻结不再意味着绝对锁死，而是
> **「V1 架构默认稳定，重大变更需评审」**——变更必须基于真实数据证据
> （基准测试 / 实验 / 法务结论），禁止凭猜测提出。具体分档与评审流程见第 52 节。

------

# 51. 最终系统原则

ConstructionAgent 不是一个简单的：

```
ChatGPT + PDF
```

而是：

```
             工程问题
                 ↓
          Orchestrator
                 ↓
      ┌──────────┼──────────┐
      ▼          ▼          ▼
   项目事实    规范依据    方案生成
      │          │          │
      └──────────┼──────────┘
                 ▼
              Evidence
                 ↓
           Conflict Check
                 ↓
             Confidence
                 ↓
              AI Answer
                 ↓
         人工确认 / 审核
                 ↓
              工程输出
```

------

# 52. V1 冻结决策表（2026-08-15 定稿）

> 本附录基于 GitHub 两轮技术调研（第一轮调研报告 + 第二轮反向验证报告）形成。
> 它细化了第 50 节的语义：**V1 架构默认稳定，重大变更需评审**。
> 在缺少真实数据验证之前，不绝对锁死任何东西；但变更必须有证据，不允许凭猜测改架构。

## 52.1 评审规则

```
1. 「默认稳定档」变更：必须提供真实数据证据（基准测试 / 对照实验 / 法务结论），
   先停止开发 → 提交证据 → 项目负责人评审 → 通过后更新本附录；
2. 「默认实现档」变更：通过其抽象接口替换即可，不需评审，
   但必须在 evaluation/ 实验报告中记录对比数据；
3. 所有 Factory / Interface 必须真实可替换（存在≥2 个真实候选实现场景），
   禁止无实际替换场景的装饰性抽象；
4. 本附录是 01/02 文档之后的最新决策，与旧文冲突处以本附录为准。
```

## 52.2 默认稳定档（重大变更需评审）

| 模块 | V1 决策 | 约束条件 |
| --- | --- | --- |
| Agent 编排 | LangGraph | 版本锁定；Project/Standard 用浅图；checkpoint-postgres Day 1 接入；不用 Function API 等新特性 |
| Agent 划分 | 项目知识检索 / 规范查询 / 施工方案 | 三 Agent 互不 import；Plan Agent 通过 Service 获取 Evidence，不嵌套调用其他 Agent 的图 |
| API | FastAPI | 短查询不 Task 化（SSE 直接流式）；仅长任务（方案编制）Task 化 |
| 检索架构 | Dense + 词法通道 + Reranker 三段式 | 管线形状冻结；词法通道的具体实现属默认实现档 |
| Vector DB | Milvus | 锁 standalone / milvus-lite，禁止 V1 上集群；检索必须先 Metadata Filter 再检索（tenant/project） |
| 关系数据 | PostgreSQL | 一库三用：业务数据 + Task 状态 + LangGraph checkpoint |
| 会话/缓存 | Redis | 短期上下文 + 缓存 + 分布式锁；不作唯一业务数据库 |
| 文档解析架构 | DocumentParser Router | 文本型/扫描型/复杂版面/Word/Excel/.doc 五路路由 + 统一 Chunk Schema（text+page+bbox+source_type） |
| 抽象层 | LLMFactory / EmbeddingFactory / ParserInterface / Retriever ABC | 必须真实可替换（52.1 规则 3） |
| HITL | LangGraph interrupt + checkpoint | 4+1 节点（模板/无模板授权/目录/数据冲突/终审）+ 超时 TTL + human_decision schema |
| Evidence | 统一结构 + 前端证据栏 + PDF 页码定位 | 回答必须携带 evidence_ids 引用 |
| 安全 | JWT + bcrypt；Service 层鉴权 + 强制 project 过滤 | Partition Key 只是查询性能优化，不是安全边界（官方文档定义） |
| 部署 | Docker + docker-compose | 单机起 PG + Redis + Milvus standalone |
| 前端 | Vue3 + TypeScript + Element Plus | 对话区 + Evidence 栏 + PDF 定位为第一版核心 |

## 52.3 默认实现档（接口冻结，实现可替换）

| 模块 | V1 默认实现 | 更换触发条件（需实验数据） |
| --- | --- | --- |
| Embedding | BGE-M3 | Qwen3-Embedding-0.6B 在建筑语料 A/B 评测中显著胜出 |
| 词法通道（LexicalRetriever 接口） | 未定（V0.1 允许 Dense 先行） | 三候选实验后定：Milvus FTS(chinese analyzer) / bm25s+自定义词典 / BGE-M3 Sparse，指标 recall@k / MRR |
| Reranker | bge-reranker-v2-m3 | Qwen3-Reranker-0.6B 在建筑语料 A/B 评测中显著胜出 |
| PDF 文本抽取 | PyMuPDF | 法务对 AGPL-3.0 决策不通过 → 换 pypdf/pdfplumber + pypdfium2（ParserInterface 后无痛切换） |
| OCR/版面/表格 | PaddleOCR PP-Structure（独立容器） | 部署重量不可接受时评估 RapidOCR 轻通道 |
| 复杂版面兜底 | MinerU（按需启用） | 解析失败率触发（<阈值不启用）；Apache-2.0 + 在线服务署名义务 |
| LLM | DeepSeek / Qwen 云 API（LLMFactory 静态配置） | 成本/效果评估后可增删 provider |

## 52.4 暂缓项（不进 V1 主链）

| 项 | 状态 |
| --- | --- |
| 图纸视觉理解（符号/几何检测，L2） | V2 |
| CAD / DWG 深度理解 | V2 |
| GraphRAG / 知识图谱 | 暂不做 |
| 多个 Critic / Reflection Agent | 暂不做 |
| MCP 生态 | 暂不做（V2 再评估，参考 OpenTakeoff） |
| 复杂长期 Memory | 暂不做（V2 参考 Letta 记忆分层） |

> 口径说明：图纸的「文本层提取」（CAD 导出 PDF 文字层 + 标题栏 OCR）属于
> 文档解析管线（52.2 DocumentParser Router），不属于暂缓的「图纸视觉理解」；
> 页级视觉检索（ColPali）按扫描件语料占比触发评估，默认暂缓。

## 52.5 新增结构约定

```
1. evaluation/ 目录（backend/evaluation/）：
   检索与答案评估基础设施，指标：Recall@K / MRR / NDCG / Citation Accuracy / Answer Accuracy；
   第一阶段只搭骨架（metrics 接口 + datasets 约定 + runner 入口），不阻塞主链路；
   52.3 的所有「更换触发条件」实验均在此目录产出数据。
2. LexicalRetriever 接口（backend/services/retrieval/）：
   只定义接口与数据契约，V0.1 不实现任何词法通道；Dense 先行；
   三候选实现（Milvus FTS / bm25s / BGE-M3 Sparse）不得在接口层有任何偏袒。
3. 评估数据约定：datasets/ 内查询集采用
   {query, expected_doc_ids, golden_answer_facts, citation_requirements} 结构，
   建筑领域评测数据允许先用人工标注的小样本（50~100 条），后迭代扩充。
```