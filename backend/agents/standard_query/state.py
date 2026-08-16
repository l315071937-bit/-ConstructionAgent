from typing import TypedDict


class StandardQueryState(TypedDict, total=False):
    request_id: str
    user_id: int
    tenant_id: int
    project_id: int
    original_query: str
    top_k: int
    conversation_context: str
    region: str | None
    discipline: str | None
    standard_type: str | None
    evidences_raw: list
    evidences: list
    version_warnings: list
    applicability: dict
    confidence: float
    fallback_needed: bool
    answer: str
    regen_requested: bool
    validate_pass: int
    human_required: bool
    human_reason: str
