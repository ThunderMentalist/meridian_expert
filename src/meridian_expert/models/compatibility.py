from __future__ import annotations

from pydantic import BaseModel, Field


class ChangeObservation(BaseModel):
    path: str
    symbol: str | None = None
    summary: str | None = None


class CompatibilityImpact(BaseModel):
    upstream_path: str
    dependent_path: str
    dependency_mode: str
    hotspot_tier: str
    risk_level: str
    reasons: list[str] = Field(default_factory=list)
    support_tests: list[str] = Field(default_factory=list)


class CompatibilityReport(BaseModel):
    changed_surfaces: list[str] = Field(default_factory=list)
    impacts: list[CompatibilityImpact] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CompatibilityFinding(BaseModel):
    """Legacy shape for CLI compatibility checks."""

    upstream: str
    dependents: list[str]
    risk_level: str
    changed: bool
    notes: str = ""
