"""评估基础设施（01 52.5）。
检索类：Recall@K / MRR / NDCG（自动指标）
生成类：Citation Accuracy / Answer Accuracy（V0.1 提供简化基线，
后续可接 LLM-judge）"""
from evaluation.metrics.answer_accuracy import answer_accuracy
from evaluation.metrics.citation_accuracy import citation_accuracy
from evaluation.metrics.mrr import mrr
from evaluation.metrics.ndcg import ndcg
from evaluation.metrics.recall_at_k import recall_at_k

__all__ = ["recall_at_k", "mrr", "ndcg", "citation_accuracy",
           "answer_accuracy"]
