from __future__ import annotations

from pydantic import BaseModel, Field


class InvestigationPlan(BaseModel):
    anchor_files: list[str]
    selected_bundles: list[str]
    mandatory_expansions: list[str]
    selected_tests: list[str]
    support_files: list[str]
    rationale: list[str]
    cross_repo_route: str | None = None
    hotspot_tier: str | None = None
    dependency_mode: str | None = None
    under_tested: bool = False


class EvidenceItem(BaseModel):
    repo_name: str
    path: str
    symbol: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    rationale: str
    authority_rank: int
    significance: float
    direct: bool
    dependency_mode: str | None = None
    test_coverage_strength: str | None = None
    reconstructs_meridian_behavior: bool = False
    schema_convention_dependency: bool = False


class EvidencePack(BaseModel):
    anchor_files: list[str]
    items: list[EvidenceItem]
    notes: list[str] = Field(default_factory=list)
