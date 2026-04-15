from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class SurfaceDependencyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aux_file: str
    cross_repo_route: str
    dependency_mode: str
    hotspot_tier: str
    compat_shim: bool = False
    under_tested: bool = False
    meridian_anchor_files: list[str]
    mandatory_meridian_expansions: list[str] = Field(default_factory=list)
    supporting_tests: list[str] = Field(default_factory=list)
    known_breakage_patterns: list[str] = Field(default_factory=list)
    notes: str


class SurfaceRegistryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surfaces: list[SurfaceDependencyRule]


class SurfaceDependencyRegistry:
    def __init__(
        self, path: Path = Path("config/surface_dependency_registry.yaml")
    ) -> None:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {"surfaces": []}
        parsed = SurfaceRegistryData.model_validate(raw)
        self._rules = parsed.surfaces
        self._by_file = {rule.aux_file: rule for rule in self._rules}

    def list(self) -> list[dict]:
        return [rule.model_dump() for rule in self._rules]

    def by_file_path(self, aux_file: str) -> dict | None:
        rule = self._by_file.get(aux_file)
        return rule.model_dump() if rule else None

    def by_hotspot_tier(self, hotspot_tier: str) -> list[dict]:
        return [rule.model_dump() for rule in self._rules if rule.hotspot_tier == hotspot_tier]

    def by_cross_repo_route(self, cross_repo_route: str) -> list[dict]:
        return [
            rule.model_dump()
            for rule in self._rules
            if rule.cross_repo_route == cross_repo_route
        ]

    def by_dependency_mode(self, dependency_mode: str) -> list[dict]:
        return [
            rule.model_dump()
            for rule in self._rules
            if rule.dependency_mode == dependency_mode
        ]
