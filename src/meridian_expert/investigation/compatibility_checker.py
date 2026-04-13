from __future__ import annotations

from pathlib import Path

import yaml

from meridian_expert.models.compatibility import CompatibilityFinding


class CompatibilityChecker:
    def __init__(self, manifest_path: Path = Path("config/compatibility_manifest.yaml")) -> None:
        self.data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    def run(self, changed: list[str]) -> list[CompatibilityFinding]:
        findings=[]
        for rel in self.data.get("relationships", []):
            upstream = rel["upstream"]
            short = upstream.replace("meridian/", "")
            hit = upstream in changed or short in changed
            findings.append(CompatibilityFinding(upstream=upstream, dependents=rel.get("dependents", []), risk_level=rel.get("risk_level", "medium"), changed=hit, notes="Potential impact" if hit else "No detected diff"))
        return findings
