"""Project-context Standard Query Agent SSE endpoint."""
import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agents.standard_query.graph import build_graph
from core.logger import get_logger
from db.models import User
from db.session import get_db
from dependencies import get_current_project, get_current_user
from services import conversation_service

router = APIRouter(prefix="/projects/{project_id}/standards",
                   tags=["standard-query"])
logger = get_logger("api.standard_query")

STAGES = {
    "validate_input": "正在分析规范问题",
    "analyze_standard_query": "正在识别地区和专业",
    "retrieve": "正在检索规范知识库",
    "build_evidence": "正在整理规范依据",
    "version_check": "正在核对规范版本和状态",
    "applicability_check": "正在检查地区适用性",
    "check_confidence": "正在核验证据可信度",
    "generate_answer": "正在生成规范回答",
    "validate_answer": "正在校验规范引用",
    "fallback": "正在整理检索结果",
}


class StandardQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    top_k: int = Field(default=8, ge=1, le=20)


def _sse(event: str, data: dict) -> str:
    return "event: {}\ndata: {}\n\n".format(
        event, json.dumps(data, ensure_ascii=False))


@router.post("/query")
async def query_standard(body: StandardQueryRequest,
                         project=Depends(get_current_project),
                         user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    request_id = "std_" + uuid.uuid4().hex[:12]
    conversation = conversation_service.get_or_create_conversation(
        db, user.tenant_id, user.id, project.id, body.conversation_id,
        agent_type="standard")
    context = conversation_service.build_context(db, conversation, body.question)
    conversation_service.append_message(
        db, conversation, "user", body.question, {"request_id": request_id})

    async def event_generator():
        yield _sse("started", {"request_id": request_id,
                               "conversation_id": conversation.id,
                               "agent_type": "standard"})
        try:
            final_state = {}
            async for mode, chunk in build_graph().astream({
                    "request_id": request_id, "user_id": user.id,
                    "tenant_id": user.tenant_id, "project_id": project.id,
                    "original_query": body.question, "top_k": body.top_k,
                    "conversation_context": context,
                    }, stream_mode=["updates", "values"]):
                if mode == "updates":
                    for node_name, delta in chunk.items():
                        if node_name in STAGES:
                            yield _sse("stage", {"message": STAGES[node_name]})
                        if delta and delta.get("evidences"):
                            yield _sse("evidence", {
                                "evidences": delta["evidences"]})
                        if delta and delta.get("answer"):
                            yield _sse("token", {"delta": delta["answer"]})
                else:
                    final_state = chunk
            answer = final_state.get("answer", "")
            evidences = final_state.get("evidences", [])
            if answer:
                conversation_service.append_message(
                    db, conversation, "assistant", answer,
                    {"request_id": request_id, "evidences": evidences,
                     "confidence": final_state.get("confidence"),
                     "agent_type": "standard"})
                conversation_service.compact_if_needed(db, conversation)
            yield _sse("done", {
                "request_id": request_id, "conversation_id": conversation.id,
                "answer": answer, "evidences": evidences,
                "confidence": final_state.get("confidence"),
                "version_warnings": final_state.get("version_warnings", []),
            })
        except Exception as exc:
            logger.exception("standard query failed: %s", exc)
            yield _sse("error", {"code": getattr(exc, "code", "INTERNAL_ERROR"),
                                 "message": str(exc)})
    return StreamingResponse(event_generator(), media_type="text/event-stream")
