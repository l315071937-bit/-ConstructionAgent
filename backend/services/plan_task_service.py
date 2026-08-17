"""Persist, run and resume Construction Plan tasks."""
import uuid
import threading

from langgraph.types import Command
from sqlalchemy.orm import Session

from agents.construction_plan.graph import build_graph
from core.exceptions import AppError, NotFoundError
from core.logger import get_logger
from db.models import PlanTask
from db.session import SessionLocal

logger = get_logger("service.plan_task")
_graph = None

STAGE_PROGRESS = {
    "TEMPLATE_SELECTION": ("template_confirmation", 15),
    "GENERIC_TEMPLATE_PERMISSION": ("template_confirmation", 15),
    "OUTLINE_CONFIRMATION": ("outline_confirmation", 30),
    "FINAL_REVIEW": ("final_review", 90),
}


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def serialize(task: PlanTask, detail=True) -> dict:
    result = {
        "task_id": task.id, "project_id": task.project_id,
        "request": task.request, "task_type": task.task_type,
        "status": task.status, "current_stage": task.current_stage,
        "progress": task.progress, "human_required": task.human_required,
        "human_reason": task.human_reason,
        "human_payload": task.human_payload or {}, "error": task.error,
        "created_at": task.created_at.isoformat() + "Z",
        "updated_at": task.updated_at.isoformat() + "Z",
    }
    if detail:
        state = task.state_json or {}
        result.update({
            "outline": state.get("outline", []),
            "project_evidences": state.get("project_evidences", []),
            "standard_evidences": state.get("standard_evidences", []),
            "warnings": state.get("warnings", []),
            "fact_checks": state.get("fact_check_results", []),
            "standard_checks": state.get("standard_check_results", []),
            "completeness_checks": state.get("completeness_results", []),
            "risk_checks": state.get("risk_results", []),
            "final_content": state.get("final_content", ""),
            "document_id": state.get("document_id"),
            "download_urls": state.get("download_urls", {}),
            "high_risk": state.get("high_risk", False),
        })
    return result


def create(db: Session, tenant_id: int, user_id: int, project_id: int,
           request: str) -> PlanTask:
    text = request.strip()
    if not text:
        raise AppError("VALIDATION_ERROR", "方案编制要求不能为空", 422)
    task_id = "plan_" + uuid.uuid4().hex
    task = PlanTask(
        id=task_id, tenant_id=tenant_id, user_id=user_id,
        project_id=project_id, request=text, status="PENDING",
        current_stage="queued", progress=0,
        state_json={"task_id": task_id, "request_id": task_id,
                    "tenant_id": tenant_id, "user_id": user_id,
                    "project_id": project_id, "original_request": text})
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get(db: Session, tenant_id: int, user_id: int, project_id: int,
        task_id: str) -> PlanTask:
    task = (db.query(PlanTask)
            .filter_by(id=task_id, tenant_id=tenant_id, user_id=user_id,
                       project_id=project_id).first())
    if task is None:
        raise NotFoundError("PLAN_TASK_NOT_FOUND", "方案任务不存在")
    return task


def list_tasks(db: Session, tenant_id: int, user_id: int,
               project_id: int, limit: int = 20) -> list[PlanTask]:
    return (db.query(PlanTask)
            .filter_by(tenant_id=tenant_id, user_id=user_id,
                       project_id=project_id)
            .order_by(PlanTask.updated_at.desc()).limit(limit).all())


def mark_running(db: Session, task: PlanTask) -> None:
    task.status = "RUNNING"
    task.human_required = False
    task.human_reason = None
    task.human_payload = {}
    task.error = None
    db.commit()


def run_task(task_id: str, decision: dict | None = None) -> None:
    db = SessionLocal()
    try:
        task = db.query(PlanTask).filter_by(id=task_id).first()
        if task is None:
            return
        task.status = "RUNNING"
        task.current_stage = "processing"
        task.human_required = False
        task.human_reason = None
        task.human_payload = {}
        db.commit()
        config = {"configurable": {"thread_id": task.id}}
        graph = get_graph()
        if decision is None:
            existing = graph.get_state(config)
            graph.invoke(None if existing.created_at else task.state_json,
                         config=config)
        else:
            graph.invoke(Command(resume=decision), config=config)
        snapshot = graph.get_state(config)
        values = dict(snapshot.values or {})
        task.state_json = values
        task.task_type = values.get("task_type", task.task_type)
        if snapshot.interrupts:
            payload = snapshot.interrupts[0].value or {}
            reason = payload.get("kind", "HUMAN_CONFIRMATION")
            stage, progress = STAGE_PROGRESS.get(
                reason, ("human_confirmation", task.progress))
            task.status = "WAITING_HUMAN"
            task.current_stage = stage
            task.progress = progress
            task.human_required = True
            task.human_reason = reason
            task.human_payload = payload
        elif not snapshot.next and values.get("document_id"):
            task.status = "COMPLETED"
            task.current_stage = "completed"
            task.progress = 100
            task.human_required = False
            task.human_reason = None
            task.human_payload = {}
        else:
            task.status = "RUNNING"
            task.current_stage = "processing"
        db.commit()
    except Exception as exc:
        db.rollback()
        task = db.query(PlanTask).filter_by(id=task_id).first()
        if task:
            task.status = ("CANCELLED" if getattr(exc, "code", "") ==
                           "PLAN_CANCELLED" else "FAILED")
            task.current_stage = "cancelled" if task.status == "CANCELLED" else "failed"
            task.human_required = False
            task.error = str(exc)
            db.commit()
        logger.exception("plan task %s failed: %s", task_id, exc)
    finally:
        db.close()


def recover_incomplete_tasks() -> int:
    """Resume tasks left active by a prior single-process server shutdown."""
    db = SessionLocal()
    try:
        task_ids = [row.id for row in db.query(PlanTask).filter(
            PlanTask.status.in_({"PENDING", "RUNNING"})).all()]
    finally:
        db.close()
    for task_id in task_ids:
        threading.Thread(
            target=run_task, args=(task_id,), daemon=True,
            name="plan-recovery-{}".format(task_id[:12])).start()
    return len(task_ids)
