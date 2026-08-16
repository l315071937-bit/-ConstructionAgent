"""Recall@K：检索召回率基线。"""
from typing import Iterable


def recall_at_k(ranked_ids: Iterable, relevant_ids: set, k: int) -> float:
    """ranked_ids：检索返回的 chunk_id 顺序列表；relevant_ids：qrels 相关集。"""
    if not relevant_ids:
        return 0.0
    topk = set(list(ranked_ids)[:k])
    return len(topk & relevant_ids) / len(relevant_ids)
