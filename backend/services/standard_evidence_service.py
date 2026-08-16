"""Build standard-specific Evidence with version and applicability metadata."""
import os
import re
from sqlalchemy.orm import Session

from db.models import StandardChunk, StandardDocument


def _region_rank(document_region: str, query_region: str | None) -> int:
    if not query_region:
        return 1
    if query_region in (document_region or ""):
        return 4
    parent_regions = {"深圳": "广东", "广州": "广东", "厦门": "福建"}
    if document_region == parent_regions.get(query_region):
        return 3
    if document_region == "全国":
        return 2
    return 0


def build_standard_evidence(db: Session, tenant_id: int, chunks: list,
                            region: str | None = None,
                            top_k: int = 8, query: str = "") -> list[dict]:
    documents = {}
    articles = {}
    candidates = []
    for chunk in chunks:
        document = documents.get(chunk.document_id)
        if document is None:
            document = (db.query(StandardDocument)
                        .filter(StandardDocument.id == chunk.document_id,
                                StandardDocument.tenant_id == tenant_id).first())
            documents[chunk.document_id] = document
        if document is None:
            continue
        article = articles.get(chunk.chunk_id)
        if article is None:
            row = (db.query(StandardChunk)
                   .filter(StandardChunk.chunk_id == chunk.chunk_id).first())
            article = row.article if row else None
            articles[chunk.chunk_id] = article
        region_rank = _region_rank(document.region, region)
        status_rank = 2 if document.status == "active" else (
            1 if document.status in {"unknown", "upcoming"} else 0)
        normalized_query = re.sub(r"\s+", "", query.casefold())
        normalized_code = re.sub(
            r"\s+", "", (document.standard_code or "").casefold())
        exact_rank = 0
        if normalized_code and normalized_code in normalized_query:
            exact_rank += 1
        if article and article in query:
            exact_rank += 2
        candidates.append((region_rank, status_rank, exact_rank, chunk.score,
                           chunk, document, article))

    candidates.sort(
        key=lambda item: (item[1], item[0], item[2], item[3]), reverse=True)
    evidences = []
    for index, (_, _, _, _, chunk, document, article) in enumerate(
            candidates[:top_k], start=1):
        extension = os.path.splitext(document.file_name)[1].lower()
        thumbnail_url = None
        if extension in {".pdf", ".doc", ".docx", ".xls", ".xlsx"}:
            thumbnail_url = (
                "/api/v1/standards/documents/{}/pages/{}/image".format(
                    document.id, chunk.page))
        evidences.append({
            "evidence_id": "std_ev_{}_{}".format(document.id[:10], index),
            "file_id": document.id, "file_name": document.file_name,
            "source_type": "STANDARD_DOCUMENT", "page": chunk.page,
            "content": chunk.content[:800],
            "score": round(float(chunk.score), 4),
            "thumbnail_url": thumbnail_url,
            "bbox": None, "version": document.version or None,
            "standard_code": document.standard_code,
            "standard_name": document.standard_name,
            "article": article, "status": document.status,
            "effective_date": (document.effective_date.isoformat()
                               if document.effective_date else None),
            "region": document.region, "discipline": document.discipline,
            "metadata": {"chunk_id": chunk.chunk_id,
                         "tenant_id": tenant_id, "method": chunk.method},
        })
    return evidences
