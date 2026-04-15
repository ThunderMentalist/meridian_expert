from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from meridian_expert.enums import TaskFamily, TaskState


class TaskBrief(BaseModel):
    title: str
    task_family: TaskFamily
    repo_scope: str = "cross_repo"
    package_domain: str = "auto"
    audience: str = "engineer"
    output_format: str = "markdown"
    goal: str
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    evidence_depth: str = "standard"
    snippets_allowed: bool = False
    appendix_requested: bool = False
    unknowns: list[str] = Field(default_factory=list)

    needs_clarification: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    family_confidence: float | None = None
    domain_confidence: float | None = None
    suggested_bundles: list[str] = Field(default_factory=list)
    anchor_concepts: list[str] = Field(default_factory=list)
    candidate_anchor_files: list[str] = Field(default_factory=list)
    cross_repo_route: str | None = None
    hotspot_tier: str | None = None
    dependency_mode: str | None = None
    is_compatibility_shim: bool = False
    under_tested_risk: bool = False
    attachment_requirements: list[str] = Field(default_factory=list)


class TaskRecord(BaseModel):
    task_id: str
    state: TaskState
    family: TaskFamily
    created_at: datetime
    current_cycle: str
    parent_task_id: Optional[str] = None
    related_task_id: Optional[str] = None
    source_task_id: Optional[str] = None
