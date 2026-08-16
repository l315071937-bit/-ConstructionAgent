"""LexicalRetriever：词法通道接口（V0.1 占位，01 52.3/52.5）。

三个候选实现待 evaluation/ 实验定案（指标 recall@k / MRR）：
1) Milvus FTS（chinese analyzer，词典可控性待验证）
2) bm25s + jieba 自定义词典
3) BGE-M3 Sparse（学习型词项权重）

接口层不得偏袒任何实现；定案前本类返回空列表，不参与召回。"""
from core.logger import get_logger
from services.retrieval.base import Retriever

logger = get_logger("lexical_retriever")


class LexicalRetriever(Retriever):
    enabled = False

    def retrieve(self, query: str, project_id: int, top_k: int = 20) -> list:
        if self.enabled:
            raise NotImplementedError(
                "词法通道实现待 evaluation/ 实验定案，见 01 52.3")
        return []
