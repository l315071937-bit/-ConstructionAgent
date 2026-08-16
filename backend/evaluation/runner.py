"""评估 Runner 骨架：加载数据集 -> 运行检索器 -> 输出指标表。
用法：python -m evaluation.runner --dataset evaluation/datasets/example.json
"""
import argparse
import json
import statistics

from evaluation.metrics.mrr import mrr
from evaluation.metrics.ndcg import ndcg
from evaluation.metrics.recall_at_k import recall_at_k


def run(dataset_path: str, retriever, k: int = 8) -> None:
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)
    recalls, mrrs, ndcgs = [], [], []
    for item in data["queries"]:
        ranked = retriever(item["query"])
        rel = set(item["relevant_chunk_ids"])
        recalls.append(recall_at_k(ranked, rel, k))
        mrrs.append(mrr(ranked, rel))
        rel_map = {cid: 1 for cid in rel}
        ndcgs.append(ndcg(ranked, rel_map, k))
        print("Q: {}".format(item["query"][:60]))
        print("   top3: {}".format(ranked[:3]))
    print("=== {} (n={}) ===".format(data.get("name"), len(data["queries"])))
    print("Recall@{}: {:.3f}".format(k, statistics.mean(recalls)))
    print("MRR:       {:.3f}".format(statistics.mean(mrrs)))
    print("NDCG@{}:   {:.3f}".format(k, statistics.mean(ndcgs)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--k", type=int, default=8)
    args = parser.parse_args()

    def _demo_retriever(query: str):
        return []

    run(args.dataset, _demo_retriever, args.k)
