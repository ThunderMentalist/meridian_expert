import ast
from pathlib import Path


def signatures(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out=[]
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(n.name)
    return out
