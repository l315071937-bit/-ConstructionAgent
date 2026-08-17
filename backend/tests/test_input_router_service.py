"""Input routing must answer cheap rules before retrieval or agent calls."""
from types import SimpleNamespace

from services import input_router_service


def test_问候语直接规则回复且不查询项目(monkeypatch):
    def should_not_run(*args, **kwargs):
        raise AssertionError("greeting must not query project candidates")

    monkeypatch.setattr(input_router_service.project_service,
                        "suggest_projects", should_not_run)

    result = input_router_service.route_input(None, 7, "你好！")

    assert result["type"] == "RULE_REPLY"
    assert result["rule"] == "GREETING"
    assert "智能 AI 建筑辅助" in result["answer"]


def test_身份与能力问题使用固定规则():
    identity = input_router_service.match_quick_rule("你是谁？")
    capabilities = input_router_service.match_quick_rule("你会什么")

    assert identity["rule"] == "IDENTITY"
    assert capabilities["rule"] == "CAPABILITIES"


def test_最近项目返回前三个可访问项目(monkeypatch):
    projects = [SimpleNamespace(id=index) for index in range(1, 6)]
    monkeypatch.setattr(input_router_service.project_service,
                        "list_projects", lambda db, user_id: projects)
    monkeypatch.setattr(
        input_router_service.project_service, "project_cards",
        lambda db, items: [{"project_id": item.id} for item in items])

    result = input_router_service.route_input(None, 7, "最近的公司项目")

    assert result["type"] == "RECENT_PROJECTS"
    assert [item["project_id"] for item in result["projects"]] == [1, 2, 3]


def test_项目预测优先于Agent意图分类(monkeypatch):
    project = SimpleNamespace(id=9)
    monkeypatch.setattr(input_router_service.project_service,
                        "suggest_projects",
                        lambda db, user_id, query, limit: [project])
    monkeypatch.setattr(
        input_router_service.project_service, "project_cards",
        lambda db, items: [{"project_id": item.id} for item in items])

    result = input_router_service.route_input(None, 7, "深圳龙华")

    assert result["type"] == "PROJECT_SUGGESTIONS"
    assert result["projects"] == [{"project_id": 9}]


def test_明确规范和方案请求进入对应Agent路由(monkeypatch):
    monkeypatch.setattr(input_router_service.project_service,
                        "suggest_projects", lambda *args: [])

    standard = input_router_service.route_input(
        None, 7, "JGJ46-2005 有什么要求")
    plan = input_router_service.route_input(None, 7, "帮我编制防水施工方案")

    assert standard == {
        "type": "AGENT_ROUTE", "intent": "standard", "available": True,
    }
    assert plan["intent"] == "plan"
    assert plan["available"] is True


def test_方案模式下普通输入固定进入方案Agent(monkeypatch):
    def should_not_search_projects(*args):
        raise AssertionError("plan mode must not search project names")

    monkeypatch.setattr(input_router_service.project_service,
                        "suggest_projects", should_not_search_projects)

    result = input_router_service.route_input(
        None, 7, "编制地下室防水方案", active_agent="plan")

    assert result == {
        "type": "AGENT_ROUTE", "intent": "plan", "available": True}


def test_规范模式下普通问题固定进入规范Agent(monkeypatch):
    def should_not_search_projects(*args):
        raise AssertionError("standard mode must not search project names")

    monkeypatch.setattr(input_router_service.project_service,
                        "suggest_projects", should_not_search_projects)

    result = input_router_service.route_input(
        None, 7, "消防车道宽度是多少", active_agent="standard")

    assert result == {
        "type": "AGENT_ROUTE", "intent": "standard", "available": True}
