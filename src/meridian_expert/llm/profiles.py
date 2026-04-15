from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ModelProfile(BaseModel):
    alias: str
    model: str
    reasoning_effort: str = "medium"
    enabled: bool = True


def load_profiles(path: Path = Path("config/model_profiles.yaml")) -> dict[str, ModelProfile]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles: dict[str, ModelProfile] = {}
    for alias, data in raw.items():
        payload = dict(data or {})
        payload["alias"] = alias
        profiles[alias] = ModelProfile.model_validate(payload)
    return profiles
