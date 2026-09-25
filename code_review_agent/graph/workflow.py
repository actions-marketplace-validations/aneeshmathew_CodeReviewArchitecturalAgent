from typing import Literal
from langgraph.graph import END, START, StateGraph
from ..config import settings
from ..state import AuditState
from .nodes import (
    failure_report_node,
    generate_lgtm_node,
    human_approval_node,
    index_repo_ast_node,
    publish_pr_node,
    run_static_analyzers_node,
    run_tests_node,
    synthesize_fix_node,
)


def route_after_static_analysis(state: AuditState) -> Literal["synthesize_fix", "generate_lgtm"]:
    """Routes to fix synthesis if errors are detected, otherwise to LGTM summary."""
    errors = state.get("static_errors", [])
    if len(errors) > 0:
        return "synthesize_fix"
    return "generate_lgtm"


def route_after_tests(state: AuditState) -> Literal["publish_pr", "human_approval", "synthesize_fix", "failure_report"]:
    """Evaluates test results and determines whether to loop, escalate, or publish."""
    test_results = state.get("test_results", {})
    static_errors = state.get("static_errors", [])
    success = test_results.get("success", False) and len(static_errors) == 0

    if success:
        # Check human-in-the-loop requirement
        if state.get("is_structural_change", False) and not state.get("is_approved_by_human", False):
            return "human_approval"
        return "publish_pr"

    # Self-correction loop retry condition
    retry_count = state.get("retry_count", 0)
    if retry_count < settings.max_retries:
        return "synthesize_fix"

    return "failure_report"


def route_after_human_approval(state: AuditState) -> Literal["publish_pr", "__end__"]:
    """Proceeds to PR creation if approved by human, or ends in awaiting state."""
    if state.get("is_approved_by_human", False):
        return "publish_pr"
    return END


def create_audit_graph() -> StateGraph:
    """Constructs the complete Self-Correcting LangGraph workflow."""
    workflow = StateGraph(AuditState)

    # Register Nodes
    workflow.add_node("index_repo_ast", index_repo_ast_node)
    workflow.add_node("run_static_analyzers", run_static_analyzers_node)
    workflow.add_node("generate_lgtm", generate_lgtm_node)
    workflow.add_node("synthesize_fix", synthesize_fix_node)
    workflow.add_node("run_tests", run_tests_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("publish_pr", publish_pr_node)
    workflow.add_node("failure_report", failure_report_node)

    # Wire Edges
    workflow.add_edge(START, "index_repo_ast")
    workflow.add_edge("index_repo_ast", "run_static_analyzers")

    workflow.add_conditional_edges(
        "run_static_analyzers",
        route_after_static_analysis,
        {
            "synthesize_fix": "synthesize_fix",
            "generate_lgtm": "generate_lgtm",
        }
    )

    workflow.add_edge("generate_lgtm", END)

    workflow.add_edge("synthesize_fix", "run_tests")

    workflow.add_conditional_edges(
        "run_tests",
        route_after_tests,
        {
            "publish_pr": "publish_pr",
            "human_approval": "human_approval",
            "synthesize_fix": "synthesize_fix",
            "failure_report": "failure_report",
        }
    )

    workflow.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {
            "publish_pr": "publish_pr",
            END: END,
        }
    )

    workflow.add_edge("publish_pr", END)
    workflow.add_edge("failure_report", END)

    return workflow.compile()
