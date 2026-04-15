from __future__ import annotations

import ast
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class SymbolSignature(BaseModel):
    name: str
    kind: Literal["function", "class", "method"]
    lineno: int
    end_lineno: int | None = None
    args: list[str] = Field(default_factory=list)


class ModuleSignature(BaseModel):
    path: str | None = None
    module_docstring: str | None = None
    top_level_imports: list[str] = Field(default_factory=list)
    symbols: list[SymbolSignature] = Field(default_factory=list)

    @property
    def symbol_spans(self) -> dict[str, tuple[int, int | None]]:
        return {symbol.name: (symbol.lineno, symbol.end_lineno) for symbol in self.symbols}


def _format_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    out: list[str] = []
    for arg in node.args.posonlyargs:
        out.append(arg.arg)
    for arg in node.args.args:
        out.append(arg.arg)
    if node.args.vararg:
        out.append(f"*{node.args.vararg.arg}")
    for arg in node.args.kwonlyargs:
        out.append(arg.arg)
    if node.args.kwarg:
        out.append(f"**{node.args.kwarg.arg}")
    return out


def extract_module_signature(source: str, path: str | None = None) -> ModuleSignature:
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree)

    imports: list[str] = []
    symbols: list[SymbolSignature] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            if len(node.names) == 1 and node.names[0].name == "*":
                imports.append(module)
            else:
                for alias in node.names:
                    imports.append(f"{module}:{alias.name}")
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                SymbolSignature(
                    name=node.name,
                    kind="class",
                    lineno=node.lineno,
                    end_lineno=node.end_lineno,
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        SymbolSignature(
                            name=f"{node.name}.{child.name}",
                            kind="method",
                            lineno=child.lineno,
                            end_lineno=child.end_lineno,
                            args=_format_args(child),
                        )
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                SymbolSignature(
                    name=node.name,
                    kind="function",
                    lineno=node.lineno,
                    end_lineno=node.end_lineno,
                    args=_format_args(node),
                )
            )

    return ModuleSignature(
        path=path,
        module_docstring=docstring,
        top_level_imports=imports,
        symbols=symbols,
    )


def extract_file_signature(path: Path) -> ModuleSignature:
    source = path.read_text(encoding="utf-8")
    return extract_module_signature(source=source, path=path.as_posix())


def signatures(path: Path) -> list[str]:
    module = extract_file_signature(path)
    return [symbol.name for symbol in module.symbols]
