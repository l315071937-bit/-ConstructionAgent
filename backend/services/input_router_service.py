"""Cheap input routing before project retrieval or specialist agents."""
import re

from sqlalchemy.orm import Session

from agents.orchestrator import classify_intent
from services import project_service

_PUNCTUATION = re.compile(r"[\s，。！？!?、,.；;：:~～]+")

_GREETINGS = {"你好", "您好", "你好啊", "您好啊", "嗨", "hello", "hi"}
_IDENTITY_QUESTIONS = {
    "你是谁", "你叫什么", "你叫什么名字", "介绍一下自己", "自我介绍",
}
_CAPABILITY_QUESTIONS = {
    "你会什么", "你能做什么", "你可以做什么", "你有什么功能", "有什么功能",
}


def normalize_query(query: str) -> str:
    return _PUNCTUATION.sub("", (query or "").strip().casefold())


def match_quick_rule(query: str) -> dict | None:
    normalized = normalize_query(query)
    if normalized in _GREETINGS:
        return {
            "type": "RULE_REPLY",
            "rule": "GREETING",
            "answer": (
                "你好，我是智能 AI 建筑辅助功能。\n"
                "我可以为您查找项目资料、查询工程规范、编制施工方案。"
            ),
        }
    if normalized in _IDENTITY_QUESTIONS:
        return {
            "type": "RULE_REPLY",
            "rule": "IDENTITY",
            "answer": (
                "我是公司的智能 AI 建筑辅助功能，负责连接项目知识库，"
                "并协助查询项目资料、工程规范和编制施工方案。"
            ),
        }
    if normalized in _CAPABILITY_QUESTIONS:
        return {
            "type": "RULE_REPLY",
            "rule": "CAPABILITIES",
            "answer": (
                "我目前可以帮助您查找项目资料和查询工程规范；"
                "施工方案编制 Agent 将按开发进度开放。"
            ),
        }
    if "最近" in normalized and "项目" in normalized:
        return {
            "type": "RECENT_PROJECTS",
            "rule": "RECENT_PROJECTS",
            "answer": "以下是您有权限访问的最近项目，可以直接点击进入知识库。",
        }
    return None


def route_input(db: Session, user_id: int, query: str,
                active_agent: str = "project") -> dict:
    quick_rule = match_quick_rule(query)
    if quick_rule:
        if quick_rule["type"] == "RECENT_PROJECTS":
            projects = project_service.list_projects(db, user_id)[:3]
            return {**quick_rule,
                    "projects": project_service.project_cards(db, projects)}
        return quick_rule

    if active_agent == "standard":
        return {"type": "AGENT_ROUTE", "intent": "standard",
                "available": True}

    suggestions = project_service.suggest_projects(db, user_id, query, 3)
    if suggestions:
        return {
            "type": "PROJECT_SUGGESTIONS",
            "intent": "project",
            "answer": (
                "我找到了以下可能相关的项目。请选择一个项目，确认后我会"
                "锁定知识库，并在右侧显示该项目的全部资料。"
            ),
            "projects": project_service.project_cards(db, suggestions),
        }

    intent = classify_intent(query)
    if intent == "standard":
        return {
            "type": "AGENT_ROUTE", "intent": intent, "available": True,
        }
    if intent == "plan":
        return {
            "type": "AGENT_ROUTE", "intent": intent, "available": False,
            "answer": "已识别为施工方案编制。施工方案 Agent 正在建设，当前尚未开放。",
        }
    return {"type": "AGENT_ROUTE", "intent": "project", "available": True}
