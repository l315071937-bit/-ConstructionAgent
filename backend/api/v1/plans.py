"""Construction Plan task, HITL resume and generated-document APIs."""
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agents.construction_plan.schemas import HumanDecision
from core.exceptions import AppError
from db.models import User
from db.session import SessionLocal, get_db
from dependencies import get_current_project, get_current_user
from services import plan_document_service, plan_task_service

router = APIRouter(prefix="/projects/{project_id}", tags=["plans"])


class PlanCreate(BaseModel):
    request: str = Field(min_length=2, max_length=2000)


@router.post("/plans", status_code=202)
def create_plan(body: PlanCreate, background_tasks: BackgroundTasks,
                project=Depends(get_current_project),
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    task = plan_task_service.create(
        db, user.tenant_id, user.id, project.id, body.request)
    background_tasks.add_task(plan_task_service.run_task, task.id)
    return plan_task_service.serialize(task)


@router.get("/tasks")
def list_tasks(limit: int = Query(default=20, ge=1, le=100),
               project=Depends(get_current_project),
               user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    items = plan_task_service.list_tasks(
        db, user.tenant_id, user.id, project.id, limit)
    return {"items": [plan_task_service.serialize(item, detail=False)
                      for item in items], "total": len(items)}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, project=Depends(get_current_project),
             user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    task = plan_task_service.get(
        db, user.tenant_id, user.id, project.id, task_id)
    return plan_task_service.serialize(task)


@router.get("/tasks/{task_id}/events")
def stream_task_events(task_id: str, project=Depends(get_current_project),
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    plan_task_service.get(
        db, user.tenant_id, user.id, project.id, task_id)
    tenant_id, user_id, project_id = user.tenant_id, user.id, project.id

    async def events():
        previous = None
        while True:
            event_db = SessionLocal()
            try:
                task = plan_task_service.get(
                    event_db, tenant_id, user_id, project_id, task_id)
                payload = plan_task_service.serialize(task)
            finally:
                event_db.close()
            marker = (payload["status"], payload["current_stage"],
                      payload["progress"])
            if marker != previous:
                event = ("human_required" if payload["status"] == "WAITING_HUMAN"
                         else "task_completed" if payload["status"] == "COMPLETED"
                         else "error" if payload["status"] == "FAILED"
                         else "stage")
                yield "event: {}\ndata: {}\n\n".format(
                    event, json.dumps(payload, ensure_ascii=False))
                previous = marker
            if payload["status"] in {
                    "WAITING_HUMAN", "COMPLETED", "FAILED", "CANCELLED"}:
                break
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/tasks/{task_id}/resume", status_code=202)
def resume_task(task_id: str, decision: HumanDecision,
                background_tasks: BackgroundTasks,
                project=Depends(get_current_project),
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    task = plan_task_service.get(
        db, user.tenant_id, user.id, project.id, task_id)
    if task.status != "WAITING_HUMAN":
        raise AppError("PLAN_TASK_NOT_WAITING",
                       "当前方案任务不在人工确认状态", 409)
    plan_task_service.mark_running(db, task)
    background_tasks.add_task(
        plan_task_service.run_task, task.id, decision.model_dump())
    return plan_task_service.serialize(task)


@router.get("/plans/documents/{document_id}/{file_format}")
def download_document(document_id: str, file_format: str,
                      project=Depends(get_current_project),
                      user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    if file_format not in {"docx", "pdf"}:
        raise AppError("PLAN_FILE_FORMAT_INVALID", "仅支持 DOCX 或 PDF", 422)
    document = plan_document_service.get(
        db, user.tenant_id, project.id, document_id)
    path = Path(document.docx_path if file_format == "docx" else document.pdf_path)
    if not path.is_file():
        raise AppError("PLAN_FILE_MISSING", "方案文件不存在", 404)
    media_type = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  if file_format == "docx" else "application/pdf")
    return FileResponse(path, media_type=media_type,
                        filename=document.file_name + "." + file_format)
