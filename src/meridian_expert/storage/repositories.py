from pathlib import Path


def has_git_repo(path: Path) -> bool:
    return (path / ".git").exists()
