"""Dense retrieval over the tenant-isolated standards collection."""
from core.embedding_factory import get_embedder
from core.standard_knowledge_base import (get_standard_milvus,
                                          ensure_standard_collection,
                                          search_standard_dense)
from services.retrieval.base import RetrievedChunk, Retriever


class StandardDenseRetriever(Retriever):
    def retrieve(self, query: str, tenant_id: int,
                 top_k: int = 20) -> list[RetrievedChunk]:
        vector = get_embedder().embed_texts([query])[0]
        client = get_standard_milvus()
        ensure_standard_collection(client)
        hits = search_standard_dense(client, vector, tenant_id, top_k)
        return [RetrievedChunk(
            chunk_id=hit["entity"]["chunk_id"],
            document_id=hit["entity"]["standard_document_id"],
            page=hit["entity"]["page"], content=hit["entity"]["text"],
            score=hit["distance"], method="dense") for hit in hits]
