import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.exceptions import AppError
from db.models import (Base, ConversationMessage, Project, ProjectMember,
                       Tenant, User)
from services import conversation_service


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    tenant = Tenant(id=1, name="测试租户")
    user = User(id=7, tenant_id=1, username="memory-user",
                password_hash="x")
    project = Project(id=1, tenant_id=1, name="项目A", created_by=7)
    session.add_all([tenant, user, project,
                     ProjectMember(project_id=1, user_id=7)])
    session.commit()
    yield session
    session.close()


def test_会话严格绑定项目(db):
    conversation = conversation_service.get_or_create_conversation(
        db, 1, 7, 1)

    with pytest.raises(AppError) as exc:
        conversation_service.get_or_create_conversation(
            db, 1, 7, 2, conversation.id)

    assert exc.value.code == "CONVERSATION_PROJECT_MISMATCH"
    assert exc.value.http_status == 409


def test_滑动窗口保留最近原始消息(db, monkeypatch):
    conversation = conversation_service.get_or_create_conversation(
        db, 1, 7, 1)
    monkeypatch.setattr(
        conversation_service.settings, "conversation_recent_token_budget", 5)
    conversation_service.append_message(db, conversation, "user", "较早问题内容")
    conversation_service.append_message(db, conversation, "assistant", "较早回答内容")
    conversation_service.append_message(db, conversation, "user", "最新")

    context = conversation_service.build_context(db, conversation, "继续")

    assert "最新" in context
    assert "较早问题内容" not in context


def test_压缩摘要不删除原始消息(db, monkeypatch):
    conversation = conversation_service.get_or_create_conversation(
        db, 1, 7, 1)
    for index in range(6):
        conversation_service.append_message(
            db, conversation, "user" if index % 2 == 0 else "assistant",
            "第{}条长消息内容".format(index))
    monkeypatch.setattr(
        conversation_service.settings, "conversation_summary_trigger_tokens", 1)
    monkeypatch.setattr(
        conversation_service.settings, "conversation_keep_recent_messages", 2)

    class LLMStub:
        def chat(self, messages, temperature, max_tokens):
            return "用户正在查找项目资料；仍有问题待确认。"

    monkeypatch.setattr(conversation_service, "get_llm", lambda: LLMStub())

    assert conversation_service.compact_if_needed(db, conversation) is True
    assert conversation.summary.startswith("用户正在查找")
    assert conversation.summary_until_message_id is not None
    assert db.query(ConversationMessage).count() == 6


def test_长期记忆必须确认并按项目隔离(db):
    conversation = conversation_service.get_or_create_conversation(
        db, 1, 7, 1)
    conversation_service.remember(
        db, conversation, "USER_PREFERENCE", "用户优先查看电气图纸",
        project_scoped=False)
    conversation_service.remember(
        db, conversation, "PROJECT_DECISION", "项目A先检查配电箱",
        project_scoped=True)

    recalled = conversation_service.recall_memories(
        db, 1, 7, 1, "继续查看电气配电箱")

    assert {item.memory_type for item in recalled} == {
        "USER_PREFERENCE", "PROJECT_DECISION"}


def test_长期记忆来源消息必须属于当前会话(db):
    first = conversation_service.get_or_create_conversation(db, 1, 7, 1)
    second = conversation_service.get_or_create_conversation(db, 1, 7, 1)
    source = conversation_service.append_message(db, first, "user", "记住这个偏好")

    with pytest.raises(AppError) as exc:
        conversation_service.remember(
            db, second, "USER_PREFERENCE", "优先查看电气图纸",
            source_message_id=source.id)

    assert exc.value.code == "MEMORY_SOURCE_INVALID"
