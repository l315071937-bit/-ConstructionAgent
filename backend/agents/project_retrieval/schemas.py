"""Agent 输出 Schema（02 15：AgentResult 的 V0.1 版）。"""
from pydantic import BaseModel


class AgentResult(BaseModel):
    request_id: str
    status: str
    answer: str | None = None
    evidences: list = []
    confidence: float | None = None
    human_required: bool = False
    human_reason: str | None = None
