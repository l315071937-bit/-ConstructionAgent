"""FastAPI 依赖注入（01 9）：JWT → User → Tenant → Project 权限链。
任何项目数据访问必须经过 get_current_project 校验成员关系。"""
import jwt
from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from config import settings
from core.exceptions import AuthError, PermissionError_, NotFoundError
from db.models import Project, ProjectMember, User
from db.session import get_db

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise AuthError()
    try:
        payload = jwt.decode(cred.credentials, settings.secret_key,
                             algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("AUTH_TOKEN_EXPIRED", "登录已过期")
    except Exception:
        raise AuthError()
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if user is None:
        raise AuthError()
    return user


def get_current_project(
    project_id: int = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise NotFoundError("PROJECT_NOT_FOUND", "项目不存在")
    member = (db.query(ProjectMember)
              .filter(ProjectMember.project_id == project_id,
                      ProjectMember.user_id == user.id).first())
    if member is None:
        raise PermissionError_()
    return project
