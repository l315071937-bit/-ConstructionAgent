from langgraph.graph import END, StateGraph

from agents.standard_query.nodes import (analyze_standard_query,
                                         build_evidence_node,
                                         check_applicability, check_confidence,
                                         check_version, fallback,
                                         generate_answer, retrieve,
                                         route_after_confidence,
                                         route_after_validate,
                                         validate_answer, validate_input)
from agents.standard_query.state import StandardQueryState


def build_graph():
    graph = StateGraph(StandardQueryState)
    graph.add_node("validate_input", validate_input)
    graph.add_node("analyze_standard_query", analyze_standard_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("build_evidence", build_evidence_node)
    graph.add_node("version_check", check_version)
    graph.add_node("applicability_check", check_applicability)
    graph.add_node("check_confidence", check_confidence)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("validate_answer", validate_answer)
    graph.add_node("fallback", fallback)
    graph.set_entry_point("validate_input")
    graph.add_edge("validate_input", "analyze_standard_query")
    graph.add_edge("analyze_standard_query", "retrieve")
    graph.add_edge("retrieve", "build_evidence")
    graph.add_edge("build_evidence", "version_check")
    graph.add_edge("version_check", "applicability_check")
    graph.add_edge("applicability_check", "check_confidence")
    graph.add_conditional_edges(
        "check_confidence", route_after_confidence,
        {"generate_answer": "generate_answer", "fallback": "fallback"})
    graph.add_edge("generate_answer", "validate_answer")
    graph.add_conditional_edges(
        "validate_answer", route_after_validate,
        {"generate_answer": "generate_answer", "end": END})
    graph.add_edge("fallback", END)
    return graph.compile()
