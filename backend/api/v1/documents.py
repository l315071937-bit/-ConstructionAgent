"""Documents API（03 5）：上传（异步解析）/列表/详情/删除/文件预览。"""
import mimetypes
import os

from fastapi import (APIRouter, BackgroundTasks, Depends, File, UploadFile,
                     Query)
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from config import settings
from core.exceptions import AppError
from db.models import Document, DocumentFolderLink, User
from db.session import SessionLocal, get_db
from dependencies import get_current_project, get_current_user
from services import document_service, folder_service, preview_service
from services.document_parser.router import SUPPORTED_EXTS

router = APIRouter(prefix="/projects/{project_id}/documents",
                   tags=["documents"])


@router.post("", status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: str | None = Query(default=None),
    project=Depends(get_current_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_name = file.filename or "unnamed"
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise AppError("UNSUPPORTED_FILE_TYPE",
                       "不支持的文件类型: {}".format(ext or "无扩展名"), 415)
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise AppError("FILE_TOO_LARGE", "文件超过 {}MB 限制".format(
            settings.max_upload_mb), 413)
    if folder_id:
        folder_service.get_folder(db, project.id, folder_id)
    file_path = document_service.save_upload(project.id, file_name, content)
    doc = document_service.create_document(
        db, project.id, file_name, file_path, len(content), user.id)
    if folder_id:
        folder_service.assign_document(db, project.id, doc.id, folder_id)
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
    rows = (db.query(Document, DocumentFolderLink.folder_id)
            .outerjoin(DocumentFolderLink,
                       DocumentFolderLink.document_id == Document.id)
            .filter(Document.project_id == project.id)
            .order_by(Document.created_at.desc()).all())
    items = [{"document_id": d.id, "file_name": d.file_name,
              "folder_id": folder_id,
              "parse_status": d.parse_status, "page_count": d.page_count,
              "chunk_count": d.chunk_count,
              "created_at": d.created_at.isoformat() + "Z"}
             for d, folder_id in rows]
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


@router.get("/{document_id}/file")
def document_file(document_id: str, project=Depends(get_current_project),
                  db: Session = Depends(get_db)):
    """Return the original document after the normal project access check."""
    d = document_service.get_document(db, project.id, document_id)
    if not os.path.isfile(d.file_path):
        raise AppError("DOCUMENT_FILE_MISSING", "文档文件不存在", 404)
    media_type = mimetypes.guess_type(d.file_name)[0] or "application/octet-stream"
    return FileResponse(d.file_path, media_type=media_type, filename=d.file_name,
                        content_disposition_type="inline")


@router.get("/{document_id}/preview")
def document_preview(document_id: str, project=Depends(get_current_project),
                     db: Session = Depends(get_db)):
    """Return the complete PDF representation used by Evidence previews."""
    d = document_service.get_document(db, project.id, document_id)
    try:
        preview_path = preview_service.get_preview_file_path(d.file_path)
    except FileNotFoundError:
        raise AppError("PREVIEW_UNAVAILABLE", "当前文档暂不支持完整预览", 422)
    preview_name = os.path.splitext(d.file_name)[0] + ".pdf"
    return FileResponse(preview_path, media_type="application/pdf",
                        filename=preview_name,
                        content_disposition_type="inline")


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
    except (FileNotFoundError, RuntimeError):
        raise AppError("PREVIEW_UNAVAILABLE", "当前文档暂不支持页面预览", 422)
    return Response(content=img, media_type="image/jpeg")
