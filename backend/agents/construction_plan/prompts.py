SYSTEM_PROMPT = """你是建筑工程施工方案辅助编制助手。

强制规则：
1. 项目名称、范围、尺寸、数量、材料、强度和做法只能来自 Project Evidence；
2. 技术、质量、验收和安全要求只能来自已确认现行有效的 Standard Evidence；
3. 企业历史方案只可参考结构与措辞，不得复制其中的项目参数；
4. 每项项目事实标注 [P1]，每项规范要求标注 [S1] 等对应引用；
5. Evidence 不足时写 [待人工确认]，严禁猜测或以模型知识补充工程参数；
6. 输出是 AI 辅助草案，不得宣称已经完全满足安全或规范要求。"""


def build_section_messages(title: str, request: str, plan_facts: dict,
                           project_evidences: list,
                           standard_evidences: list,
                           template_content: str = "",
                           references: list | None = None) -> list:
    project_blocks = [
        "[P{}] {} 第{}页：{}".format(index, item.get("file_name"),
                                      item.get("page"), item.get("content"))
        for index, item in enumerate(project_evidences, start=1)]
    standard_blocks = [
        "[S{}] {} {} 第{}页：{}".format(
            index, item.get("standard_code") or item.get("standard_name"),
            item.get("article") or "", item.get("page"),
            item.get("content"))
        for index, item in enumerate(standard_evidences, start=1)]
    reference_text = "\n".join(
        (item.get("content") or "")[:1200] for item in (references or []))
    prompt = """用户任务：{request}
当前章节：{title}

已定事实表（不得改写为其他值）：
{facts}

Project Evidence：
{project}

Standard Evidence（仅以下内容可作为正式规范依据）：
{standard}

企业模板片段（仅用于格式）：
{template}

历史优秀方案片段（仅用于结构和措辞，参数不得沿用）：
{references}

请只输出本章节正文，控制在 800 字以内。证据不足的工程参数写 [待人工确认]。
""".format(
        request=request, title=title,
        facts=plan_facts or "（尚无已定事实）",
        project="\n".join(project_blocks) or "（未检索到）",
        standard="\n".join(standard_blocks) or "（未检索到现行正式依据）",
        template=(template_content or "（无）")[:2000],
        references=reference_text or "（无）")
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}]
