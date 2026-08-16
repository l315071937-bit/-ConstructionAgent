"""Projects API（03 4）。"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.models import User
from db.session import get_db
from dependencies import get_current_project, get_current_user
from services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


@router.post("", status_code=201)
def create_project(body: ProjectCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = project_service.create_project(db, user.tenant_id, body.name,
                                       body.description, user.id)
    return {"project_id": p.id, "tenant_id": p.tenant_id, "name": p.name,
            "description": p.description,
            "created_at": p.created_at.isoformat() + "Z"}


@router.get("")
def list_projects(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    items = project_service.project_cards(
        db, project_service.list_projects(db, user.id))
    return {"items": items, "total": len(items)}


@router.get("/suggestions")
def suggest_projects(
    q: str = Query(min_length=2, max_length=128),
    limit: int = Query(default=3, ge=1, le=3),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = project_service.suggest_projects(db, user.id, q, limit)
    return {"items": project_service.project_cards(db, projects)}


@router.get("/{project_id}")
def get_project(project=Depends(get_current_project),
                db: Session = Depends(get_db)):
    return project_service.project_detail(db, project)
