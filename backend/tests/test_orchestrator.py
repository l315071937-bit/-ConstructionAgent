"""agents.orchestrator 意图分类与路由的单元测试。

业务规则（2026-08-16 保守路由原则）：拿不准就走 project 检索，
只有明确的方案编制类 / 规范查询类才路由到对应 Agent。
"""
from agents.orchestrator import classify_intent, route


class TestClassifyIntent:
    def test_编制方案类_判为plan(self):
        assert classify_intent("帮我编制地下室防水施工方案") == "plan"
        assert classify_intent("请生成一份基坑支护方案") == "plan"

    def test_规范编号类_判为standard(self):
        assert classify_intent("JGJ46-2005 对临时用电有什么要求") == "standard"
        assert classify_intent("GB 50303-2015 的验收规定") == "standard"

    def test_规范咨询句式_判为standard(self):
        assert classify_intent("《施工现场临时用电安全技术规范》有哪些要求") == "standard"
        assert classify_intent("这个规范是否现行有效") == "standard"

    def test_普通问题_默认走project检索(self):
        # 关键词"施工方案"出现但没有编制类动词 -> 不算 plan
        assert classify_intent("建筑电气工程施工方案里临时用电怎么配电") == "project"
        # 有"要求"但没有"规范"前缀 -> 不算 standard
        assert classify_intent("这个项目的接地电阻要求是多少") == "project"
        # "帮我看看"不含编制类动词 -> 保守走 project
        assert classify_intent("帮我看看这个项目的施工方案") == "project"


class TestRoute:
    def test_project意图正常放行(self):
        assert route("临时用电怎么配电") == "project"

    def test_plan意图路由到方案Agent(self):
        assert route("帮我编制地下室防水施工方案") == "plan"

    def test_standard意图路由到规范Agent(self):
        assert route("JGJ46-2005 有什么要求") == "standard"
