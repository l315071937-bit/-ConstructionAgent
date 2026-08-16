"""evaluation.metrics 的单元测试：评测指标是"尺子"，尺子本身的正确性必须有保护。

覆盖 2026-08-16 首轮评测中踩过的坑：
- 空格/标点差异（"T5 型 LED 灯" vs "T5型LED灯"、"一机、一闸" vs "一机一闸"）
- 汉字数字 vs 阿拉伯数字（"三层" vs "3"）
"""
from evaluation.metrics.answer_accuracy import answer_accuracy
from evaluation.metrics.citation_accuracy import citation_accuracy
from evaluation.metrics.recall_at_k import recall_at_k


class TestAnswerAccuracy:
    def test_全部命中(self):
        out = answer_accuracy("采用T5型LED灯、LED悬挂灯", ["T5型LED灯", "LED悬挂灯"])
        assert out["coverage"] == 1.0
        assert out["miss"] == []

    def test_空格差异_命中(self):
        out = answer_accuracy("采用 T5 型 LED 灯", ["T5型LED灯"])
        assert out["coverage"] == 1.0

    def test_汉字数字与阿拉伯数字等价_命中(self):
        out = answer_accuracy("每隔三层连接一次", ["三层"])
        assert out["coverage"] == 1.0
        out2 = answer_accuracy("每隔三层连接一次", ["3层"])
        assert out2["coverage"] == 1.0

    def test_标点差异_命中(self):
        out = answer_accuracy("实行一机、一闸制", ["一机一闸"])
        assert out["coverage"] == 1.0

    def test_事实缺失_未命中并列出(self):
        out = answer_accuracy("只有T5型LED灯", ["T5型LED灯", "LED悬挂灯"])
        assert out["coverage"] == 0.5
        assert out["miss"] == ["LED悬挂灯"]

    def test_空金标_覆盖为0(self):
        out = answer_accuracy("任意回答", [])
        assert out["coverage"] == 0.0


class TestCitationAccuracy:
    def test_引用合法且数字可追溯(self):
        evs = [{"content": "接地电阻不大于 4 欧姆"}]
        out = citation_accuracy("接地电阻不大于4欧姆 [E1]", evs)
        assert out["ref_valid_ratio"] == 1.0
        assert out["fact_traceable_ratio"] == 1.0
        assert out["invalid_refs"] == []

    def test_引用越界_判定非法(self):
        evs = [{"content": "x"}]
        out = citation_accuracy("答案 [E3]", evs)
        assert out["invalid_refs"] == [3]
        assert out["ref_valid_ratio"] == 0.0

    def test_无引用_折中0_5(self):
        out = citation_accuracy("没有引用的回答", [{"content": "x"}])
        assert out["ref_valid_ratio"] == 0.5


class TestRecallAtK:
    def test_相关项全部在topk内(self):
        assert recall_at_k(["a", "b", "c"], {"b"}, 3) == 1.0

    def test_相关项部分命中(self):
        assert recall_at_k(["a", "b", "c"], {"b", "z"}, 3) == 0.5

    def test_相关项排在k之外_为0(self):
        assert recall_at_k(["a", "b"], {"z"}, 2) == 0.0

    def test_空相关集_为0(self):
        assert recall_at_k(["a"], set(), 2) == 0.0
