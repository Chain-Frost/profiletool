"""Pure-Python tests for the local Pyright diagnostics summariser."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "pyright_triage.py"
    spec = importlib.util.spec_from_file_location("profiletool_pyright_triage", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_group_and_redact_diagnostic_paths() -> None:
    module = _module()
    data = {
        "generalDiagnostics": [
            {"severity": "error", "rule": "reportMissingImports", "file": r"C:\\project\\profiletool\\tools\\utils.py"},
            {"severity": "error", "rule": "reportUnknownVariableType", "file": "/tmp/profiletool/tools/utils.py"},
            {"severity": "error", "rule": "reportUnknownVariableType", "file": "/tmp/profiletool/tools/profilers.py"},
            {"severity": "warning", "rule": "reportUnknownVariableType", "file": "/tmp/profiletool/tools/profilers.py"},
        ],
        "summary": {"errorCount": 3},
    }
    summary = module.summarise(data)
    assert summary["collected_errors"] == 3
    assert summary["reported_errors"] == 3
    assert summary["by_rule"][0] == {"name": "reportUnknownVariableType", "count": 2}
    assert summary["by_file"][0] == {"name": "tools/utils.py", "count": 2}
    assert summary["unresolved_imports_by_file"] == [{"name": "tools/utils.py", "count": 1}]
    assert "C:\\project" not in str(summary)


def test_invalid_json_shape_is_rejected() -> None:
    module = _module()
    with pytest.raises(ValueError, match="generalDiagnostics"):
        module.summarise({})
