"""Project Retrieval Agent 节点（02 6.4~6.20 的 V0.1 简化版）。"""
import re

from config import settings
from core.exceptions import AppError
from core.llm_factory import get_llm
from core.logger import get_logger
from agents.project_retrieval.prompts import (FALLBACK_ANSWER,
                                              build_answer_messages)
from services.evidence_service import build_evidence
from services.retrieval.dense_retriever import DenseRetriever
from services.retrieval.lexical_retriever import LexicalRetriever
from services.retrieval.reranker import rerank

logger = get_logger("agent.project_retrieval")


def validate_input(state: dict) -> dict:
    q = (state.get("original_query") or "").strip()
    if not q:
        raise AppError("VALIDATION_ERROR", "问题不能为空", 422)
    if not state.get("project_id"):
        raise AppError("VALIDATION_ERROR", "缺少 project_id", 422)
    return {"fallback_level": 0}


def analyze_query(state: dict) -> dict:
    return {"query_type": "PROJECT_GENERAL"}


def retrieve(state: dict) -> dict:
    # Dense + Lexical（占位）合并召回；词法未实现时 Dense 独跑（01 28 降级）
    query = state["original_query"]
    project_id = state["project_id"]
    try:
        dense = DenseRetriever().retrieve(query, project_id, top_k=20)
    except Exception as e:
        logger.error("dense retrieve failed: %s", e)
        raise AppError("RETRIEVAL_FAILED", "项目资料检索失败，请稍后重试", 500)
    lexical = LexicalRetriever().retrieve(query, project_id, top_k=20)
    merged = {c.chunk_id: c for c in dense + lexical}
    top = rerank(query, list(merged.values()), top_k=8)
    return {"evidences_raw": top,
            "retrieval_status": "OK" if top else "EMPTY"}


def build_evidence_node(state: dict) -> dict:
    from db.session import SessionLocal
    db = SessionLocal()
    try:
        evs = build_evidence(db, state["project_id"],
                             state.get("evidences_raw", []))
    finally:
        db.close()
    return {"evidences": evs}


def check_confidence(state: dict) -> dict:
    # 02 6.15 规则版（阈值可配置，后续用 evaluation/ 数据校准）
    evs = state.get("evidences") or []
    top = evs[0]["score"] if evs else 0.0
    thr = settings.retrieval_confidence_threshold
    high = top >= thr and len(evs) >= 2
    return {"confidence": 1.0 if high else 0.2,
            "human_required": False, "fallback_needed": not high}


def route_after_confidence(state: dict) -> str:
    if state.get("fallback_needed") or not state.get("evidences"):
        return "fallback"
    return "generate_answer"


def generate_answer(state: dict) -> dict:
    messages = build_answer_messages(state["original_query"],
                                     state["evidences"])
    answer = get_llm().chat(messages)
    return {"answer": answer}


def validate_answer(state: dict) -> dict:
    # 02 6.20 简化硬事实校验：回答中的数字必须出现在证据内容中。
    # 最多校验 2 轮：第 1 轮失败触发一次重生成，第 2 轮仍失败则附加人工核对提示。
    answer = state.get("answer") or ""
    evs = state.get("evidences") or []
    numbers = re.findall(r"\d+(?:\.\d+)?", answer)
    evidence_text = " ".join(e["content"] for e in evs)
    missing = [n for n in numbers if n not in evidence_text]
    pass_no = state.get("validate_pass", 0) + 1
    if missing and pass_no == 1:
        logger.warning("validate_answer: %s 个数字不在证据中，重生成一次",
                       len(missing))
        return {"validate_pass": pass_no, "regen_requested": True}
    if missing:
        return {"validate_pass": pass_no, "regen_requested": False,
                "answer": answer +
                "（提示：部分数值未能与项目资料完全对应，请人工核对。）"}
    return {"validate_pass": pass_no, "regen_requested": False}


def route_after_validate(state: dict) -> str:
    if state.get("regen_requested"):
        return "generate_answer"
    return "end"


def fallback(state: dict) -> dict:
    return {"answer": FALLBACK_ANSWER, "confidence": 0.0,
            "retrieval_status": "EMPTY"}
