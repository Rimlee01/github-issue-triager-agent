"""Pydantic schemas — upgraded with pr_description, processing_time_ms, feedback."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class IssueCategory(str, Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    SECURITY = "security"
    QUESTION = "question"
    UNKNOWN = "unknown"


class IssuePriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RepositoryStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    READY = "ready"
    FAILED = "failed"


class AnalyzeRepositoryRequest(BaseModel):
    repo_url: str


class AnalyzeRepositoryResponse(BaseModel):
    repo_id: str
    owner: str
    name: str
    status: RepositoryStatus
    files_ingested: int
    issues_ingested: int
    pull_requests_ingested: int
    message: str


class AnalyzeIssueRequest(BaseModel):
    issue_title: str = Field(..., min_length=3, max_length=500)
    issue_description: str = Field(..., min_length=5)
    repo_id: str
    analysis_id: Optional[str] = None  # passed from frontend for WebSocket routing


class RelatedFile(BaseModel):
    path: str
    relevance_score: float
    snippet: str
    chunk_influence: Optional[str] = None


class SimilarIssue(BaseModel):
    number: Optional[int] = None
    title: str
    similarity_score: float
    url: Optional[str] = None
    is_likely_duplicate: bool = False


class SolutionSuggestion(BaseModel):
    root_cause: str
    suggested_fix: str
    files_to_modify: list[str]
    implementation_approach: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class AnalyzeIssueResponse(BaseModel):
    issue_id: str
    summary: str
    category: IssueCategory
    category_confidence: float
    priority: IssuePriority
    priority_reason: str
    technical_area: str
    suggested_labels: list[str]
    related_files: list[RelatedFile]
    similar_issues: list[SimilarIssue]
    duplicate_of: Optional[SimilarIssue] = None
    suggested_solution: SolutionSuggestion
    pr_description: str = ""
    generated_response: str
    reasoning_trace: list[str] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IngestedFile(BaseModel):
    path: str
    content: str
    size_bytes: int


class GitHubIssueRecord(BaseModel):
    number: int
    title: str
    body: str
    state: str
    url: str
    labels: list[str] = Field(default_factory=list)
