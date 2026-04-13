from __future__ import annotations

from pathlib import Path

import yaml


class BundleRegistry:
    def __init__(self, path: Path = Path("config/bundle_registry.yaml")) -> None:
        self.path = path
        self.data = yaml.safe_load(path.read_text(encoding="utf-8")) or {"bundles": []}

    def list(self) -> list[dict]:
        return self.data.get("bundles", [])

    def rank_for(self, family: str, domain: str) -> list[dict]:
        out = []
        for b in self.list():
            if family in b.get("families", []) and (domain in b.get("domains", []) or "auto" in b.get("domains", [])):
                out.append(b)
        out.sort(key=lambda b: 0 if b.get("priority") == "high" else 1)
        return out
