"""Auth API（03 3）：登录签发 JWT / 当前用户。"""
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from core.exceptions import AuthError
from db.models import User
from db.session import get_db
from dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _user_dict(user: User) -> dict:
    return {"user_id": user.id, "username": user.username,
            "role": user.role, "tenant_id": user.tenant_id}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not bcrypt.checkpw(
            body.password.encode(), user.password_hash.encode()):
        raise AuthError("AUTH_INVALID_CREDENTIALS", "用户名或密码错误")
    exp = datetime.utcnow() + timedelta(seconds=settings.jwt_expire_seconds)
    payload = {"user_id": user.id, "role": user.role,
               "tenant_id": user.tenant_id, "exp": exp}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer",
            "expires_in": settings.jwt_expire_seconds,
            "user": _user_dict(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_dict(user)
