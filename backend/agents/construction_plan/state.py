from typing import TypedDict


class ConstructionPlanState(TypedDict, total=False):
    task_id: str
    request_id: str
    user_id: int
    tenant_id: int
    project_id: int
    original_request: str
    task_type: str
    discipline: str
    construction_object: str
    high_risk: bool
    template_candidates: list
    template_id: str | None
    template_name: str | None
    template_content: str | None
    template_outline: list
    reference_plans: list
    outline: list
    project_evidences: list
    standard_evidences: list
    plan_facts: dict
    generated_sections: list
    fact_check_results: list
    standard_check_results: list
    completeness_results: list
    risk_results: list
    warnings: list
    final_content: str
    document_id: str | None
    download_urls: dict
    human_required: bool
    human_reason: str | None
    human_payload: dict
    review_action: str | None
    review_feedback: str
    retry_count: int
    fallback_level: int
    error: str | None
