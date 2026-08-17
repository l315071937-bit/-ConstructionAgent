"""Unified low-cost input routing before any LLM or retrieval call."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.models import User
from db.session import get_db
from dependencies import get_current_user
from services import input_router_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


class InputRouteRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    active_agent: str = Field(
        default="project", pattern="^(project|standard|plan)$")


@router.post("/route")
def route_input(body: InputRouteRequest,
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return input_router_service.route_input(
        db, user.id, body.query, body.active_agent)
