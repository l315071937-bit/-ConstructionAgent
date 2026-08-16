"""Prompt 模块（02 16/17/18：System + Task + Evidence 注入 + 输出约定）。"""
SYSTEM_PROMPT = """你是建筑工程领域的资料检索助手。
你的回答只能依据下面提供的项目资料 Evidence。

规则：
1. 不得编造事实、图号、页码、尺寸、材料；
2. 不得补充 Evidence 中不存在的工程参数；
3. 引用证据时在句末标注 [E1] [E2]（序号对应 Evidence 编号）；
4. 证据不足时明确说明，不得猜测；
5. 发现证据之间矛盾时，并列列出矛盾并提示人工确认，不得自行选择。"""

def build_answer_messages(question: str, evidences: list,
                          conversation_context: str = "") -> list:
    ctx = []
    for i, ev in enumerate(evidences, start=1):
        ctx.append("[E{num}] 文件：{fname} 页码：{page}\n内容：{content}".format(
            num=i, fname=ev['file_name'], page=ev['page'],
            content=ev['content']))
    evidence_text = "\n\n".join(ctx) if ctx else "（无证据）"
    history = conversation_context or "（无历史上下文）"
    user_msg = (
        "对话上下文（仅用于理解指代和用户目标，不可作为工程事实依据）：\n"
        "{history}\n\n用户当前问题：{q}\n\n项目资料 Evidence：\n{ev}\n\n"
        "请基于本轮 Evidence 回答，并标注 [En] 引用。"
    ).format(history=history, q=question, ev=evidence_text)
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}]

FALLBACK_ANSWER = ("当前未找到足够项目依据。\n建议人工查看相关图纸/文档，或换个问法重试。")
