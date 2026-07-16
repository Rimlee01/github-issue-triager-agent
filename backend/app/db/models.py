"""
SQLAlchemy ORM models.

Decision: async SQLAlchemy with asyncpg driver keeps the database layer
non-blocking inside FastAPI's async event loop. Every model has a UUID
primary key (not integer) — more resilient to merge conflicts if you ever
shard or replicate the DB, and safer to expose in APIs (no sequential ID
enumeration attacks).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text, Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(String(200), unique=True, nullable=False, index=True)
    owner = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    full_name = Column(String(200), nullable=False)
    default_branch = Column(String(50), default="main")
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    files_ingested = Column(Integer, default=0)
    issues_ingested = Column(Integer, default=0)
    pull_requests_ingested = Column(Integer, default=0)
    chunks_indexed = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analyses = relationship("IssueAnalysis", back_populates="repository", cascade="all, delete-orphan")


class IssueAnalysis(Base):
    __tablename__ = "issue_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(String(200), ForeignKey("repositories.repo_id"), nullable=False, index=True)
    issue_title = Column(Text, nullable=False)
    issue_description = Column(Text, nullable=False)
    summary = Column(Text)
    category = Column(String(50))
    category_confidence = Column(Float)
    priority = Column(String(20))
    priority_reason = Column(Text)
    technical_area = Column(String(100))
    suggested_labels = Column(JSON, default=list)
    related_files = Column(JSON, default=list)
    similar_issues = Column(JSON, default=list)
    duplicate_of = Column(JSON, nullable=True)
    root_cause = Column(Text)
    suggested_fix = Column(Text)
    files_to_modify = Column(JSON, default=list)
    implementation_approach = Column(Text)
    solution_confidence = Column(Float)
    pr_description = Column(Text, nullable=True)
    generated_response = Column(Text)
    reasoning_trace = Column(JSON, default=list)
    feedback_score = Column(Integer, nullable=True)  # 1 = thumbs up, -1 = thumbs down
    feedback_comment = Column(Text, nullable=True)
    cached = Column(Boolean, default=False)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="analyses")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(String(200), nullable=False, index=True)
    github_issue_number = Column(Integer, nullable=False)
    github_issue_title = Column(Text, nullable=False)
    event_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    analysis_id = Column(UUID(as_uuid=True), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
