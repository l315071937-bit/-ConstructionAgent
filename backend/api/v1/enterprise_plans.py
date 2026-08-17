"""Tenant enterprise templates and approved historical plans."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.exceptions import PermissionError_
from db.models import User
from db.session import get_db
from dependencies import get_current_user
from services import enterprise_plan_service

router = APIRouter(prefix="/enterprise/plan-documents",
                   tags=["enterprise-plans"])


class EnterprisePlanCreate(BaseModel):
    document_type: str = Field(pattern="^(template|reference_plan)$")
    name: str = Field(min_length=1, max_length=256)
    task_type: str = Field(default="general", max_length=64)
    discipline: str = Field(default="", max_length=64)
    version: str = Field(default="", max_length=64)
    content: str = Field(default="", max_length=100000)
    outline: list[str] = Field(default_factory=list, max_length=15)


@router.post("", status_code=201)
def create_document(body: EnterprisePlanCreate,
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user.role != "admin":
        raise PermissionError_("仅管理员可以维护企业方案资料")
    item = enterprise_plan_service.create(
        db, user.tenant_id, user.id, body.document_type, body.name,
        body.task_type, body.discipline, body.version, body.content,
        body.outline)
    return enterprise_plan_service.serialize(item, True)


@router.get("")
def list_documents(
    document_type: str | None = Query(
        default=None, pattern="^(template|reference_plan)$"),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items = enterprise_plan_service.list_documents(
        db, user.tenant_id, document_type)
    return {"items": [enterprise_plan_service.serialize(item)
                      for item in items], "total": len(items)}


@router.get("/{document_id}")
def get_document(document_id: str, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    item = enterprise_plan_service.get(db, user.tenant_id, document_id)
    return enterprise_plan_service.serialize(item, True)
