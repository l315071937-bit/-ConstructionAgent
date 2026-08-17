"""V0.1 数据模型（01 24 的子集，仅主链路所需）。
权限链：Tenant → User → Project → ProjectMember → 访问（01 9）。"""
import uuid
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer,
                        LargeBinary, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.utcnow()


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128))  # bcrypt，禁止明文
    role: Mapped[str] = mapped_column(String(32), default="engineer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(512), default="")
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(32), default="member")  # owner|member


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    file_name: Mapped[str] = mapped_column(String(256))
    file_path: Mapped[str] = mapped_column(String(512))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    parse_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    parse_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    chunk_id: Mapped[str] = mapped_column(String(64), unique=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    project_id: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page: Mapped[int] = mapped_column(Integer, default=1)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), default="PROJECT_DOCUMENT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ProjectFolder(Base):
    """A persisted project folder; parent_id enables arbitrary nesting."""
    __tablename__ = "project_folders"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_folders.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now)


class DocumentFolderLink(Base):
    """Optional folder ownership kept separate for existing databases."""
    __tablename__ = "document_folder_links"
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    folder_id: Mapped[str] = mapped_column(
        ForeignKey("project_folders.id"), index=True)


class StandardDocument(Base):
    __tablename__ = "standard_documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), index=True)
    standard_code: Mapped[str] = mapped_column(String(64), default="")
    standard_name: Mapped[str] = mapped_column(String(256))
    version: Mapped[str] = mapped_column(String(64), default="")
    region: Mapped[str] = mapped_column(String(64), default="全国")
    discipline: Mapped[str] = mapped_column(String(64), default="")
    standard_type: Mapped[str] = mapped_column(String(64), default="国家标准")
    status: Mapped[str] = mapped_column(String(24), default="unknown")
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_name: Mapped[str] = mapped_column(String(256))
    file_path: Mapped[str] = mapped_column(String(512))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    parse_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    parse_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class StandardChunk(Base):
    __tablename__ = "standard_chunks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    chunk_id: Mapped[str] = mapped_column(String(64), unique=True)
    standard_document_id: Mapped[str] = mapped_column(
        ForeignKey("standard_documents.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    content: Mapped[str] = mapped_column(Text)
    page: Mapped[int] = mapped_column(Integer, default=1)
    article: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    agent_type: Mapped[str] = mapped_column(String(32), default="project")
    title: Mapped[str] = mapped_column(String(128), default="新对话")
    summary: Mapped[str] = mapped_column(Text, default="")
    summary_until_message_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    extra_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LongTermMemory(Base):
    __tablename__ = "long_term_memories"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True)
    memory_type: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversation_messages.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now)


class EnterprisePlanDocument(Base):
    """Tenant-owned plan template or approved historical reference plan."""
    __tablename__ = "enterprise_plan_documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(256))
    task_type: Mapped[str] = mapped_column(String(64), default="general")
    discipline: Mapped[str] = mapped_column(String(64), default="")
    version: Mapped[str] = mapped_column(String(64), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    outline_json: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now)


class PlanTask(Base):
    """Durable user-facing state for a Construction Plan workflow."""
    __tablename__ = "plan_tasks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), index=True)
    request: Mapped[str] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(64), default="general")
    status: Mapped[str] = mapped_column(String(24), default="PENDING")
    current_stage: Mapped[str] = mapped_column(String(64), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    human_required: Mapped[bool] = mapped_column(Boolean, default=False)
    human_reason: Mapped[str | None] = mapped_column(
        String(64), nullable=True)
    human_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now)


class GeneratedPlanDocument(Base):
    __tablename__ = "generated_plan_documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), index=True)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("plan_tasks.id"), unique=True, index=True)
    file_name: Mapped[str] = mapped_column(String(256))
    docx_path: Mapped[str] = mapped_column(String(512))
    pdf_path: Mapped[str] = mapped_column(String(512))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LangGraphCheckpoint(Base):
    """SQL-backed LangGraph checkpoint metadata and channel-version index."""
    __tablename__ = "langgraph_checkpoints"
    thread_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(
        String(128), primary_key=True, default="")
    checkpoint_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    parent_checkpoint_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True)
    checkpoint_type: Mapped[str] = mapped_column(String(32))
    checkpoint_data: Mapped[bytes] = mapped_column(LargeBinary)
    metadata_type: Mapped[str] = mapped_column(String(32))
    metadata_data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LangGraphCheckpointBlob(Base):
    __tablename__ = "langgraph_checkpoint_blobs"
    thread_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(
        String(128), primary_key=True, default="")
    channel: Mapped[str] = mapped_column(String(256), primary_key=True)
    version: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_type: Mapped[str] = mapped_column(String(32))
    value_data: Mapped[bytes] = mapped_column(LargeBinary)


class LangGraphCheckpointWrite(Base):
    __tablename__ = "langgraph_checkpoint_writes"
    thread_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(
        String(128), primary_key=True, default="")
    checkpoint_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    write_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(256))
    value_type: Mapped[str] = mapped_column(String(32))
    value_data: Mapped[bytes] = mapped_column(LargeBinary)
    task_path: Mapped[str] = mapped_column(String(512), default="")
