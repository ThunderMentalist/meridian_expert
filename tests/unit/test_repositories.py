from pathlib import Path

from meridian_expert.storage.repositories import (
    find_repo_root,
    has_git_repo,
    resolve_repositories,
    resolve_repository_status,
)


def test_resolve_existing_directory_with_git(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    status = resolve_repository_status("meridian", repo)
    assert status.source_kind == "directory"
    assert status.exists is True
    assert status.git_available is True
    assert status.root_path == repo
    assert has_git_repo(repo)


def test_resolve_existing_directory_without_git(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    nested = repo / "sub" / "leaf"
    nested.mkdir(parents=True)
    status = resolve_repository_status("meridian_aux", repo)
    assert status.source_kind == "directory"
    assert status.exists is True
    assert status.git_available is False
    assert status.root_path is None
    assert "no .git" in status.notes[0].lower()
    assert find_repo_root(nested) is None


def test_resolve_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    status = resolve_repository_status("meridian", missing)
    assert status.source_kind == "missing"
    assert status.exists is False
    assert status.git_available is False
    all_statuses = resolve_repositories({"meridian": missing, "meridian_aux": None})
    assert all_statuses["meridian"].source_kind == "missing"
    assert all_statuses["meridian_aux"].configured_path is None
