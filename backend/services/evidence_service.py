"""Evidence 组装（03 6 结构落地，01 18）。"""
from db.models import Document
from sqlalchemy.orm import Session


def build_evidence(db: Session, project_id: int,
                   chunks: list) -> list:
    """list[RetrievedChunk] → list[Evidence dict]"""
    evidences = []
    doc_cache = {}
    for i, c in enumerate(chunks):
        doc = doc_cache.get(c.document_id)
        if doc is None:
            doc = (db.query(Document)
                   .filter(Document.id == c.document_id).first())
            doc_cache[c.document_id] = doc
        file_name = doc.file_name if doc else c.document_id
        evidences.append({
            "evidence_id": "ev_{}_{}".format(project_id, i),
            "file_id": c.document_id,
            "file_name": file_name,
            "source_type": "PROJECT_DOCUMENT",
            "page": c.page,
            "content": c.content[:600],
            "score": round(float(c.score), 4),
            "thumbnail_url": "/api/v1/projects/{}/documents/{}/pages/{}/image".format(
                project_id, c.document_id, c.page),
            "bbox": None,
            "version": None,
            "metadata": {"chunk_id": c.chunk_id, "project_id": project_id,
                         "method": c.method},
        })
    return evidences
