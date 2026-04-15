from __future__ import annotations

from pathlib import Path

import yaml

from meridian_expert.investigation.git_tools import derive_changed_paths_from_git
from meridian_expert.models.compatibility import (
    ChangeObservation,
    CompatibilityFinding,
    CompatibilityImpact,
    CompatibilityReport,
)

_RISK_ORDER = ["low", "medium", "high", "very_high"]

_BASE_RISK_BY_MODE = {
    "compat_shim": "high",
    "semi_internal": "high",
    "publicish_output": "medium",
    "schema_convention": "medium",
    "duck_typed": "medium",
    "public_api": "medium",
}


class CompatibilityChecker:
    def __init__(self, manifest_path: Path = Path("config/compatibility_manifest.yaml")) -> None:
        self.manifest_path = manifest_path
        self.data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}

    def check_changed_paths(self, changed_paths: list[str]) -> CompatibilityReport:
        observations = [ChangeObservation(path=p) for p in changed_paths]
        return self.check_observations(observations)

    def check_observations(self, observations: list[ChangeObservation]) -> CompatibilityReport:
        changed = {_normalize_path(o.path) for o in observations}
        report = CompatibilityReport(changed_surfaces=sorted(changed))

        packaging = self.data.get("packaging", {})
        if packaging.get("warning"):
            report.warnings.append(packaging["warning"])

        under_tested = set(self.data.get("under_tested_modules", []))
        relationships = self.data.get("relationships", [])

        for relationship in relationships:
            upstream = relationship["upstream"]
            if _normalize_path(upstream) not in changed:
                continue

            for dependent in relationship.get("dependents", []):
                mode = relationship.get("dependency_mode", "publicish_output")
                hotspot_tier = relationship.get("hotspot_tier", "tier_2")
                risk = self._risk_for(relationship=relationship, dependent=dependent, under_tested=under_tested)
                reasons = [
                    f"Changed upstream surface: {upstream}",
                    f"Dependency mode: {mode}",
                    f"Hotspot tier: {hotspot_tier}",
                ]
                if dependent in under_tested:
                    reasons.append("Dependent module is explicitly under-tested")

                patterns = relationship.get("known_breakage_patterns", [])
                if patterns:
                    reasons.append(f"Known breakage patterns: {', '.join(patterns)}")

                report.impacts.append(
                    CompatibilityImpact(
                        upstream_path=upstream,
                        dependent_path=dependent,
                        dependency_mode=mode,
                        hotspot_tier=hotspot_tier,
                        risk_level=risk,
                        reasons=reasons,
                        support_tests=relationship.get("support_tests", []),
                    )
                )

        if any(path.endswith("src/meridian_aux/nest/nest.py") for path in changed):
            report.warnings.append(
                "src/meridian_aux/nest/nest.py is meaningfully coupled and effectively under-tested."
            )

        notes = self.data.get("notes", [])
        report.notes.extend(notes)

        return report

    def check_with_git(self, repo: Path, ref: str = "HEAD~1") -> CompatibilityReport:
        changed = derive_changed_paths_from_git(repo=repo, ref=ref)
        return self.check_changed_paths(changed)

    def render_markdown(self, report: CompatibilityReport) -> str:
        lines = ["# Compatibility and update-risk report", ""]
        if report.changed_surfaces:
            lines.extend(["## Changed surfaces", ""])
            lines.extend([f"- `{path}`" for path in report.changed_surfaces])
            lines.append("")

        if report.impacts:
            lines.extend(["## Affected meridian_aux files", ""])
            for impact in report.impacts:
                lines.append(
                    f"- `{impact.dependent_path}` ← `{impact.upstream_path}` "
                    f"(**risk:** {impact.risk_level})"
                )
                lines.append(f"  - dependency mode: {impact.dependency_mode}")
                lines.append(f"  - hotspot tier: {impact.hotspot_tier}")
                for reason in impact.reasons:
                    lines.append(f"  - why: {reason}")
                if impact.support_tests:
                    lines.append(f"  - support tests: {', '.join(impact.support_tests)}")
            lines.append("")
        else:
            lines.extend(["## Affected meridian_aux files", "", "- No impacted surfaces found in manifest mapping.", ""])

        if report.warnings:
            lines.extend(["## Warnings", ""])
            lines.extend([f"- {warning}" for warning in report.warnings])
            lines.append("")

        if report.notes:
            lines.extend(["## Notes", ""])
            lines.extend([f"- {note}" for note in report.notes])
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def run(self, changed: list[str]) -> list[CompatibilityFinding]:
        """Legacy API retained for existing CLI behavior."""
        report = self.check_changed_paths(changed)
        by_upstream: dict[str, list[CompatibilityImpact]] = {}
        for impact in report.impacts:
            by_upstream.setdefault(impact.upstream_path, []).append(impact)

        results: list[CompatibilityFinding] = []
        for relationship in self.data.get("relationships", []):
            upstream = relationship["upstream"]
            impacts = by_upstream.get(upstream, [])
            results.append(
                CompatibilityFinding(
                    upstream=upstream,
                    dependents=[i.dependent_path for i in impacts] or relationship.get("dependents", []),
                    risk_level=_max_risk([i.risk_level for i in impacts], default=relationship.get("risk_level", "medium")),
                    changed=bool(impacts),
                    notes="Potential impact" if impacts else "No detected diff",
                )
            )
        return results

    def _risk_for(self, *, relationship: dict, dependent: str, under_tested: set[str]) -> str:
        explicit = (relationship.get("explicit_risk_by_dependent") or {}).get(dependent)
        if explicit:
            risk = explicit
        else:
            mode = relationship.get("dependency_mode", "publicish_output")
            risk = _BASE_RISK_BY_MODE.get(mode, "medium")
            if mode == "semi_internal" and relationship.get("reconstructs_model_behavior", False):
                risk = "very_high"

        if dependent in under_tested:
            risk = _raise_risk(risk)
        return risk


def _normalize_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _raise_risk(risk_level: str) -> str:
    if risk_level not in _RISK_ORDER:
        return "high"
    idx = _RISK_ORDER.index(risk_level)
    return _RISK_ORDER[min(idx + 1, len(_RISK_ORDER) - 1)]


def _max_risk(levels: list[str], default: str) -> str:
    if not levels:
        return default
    ranked = sorted(levels, key=lambda item: _RISK_ORDER.index(item) if item in _RISK_ORDER else 999)
    return ranked[-1]
