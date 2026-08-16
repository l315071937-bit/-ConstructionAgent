"""Project Retrieval Agent 图（02 6.3 的 V0.1 浅图）。
短查询不接 Checkpointer（01 52.2），HITL 场景仅存在于 Plan Agent。"""
from langgraph.graph import END, StateGraph

from agents.project_retrieval.nodes import (analyze_query,
                                            build_evidence_node,
                                            check_confidence, fallback,
                                            generate_answer, retrieve,
                                            route_after_confidence,
                                            route_after_validate,
                                            validate_answer, validate_input)
from agents.project_retrieval.state import ProjectRetrievalState


def build_graph():
    g = StateGraph(ProjectRetrievalState)
    g.add_node("validate_input", validate_input)
    g.add_node("analyze_query", analyze_query)
    g.add_node("retrieve", retrieve)
    g.add_node("build_evidence", build_evidence_node)
    g.add_node("check_confidence", check_confidence)
    g.add_node("generate_answer", generate_answer)
    g.add_node("validate_answer", validate_answer)
    g.add_node("fallback", fallback)

    g.set_entry_point("validate_input")
    g.add_edge("validate_input", "analyze_query")
    g.add_edge("analyze_query", "retrieve")
    g.add_edge("retrieve", "build_evidence")
    g.add_edge("build_evidence", "check_confidence")
    g.add_conditional_edges(
        "check_confidence", route_after_confidence,
        {"generate_answer": "generate_answer", "fallback": "fallback"})
    g.add_edge("generate_answer", "validate_answer")
    g.add_conditional_edges(
        "validate_answer", route_after_validate,
        {"generate_answer": "generate_answer", "end": END})
    g.add_edge("fallback", END)
    return g.compile()
