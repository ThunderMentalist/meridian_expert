from __future__ import annotations

import ast
from pathlib import Path
from typing import Literal

RepoKind = Literal["meridian", "meridian_aux"]


class ImportGraph:
    def __init__(self, dependencies: dict[str, set[str]]) -> None:
        self._deps = dependencies
        reverse: dict[str, set[str]] = {}
        for source, deps in dependencies.items():
            reverse.setdefault(source, set())
            for dep in deps:
                reverse.setdefault(dep, set()).add(source)
        self._reverse = reverse

    def get_direct_dependencies(self, path: str) -> set[str]:
        return set(self._deps.get(path, set()))

    def get_reverse_dependencies(self, path: str) -> set[str]:
        return set(self._reverse.get(path, set()))

    @property
    def dependencies(self) -> dict[str, set[str]]:
        return {k: set(v) for k, v in self._deps.items()}

    @property
    def reverse_dependencies(self) -> dict[str, set[str]]:
        return {k: set(v) for k, v in self._reverse.items()}


def _module_to_possible_paths(module: str, repo_kind: RepoKind) -> list[str]:
    parts = module.split(".") if module else []
    if not parts:
        return []

    candidates: list[str] = []
    if repo_kind == "meridian":
        if parts[0] == "meridian":
            rel = Path(*parts)
            candidates.append((rel.with_suffix(".py")).as_posix())
            candidates.append((rel / "__init__.py").as_posix())
        elif parts[0] == "scenarioplanner":
            rel = Path(*parts)
            candidates.append((rel.with_suffix(".py")).as_posix())
            candidates.append((rel / "__init__.py").as_posix())
        elif module == "schema":
            candidates.append("schema.py")
    else:
        if parts[0] == "meridian_aux":
            rel = Path("src", *parts)
            candidates.append((rel.with_suffix(".py")).as_posix())
            candidates.append((rel / "__init__.py").as_posix())
    return candidates


def _path_to_module(path: str, repo_kind: RepoKind) -> str | None:
    p = Path(path)
    if repo_kind == "meridian":
        if path == "schema.py":
            return "schema"
        if p.parts and p.parts[0] in {"meridian", "scenarioplanner"} and p.suffix == ".py":
            no_suffix = p.with_suffix("")
            if no_suffix.name == "__init__":
                return ".".join(no_suffix.parts[:-1])
            return ".".join(no_suffix.parts)
        return None

    if len(p.parts) >= 3 and p.parts[0] == "src" and p.parts[1] == "meridian_aux" and p.suffix == ".py":
        no_suffix = p.with_suffix("")
        if no_suffix.name == "__init__":
            return ".".join(no_suffix.parts[1:-1])
        return ".".join(no_suffix.parts[1:])
    return None


def resolve_import_to_path(
    import_name: str,
    repo_kind: RepoKind,
    available_paths: set[str] | None = None,
) -> str | None:
    for candidate in _module_to_possible_paths(import_name, repo_kind):
        if available_paths is None or candidate in available_paths:
            return candidate
    return None


def _resolve_relative_module(module: str | None, level: int, current_path: str, repo_kind: RepoKind) -> str | None:
    current_module = _path_to_module(current_path, repo_kind)
    if not current_module:
        return None

    package_parts = current_module.split(".")[:-1]
    if level > len(package_parts) + 1:
        return None

    up = level - 1
    base_parts = package_parts[: len(package_parts) - up]
    if module:
        base_parts.extend(module.split("."))
    if not base_parts:
        return None
    return ".".join(base_parts)


def _extract_import_dependencies(source: str, current_path: str, repo_kind: RepoKind, available_paths: set[str]) -> set[str]:
    tree = ast.parse(source)
    deps: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = resolve_import_to_path(alias.name, repo_kind, available_paths)
                if resolved:
                    deps.add(resolved)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                base = _resolve_relative_module(node.module, node.level, current_path, repo_kind)
            else:
                base = node.module
            if not base:
                continue

            base_resolved = resolve_import_to_path(base, repo_kind, available_paths)
            if base_resolved:
                deps.add(base_resolved)

            for alias in node.names:
                if alias.name == "*":
                    continue
                candidate_module = f"{base}.{alias.name}"
                candidate = resolve_import_to_path(candidate_module, repo_kind, available_paths)
                if candidate:
                    deps.add(candidate)

    deps.discard(current_path)
    return deps


def build_import_graph(repo_root: Path, repo_kind: RepoKind) -> ImportGraph:
    files = sorted(path for path in repo_root.rglob("*.py") if path.is_file())
    normalized_paths: set[str] = {path.relative_to(repo_root).as_posix() for path in files}

    dependencies: dict[str, set[str]] = {}
    for file_path in files:
        rel = file_path.relative_to(repo_root).as_posix()
        source = file_path.read_text(encoding="utf-8")
        dependencies[rel] = _extract_import_dependencies(
            source=source,
            current_path=rel,
            repo_kind=repo_kind,
            available_paths=normalized_paths,
        )

    return ImportGraph(dependencies)
