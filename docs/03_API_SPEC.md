# 建筑工程智能 Agent 系统
# 03_API_SPEC.md（精简版 V0.1）

> Version: V0.1
> Status: 第一条垂直主链路 API 冻结（骨架开发基准）
> 覆盖范围：auth / projects / documents / retrieval（SSE）
> 未覆盖（后续增量补齐）：standards / plans / tasks / HITL resume / 文件预览高级特性
> 依据：01 §52 冻结决策表（2026-08-15 定稿）

---

# 1. 通用约定

```
Base URL:    /api/v1
认证:        Authorization: Bearer <JWT>（除 POST /auth/login 外全部要求）
内容类型:     application/json；文件上传 multipart/form-data
时间格式:     ISO 8601 UTC
分页:        ?page=1&page_size=20 → {items, total, page, page_size}
错误响应:     {"error": {"code": "...", "message": "..."}}，配合 HTTP 状态码
权限链:       JWT → user → tenant → project membership → project access（01 §9）
```

V0.1 权限模型最小化：user 属于 tenant；project 属于 tenant；project_members 表记录成员关系。
所有项目数据接口必须验证：token 有效 → user 是该 project 的成员 → 否则 403 PERMISSION_DENIED。
Milvus 检索必须强制携带 project_id 过滤（服务层注入，不接受客户端传值）。

---

# 2. 错误码（V0.1）

| code | HTTP | 说明 |
| --- | --- | --- |
| AUTH_INVALID_CREDENTIALS | 401 | 用户名或密码错误 |
| AUTH_TOKEN_EXPIRED | 401 | JWT 过期 |
| AUTH_TOKEN_INVALID | 401 | JWT 无效 |
| PERMISSION_DENIED | 403 | 无项目权限 |
| PROJECT_NOT_FOUND | 404 | 项目不存在 |
| DOCUMENT_NOT_FOUND | 404 | 文档不存在 |
| DOCUMENT_FILE_MISSING | 404 | 文档记录存在但原始文件缺失 |
| VALIDATION_ERROR | 422 | 参数校验失败 |
| FILE_TOO_LARGE | 413 | 超过大小限制（50MB） |
| UNSUPPORTED_FILE_TYPE | 415 | 文件类型不支持 |
| PARSE_FAILED | 422 | 文档解析失败（携带 reason） |
| PREVIEW_UNAVAILABLE | 422 | 当前文档无法生成页面预览 |
| RETRIEVAL_FAILED | 500 | 检索异常（已走降级仍失败） |
| LLM_FAILED | 500 | LLM 调用失败（已重试） |
| INTERNAL_ERROR | 500 | 未知错误 |

---

# 3. Auth

## POST /api/v1/auth/login

```
Request:  {"username": "...", "password": "..."}
Response: 200
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {"user_id": 10001, "username": "...", "role": "engineer", "tenant_id": 1}
}
```
- 密码 bcrypt 校验；JWT payload = {user_id, role, tenant_id, exp}（01 §8）
- 明文密码禁止出现在任何日志/响应

## GET /api/v1/auth/me

```
Response: 200 {"user_id": ..., "username": ..., "role": ..., "tenant_id": ...}
```

---

# 4. Projects

## POST /api/v1/projects

```
Request:  {"name": "...", "description": "..."}
Response: 201 {"project_id": ..., "name": ..., "description": ..., "tenant_id": ..., "created_at": ...}
```
- 创建者自动成为项目成员（owner）

## GET /api/v1/projects

```
Response: 200 {"items": [project...], "total": n, "page": 1, "page_size": 20}
```
- 只返回当前用户有成员关系的项目（tenant 内）

## GET /api/v1/projects/suggestions

按项目名称或描述联想当前用户有权限访问的项目。`q` 至少 2 个字符，
`limit` 范围为 1～3，默认返回前三项。项目名称匹配优先于描述匹配。

```json
{
  "items": [
    {
      "project_id": 12,
      "name": "深圳市龙华区某幼儿园",
      "description": "公建学校项目",
      "document_count": 26,
      "created_at": "2026-08-16T00:00:00Z"
    }
  ]
}
```

用户必须点击联想结果后，前端才可锁定该项目的 `project_id`；禁止仅凭输入文本自动切换知识库。

## GET /api/v1/projects/{project_id}

```
Response: 200 {project 详情 + "member_count": n, "document_count": n}
```

---

# 5. Documents

## POST /api/v1/projects/{project_id}/documents

```
Content-Type: multipart/form-data
字段: file（必填）, name（可选，默认取文件名）
支持类型: .pdf .doc .docx .xlsx .xls .txt（V0.1 主链路保证 .pdf 文本型；其余进入解析管线但质量承诺分级）
大小限制: 50MB
Response: 201
{
  "document_id": "...",
  "file_name": "...",
  "file_size": 12345,
  "parse_status": "PENDING",        // PENDING → PARSING → READY | FAILED
  "created_at": "..."
}
```
- 文件落盘（MinIO/本地存储抽象层）后解析**异步执行**
- 解析完成 → Chunk → Embedding → 入库 Milvus（携带 project_id / document_id / page / bbox 元数据）

## GET /api/v1/projects/{project_id}/documents

```
Response: 200 {"items": [{document_id, file_name, parse_status, page_count, chunk_count, created_at}], "total": n}
```

## GET /api/v1/projects/{project_id}/documents/{document_id}

```
Response: 200
{
  "document_id": ..., "file_name": ..., "parse_status": "READY",
  "page_count": 53, "chunk_count": 812,
  "parse_error": null,              // FAILED 时携带原因
  "created_at": ...
}
```

## DELETE /api/v1/projects/{project_id}/documents/{document_id}

```
Response: 204
```
- 同步删除存储文件 + Milvus 中该 document_id 的向量（V0.1 允许软删除标记 + 异步清理）

## GET /api/v1/projects/{project_id}/documents/{document_id}/file

```
Response: 200 原始文件内容（Content-Disposition: inline）
```

- 经过 JWT 和项目成员权限校验；前端使用带 Bearer Token 的 fetch 获取 Blob URL
- PDF 可通过 Blob URL 的 `#page=N` 定位到 Evidence 页码
- Office 文档保留原文件下载；页面预览使用解析阶段转换出的 PDF

## GET /api/v1/projects/{project_id}/documents/{document_id}/preview

```
Response: 200 application/pdf（Content-Disposition: inline）
```

- 返回 Evidence 使用的完整可翻页 PDF：原 PDF 直接返回，Office 返回解析阶段转换出的 PDF
- 前端通过带 Bearer Token 的 fetch 获取 Blob URL，并附加 `#page=N` 定位 Evidence 页码
- 点击右侧证据缩略图时在固定项目工作区加载完整 PDF 并定位页码；用户可在右栏翻页或新窗口打开

## GET /api/v1/projects/{project_id}/documents/{document_id}/pages/{page}/image

```
Response: 200 image/jpeg（页面缩略图，Evidence 栏渲染用）
Query:   ?width=400（可选，等比缩放）
```

---

# 6. Retrieval（SSE）

## POST /api/v1/projects/{project_id}/retrieval/query

```
Content-Type: application/json
Request:
{
  "question": "3号楼二层卫生间防水高度是多少？",
  "conversation_id": null,          // 首轮为空；后续传 started/done 返回的 ID
  "top_k": 8                        // 可选，默认 8，范围 1~20
}
Response: 200 text/event-stream
```

### SSE 事件序列（顺序约定）

```
event: started
data: {"request_id": "req_xxx", "conversation_id": "conv_xxx"}

event: stage
data: {"stage": "retrieving", "message": "正在检索项目资料"}

event: evidence          ← 检索完成后先推证据（前端右栏实时渲染，不等回答）
data: {"evidences": [Evidence...]}

event: token             ← LLM 流式输出（可多条）
data: {"delta": "根据"}

event: done
data: {"request_id": "req_xxx", "conversation_id": "conv_xxx", "answer": "完整回答...", "evidences": [Evidence...]}

event: error
data: {"code": "RETRIEVAL_FAILED", "message": "..."}
```

- 前端不得展示内部 node 名称（01 §38），stage.message 使用业务语言
- 检索不到足够证据时：`evidence` 事件返回空数组 + `done.answer` 为
  「未找到足够证据 + 推荐人工查看清单」（推荐文件来自低置信召回结果，不编造）

### Evidence 结构（01 §18 落地）

```
{
  "evidence_id": "ev_xxx",
  "file_id": "doc_xxx",
  "file_name": "A-205.pdf",
  "source_type": "PROJECT_DOCUMENT",   // PROJECT_DRAWING / PROJECT_TABLE / ...（01 §19）
  "page": 12,
  "content": "...",
  "score": 0.87,
  "thumbnail_url": "/api/v1/projects/{pid}/documents/{doc_id}/pages/12/image",
  "bbox": null,                        // V0.1 可空，V1.1 页面内高亮
  "version": null,
  "metadata": {"chunk_id": "chunk_xxx", "project_id": 1001}
}
```

### Answer 引用约定

- LLM 生成时以 `[E1]` `[E2]` 标注引用证据序号，序号与 done 事件 evidences 数组下标一致
- Citation 校验：answer 中的数字/图号/材料名必须在对应 Evidence.content 中出现，
  否则触发 validate 重生成（02 §6.20 的 V0.1 简化版：仅校验显式引用与硬事实项）

## Conversation Memory

```
GET  /api/v1/projects/{project_id}/conversations
GET  /api/v1/projects/{project_id}/conversations/{conversation_id}
POST /api/v1/projects/{project_id}/conversations/{conversation_id}/memories
```

- 完整原始消息保存在 `conversation_messages`，滑动窗口只控制发送给模型的最近消息
- 达到 Token 阈值后，较早消息生成增量摘要；摘要不得替代项目 Evidence
- `conversation_id` 与 tenant、user、project 严格绑定，跨项目复用返回 409
- 长期记忆仅允许写入用户明确确认的偏好、决定或待办；工程参数仍需重新检索原始资料
- 项目级记忆与用户通用记忆分开，检索时最多注入相关的 5 条已确认记忆

---

# 7. 内部实现约定（非接口契约，开发基准）

```
1. 路由：Orchestrator 意图分类，V0.1 仅实现 project 检索意图
   （intent=STANDARD / PLAN 返回 501 NOT_IMPLEMENTED_V0.1，不在 API 层暴露内部名）
2. 检索管线（V0.1）：
   DenseRetriever(BGE-M3) + LexicalRetriever(接口占位，返回空) → merge
   → Reranker 占位（按 dense score 排序）→ TopK → Evidence 组装
   词法通道三候选（Milvus FTS / bm25s / BGE-M3 Sparse）由 evaluation/ 实验定案，
   实现前不写死任何偏袒逻辑（01 §52.5）
3. 查询不建 Task：SSE 直接流式返回；超时预算：检索 ≤5s，生成 ≤30s（01 §24 性能目标）
4. LLM 调用经 LLMFactory；Embedding 经 EmbeddingFactory；两者均可配置切换
5. 三层兜底（01 §28）：Retry → 降级（dense 独跑）→ 人工兜底（推荐文件清单）
```

---

# 8. 占位模块（后续版本增量补齐，不在本版冻结）

| 模块 | 说明 |
| --- | --- |
| standards/query | 规范查询 Agent；契约遵循 01 §45 数据流，schema 到对应阶段冻结 |
| plans/create + resume | 施工方案 Agent + HITL；长任务 Task 化 + checkpoint resume（01 §39/40） |
| tasks/* | Task 状态查询/恢复/事件；仅 Plan 长任务使用 |
| 文件预览高级特性 | bbox 页面内高亮、多页缩略图网格（V1.1） |

---

# 9. 前端最小页面约定（V0.1）

```
1. 登录页：用户名/密码 → 存储 token
2. 项目列表页：项目卡片（名称/文档数）→ 进入项目
3. 项目对话页（核心）：
   ├─ 左侧：对话流（用户问题 / AI 回答流式渲染 / [E1][E2] 引用徽标）
   ├─ 右侧：Evidence 栏（缩略图 + 文件名 + 页码；点击打开 PDF 并定位页码）
   └─ 底部：输入框 + 发送
4. 文件上传：项目内上传入口 + 解析状态轮询（PENDING/PARSING/READY/FAILED）
5. 不包含（V0.1）：方案编制界面、任务中心、拖拽式编辑器
```

---

# 10. V0.1 验收清单（对应 00 §35 的先行子集）

```
[ ] 登录 / 登出 / token 过期处理
[ ] 创建项目 / 项目列表 / 无权限项目不可见
[ ] 上传文本型 PDF → 解析 READY → 可查询
[ ] 提问 → SSE 流式回答 → 回答携带 [En] 引用
[ ] Evidence 栏展示缩略图 + 页码 → 点击打开 PDF 定位
[ ] 检索不到时返回「未找到足够证据 + 推荐文件」，不编造
[ ] 非项目成员访问接口 → 403
```
