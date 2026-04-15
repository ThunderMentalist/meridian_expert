from __future__ import annotations

import subprocess
from pathlib import Path


def changed_files(repo: Path, ref: str = "HEAD~1") -> list[str]:
    if not (repo / ".git").exists():
        return []
    cp = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", ref, "HEAD"],
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        return []
    return [x.strip() for x in cp.stdout.splitlines() if x.strip()]


def derive_changed_paths_from_git(repo: Path, ref: str = "HEAD~1") -> list[str]:
    """Runtime helper for real local sibling repos. Safe no-op outside git repos."""
    return changed_files(repo=repo, ref=ref)
