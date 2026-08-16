"""Standard Query Agent nodes: applicability and version checks precede LLM."""
import re

from config import settings
from core.exceptions import AppError
from core.llm_factory import get_llm
from core.logger import get_logger
from agents.standard_query.prompts import (FALLBACK_ANSWER,
                                           build_standard_messages)
from services.retrieval.standard_dense_retriever import StandardDenseRetriever
from services.standard_evidence_service import build_standard_evidence

logger = get_logger("agent.standard_query")

REGIONS = ["深圳", "广州", "广东", "福建", "厦门", "上海", "北京", "全国"]
DISCIPLINES = ["建筑", "结构", "给排水", "电气", "暖通", "消防", "市政", "园林"]


def validate_input(state: dict) -> dict:
    if not (state.get("original_query") or "").strip():
        raise AppError("VALIDATION_ERROR", "问题不能为空", 422)
    if not state.get("tenant_id"):
        raise AppError("VALIDATION_ERROR", "缺少租户信息", 422)
    top_k = state.get("top_k", 8)
    if not isinstance(top_k, int) or not 1 <= top_k <= 20:
        raise AppError("VALIDATION_ERROR", "top_k 必须在 1 到 20 之间", 422)
    return {"human_required": False}


def analyze_standard_query(state: dict) -> dict:
    query = state["original_query"]
    region = next((item for item in REGIONS if item in query), None)
    discipline = next((item for item in DISCIPLINES if item in query), None)
    return {"region": region, "discipline": discipline,
            "standard_type": "STANDARD_QUERY"}


def retrieve(state: dict) -> dict:
    try:
        chunks = StandardDenseRetriever().retrieve(
            state["original_query"], state["tenant_id"],
            top_k=max(20, state.get("top_k", 8)))
    except Exception as exc:
        logger.error("standard retrieval failed: %s", exc)
        raise AppError("RETRIEVAL_FAILED", "规范知识库检索失败", 500)
    return {"evidences_raw": chunks}


def build_evidence_node(state: dict) -> dict:
    from db.session import SessionLocal
    db = SessionLocal()
    try:
        evidences = build_standard_evidence(
            db, state["tenant_id"], state.get("evidences_raw", []),
            state.get("region"), state.get("top_k", 8),
            state.get("original_query", ""))
    finally:
        db.close()
    return {"evidences": evidences}


def check_version(state: dict) -> dict:
    warnings = []
    seen = set()
    for evidence in state.get("evidences", []):
        status = evidence.get("status") or "unknown"
        label = evidence.get("standard_code") or evidence.get("standard_name")
        if status == "unknown":
            warning = "{}：无法确认最新有效状态".format(label)
            if warning not in seen:
                warnings.append(warning)
                seen.add(warning)
        elif status in {"repealed", "replaced"}:
            warning = "{}：已废止或被替代".format(label)
            if warning not in seen:
                warnings.append(warning)
                seen.add(warning)
    return {"version_warnings": warnings}


def check_applicability(state: dict) -> dict:
    region = state.get("region")
    parent_regions = {"深圳": "广东", "广州": "广东", "厦门": "福建"}
    allowed_regions = {region, "全国", parent_regions.get(region)}
    matches = [evidence for evidence in state.get("evidences", [])
               if not region or evidence.get("region") in allowed_regions
               or region in (evidence.get("region") or "")]
    return {"applicability": {
        "region": region, "matched_count": len(matches),
        "needs_warning": bool(region and not matches),
    }}


def check_confidence(state: dict) -> dict:
    evidences = state.get("evidences", [])
    top_score = evidences[0]["score"] if evidences else 0.0
    applicable = state.get("applicability", {}).get("matched_count", 0)
    enough = bool(evidences) and top_score >= settings.retrieval_confidence_threshold
    if state.get("region") and not applicable:
        enough = False
    return {"confidence": 1.0 if enough else 0.0,
            "fallback_needed": not enough}


def route_after_confidence(state: dict) -> str:
    return "generate_answer" if not state.get("fallback_needed") else "fallback"


def generate_answer(state: dict) -> dict:
    messages = build_standard_messages(
        state["original_query"], state["evidences"], state.get("region"),
        state.get("conversation_context", ""))
    return {"answer": get_llm().chat(messages)}


def validate_answer(state: dict) -> dict:
    answer = state.get("answer") or ""
    evidence_text = " ".join(
        "{} {} {} {}".format(
            item.get("content", ""), item.get("standard_code", ""),
            item.get("article", ""), item.get("version", ""))
        for item in state.get("evidences", []))
    citations = re.findall(r"\[E(\d+)\]", answer)
    numbers = re.findall(r"\d+(?:\.\d+)?", answer)
    missing_numbers = [number for number in numbers if number not in evidence_text]
    pass_number = state.get("validate_pass", 0) + 1
    invalid_citations = [int(item) for item in citations
                         if int(item) > len(state.get("evidences", []))]
    should_regenerate = (not citations or missing_numbers or invalid_citations)
    if should_regenerate and pass_number == 1:
        return {"validate_pass": pass_number, "regen_requested": True}
    if should_regenerate:
        return {"validate_pass": pass_number, "regen_requested": False,
                "answer": answer + "\n请人工复核规范编号、条款和有效状态。"}
    return {"validate_pass": pass_number, "regen_requested": False}


def route_after_validate(state: dict) -> str:
    return "generate_answer" if state.get("regen_requested") else "end"


def fallback(state: dict) -> dict:
    return {"answer": FALLBACK_ANSWER, "confidence": 0.0,
            "human_required": True, "human_reason": "STANDARD_EVIDENCE_MISSING"}
