"""Product copy must not use em dash in user-facing strings."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOTS = (ROOT / "ui", ROOT / "core")


def _is_docstring(node: ast.Constant, parents: dict[ast.AST, ast.AST]) -> bool:
    if not isinstance(node.value, str):
        return False
    parent = parents.get(node)
    if not isinstance(parent, ast.Expr):
        return False
    grandparent = parents.get(parent)
    if not isinstance(grandparent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return False
    return bool(grandparent.body) and grandparent.body[0] is parent


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    parents = _parent_map(tree)
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if "—" not in node.value:
            continue
        if _is_docstring(node, parents):
            continue
        hits.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    return hits


def test_no_em_dash_in_user_facing_strings():
    violations: list[str] = []
    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            violations.extend(_violations(path))
    assert not violations, "Em dash in user-facing copy:\n" + "\n".join(violations)