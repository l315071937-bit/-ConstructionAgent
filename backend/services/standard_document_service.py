"""Standard document storage, clause-aware chunking and vector ingestion."""
import os
import re
import uuid
from datetime import date

from sqlalchemy.orm import Session

from config import settings
from core.embedding_factory import get_embedder
from core.exceptions import AppError, NotFoundError
from core.logger import get_logger
from core.standard_knowledge_base import (delete_standard_document,
                                          ensure_standard_collection,
                                          get_standard_milvus,
                                          insert_standard_chunks)
from db.models import StandardChunk, StandardDocument

logger = get_logger("standard_document_service")
STANDARD_CHUNK_MAX_CHARS = 900
ARTICLE_PATTERN = re.compile(
    r"(?:第\s*)?(\d+(?:\.\d+){1,4})(?:\s*条)?|第\s*([一二三四五六七八九十百]+)\s*条")
VALID_STATUSES = {"active", "repealed", "replaced", "upcoming", "unknown"}


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise AppError("STANDARD_DATE_INVALID", "日期必须使用 YYYY-MM-DD 格式", 422)


def save_upload(tenant_id: int, file_name: str, content: bytes) -> str:
    directory = os.path.join(settings.standard_storage_dir, str(tenant_id))
    os.makedirs(directory, exist_ok=True)
    extension = os.path.splitext(file_name)[1].lower() or ".bin"
    path = os.path.join(directory, uuid.uuid4().hex + extension)
    with open(path, "wb") as output:
        output.write(content)
    return path


def create_document(db: Session, tenant_id: int, user_id: int,
                    file_name: str, file_path: str, file_size: int,
                    metadata: dict) -> StandardDocument:
    status = metadata.get("status", "unknown")
    if status not in VALID_STATUSES:
        raise AppError("STANDARD_STATUS_INVALID", "规范状态值无效", 422)
    document = StandardDocument(
        tenant_id=tenant_id, created_by=user_id, file_name=file_name,
        file_path=file_path, file_size=file_size, parse_status="PENDING",
        standard_code=metadata.get("standard_code", "").strip(),
        standard_name=metadata.get("standard_name", "").strip(),
        version=metadata.get("version", "").strip(),
        region=metadata.get("region", "全国").strip() or "全国",
        discipline=metadata.get("discipline", "").strip(),
        standard_type=metadata.get("standard_type", "国家标准").strip(),
        status=status,
        publish_date=parse_date(metadata.get("publish_date")),
        effective_date=parse_date(metadata.get("effective_date")))
    if not document.standard_name:
        raise AppError("STANDARD_NAME_REQUIRED", "请输入规范名称", 422)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, tenant_id: int,
                 document_id: str) -> StandardDocument:
    document = (db.query(StandardDocument)
                .filter(StandardDocument.id == document_id,
                        StandardDocument.tenant_id == tenant_id).first())
    if document is None:
        raise NotFoundError("STANDARD_DOCUMENT_NOT_FOUND", "规范文件不存在")
    return document


def list_documents(db: Session, tenant_id: int) -> list[StandardDocument]:
    return (db.query(StandardDocument)
            .filter(StandardDocument.tenant_id == tenant_id)
            .order_by(StandardDocument.created_at.desc()).all())


def ensure_not_duplicate(db: Session, tenant_id: int, standard_code: str,
                         version: str) -> None:
    code = standard_code.strip()
    if not code:
        return
    existing = (db.query(StandardDocument)
                .filter(StandardDocument.tenant_id == tenant_id,
                        StandardDocument.standard_code == code,
                        StandardDocument.version == version.strip()).first())
    if existing:
        raise AppError("STANDARD_ALREADY_EXISTS",
                       "相同编号和版本的规范已经入库", 409)


def chunk_standard_pages(pages, tenant_id: int,
                         document_id: str) -> list[dict]:
    chunks = []
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        matches = list(ARTICLE_PATTERN.finditer(text))
        sections = []
        if matches:
            if matches[0].start() > 0:
                sections.append((None, text[:matches[0].start()]))
            for match_index, match in enumerate(matches):
                end = (matches[match_index + 1].start()
                       if match_index + 1 < len(matches) else len(text))
                article = match.group(1) or match.group(2)
                sections.append((article, text[match.start():end]))
        else:
            sections.append((None, text))
        chunk_index = 0
        for article, section in sections:
            section = section.strip()
            for start in range(0, len(section), STANDARD_CHUNK_MAX_CHARS):
                content = section[start:start + STANDARD_CHUNK_MAX_CHARS]
                chunks.append({
                    "chunk_id": "std_{}_{}_{}".format(
                        document_id[:12], page.page_no, chunk_index),
                    "standard_document_id": document_id,
                    "tenant_id": tenant_id, "content": content,
                    "page": page.page_no, "article": article,
                })
                chunk_index += 1
    return chunks


def run_parse(db: Session, document_id: str) -> None:
    document = db.query(StandardDocument).filter(
        StandardDocument.id == document_id).first()
    if document is None:
        return
    try:
        document.parse_status = "PARSING"
        db.commit()
        from services.document_parser.router import get_parser_router
        parsed = get_parser_router().parse(document.file_path)
        chunks = chunk_standard_pages(
            parsed.pages, document.tenant_id, document.id)
        if not chunks:
            raise AppError("PARSE_FAILED", "规范文件未提取到文本", 422)

        embedder = get_embedder()
        client = get_standard_milvus()
        ensure_standard_collection(client)
        for start in range(0, len(chunks), 32):
            batch = chunks[start:start + 32]
            embedding_texts = [
                "{} {} {}".format(document.standard_code,
                                  document.standard_name, item["content"])
                for item in batch]
            vectors = embedder.embed_texts(embedding_texts)
            rows = []
            for item, vector in zip(batch, vectors):
                db.add(StandardChunk(**item))
                rows.append({
                    "chunk_id": item["chunk_id"],
                    "standard_document_id": document.id,
                    "tenant_id": document.tenant_id,
                    "text": item["content"][:4096], "embedding": vector,
                    "page": item["page"], "article": item["article"] or "",
                })
            insert_standard_chunks(client, rows)
        document.parse_status = "READY"
        document.page_count = parsed.meta.get("total_pages", 0)
        document.chunk_count = len(chunks)
        document.parse_error = None
        db.commit()
    except Exception as exc:
        db.rollback()
        document = db.query(StandardDocument).filter(
            StandardDocument.id == document_id).first()
        if document:
            document.parse_status = "FAILED"
            document.parse_error = str(exc)[:500]
            db.commit()
        logger.error("standard %s parse failed: %s", document_id, exc)


def delete_document(db: Session, document: StandardDocument) -> None:
    try:
        delete_standard_document(get_standard_milvus(), document.id)
    except Exception as exc:
        logger.warning("standard vector delete failed: %s", exc)
    db.query(StandardChunk).filter(
        StandardChunk.standard_document_id == document.id).delete()
    db.delete(document)
    db.commit()
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except OSError:
        pass


def document_item(document: StandardDocument) -> dict:
    return {
        "document_id": document.id, "file_name": document.file_name,
        "standard_code": document.standard_code,
        "standard_name": document.standard_name, "version": document.version,
        "region": document.region, "discipline": document.discipline,
        "standard_type": document.standard_type, "status": document.status,
        "publish_date": (document.publish_date.isoformat()
                         if document.publish_date else None),
        "effective_date": (document.effective_date.isoformat()
                           if document.effective_date else None),
        "parse_status": document.parse_status,
        "page_count": document.page_count, "chunk_count": document.chunk_count,
        "parse_error": document.parse_error,
        "created_at": document.created_at.isoformat() + "Z",
    }
