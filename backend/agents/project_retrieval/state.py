"""ProjectRetrievalState（02 6.2 的 V0.1 子集）。
短查询不 Task 化（01 52.2），无需 checkpointer。
注意：LangGraph 只保留 Schema 中声明的键，节点返回的键必须在下方声明。"""
from typing import TypedDict


class ProjectRetrievalState(TypedDict, total=False):
    request_id: str
    user_id: int
    tenant_id: int
    project_id: int

    original_query: str
    query_type: str          # V0.1 恒为 PROJECT_GENERAL
    top_k: int
    conversation_context: str

    evidences_raw: list      # retrieve 节点产出的 RetrievedChunk 列表
    retrieval_candidate_count: int
    evidences: list          # build_evidence 产出的 Evidence 字典列表
    answer: str
    confidence: float
    retrieval_status: str    # OK | EMPTY
    fallback_level: int
    fallback_needed: bool    # check_confidence 路由信号
    validate_pass: int      # validate_answer 校验轮次（最多 2 轮）
    regen_requested: bool   # 是否触发一次重生成
    human_required: bool
    human_reason: str
    error: str | None
