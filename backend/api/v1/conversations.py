"""Conversation history and explicit long-term memory endpoints."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.models import Conversation, User
from db.session import get_db
from dependencies import get_current_project, get_current_user
from services import conversation_service

router = APIRouter(prefix="/projects/{project_id}/conversations",
                   tags=["conversations"])


class MemoryCreate(BaseModel):
    memory_type: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=2000)
    source_message_id: int | None = None
    project_scoped: bool = True


def _conversation(db: Session, conversation_id: str, project_id: int,
                  user: User, agent_type: str = "project") -> Conversation:
    return conversation_service.get_or_create_conversation(
        db, user.tenant_id, user.id, project_id, conversation_id, agent_type)


@router.get("")
def list_conversations(project=Depends(get_current_project),
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    rows = (db.query(Conversation)
            .filter(Conversation.project_id == project.id,
                    Conversation.tenant_id == user.tenant_id,
                    Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc()).limit(30).all())
    return {"items": [
        {"conversation_id": item.id, "title": item.title,
         "agent_type": item.agent_type,
         "updated_at": item.updated_at.isoformat() + "Z"}
        for item in rows]}


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str,
                     agent_type: str = Query(default="project",
                                             pattern="^(project|standard)$"),
                     project=Depends(get_current_project),
                     user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    conversation = _conversation(
        db, conversation_id, project.id, user, agent_type)
    messages = conversation_service.list_messages(db, conversation.id)
    return {
        "conversation_id": conversation.id,
        "project_id": conversation.project_id,
        "title": conversation.title,
        "summary": conversation.summary,
        "state": conversation.state_json,
        "messages": [
            {"message_id": message.id, "role": message.role,
             "content": message.content, "token_count": message.token_count,
             "metadata": message.extra_json,
             "created_at": message.created_at.isoformat() + "Z"}
            for message in messages],
    }


@router.post("/{conversation_id}/memories", status_code=201)
def create_memory(conversation_id: str, body: MemoryCreate,
                  project=Depends(get_current_project),
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    conversation = _conversation(db, conversation_id, project.id, user)
    memory = conversation_service.remember(
        db, conversation, body.memory_type, body.content,
        body.source_message_id, body.project_scoped)
    return {"memory_id": memory.id, "memory_type": memory.memory_type,
            "content": memory.content, "project_id": memory.project_id,
            "confirmed": memory.confirmed}
