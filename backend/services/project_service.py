"""项目服务：创建/列表/详情（成员关系过滤，03 4）。"""
import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Document, Project, ProjectMember


def create_project(db: Session, tenant_id: int, name: str,
                   description: str, user_id: int) -> Project:
    project = Project(tenant_id=tenant_id, name=name,
                      description=description, created_by=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    db.add(ProjectMember(project_id=project.id, user_id=user_id, role="owner"))
    db.commit()
    return project


def list_projects(db: Session, user_id: int) -> list:
    rows = (db.query(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .filter(ProjectMember.user_id == user_id)
            .order_by(Project.created_at.desc()).all())
    return rows


def _search_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", (value or "").casefold())


def _geographic_text(value: str) -> str:
    """Allow abbreviated place names such as 深圳龙华 to match 深圳市龙华区."""
    return re.sub(r"省|市|区|县|镇|街道", "", _search_text(value))


def suggest_projects(db: Session, user_id: int, query: str,
                     limit: int = 3) -> list:
    """Rank only projects the user may access; no project name may leak."""
    keyword = _search_text(query)
    geographic_keyword = _geographic_text(query)
    if not keyword:
        return []

    ranked = []
    for project in list_projects(db, user_id):
        name = _search_text(project.name)
        description = _search_text(project.description)
        geographic_name = _geographic_text(project.name)
        geographic_description = _geographic_text(project.description)
        if name == keyword:
            score = 1000
        elif name.startswith(keyword):
            score = 800
        elif keyword in name:
            score = 600
        elif geographic_keyword and geographic_keyword in geographic_name:
            score = 500
        elif keyword in description:
            score = 300
        elif geographic_keyword and geographic_keyword in geographic_description:
            score = 200
        else:
            continue
        ranked.append((score, project.created_at, project))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:limit]]


def project_cards(db: Session, projects: list) -> list[dict]:
    projects = list(projects)
    project_ids = [project.id for project in projects]
    counts = {}
    if project_ids:
        rows = (db.query(Document.project_id, func.count(Document.id))
                .filter(Document.project_id.in_(project_ids))
                .group_by(Document.project_id).all())
        counts = dict(rows)
    return [{"project_id": project.id, "name": project.name,
             "description": project.description,
             "document_count": counts.get(project.id, 0),
             "created_at": project.created_at.isoformat() + "Z"}
            for project in projects]


def project_detail(db: Session, project: Project) -> dict:
    doc_count = (db.query(Document)
                 .filter(Document.project_id == project.id).count())
    member_count = (db.query(ProjectMember)
                    .filter(ProjectMember.project_id == project.id).count())
    return {"project_id": project.id, "tenant_id": project.tenant_id,
            "name": project.name, "description": project.description,
            "created_at": project.created_at.isoformat() + "Z",
            "member_count": member_count, "document_count": doc_count}
