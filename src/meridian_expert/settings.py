from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class RepoPaths(BaseModel):
    meridian_repo_path: Path
    meridian_aux_repo_path: Path
    workspace_path: Path


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_paths(cli_meridian: str | None = None, cli_aux: str | None = None, cli_workspace: str | None = None) -> RepoPaths:
    local = _read_yaml(Path("config/repos.local.yaml"))
    example = _read_yaml(Path("config/repos.example.yaml"))

    meridian = cli_meridian or os.getenv("MERIDIAN_REPO_PATH") or local.get("meridian_repo_path") or example.get("meridian_repo_path", "../meridian")
    aux = cli_aux or os.getenv("MERIDIAN_AUX_REPO_PATH") or local.get("meridian_aux_repo_path") or example.get("meridian_aux_repo_path", "../meridian_aux")
    workspace = cli_workspace or os.getenv("MERIDIAN_EXPERT_WORKSPACE") or local.get("workspace_path") or example.get("workspace_path", "./runtime")
    return RepoPaths(meridian_repo_path=Path(meridian), meridian_aux_repo_path=Path(aux), workspace_path=Path(workspace))


def load_yaml_config(path: str) -> dict[str, Any]:
    return _read_yaml(Path(path))


def llm_backend_kind() -> str:
    return os.getenv("MERIDIAN_EXPERT_LLM_BACKEND", "openai").strip().lower() or "openai"
