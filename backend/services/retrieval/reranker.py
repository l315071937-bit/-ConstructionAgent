"""Reranker 封装（默认实现档，01 52.3）。
V0.1 占位：按 dense score 排序。默认实现档：bge-reranker-v2-m3（后续接入）。"""
from core.logger import get_logger

logger = get_logger("reranker")


def rerank(query: str, chunks: list, top_k: int = 8) -> list:
    """输入 list[RetrievedChunk]，返回重排后的 top_k。"""
    sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)
    return sorted_chunks[:top_k]
