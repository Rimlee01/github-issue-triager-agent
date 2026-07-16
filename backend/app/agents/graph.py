"""LangGraph workflow — upgraded to 7 nodes including PR description generation."""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    classification_node,
    issue_analyzer_node,
    pr_description_node,
    priority_assessment_node,
    repo_context_retrieval_node,
    response_generator_node,
    solution_suggestion_node,
)
from app.agents.state import AgentState

_checkpointer = MemorySaver()
_compiled_graph = None


def build_triage_graph():
    graph = StateGraph(AgentState)
    graph.add_node("issue_analyzer", issue_analyzer_node)
    graph.add_node("repo_context_retrieval", repo_context_retrieval_node)
    graph.add_node("classification", classification_node)
    graph.add_node("priority_assessment", priority_assessment_node)
    graph.add_node("solution_suggestion", solution_suggestion_node)
    graph.add_node("pr_generator", pr_description_node)
    graph.add_node("response_generator", response_generator_node)

    graph.set_entry_point("issue_analyzer")
    graph.add_edge("issue_analyzer", "repo_context_retrieval")
    graph.add_edge("repo_context_retrieval", "classification")
    graph.add_edge("classification", "priority_assessment")
    graph.add_edge("priority_assessment", "solution_suggestion")
    graph.add_edge("solution_suggestion", "pr_generator")
    graph.add_edge("pr_generator", "response_generator")
    graph.add_edge("response_generator", END)
    return graph.compile(checkpointer=_checkpointer)


def get_triage_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_triage_graph()
    return _compiled_graph


async def run_triage(
    repo_id: str,
    issue_title: str,
    issue_description: str,
    thread_id: str,
    analysis_id: str = "",
) -> AgentState:
    graph = get_triage_graph()
    initial_state: AgentState = {
        "repo_id": repo_id,
        "issue_title": issue_title,
        "issue_description": issue_description,
        "analysis_id": analysis_id,
        "reasoning_trace": [],
    }
    config = {"configurable": {"thread_id": thread_id}}
    return await graph.ainvoke(initial_state, config=config)
