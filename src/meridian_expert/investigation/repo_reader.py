from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ResolvedSourcePath(BaseModel):
    repo_root: Path
    repo_path: str
    absolute_path: Path


class FileSlice(BaseModel):
    repo_path: str
    start_line: int
    end_line: int
    text: str


class RepoReader:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def normalize_repo_path(self, path: str | Path) -> str:
        resolved = self.resolve_path(path)
        return resolved.repo_path

    def resolve_path(self, path: str | Path) -> ResolvedSourcePath:
        raw = Path(path)
        abs_path = raw if raw.is_absolute() else (self.repo_root / raw)
        abs_path = abs_path.resolve()

        try:
            rel = abs_path.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"Path {path!s} is outside repo root {self.repo_root!s}") from exc

        return ResolvedSourcePath(
            repo_root=self.repo_root,
            repo_path=rel.as_posix(),
            absolute_path=abs_path,
        )

    def exists(self, path: str | Path) -> bool:
        return self.resolve_path(path).absolute_path.exists()

    def read_text(self, path: str | Path) -> str:
        return self.resolve_path(path).absolute_path.read_text(encoding="utf-8")

    def read_lines(self, path: str | Path, start_line: int, end_line: int) -> FileSlice:
        if start_line < 1:
            raise ValueError("start_line must be >= 1")
        if end_line < start_line:
            raise ValueError("end_line must be >= start_line")

        resolved = self.resolve_path(path)
        lines = resolved.absolute_path.read_text(encoding="utf-8").splitlines()
        snippet = "\n".join(lines[start_line - 1 : end_line])
        return FileSlice(
            repo_path=resolved.repo_path,
            start_line=start_line,
            end_line=end_line,
            text=snippet,
        )


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")
