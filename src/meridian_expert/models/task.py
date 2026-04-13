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


class TaskRecord(BaseModel):
    task_id: str
    state: TaskState
    family: TaskFamily
    created_at: datetime
    current_cycle: str
    parent_task_id: Optional[str] = None
    related_task_id: Optional[str] = None
    source_task_id: Optional[str] = None
