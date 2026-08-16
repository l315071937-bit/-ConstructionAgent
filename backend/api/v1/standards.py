"""Standard library upload, metadata, preview and deletion endpoints."""
import mimetypes
import os

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     UploadFile)
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from config import settings
from core.exceptions import AppError, PermissionError_
from db.models import User
from db.session import SessionLocal, get_db
from dependencies import get_current_user
from services import preview_service, standard_document_service
from services.document_parser.router import SUPPORTED_EXTS

router = APIRouter(prefix="/standards", tags=["standards"])


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise PermissionError_("仅管理员可以维护规范知识库")


@router.post("/documents", status_code=201)
async def upload_standard(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    standard_name: str = Form(...), standard_code: str = Form(default=""),
    version: str = Form(default=""), region: str = Form(default="全国"),
    discipline: str = Form(default=""),
    standard_type: str = Form(default="国家标准"),
    status: str = Form(default="unknown"),
    publish_date: str = Form(default=""),
    effective_date: str = Form(default=""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    file_name = file.filename or "unnamed"
    extension = os.path.splitext(file_name)[1].lower()
    if extension not in SUPPORTED_EXTS:
        raise AppError("UNSUPPORTED_FILE_TYPE", "不支持的文件类型", 415)
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise AppError("FILE_TOO_LARGE", "规范文件超过上传限制", 413)
    if not standard_name.strip():
        raise AppError("STANDARD_NAME_REQUIRED", "请输入规范名称", 422)
    metadata = {
        "standard_name": standard_name, "standard_code": standard_code,
        "version": version, "region": region, "discipline": discipline,
        "standard_type": standard_type, "status": status,
        "publish_date": publish_date, "effective_date": effective_date,
    }
    standard_document_service.parse_date(publish_date)
    standard_document_service.parse_date(effective_date)
    if status not in standard_document_service.VALID_STATUSES:
        raise AppError("STANDARD_STATUS_INVALID", "规范状态值无效", 422)
    standard_document_service.ensure_not_duplicate(
        db, user.tenant_id, standard_code, version)
    file_path = standard_document_service.save_upload(
        user.tenant_id, file_name, content)
    document = standard_document_service.create_document(
        db, user.tenant_id, user.id, file_name, file_path, len(content), metadata)

    def _parse():
        session = SessionLocal()
        try:
            standard_document_service.run_parse(session, document.id)
        finally:
            session.close()
    background_tasks.add_task(_parse)
    return standard_document_service.document_item(document)


@router.get("/documents")
def list_standards(user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    items = [standard_document_service.document_item(document)
             for document in standard_document_service.list_documents(
                 db, user.tenant_id)]
    return {"items": items, "total": len(items)}


@router.delete("/documents/{document_id}", status_code=204)
def delete_standard(document_id: str,
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _require_admin(user)
    document = standard_document_service.get_document(
        db, user.tenant_id, document_id)
    standard_document_service.delete_document(db, document)
    return Response(status_code=204)


@router.get("/documents/{document_id}/file")
def standard_file(document_id: str,
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    document = standard_document_service.get_document(
        db, user.tenant_id, document_id)
    if not os.path.isfile(document.file_path):
        raise AppError("STANDARD_FILE_MISSING", "规范文件不存在", 404)
    media_type = mimetypes.guess_type(document.file_name)[0] or "application/octet-stream"
    return FileResponse(document.file_path, media_type=media_type,
                        filename=document.file_name,
                        content_disposition_type="inline")


@router.get("/documents/{document_id}/preview")
def standard_preview(document_id: str,
                     user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    document = standard_document_service.get_document(
        db, user.tenant_id, document_id)
    try:
        preview_path = preview_service.get_preview_file_path(document.file_path)
    except FileNotFoundError:
        raise AppError("PREVIEW_UNAVAILABLE", "当前规范暂不支持预览", 422)
    return FileResponse(preview_path, media_type="application/pdf",
                        filename=os.path.splitext(document.file_name)[0] + ".pdf",
                        content_disposition_type="inline")


@router.get("/documents/{document_id}/pages/{page}/image")
def standard_page_image(document_id: str, page: int,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    document = standard_document_service.get_document(
        db, user.tenant_id, document_id)
    try:
        image = preview_service.render_page(document.file_path, page, 400)
    except ValueError:
        raise AppError("VALIDATION_ERROR", "页码超出范围", 422)
    except (FileNotFoundError, RuntimeError):
        raise AppError("PREVIEW_UNAVAILABLE", "规范页面暂不支持预览", 422)
    return Response(content=image, media_type="image/jpeg")
