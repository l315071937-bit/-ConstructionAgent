"""最小版评测 Runner（V0.1，2026-08-16）。

三层评估：
1) 检索层：Recall@K / MRR / nDCG@K（金标 qrels，只统计 expect_answer=true 的问题）
2) 阈值校准：扫 0.10~0.50，找「回答/兜底」判定与金标一致率最高的置信度阈值
3) 生成层：金标事实覆盖率（answer_accuracy）+ 引用质量（citation_accuracy）
   说明：生成层调用真实 DeepSeek LLM，会消耗少量 API 额度。

用法（backend 目录）：
    ../.venv/Scripts/python -m evaluation.run_minimal
"""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.getcwd())

from config import settings
from core.llm_factory import get_llm
from db.session import SessionLocal
from services.evidence_service import build_evidence
from services.retrieval.dense_retriever import DenseRetriever
from services.retrieval.reranker import rerank
from agents.project_retrieval.prompts import build_answer_messages
from evaluation.metrics.answer_accuracy import answer_accuracy
from evaluation.metrics.citation_accuracy import citation_accuracy
from evaluation.metrics.mrr import mrr
from evaluation.metrics.ndcg import ndcg
from evaluation.metrics.recall_at_k import recall_at_k

DATASET = "evaluation/datasets/v0.1_minimal.json"
K = 8
SWEEP = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]


def main():
    with open(DATASET, encoding="utf-8") as f:
        data = json.load(f)
    queries = data["queries"]
    project_id = data["project_id"]

    print("加载 Embedder（首次约 90s，BGE-M3 本地加载）...", flush=True)
    retriever = DenseRetriever()
    llm = get_llm()

    recalls, mrrs, ndcgs = [], [], []
    fact_covs, ref_vals, fact_traces = [], [], []
    sweep_correct = {t: [] for t in SWEEP}
    rows = []

    t0 = time.time()
    for i, item in enumerate(queries, 1):
        qid, q = item["id"], item["query"]
        gold = set(item["relevant_chunk_ids"])

        # --- 与生产一致的检索链：dense top20 -> rerank top8 ---
        chunks = retriever.retrieve(q, project_id, top_k=20)
        top = rerank(q, chunks, top_k=K)
        ranked_ids = [c.chunk_id for c in top]

        r, m, n = 0.0, 0.0, 0.0
        if gold:
            r = recall_at_k(ranked_ids, gold, K)
            m = mrr(ranked_ids, gold)
            n = ndcg(ranked_ids, {cid: 1 for cid in gold}, K)
            recalls.append(r)
            mrrs.append(m)
            ndcgs.append(n)

        # --- 证据组装（真实 DB 链）---
        db = SessionLocal()
        try:
            evs = build_evidence(db, project_id, top)
        finally:
            db.close()
        top_score = evs[0]["score"] if evs else 0.0
        n_ev = len(evs)

        # --- 阈值校准：规则与 check_confidence 一致（top>=thr 且 >=2 条）---
        for thr in SWEEP:
            predicted = (top_score >= thr) and (n_ev >= 2)
            sweep_correct[thr].append(predicted == item["expect_answer"])

        # --- 生成层（只对金标可回答的问题生成，避免浪费额度）---
        fc, cv = None, None
        if item["expect_answer"]:
            answer = llm.chat(build_answer_messages(q, evs))
            a = answer_accuracy(answer, item["golden_facts"])
            c = citation_accuracy(answer, evs)
            fc, cv = a["coverage"], c
            fact_covs.append(fc)
            ref_vals.append(c["ref_valid_ratio"])
            fact_traces.append(c["fact_traceable_ratio"])
        else:
            answer = "(不生成：金标期望兜底)"

        row = {"id": qid, "recall": r, "mrr": m, "ndcg": n,
               "top_score": round(top_score, 3), "n_ev": n_ev,
               "fact_coverage": fc, "answer": answer}
        rows.append(row)
        print(f"[{i}/{len(queries)}] {qid} top={top_score:.3f} n={n_ev} "
              f"R@8={r:.2f} MRR={m:.2f} facts={fc if fc is not None else '-'}",
              flush=True)

    # ================= 汇总报告 =================
    print("\n" + "=" * 62)
    print(f"评测集：{data['name']}（n={len(queries)}，可回答 {len(recalls)} 条）")
    print("=" * 62)
    print(f"检索指标（可回答子集）：")
    print(f"  Recall@{K} : {statistics.mean(recalls):.3f}")
    print(f"  MRR       : {statistics.mean(mrrs):.3f}")
    print(f"  nDCG@{K}   : {statistics.mean(ndcgs):.3f}")
    print(f"生成指标（可回答子集）：")
    print(f"  金标事实覆盖率 : {statistics.mean(fact_covs):.3f}")
    print(f"  引用下标合法率 : {statistics.mean(ref_vals):.3f}")
    print(f"  数字可追溯率   : {statistics.mean(fact_traces):.3f}")

    print("\n阈值校准（22 条：17 应回答 + 5 应兜底）：")
    best_thr, best_acc = None, 0.0
    for thr in SWEEP:
        acc = statistics.mean(sweep_correct[thr])
        marker = ""
        if acc > best_acc:
            best_acc, best_thr = acc, thr
        if abs(thr - settings.retrieval_confidence_threshold) < 1e-9:
            marker = "  <- 当前 .env 值"
        print(f"  thr={thr:.2f}  判定正确率={acc:.3f}{marker}")
    print(f"\n最优阈值: {best_thr}（正确率 {best_acc:.3f}）")
    print(f"当前配置: {settings.retrieval_confidence_threshold}")
    print(f"总耗时: {time.time()-t0:.1f}s")

    # 保存报告
    os.makedirs("evaluation/reports", exist_ok=True)
    report = {
        "dataset": DATASET,
        "ran_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "retrieval": {
            f"recall@{K}": round(statistics.mean(recalls), 3),
            "mrr": round(statistics.mean(mrrs), 3),
            f"ndcg@{K}": round(statistics.mean(ndcgs), 3),
        },
        "generation": {
            "fact_coverage": round(statistics.mean(fact_covs), 3),
            "ref_valid_ratio": round(statistics.mean(ref_vals), 3),
            "fact_traceable_ratio": round(statistics.mean(fact_traces), 3),
        },
        "threshold_sweep": {str(t): round(statistics.mean(sweep_correct[t]), 3)
                            for t in SWEEP},
        "best_threshold": best_thr,
        "current_threshold": settings.retrieval_confidence_threshold,
        "per_query": rows,
    }
    out = "evaluation/reports/v0.1_{}.json".format(time.strftime("%Y%m%d_%H%M%S"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {out}")


if __name__ == "__main__":
    main()
