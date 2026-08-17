from pydantic import BaseModel, Field


class HumanDecision(BaseModel):
    action: str = Field(min_length=1, max_length=32)
    template_id: str | None = None
    outline: list[str] | None = None
    comment: str = Field(default="", max_length=1000)


class PlanAgentResult(BaseModel):
    task_id: str
    status: str
    outline: list[str] = Field(default_factory=list)
    document_id: str | None = None
    project_evidences: list[dict] = Field(default_factory=list)
    standard_evidences: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    human_required: bool = False
    human_reason: str | None = None
