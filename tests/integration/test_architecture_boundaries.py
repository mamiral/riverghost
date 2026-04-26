"""Architecture regression tests for production-only import boundaries."""

import ast
import os
import sys
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python"))


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_ROOT = PROJECT_ROOT / "python" / "hopilot"


def _iter_python_files() -> list[Path]:
    return [
        path
        for path in PRODUCTION_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def _find_prototyping_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "prototyping" or alias.name.startswith("prototyping."):
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "prototyping" or module.startswith("prototyping."):
                violations.append(f"from {module} import ...")

    return violations


def test_production_code_does_not_import_prototyping_modules() -> None:
    violations: list[str] = []

    for path in _iter_python_files():
        imports = _find_prototyping_imports(path)
        violations.extend(f"{path.relative_to(PROJECT_ROOT)}: {value}" for value in imports)

    assert not violations, "Production code must not import from prototyping/:\n" + "\n".join(violations)