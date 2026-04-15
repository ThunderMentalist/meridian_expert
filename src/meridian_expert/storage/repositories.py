from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ResolvedRepository(BaseModel):
    name: str
    configured_path: Path | None
    source_kind: Literal["directory", "missing"]
    exists: bool
    git_available: bool
    root_path: Path | None
    notes: list[str] = Field(default_factory=list)


def has_git_repo(path: Path) -> bool:
    return (path / ".git").is_dir()


def find_repo_root(path: Path) -> Path | None:
    candidate = path
    if not candidate.exists():
        return None
    if candidate.is_file():
        candidate = candidate.parent
    for probe in [candidate, *candidate.parents]:
        if (probe / ".git").is_dir():
            return probe
    return None


def resolve_repository_status(name: str, configured_path: Path | None) -> ResolvedRepository:
    notes: list[str] = []
    if configured_path is None:
        notes.append("No path configured.")
        return ResolvedRepository(
            name=name,
            configured_path=None,
            source_kind="missing",
            exists=False,
            git_available=False,
            root_path=None,
            notes=notes,
        )

    path = configured_path
    if not path.exists():
        notes.append("Configured path does not exist.")
        return ResolvedRepository(
            name=name,
            configured_path=path,
            source_kind="missing",
            exists=False,
            git_available=False,
            root_path=None,
            notes=notes,
        )

    if not path.is_dir():
        notes.append("Configured path exists but is not a directory.")
        return ResolvedRepository(
            name=name,
            configured_path=path,
            source_kind="missing",
            exists=False,
            git_available=False,
            root_path=None,
            notes=notes,
        )

    root = find_repo_root(path)
    git_available = root is not None
    if not git_available:
        notes.append("Directory exists but no .git directory was found.")

    return ResolvedRepository(
        name=name,
        configured_path=path,
        source_kind="directory",
        exists=True,
        git_available=git_available,
        root_path=root,
        notes=notes,
    )


def resolve_repositories(configured_paths: dict[str, Path | None]) -> dict[str, ResolvedRepository]:
    return {name: resolve_repository_status(name, path) for name, path in configured_paths.items()}
