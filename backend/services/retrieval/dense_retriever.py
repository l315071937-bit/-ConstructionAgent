"""Dense 检索（V0.1 唯一生效通道）：BGE-M3 向量 + Milvus。"""
from core.embedding_factory import get_embedder
from core.knowledge_base import get_milvus, search_dense
from core.logger import get_logger
from services.retrieval.base import Retriever, RetrievedChunk

logger = get_logger("dense_retriever")


class DenseRetriever(Retriever):
    def retrieve(self, query: str, project_id: int, top_k: int = 20) -> list:
        vec = get_embedder().embed_texts([query])[0]
        hits = search_dense(get_milvus(), vec, project_id, top_k=top_k)
        results = []
        for h in hits:
            e = h["entity"]
            results.append(RetrievedChunk(
                chunk_id=e["chunk_id"], document_id=e["document_id"],
                page=e["page"], content=e["text"],
                score=h["distance"], method="dense"))
        return results
