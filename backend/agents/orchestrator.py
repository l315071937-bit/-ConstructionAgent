"""Orchestrator（01 10 的最小实现）：意图分类与路由。
V0.1 仅实现 project 检索意图；standard/plan 返回明确错误（03 7）。"""
import re

from core.exceptions import AppError

# 保守路由原则（2026-08-16 实测修正）：拿不准就默认走项目检索，
# 拦截永远不是安全选择。只有明确的生成任务/规范咨询才路由到对应 Agent。
# 方案意图：动词 + 方案（如 帮我编制地下室防水施工方案）
_PLAN_HINTS = re.compile(r"(帮我|请)?(编制|编写|生成|写).{0,8}(施工)?方案")
# 规范意图：明确规范编号（GB/JGJ/DB+数字）或明确的规范咨询句式
_STANDARD_HINTS = re.compile(
    r"(GB|JGJ|DB)\s?/?T?\s?\d|规范.{0,6}(要求|规定|是否有效|现行|废止|是多少)|标准图集")



def classify_intent(question: str) -> str:
    if _PLAN_HINTS.search(question):
        return "plan"
    if _STANDARD_HINTS.search(question):
        return "standard"
    return "project"


def route(question: str) -> str:
    intent = classify_intent(question)
    if intent in ("standard", "plan"):
        raise AppError("NOT_IMPLEMENTED_V0_1",
                       "规范查询与方案编制将在后续阶段开放", 501)
    return intent
