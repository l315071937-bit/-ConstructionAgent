"""项目服务：创建/列表/详情（成员关系过滤，03 4）。"""
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


def project_detail(db: Session, project: Project) -> dict:
    doc_count = (db.query(Document)
                 .filter(Document.project_id == project.id).count())
    member_count = (db.query(ProjectMember)
                    .filter(ProjectMember.project_id == project.id).count())
    return {"project_id": project.id, "tenant_id": project.tenant_id,
            "name": project.name, "description": project.description,
            "created_at": project.created_at.isoformat() + "Z",
            "member_count": member_count, "document_count": doc_count}
