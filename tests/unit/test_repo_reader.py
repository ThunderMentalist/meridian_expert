from pathlib import Path

import pytest

from meridian_expert.investigation.repo_reader import RepoReader


def test_repo_reader_resolve_read_and_slice(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    file_path = repo / "pkg" / "module.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("line1\nline2\nline3\n", encoding="utf-8")

    reader = RepoReader(repo)
    resolved = reader.resolve_path("pkg/module.py")
    assert resolved.repo_path == "pkg/module.py"
    assert reader.exists("pkg/module.py") is True
    assert reader.read_text("pkg/module.py").startswith("line1")

    slice_ = reader.read_lines("pkg/module.py", 2, 3)
    assert slice_.text == "line2\nline3"


def test_repo_reader_rejects_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("print('x')\n", encoding="utf-8")

    reader = RepoReader(repo)
    with pytest.raises(ValueError):
        reader.resolve_path(outside)
