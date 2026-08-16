SYSTEM_PROMPT = """你是建筑工程规范查询助手，只能依据提供的规范 Evidence 回答。

强制规则：
1. 不得编造规范编号、名称、条款、页码、版本或有效状态；
2. 每项具体要求必须在句末标注 [E1] [E2] 等引用；
3. 明确区分强制要求、推荐做法和适用范围；
4. 状态为 unknown 时必须说明当前知识库无法确认最新有效状态；
5. 状态为 repealed/replaced 时必须提示不可直接作为现行依据；
6. 地区或专业不匹配时必须说明适用性风险；
7. 证据不足时明确说明，不得使用模型记忆补充条款。"""


def build_standard_messages(question: str, evidences: list,
                            region: str | None,
                            conversation_context: str = "") -> list:
    blocks = []
    for index, evidence in enumerate(evidences, start=1):
        blocks.append(
            "[E{index}] {code}《{name}》 版本：{version} 状态：{status} "
            "地区：{region} 条款：{article} 页码：{page}\n内容：{content}".format(
                index=index, code=evidence.get("standard_code") or "未标注编号",
                name=evidence.get("standard_name") or evidence["file_name"],
                version=evidence.get("version") or "未标注",
                status=evidence.get("status") or "unknown",
                region=evidence.get("region") or "未标注",
                article=evidence.get("article") or "未识别",
                page=evidence["page"], content=evidence["content"]))
    user_prompt = (
        "对话上下文仅用于理解指代，不可作为规范事实：\n{history}\n\n"
        "查询地区：{region}\n用户问题：{question}\n\n规范 Evidence：\n{evidence}\n\n"
        "请按“结论、规范依据、适用范围、状态与注意事项”回答并标注引用。"
    ).format(history=conversation_context or "（无）",
             region=region or "未指定", question=question,
             evidence="\n\n".join(blocks))
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}]


FALLBACK_ANSWER = (
    "当前规范知识库未找到足够依据，无法确认具体规范要求。\n"
    "请补充规范编号、地区或专业，或由管理员上传对应的现行规范文件。")
