"""Conversation persistence, sliding context and confirmed long-term memory."""
import math
import re
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from config import settings
from core.exceptions import AppError, NotFoundError
from core.llm_factory import get_llm
from core.logger import get_logger
from db.models import Conversation, ConversationMessage, LongTermMemory

logger = get_logger("conversation_service")


def estimate_tokens(text: str) -> int:
    """Conservative approximation: CJK chars count as one, other text as 4 chars."""
    text = text or ""
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    return max(1, cjk + math.ceil((len(text) - cjk) / 4))


def get_or_create_conversation(db: Session, tenant_id: int, user_id: int,
                               project_id: int,
                               conversation_id: str | None = None,
                               agent_type: str = "project") -> Conversation:
    if conversation_id:
        conversation = (db.query(Conversation)
                        .filter(Conversation.id == conversation_id,
                                Conversation.tenant_id == tenant_id,
                                Conversation.user_id == user_id).first())
        if conversation is None:
            raise NotFoundError("CONVERSATION_NOT_FOUND", "会话不存在")
        if conversation.project_id != project_id:
            raise AppError("CONVERSATION_PROJECT_MISMATCH",
                           "该会话属于其他项目，请新建会话", 409)
        return conversation

    conversation = Conversation(
        tenant_id=tenant_id, user_id=user_id, project_id=project_id,
        agent_type=agent_type,
        state_json={"locked_project_id": project_id,
                    "active_agent": agent_type,
                    "pending_questions": []})
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def append_message(db: Session, conversation: Conversation, role: str,
                   content: str, extra: dict | None = None) -> ConversationMessage:
    message = ConversationMessage(
        conversation_id=conversation.id, role=role, content=content,
        token_count=estimate_tokens(content), extra_json=extra or {})
    db.add(message)
    conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if role == "user" and conversation.title == "新对话":
        conversation.title = content.strip()[:128] or "新对话"
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: Session, conversation_id: str) -> list:
    return (db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.id.asc()).all())


def _recent_window(messages: list, token_budget: int) -> list:
    selected = []
    used = 0
    for message in reversed(messages):
        cost = message.token_count or estimate_tokens(message.content)
        if selected and used + cost > token_budget:
            break
        selected.append(message)
        used += cost
    return list(reversed(selected))


def _memory_score(content: str, query: str) -> int:
    query_chars = set(re.sub(r"\s+", "", query.casefold()))
    content_chars = set(re.sub(r"\s+", "", content.casefold()))
    return len(query_chars & content_chars)


def recall_memories(db: Session, tenant_id: int, user_id: int,
                    project_id: int, query: str) -> list:
    candidates = (db.query(LongTermMemory)
                  .filter(LongTermMemory.tenant_id == tenant_id,
                          LongTermMemory.user_id == user_id,
                          LongTermMemory.confirmed.is_(True),
                          or_(LongTermMemory.project_id.is_(None),
                              LongTermMemory.project_id == project_id))
                  .order_by(LongTermMemory.updated_at.desc()).limit(50).all())
    ranked = sorted(candidates,
                    key=lambda item: (_memory_score(item.content, query),
                                      item.updated_at), reverse=True)
    return [item for item in ranked if _memory_score(item.content, query) > 0][
        :settings.memory_recall_limit]


def build_context(db: Session, conversation: Conversation,
                  query: str) -> str:
    messages = list_messages(db, conversation.id)
    recent = _recent_window(messages,
                            settings.conversation_recent_token_budget)
    memories = recall_memories(db, conversation.tenant_id,
                               conversation.user_id,
                               conversation.project_id, query)
    sections = []
    if conversation.summary:
        sections.append("较早对话摘要：\n" + conversation.summary)
    if memories:
        sections.append("用户已确认的相关记忆：\n" + "\n".join(
            "- " + memory.content for memory in memories))
    if recent:
        role_names = {"user": "用户", "assistant": "助手", "system": "系统"}
        sections.append("最近对话：\n" + "\n".join(
            "{}：{}".format(role_names.get(message.role, message.role),
                            message.content) for message in recent))
    return "\n\n".join(sections)


def compact_if_needed(db: Session, conversation: Conversation) -> bool:
    messages = list_messages(db, conversation.id)
    unsummarized = [message for message in messages
                    if not conversation.summary_until_message_id or
                    message.id > conversation.summary_until_message_id]
    total_tokens = sum(message.token_count for message in unsummarized)
    keep_count = settings.conversation_keep_recent_messages
    if total_tokens < settings.conversation_summary_trigger_tokens or \
            len(unsummarized) <= keep_count:
        return False

    candidates = unsummarized[:-keep_count]
    transcript = "\n".join(
        "{}: {}".format(message.role, message.content)
        for message in candidates)
    prompt = (
        "请增量整理建筑工程助手的会话摘要。只保留用户目标、已确认决定、"
        "约束、当前项目操作和待解决问题；不得把检索回答中的工程参数写成"
        "已确认事实。输出简洁中文。\n\n已有摘要：\n{}\n\n新增对话：\n{}"
    ).format(conversation.summary or "（无）", transcript)
    try:
        summary = get_llm().chat(
            [{"role": "system", "content": "你是会话记忆压缩器。"},
             {"role": "user", "content": prompt}],
            temperature=0, max_tokens=600)
    except Exception as error:
        logger.warning("conversation summary failed, using safe fallback: %s",
                       error)
        summary = (conversation.summary + "\n" + transcript)[-4000:]
    conversation.summary = summary.strip()
    conversation.summary_until_message_id = candidates[-1].id
    db.commit()
    return True


def remember(db: Session, conversation: Conversation, memory_type: str,
             content: str, source_message_id: int | None = None,
             project_scoped: bool = True) -> LongTermMemory:
    if source_message_id is not None:
        source = (db.query(ConversationMessage)
                  .filter(ConversationMessage.id == source_message_id,
                          ConversationMessage.conversation_id ==
                          conversation.id).first())
        if source is None:
            raise AppError("MEMORY_SOURCE_INVALID",
                           "长期记忆来源消息不属于当前会话", 422)
    memory = LongTermMemory(
        tenant_id=conversation.tenant_id, user_id=conversation.user_id,
        project_id=conversation.project_id if project_scoped else None,
        memory_type=memory_type, content=content.strip(), confidence=1.0,
        confirmed=True, source_message_id=source_message_id)
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory
