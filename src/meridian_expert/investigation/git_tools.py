import subprocess
from pathlib import Path


def changed_files(repo: Path, ref: str = "HEAD~1") -> list[str]:
    if not (repo / ".git").exists():
        return []
    cp = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", ref, "HEAD"], capture_output=True, text=True)
    if cp.returncode != 0:
        return []
    return [x for x in cp.stdout.splitlines() if x.strip()]
