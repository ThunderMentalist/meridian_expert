from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BundleEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    priority_rank: int = Field(ge=1)
    priority: str = "low"
    task_family_weights: dict[str, float]
    package_domain_weights: dict[str, float]
    anchor_files: list[str]
    primary_files: list[str]
    supporting_tests: list[str] = Field(default_factory=list)
    neighboring_bundles: list[str] = Field(default_factory=list)
    expansion_hints: list[str] = Field(default_factory=list)
    optional_support_files: list[str] = Field(default_factory=list)
    notes: str
    files: list[str] = Field(default_factory=list)
    hotspot_tier: str | None = None
    default_dependency_modes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ensure_files(self) -> "BundleEntry":
        if not self.files:
            merged: list[str] = []
            for path in [
                *self.anchor_files,
                *self.primary_files,
                *self.supporting_tests,
                *self.optional_support_files,
            ]:
                if path not in merged:
                    merged.append(path)
            self.files = merged
        return self


class BundleRegistryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundles: list[BundleEntry]


class BundleRegistry:
    def __init__(self, path: Path = Path("config/bundle_registry.yaml")) -> None:
        self.path = path
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {"bundles": []}
        parsed = BundleRegistryData.model_validate(raw)
        self._bundles = sorted(parsed.bundles, key=lambda b: b.priority_rank)
        self._home_bundle_by_file: dict[str, BundleEntry] = {}
        for bundle in self._bundles:
            for file_path in bundle.primary_files:
                existing = self._home_bundle_by_file.get(file_path)
                if existing and existing.name != bundle.name:
                    raise ValueError(
                        f"file {file_path} is primary in both {existing.name} and {bundle.name}"
                    )
                self._home_bundle_by_file[file_path] = bundle

    def list(self) -> list[dict]:
        return [bundle.model_dump() for bundle in self._bundles]

    def by_name(self, name: str) -> dict | None:
        for bundle in self._bundles:
            if bundle.name == name:
                return bundle.model_dump()
        return None

    def by_file_path(self, file_path: str) -> list[dict]:
        out = [bundle.model_dump() for bundle in self._bundles if file_path in bundle.files]
        return out

    def home_bundle_for_file(self, file_path: str) -> dict | None:
        bundle = self._home_bundle_by_file.get(file_path)
        return bundle.model_dump() if bundle else None

    def by_hotspot_tier(self, hotspot_tier: str) -> list[dict]:
        return [
            bundle.model_dump()
            for bundle in self._bundles
            if bundle.hotspot_tier == hotspot_tier
        ]

    def by_dependency_mode(self, dependency_mode: str) -> list[dict]:
        return [
            bundle.model_dump()
            for bundle in self._bundles
            if dependency_mode in bundle.default_dependency_modes
        ]

    def rank_for(self, family: str, domain: str) -> list[dict]:
        scored: list[tuple[int, float, BundleEntry]] = []
        for bundle in self._bundles:
            family_weight = bundle.task_family_weights.get(family, 0.0)
            domain_weight = bundle.package_domain_weights.get(domain, 0.0)
            if family_weight <= 0 and domain_weight <= 0:
                continue
            score = family_weight + domain_weight
            scored.append((bundle.priority_rank, -score, bundle))
        scored.sort(key=lambda item: (item[0], item[1]))
        return [bundle.model_dump() for _, __, bundle in scored]
