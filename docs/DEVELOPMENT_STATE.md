# Development State

当前开发分支：`feature/conversation-memory`

已完成主链路：

- 固定三栏工作台与项目多级目录（最多 10 层）
- 已移除独立项目选择页；项目切换和新建统一在三栏工作台内完成
- 规则前置、项目名称预测、项目资料检索 Agent
- 工程规范查询 Agent、独立规范知识库、版本和适用性检查
- 项目与规范多轮会话隔离、滑动窗口和压缩摘要
- 施工方案编制 Agent：企业模板/历史方案、持久化 Task、LangGraph checkpoint
- 模板确认、目录确认、终审恢复，分章节生成、事实/规范/完整性/风险检查
- 危大工程专家论证红色警示，测试/示例/非现行规范禁止作为正式依据
- 终审通过后生成受权限保护的 DOCX/PDF，方案流程已接入三栏工作台

下一阶段：真实企业模板与项目语料联调、施工方案质量评测和提示词校准。
不得把测试规范当作正式工程依据。

Windows 关机后恢复：

```powershell
cd H:\A.AI_MODEL_DEVEL\resume\project\Achi
git switch feature/conversation-memory
git pull origin feature/conversation-memory
.\scripts\start_dev.bat
```

浏览器：`http://127.0.0.1:5173`

登录：`admin / admin123`

交给新的开发会话时，要求先阅读本文件、`docs/00_PROJECT_CONTEXT.md`、
`docs/01_ARCHITECTURE.md`、`docs/02_AGENT_SPEC.md` 和 `docs/03_API_SPEC.md`，
再从当前分支最新提交继续，禁止重新搭建或覆盖已完成主链路。
