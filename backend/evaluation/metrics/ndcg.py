"""NDCG@K：排序质量（relevance 允许分级：0 无关 / 1 相关 / 2 高相关）。"""
import math
from typing import Iterable


def ndcg(ranked_ids: Iterable, relevance: dict, k: int) -> float:
    gains = [relevance.get(cid, 0) for cid in list(ranked_ids)[:k]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0
