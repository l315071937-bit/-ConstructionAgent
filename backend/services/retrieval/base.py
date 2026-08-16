"""Retriever 抽象（01 52.2 抽象层，真实可替换）。
替换场景：dense（Milvus/Qdrant）、lexical（三候选实验）、未来视觉检索。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    page: int
    content: str
    score: float
    method: str


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, project_id: int, top_k: int = 20) -> list:
        """返回 list[RetrievedChunk]，score 归一化到 0~1（越大越相关）。"""
        ...
