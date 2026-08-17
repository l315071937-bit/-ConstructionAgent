"""Retrieval API（03 6）：SSE 流式问答（短查询不 Task 化）。"""
import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agents.orchestrator import route
from core.exceptions import AppError
from agents.project_retrieval.graph import build_graph
from core.logger import get_logger
from db.models import User
from db.session import get_db
from dependencies import get_current_project, get_current_user
from services import conversation_service

router = APIRouter(prefix="/projects/{project_id}/retrieval",
                   tags=["retrieval"])

logger = get_logger("api.retrieval")

# 节点 → 用户可见阶段文案（01 38：不得暴露内部 node 名称）
STAGE_MESSAGES = {
    "validate_input": "正在分析问题",
    "analyze_query": "正在分析问题",
    "retrieve": "正在检索项目资料",
    "build_evidence": "正在整理检索依据",
    "check_confidence": "正在核验证据可信度",
    "generate_answer": "正在生成回答",
    "validate_answer": "正在校验回答",
    "fallback": "正在整理检索结果",
}


class QueryRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    top_k: int = Field(default=8, ge=1, le=20)


def _sse(event: str, data: dict) -> str:
    return "event: {}\ndata: {}\n\n".format(
        event, json.dumps(data, ensure_ascii=False))


@router.post("/query")
async def query(body: QueryRequest,
                project=Depends(get_current_project),
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    intent = route(body.question)
    if intent != "project":
        raise AppError(
            "AGENT_ROUTE_REQUIRED",
            "该请求应由{}处理".format(
                "规范查询 Agent" if intent == "standard" else "施工方案 Agent"),
            409)

    request_id = "req_" + uuid.uuid4().hex[:12]
    conversation = conversation_service.get_or_create_conversation(
        db, user.tenant_id, user.id, project.id, body.conversation_id)
    conversation_context = conversation_service.build_context(
        db, conversation, body.question)
    conversation_service.append_message(
        db, conversation, "user", body.question,
        {"request_id": request_id})

    async def event_gen():
        yield _sse("started", {"request_id": request_id,
                               "conversation_id": conversation.id})
        try:
            graph = build_graph()
            final_state = None
            async for mode, chunk in graph.astream(
                    {"request_id": request_id,
                     "user_id": user.id,
                     "tenant_id": user.tenant_id,
                     "project_id": project.id,
                     "original_query": body.question,
                     "top_k": body.top_k,
                     "conversation_context": conversation_context},
                    stream_mode=["updates", "values"]):
                if mode == "updates":
                    for node_name, delta in chunk.items():
                        message = STAGE_MESSAGES.get(node_name)
                        if message:
                            yield _sse("stage", {"stage": node_name,
                                                 "message": message})
                        # delta 可能为 None（节点返回空 dict 时 LangGraph 置 None）
                        if delta and "evidences" in delta and delta["evidences"]:
                            yield _sse("evidence",
                                       {"evidences": delta["evidences"]})
                        if delta and "answer" in delta and delta.get("answer"):
                            yield _sse("token", {"delta": delta["answer"]})
                else:
                    final_state = chunk
            if final_state is None:
                final_state = {}
            answer = final_state.get("answer", "")
            evidences = final_state.get("evidences", [])
            if answer:
                conversation_service.append_message(
                    db, conversation, "assistant", answer,
                    {"request_id": request_id, "evidences": evidences,
                     "confidence": final_state.get("confidence")})
                conversation_service.compact_if_needed(db, conversation)
            yield _sse("done", {
                "request_id": request_id,
                "conversation_id": conversation.id,
                "answer": answer,
                "evidences": evidences,
                "confidence": final_state.get("confidence"),
            })
        except Exception as e:
            logger.exception("retrieval query failed: %s", e)
            yield _sse("error", {"code": getattr(e, "code", "INTERNAL_ERROR"),
                                 "message": str(e)})
    return StreamingResponse(event_gen(), media_type="text/event-stream")
