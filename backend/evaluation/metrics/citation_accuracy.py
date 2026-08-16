"""Citation Accuracy：回答引用质量（V0.1 简化基线）。

基线定义：
1. 引用下标合法性：answer 中 [En] 的 n 均在 evidence 数量范围内；
2. 硬事实可追溯：answer 中的数字必须出现在至少一条被引用 Evidence 的内容中。

后续升级：LLM-judge 评估「引用是否真的支撑对应论断」。"""
import re


def citation_accuracy(answer: str, evidences: list) -> dict:
    n_ev = len(evidences)
    refs = [int(x) for x in re.findall(r"\[E(\d+)\]", answer)]
    invalid = [r for r in refs if r < 1 or r > n_ev]
    ref_valid = 1.0 if refs and not invalid else (0.0 if invalid else 0.5)

    numbers = re.findall(r"\d+(?:\.\d+)?", answer)
    cited_text = " ".join(
        ev["content"] for i, ev in enumerate(evidences, start=1)
        if i in refs) if refs else ""
    missing = [n for n in numbers if n not in cited_text]
    fact_ok = 1.0 - (len(missing) / len(numbers)) if numbers else 1.0

    return {"ref_valid_ratio": ref_valid, "fact_traceable_ratio": fact_ok,
            "invalid_refs": invalid, "untraceable_numbers": missing}
