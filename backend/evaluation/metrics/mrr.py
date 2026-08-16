"""MRR：平均倒数排名。"""
from typing import Iterable


def mrr(ranked_list: Iterable, relevant_ids: set) -> float:
    for i, cid in enumerate(ranked_list, start=1):
        if cid in relevant_ids:
            return 1.0 / i
    return 0.0
