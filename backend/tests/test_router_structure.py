import ast
from pathlib import Path

import pytest

ROUTERS = Path(__file__).resolve().parents[1] / "app" / "api" / "v1"


def _router_trees() -> list[tuple[str, ast.Module]]:
    return [(path.name, ast.parse(path.read_text())) for path in sorted(ROUTERS.glob("*.py"))]


@pytest.mark.parametrize(("name", "tree"), _router_trees())
def test_router_module_has_no_exception_handling(name, tree):
    handlers = [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)]

    assert handlers == []


@pytest.mark.parametrize(("name", "tree"), _router_trees())
def test_router_module_has_no_isinstance_chains(name, tree):
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "isinstance"
    ]

    assert calls == []
