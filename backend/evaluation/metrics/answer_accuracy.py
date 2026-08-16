"""Answer Accuracy：回答正确性（V0.1 基线：golden_facts 覆盖比）。

golden_facts：人工标注的关键事实列表（如 ["防水高度 1800mm"]）。
基线实现按字符串包含计算覆盖比；方案类长文档的评估
（事实错误数/规范引用正确率/结构完整度/可用率）需人工评审量表，
见 docs/02_AGENT_SPEC 8.20 与 evaluation/datasets/ 说明。

2026-08-16 校准改进（源自首轮评测发现的误判）：
- 归一化空白：PDF/LLM 常带空格（"T5 型 LED 灯" vs "T5型LED灯"）
- 归一化汉字数字：回答用"三层"而金标写"3"（三->3）
后续升级：LLM-judge 语义等价评估。
"""
import re

_CN_NUM = str.maketrans("零一二三四五六七八九", "0123456789")


def _normalize(text: str) -> str:
    """去掉空白与常见中文标点 + 汉字数字转阿拉伯数字（仅个位级，够基线用）。

    标点示例：回答"一机、一闸"与金标"一机一闸"语义相同，剥离顿号后可匹配。
    """
    text = re.sub(r"[\s、，。；：·]+", "", text or "")
    text = text.translate(_CN_NUM)
    return text


def answer_accuracy(answer: str, golden_facts: list) -> dict:
    """V0.1 基线：归一化（去空白/标点/汉字数字转阿拉伯）后整串包含匹配。

    注：数字+关键词拆分匹配在 2026-08-16 首轮评测中发现缺陷
    （"T5型LED灯" 去掉数字后 "T型LED灯" 不可能原样出现），已废弃。
    语义等价与语序宽容留给后续 LLM-judge 升级。
    """
    if not golden_facts:
        return {"coverage": 0.0, "hit": [], "miss": golden_facts}
    ans_n = _normalize(answer)
    hit, miss = [], []
    for f in golden_facts:
        f_n = _normalize(f)
        if f_n in ans_n:
            hit.append(f)
        else:
            miss.append(f)
    return {"coverage": len(hit) / len(golden_facts),
            "hit": hit, "miss": miss}
