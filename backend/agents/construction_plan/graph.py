from langgraph.graph import END, StateGraph

from agents.construction_plan.nodes import (
    analyze_plan_task, build_final_content, completeness_check, fact_check,
    final_review, generate_document, generate_outline, generate_plan_sections,
    human_confirm_outline, human_confirm_template, retrieve_project_context,
    retrieve_reference_plans, retrieve_standard_context, retrieve_template,
    risk_check, route_after_final_review, standard_check, validate_request,
)
from agents.construction_plan.state import ConstructionPlanState
from services.sqlalchemy_checkpointer import SQLAlchemyCheckpointSaver


def build_graph(checkpointer=None):
    graph = StateGraph(ConstructionPlanState)
    graph.add_node("validate_request", validate_request)
    graph.add_node("analyze_plan_task", analyze_plan_task)
    graph.add_node("retrieve_template", retrieve_template)
    graph.add_node("human_confirm_template", human_confirm_template)
    graph.add_node("generate_outline", generate_outline)
    graph.add_node("human_confirm_outline", human_confirm_outline)
    graph.add_node("retrieve_reference_plans", retrieve_reference_plans)
    graph.add_node("retrieve_project_context", retrieve_project_context)
    graph.add_node("retrieve_standard_context", retrieve_standard_context)
    graph.add_node("generate_plan_sections", generate_plan_sections)
    graph.add_node("fact_check", fact_check)
    graph.add_node("standard_check", standard_check)
    graph.add_node("completeness_check", completeness_check)
    graph.add_node("risk_check", risk_check)
    graph.add_node("build_final_content", build_final_content)
    graph.add_node("final_review", final_review)
    graph.add_node("generate_document", generate_document)
    graph.set_entry_point("validate_request")
    graph.add_edge("validate_request", "analyze_plan_task")
    graph.add_edge("analyze_plan_task", "retrieve_template")
    graph.add_edge("retrieve_template", "human_confirm_template")
    graph.add_edge("human_confirm_template", "generate_outline")
    graph.add_edge("generate_outline", "human_confirm_outline")
    graph.add_edge("human_confirm_outline", "retrieve_reference_plans")
    graph.add_edge("retrieve_reference_plans", "retrieve_project_context")
    graph.add_edge("retrieve_project_context", "retrieve_standard_context")
    graph.add_edge("retrieve_standard_context", "generate_plan_sections")
    graph.add_edge("generate_plan_sections", "fact_check")
    graph.add_edge("fact_check", "standard_check")
    graph.add_edge("standard_check", "completeness_check")
    graph.add_edge("completeness_check", "risk_check")
    graph.add_edge("risk_check", "build_final_content")
    graph.add_edge("build_final_content", "final_review")
    graph.add_conditional_edges(
        "final_review", route_after_final_review,
        {"modify": "generate_plan_sections", "approve": "generate_document"})
    graph.add_edge("generate_document", END)
    return graph.compile(checkpointer=checkpointer or SQLAlchemyCheckpointSaver())
