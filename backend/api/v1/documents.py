"""Documents API（03 5）：上传（异步解析）/列表/详情/删除/页码缩略图。"""
from fastapi import (APIRouter, BackgroundTasks, Depends, File, UploadFile,
                     Query)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from config import settings
from core.exceptions import AppError
from db.models import User
from db.session import SessionLocal, get_db
from dependencies import get_current_project, get_current_user
from services import document_service, preview_service

router = APIRouter(prefix="/projects/{project_id}/documents",
                   tags=["documents"])


@router.post("", status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project=Depends(get_current_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise AppError("FILE_TOO_LARGE", "文件超过 {}MB 限制".format(
            settings.max_upload_mb), 413)
    file_name = file.filename or "unnamed"
    file_path = document_service.save_upload(project.id, file_name, content)
    doc = document_service.create_document(
        db, project.id, file_name, file_path, len(content), user.id)
    # 解析异步执行（FastAPI BackgroundTasks 同请求进程内；Celery 化留后续）
    def _parse():
        s = SessionLocal()
        try:
            document_service.run_parse(s, doc.id)
        finally:
            s.close()
    background_tasks.add_task(_parse)
    return {"document_id": doc.id, "file_name": doc.file_name,
            "file_size": doc.file_size, "parse_status": doc.parse_status,
            "created_at": doc.created_at.isoformat() + "Z"}


@router.get("")
def list_documents(project=Depends(get_current_project),
                   db: Session = Depends(get_db)):
    from db.models import Document
    docs = (db.query(Document)
            .filter(Document.project_id == project.id)
            .order_by(Document.created_at.desc()).all())
    items = [{"document_id": d.id, "file_name": d.file_name,
              "parse_status": d.parse_status, "page_count": d.page_count,
              "chunk_count": d.chunk_count,
              "created_at": d.created_at.isoformat() + "Z"} for d in docs]
    return {"items": items, "total": len(items)}


@router.get("/{document_id}")
def get_document(document_id: str, project=Depends(get_current_project),
                 db: Session = Depends(get_db)):
    d = document_service.get_document(db, project.id, document_id)
    return {"document_id": d.id, "file_name": d.file_name,
            "parse_status": d.parse_status, "page_count": d.page_count,
            "chunk_count": d.chunk_count, "parse_error": d.parse_error,
            "created_at": d.created_at.isoformat() + "Z"}


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, project=Depends(get_current_project),
                    db: Session = Depends(get_db)):
    d = document_service.get_document(db, project.id, document_id)
    document_service.delete_document(db, d)


@router.get("/{document_id}/pages/{page}/image")
def page_image(document_id: str, page: int,
               width: int = Query(default=400, ge=100, le=1200),
               project=Depends(get_current_project),
               db: Session = Depends(get_db)):
    d = document_service.get_document(db, project.id, document_id)
    try:
        img = preview_service.render_page(d.file_path, page, width)
    except ValueError:
        raise AppError("VALIDATION_ERROR", "页码超出范围", 422)
    return Response(content=img, media_type="image/jpeg")
