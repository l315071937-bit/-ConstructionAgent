"""Enterprise plan templates and approved historical reference plans."""
from sqlalchemy.orm import Session

from core.exceptions import AppError, NotFoundError
from db.models import EnterprisePlanDocument

DOCUMENT_TYPES = {"template", "reference_plan"}


def serialize(document: EnterprisePlanDocument, include_content=False) -> dict:
    result = {
        "document_id": document.id,
        "document_type": document.document_type,
        "name": document.name,
        "task_type": document.task_type,
        "discipline": document.discipline,
        "version": document.version,
        "outline": document.outline_json or [],
        "active": document.active,
        "created_at": document.created_at.isoformat() + "Z",
    }
    if include_content:
        result["content"] = document.content
    return result


def create(db: Session, tenant_id: int, user_id: int, document_type: str,
           name: str, task_type: str = "general", discipline: str = "",
           version: str = "", content: str = "",
           outline: list | None = None) -> EnterprisePlanDocument:
    if document_type not in DOCUMENT_TYPES:
        raise AppError("PLAN_DOCUMENT_TYPE_INVALID", "企业方案资料类型无效", 422)
    if not name.strip():
        raise AppError("VALIDATION_ERROR", "资料名称不能为空", 422)
    item = EnterprisePlanDocument(
        tenant_id=tenant_id, created_by=user_id,
        document_type=document_type, name=name.strip(),
        task_type=(task_type or "general").strip().casefold(),
        discipline=discipline.strip(), version=version.strip(),
        content=content.strip(), outline_json=outline or [])
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_documents(db: Session, tenant_id: int,
                   document_type: str | None = None) -> list:
    query = db.query(EnterprisePlanDocument).filter_by(tenant_id=tenant_id)
    if document_type:
        if document_type not in DOCUMENT_TYPES:
            raise AppError("PLAN_DOCUMENT_TYPE_INVALID", "企业方案资料类型无效", 422)
        query = query.filter_by(document_type=document_type)
    return query.order_by(EnterprisePlanDocument.updated_at.desc()).all()


def get(db: Session, tenant_id: int,
        document_id: str) -> EnterprisePlanDocument:
    item = (db.query(EnterprisePlanDocument)
            .filter_by(id=document_id, tenant_id=tenant_id).first())
    if item is None:
        raise NotFoundError("PLAN_DOCUMENT_NOT_FOUND", "企业方案资料不存在")
    return item


def find_templates(db: Session, tenant_id: int,
                   task_type: str, limit: int = 3) -> list:
    candidates = (db.query(EnterprisePlanDocument)
                  .filter_by(tenant_id=tenant_id, document_type="template",
                             active=True).all())
    normalized = (task_type or "general").casefold()
    candidates.sort(
        key=lambda item: (item.task_type == normalized,
                          item.task_type == "general", item.updated_at),
        reverse=True)
    matched = [item for item in candidates
               if item.task_type in {normalized, "general"}]
    return matched[:limit]


def find_reference_plans(db: Session, tenant_id: int,
                         task_type: str, limit: int = 3) -> list:
    candidates = (db.query(EnterprisePlanDocument)
                  .filter_by(tenant_id=tenant_id,
                             document_type="reference_plan", active=True)
                  .order_by(EnterprisePlanDocument.updated_at.desc()).all())
    normalized = (task_type or "general").casefold()
    return [item for item in candidates
            if item.task_type in {normalized, "general"}][:limit]
