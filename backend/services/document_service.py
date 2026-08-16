"""文档服务：上传落盘 + 异步解析切片 + 向量化入库（03 5）。
状态机：PENDING → PARSING → READY | FAILED"""
import os
import uuid

from sqlalchemy.orm import Session

from config import settings
from core.embedding_factory import get_embedder
from core.exceptions import AppError, NotFoundError
from core.knowledge_base import (delete_by_document, ensure_collection,
                                 get_milvus, insert_chunks)
from core.logger import get_logger
from db.models import Chunk, Document

logger = get_logger("document_service")

CHUNK_MAX_CHARS = 800


def _storage_dir(project_id: int) -> str:
    d = os.path.join(settings.storage_dir, str(project_id))
    os.makedirs(d, exist_ok=True)
    return d


def save_upload(project_id: int, file_name: str, content: bytes) -> str:
    ext = os.path.splitext(file_name)[1].lower() or ".bin"
    path = os.path.join(_storage_dir(project_id), uuid.uuid4().hex + ext)
    with open(path, "wb") as f:
        f.write(content)
    return path


def create_document(db: Session, project_id: int, file_name: str,
                    file_path: str, file_size: int, user_id: int) -> Document:
    doc = Document(project_id=project_id, file_name=file_name,
                   file_path=file_path, file_size=file_size,
                   parse_status="PENDING", created_by=user_id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, project_id: int, document_id: str) -> Document:
    doc = (db.query(Document)
           .filter(Document.id == document_id,
                   Document.project_id == project_id).first())
    if doc is None:
        raise NotFoundError("DOCUMENT_NOT_FOUND", "文档不存在")
    return doc


def chunk_pages(pages, project_id: int, document_id: str) -> list:
    """V0.1 简单切片：按页切 + 超长分段。
    规范类文档的层级切片（参考 RAGFlow laws.py 思路）在标准知识库阶段实现。"""
    chunks = []
    for p in pages:
        text = p.text.strip()
        if not text:
            continue
        parts = [text[i:i + CHUNK_MAX_CHARS]
                 for i in range(0, len(text), CHUNK_MAX_CHARS)]
        for j, part in enumerate(parts):
            chunk_id = "{}_{}_{}".format(document_id[:12], p.page_no, j)
            chunks.append({"chunk_id": chunk_id,
                           "document_id": document_id,
                           "project_id": project_id,
                           "content": part, "page": p.page_no,
                           "bbox": None, "source_type": "PROJECT_DOCUMENT"})
    return chunks


def run_parse(db: Session, document_id: str) -> None:
    """后台解析任务：解析 → 切片 → 嵌入 → 入库。任何一步失败 → FAILED。"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        return
    try:
        doc.parse_status = "PARSING"
        db.commit()

        from services.document_parser.router import get_parser_router
        parsed = get_parser_router().parse(doc.file_path)

        chunks = chunk_pages(parsed.pages, doc.project_id, doc.id)
        if not chunks:
            raise AppError("PARSE_FAILED", "文档未提取到任何文本内容")

        embedder = get_embedder()
        client = get_milvus()
        ensure_collection(client)

        rows = []
        for i in range(0, len(chunks), 32):
            batch = chunks[i:i + 32]
            vecs = embedder.embed_texts([c["content"] for c in batch])
            for c, v in zip(batch, vecs):
                db.add(Chunk(chunk_id=c["chunk_id"], document_id=c["document_id"],
                             project_id=c["project_id"], content=c["content"],
                             page=c["page"], source_type=c["source_type"]))
                rows.append({"chunk_id": c["chunk_id"],
                             "document_id": c["document_id"],
                             "project_id": c["project_id"],
                             "text": c["content"][:4096],
                             "embedding": v,
                             "page": c["page"],
                             "source_type": c["source_type"]})
            insert_chunks(client, rows)
            rows = []

        doc.parse_status = "READY"
        doc.page_count = parsed.meta.get("total_pages", 0)
        doc.chunk_count = len(chunks)
        doc.parse_error = None
        db.commit()
        logger.info("document %s parsed: pages=%s chunks=%s",
                    document_id, doc.page_count, doc.chunk_count)
    except Exception as e:
        db.rollback()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is not None:
            doc.parse_status = "FAILED"
            doc.parse_error = str(e)[:500]
            db.commit()
        logger.error("document %s parse failed: %s", document_id, e)


def delete_document(db: Session, doc: Document) -> None:
    try:
        delete_by_document(get_milvus(), doc.id)
    except Exception as e:
        logger.warning("milvus delete failed for %s: %s", doc.id, e)
    db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
    db.delete(doc)
    db.commit()
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except OSError:
        pass
