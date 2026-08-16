"""agents.project_retrieval.nodes 与 services.retrieval.reranker 的单元测试。

原则：只测纯函数，不启动 DB / Milvus / LLM，全部用例毫秒级跑完。
运行方式（在 backend 目录下）：
    ../.venv/Scripts/python -m pytest tests -v
"""
from types import SimpleNamespace

import pytest

import agents.project_retrieval.nodes as retrieval_nodes
from services import project_service
from core.exceptions import AppError
from services.retrieval.base import RetrievedChunk
from services.retrieval.reranker import rerank
from agents.project_retrieval.nodes import (
    check_confidence,
    route_after_confidence,
    validate_input,
    validate_answer,
    route_after_validate,
    fallback,
)


def make_chunk(chunk_id: str, score: float) -> RetrievedChunk:
    """测试工厂：构造最小可用的 RetrievedChunk，隐藏无关字段。"""
    return RetrievedChunk(
        chunk_id=chunk_id, document_id="doc-1", page=1,
        content="x", score=score, method="dense",
    )


# ================= rerank：合并召回后的重排序 =================

class TestRerank:
    def test_按分数降序排列(self):
        chunks = [make_chunk("a", 0.3), make_chunk("b", 0.9), make_chunk("c", 0.6)]
        result = rerank("任意问题", chunks, top_k=8)
        assert [c.chunk_id for c in result] == ["b", "c", "a"]

    def test_top_k截断(self):
        chunks = [make_chunk(str(i), i / 10) for i in range(10)]
        result = rerank("q", chunks, top_k=3)
        assert len(result) == 3
        assert result[0].score == 0.9

    def test_候选不足top_k时全量返回(self):
        chunks = [make_chunk("a", 0.5)]
        assert len(rerank("q", chunks, top_k=8)) == 1

    def test_默认top_k为8(self):
        chunks = [make_chunk(str(i), i / 100) for i in range(12)]
        assert len(rerank("q", chunks)) == 8


# ============ check_confidence：检索置信度规则（0.25 阈值待校准的那条） ============

class TestCheckConfidence:
    def test_高分且证据不少于两条_置信度为1(self):
        state = {"evidences": [{"score": 0.9}, {"score": 0.8}]}
        out = check_confidence(state)
        assert out["confidence"] == 1.0
        assert out["fallback_needed"] is False

    def test_低于阈值_即使证据多条_进入兜底(self):
        state = {"evidences": [{"score": 0.01}, {"score": 0.02}]}
        out = check_confidence(state)
        assert out["confidence"] == 0.2
        assert out["fallback_needed"] is True

    def test_只有一条证据_不满足两条门槛(self):
        state = {"evidences": [{"score": 0.9}]}
        assert check_confidence(state)["fallback_needed"] is True

    def test_无证据_兜底(self):
        out = check_confidence({})
        assert out["confidence"] == 0.2
        assert out["fallback_needed"] is True


# ================= 置信度之后的图路由 =================

class TestRouteAfterConfidence:
    def test_需要兜底时路由到fallback(self):
        state = {"fallback_needed": True, "evidences": [{"score": 0.1}]}
        assert route_after_confidence(state) == "fallback"

    def test_证据充分时路由到生成回答(self):
        state = {"fallback_needed": False, "evidences": [{"score": 0.9}]}
        assert route_after_confidence(state) == "generate_answer"


# ================= validate_input：入口校验 =================

class TestValidateInput:
    def test_空问题抛422(self):
        with pytest.raises(AppError) as exc:
            validate_input({"original_query": "   ", "project_id": 1})
        assert exc.value.http_status == 422
        assert exc.value.code == "VALIDATION_ERROR"

    def test_缺project_id抛422(self):
        with pytest.raises(AppError):
            validate_input({"original_query": "什么是TN-S系统", "project_id": None})

    def test_正常输入通过(self):
        out = validate_input({"original_query": "电气方案", "project_id": 1})
        assert out == {"fallback_level": 0}

    @pytest.mark.parametrize("top_k", [0, 21, "8"])
    def test_top_k越界或类型错误抛422(self, top_k):
        with pytest.raises(AppError) as exc:
            validate_input({"original_query": "电气方案", "project_id": 1,
                            "top_k": top_k})
        assert exc.value.http_status == 422


class TestRetrieve:
    def test_top_k控制最终证据数量(self, monkeypatch):
        chunks = [make_chunk(str(i), 1 - i / 10) for i in range(5)]
        calls = []

        class DenseStub:
            def retrieve(self, query, project_id, top_k):
                calls.append(top_k)
                return chunks

        class LexicalStub:
            def retrieve(self, query, project_id, top_k):
                calls.append(top_k)
                return []

        monkeypatch.setattr(retrieval_nodes, "DenseRetriever", DenseStub)
        monkeypatch.setattr(retrieval_nodes, "LexicalRetriever", LexicalStub)

        out = retrieval_nodes.retrieve({"original_query": "配电箱",
                                        "project_id": 1, "top_k": 3})

        assert len(out["evidences_raw"]) == 3
        assert out["retrieval_candidate_count"] == 5
        assert calls == [20, 20]


# ======== validate_answer：硬事实校验（回答中的数字必须来自证据） ========

class TestValidateAnswer:
    EVIDENCES = [{"content": "接地电阻不大于 4 欧姆，漏电动作电流 30mA。"}]

    def test_数字全部在证据中_直接通过(self):
        out = validate_answer({"answer": "接地电阻不大于4欧姆", "evidences": self.EVIDENCES})
        assert out["regen_requested"] is False

    def test_数字不在证据中_第一轮触发重生成(self):
        out = validate_answer({"answer": "接地电阻为999欧姆",
                               "evidences": self.EVIDENCES, "validate_pass": 0})
        assert out["regen_requested"] is True

    def test_第二轮仍失败_附加人工核对提示(self):
        out = validate_answer({"answer": "接地电阻为999欧姆",
                               "evidences": self.EVIDENCES, "validate_pass": 1})
        assert out["regen_requested"] is False
        assert "人工核对" in out["answer"]

    def test_重生成请求路由回generate_answer(self):
        assert route_after_validate({"regen_requested": True}) == "generate_answer"
        assert route_after_validate({"regen_requested": False}) == "end"


# ================= fallback：兜底节点 =================

class TestFallback:
    def test_兜底回答_置信度为0(self):
        out = fallback({})
        assert out["confidence"] == 0.0
        assert out["retrieval_status"] == "EMPTY"
        assert len(out["answer"]) > 0


class TestProjectSuggestions:
    def test_名称前缀优先且自动清理标点(self, monkeypatch):
        projects = [
            SimpleNamespace(id=1, name="福建省学校项目", description="",
                            created_at=1),
            SimpleNamespace(id=2, name="深圳市龙华区幼儿园", description="公建项目",
                            created_at=2),
            SimpleNamespace(id=3, name="龙华设计资料", description="深圳市项目",
                            created_at=3),
        ]
        monkeypatch.setattr(project_service, "list_projects",
                            lambda db, user_id: projects)

        result = project_service.suggest_projects(
            None, 7, "深圳市龙华...", limit=3)

        assert [project.id for project in result] == [2]

    def test_名称匹配排在描述匹配之前(self, monkeypatch):
        projects = [
            SimpleNamespace(id=1, name="龙华区医院项目", description="",
                            created_at=1),
            SimpleNamespace(id=2, name="人民医院项目", description="位于龙华区",
                            created_at=2),
        ]
        monkeypatch.setattr(project_service, "list_projects",
                            lambda db, user_id: projects)

        result = project_service.suggest_projects(None, 7, "龙华", limit=3)

        assert [project.id for project in result] == [1, 2]

    def test_省略行政区后缀仍可预测项目(self, monkeypatch):
        projects = [
            SimpleNamespace(id=index, name=name, description="深圳龙华项目",
                            created_at=index)
            for index, name in enumerate([
                "深圳市龙华区星河幼儿园", "深圳市龙华区中心儿童医院",
                "深圳市龙华区儿童公园"], start=1)
        ]
        monkeypatch.setattr(project_service, "list_projects",
                            lambda db, user_id: projects)

        result = project_service.suggest_projects(None, 7, "深圳龙华", limit=3)

        assert len(result) == 3
