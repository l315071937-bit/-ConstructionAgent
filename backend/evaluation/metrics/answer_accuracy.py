"""Answer Accuracy：回答正确性（V0.1 简化基线：golden_facts 覆盖比）。

golden_facts：人工标注的关键事实列表（如 ["防水高度 1800mm"]）。
基线实现按字符串包含计算覆盖比；方案类长文档的评估
（事实错误数/规范引用正确率/结构完整度/可用率）需人工评审量表，
见 docs/02_AGENT_SPEC 8.20 与 evaluation/datasets/ 说明。"""
import re


def answer_accuracy(answer: str, golden_facts: list) -> dict:
    if not golden_facts:
        return {"coverage": 0.0, "hit": [], "miss": golden_facts}
    hit, miss = [], []
    for f in golden_facts:
        # 数字与关键词分别匹配，容忍表述差异
        nums = re.findall(r"\d+(?:\.\d+)?", f)
        key = re.sub(r"\d+(?:\.\d+)?", "", f).strip()
        if nums and not all(n in answer for n in nums):
            miss.append(f)
        elif key and key not in answer:
            miss.append(f)
        else:
            hit.append(f)
    return {"coverage": len(hit) / len(golden_facts),
            "hit": hit, "miss": miss}
