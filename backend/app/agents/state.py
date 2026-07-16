"""LangGraph shared state — upgraded with analysis_id for WS routing and PR description."""
from __future__ import annotations
from typing import Annotated, Optional, TypedDict
import operator


class AgentState(TypedDict, total=False):
    # Input
    repo_id: str
    issue_title: str
    issue_description: str
    analysis_id: str  # used to route WebSocket events to correct connection

    # Node 1
    summary: str
    technical_area: str

    # Node 2
    related_files: list[dict]
    similar_issues: list[dict]
    duplicate_of: Optional[dict]

    # Node 3
    category: str
    category_confidence: float
    suggested_labels: list[str]

    # Node 4
    priority: str
    priority_reason: str

    # Node 5
    root_cause: str
    suggested_fix: str
    files_to_modify: list[str]
    implementation_approach: str
    solution_confidence: float

    # Node 6 (new)
    pr_description: str

    # Node 7
    generated_response: str

    # Explainability
    reasoning_trace: Annotated[list[str], operator.add]
