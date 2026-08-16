"""Project Retrieval Graph wiring tests without external infrastructure."""
from services.retrieval.base import RetrievedChunk

import agents.project_retrieval.graph as graph_module


def test_graph保留top_k并走完整成功分支(monkeypatch):
    seen = {}

    def retrieve(state):
        seen["top_k"] = state["top_k"]
        chunk = RetrievedChunk("c1", "d1", 1, "配电箱要求", 0.9, "dense")
        return {"evidences_raw": [chunk], "retrieval_candidate_count": 2,
                "retrieval_status": "OK"}

    def build_evidence(state):
        return {"evidences": [{"content": "配电箱要求", "score": 0.9}]}

    monkeypatch.setattr(graph_module, "retrieve", retrieve)
    monkeypatch.setattr(graph_module, "build_evidence_node", build_evidence)
    monkeypatch.setattr(graph_module, "generate_answer",
                        lambda state: {"answer": "应按项目资料执行"})
    monkeypatch.setattr(graph_module, "validate_answer",
                        lambda state: {"regen_requested": False})

    final = graph_module.build_graph().invoke({
        "request_id": "req-test", "user_id": 1, "tenant_id": 1,
        "project_id": 1, "original_query": "配电箱如何安装？", "top_k": 3,
    })

    assert seen["top_k"] == 3
    assert final["answer"] == "应按项目资料执行"
    assert final["fallback_needed"] is False
