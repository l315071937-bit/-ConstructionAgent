"""Evidence gateways used by the Plan Agent without importing other agents."""
from core.logger import get_logger
from db.session import SessionLocal
from services.evidence_service import build_evidence
from services.retrieval.dense_retriever import DenseRetriever
from services.retrieval.reranker import rerank
from services.retrieval.standard_dense_retriever import StandardDenseRetriever
from services.standard_evidence_service import build_standard_evidence

logger = get_logger("service.plan_evidence")
_TEST_MARKERS = ("测试", "样例", "示例", "test", "demo")


def _is_formal_standard(evidence: dict) -> bool:
    searchable = " ".join(str(evidence.get(key) or "") for key in (
        "file_name", "standard_name", "standard_code")).casefold()
    return (evidence.get("status") == "active"
            and not any(marker in searchable for marker in _TEST_MARKERS))


def retrieve_project_evidence(project_id: int, query: str,
                              top_k: int = 12) -> dict:
    try:
        chunks = DenseRetriever().retrieve(query, project_id,
                                           top_k=max(20, top_k))
        chunks = rerank(query, chunks, top_k=top_k)
        db = SessionLocal()
        try:
            evidences = build_evidence(db, project_id, chunks)
        finally:
            db.close()
        return {"evidences": evidences, "warnings": []}
    except Exception as exc:
        logger.error("plan project evidence retrieval failed: %s", exc)
        return {"evidences": [],
                "warnings": ["项目资料检索失败，相关工程参数须人工补充。"]}


def retrieve_standard_evidence(tenant_id: int, query: str,
                               top_k: int = 12) -> dict:
    try:
        chunks = StandardDenseRetriever().retrieve(
            query, tenant_id, top_k=max(20, top_k))
        db = SessionLocal()
        try:
            candidates = build_standard_evidence(
                db, tenant_id, chunks, top_k=top_k, query=query)
        finally:
            db.close()
    except Exception as exc:
        logger.error("plan standard evidence retrieval failed: %s", exc)
        return {"evidences": [],
                "warnings": ["现行规范检索失败，不得将模型知识作为正式依据。"]}

    formal = [item for item in candidates if _is_formal_standard(item)]
    excluded = len(candidates) - len(formal)
    warnings = []
    if excluded:
        warnings.append(
            "已排除 {} 条测试、示例、状态未知或非现行规范，未作为正式工程依据。".format(
                excluded))
    if not formal:
        warnings.append("未检索到可确认现行有效的正式规范依据。")
    return {"evidences": formal, "warnings": warnings}
