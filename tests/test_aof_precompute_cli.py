import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto import aof_precompute_cli as cli


def test_aof_precompute_cli_surfaces_boundary_diagnostics(monkeypatch, capsys):
    fake_runner = MagicMock()
    fake_runner.last_job_session_id = 123
    fake_runner.run.return_value = 0
    fake_runner.get_job_scenario_mappings.return_value = [
        {
            "scenario_index": 0,
            "scenario_key": "UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
            "status": "FAILED",
            "simulation_id": None,
            "matrix_id": None,
            "failure_boundary": "aggregation",
            "failure_reason": "aggregation failed",
        }
    ]

    fake_provider_module = MagicMock(PrecomputeProvider=MagicMock(return_value=MagicMock()))
    monkeypatch.setitem(sys.modules, "hopilot.gto.precompute_provider", fake_provider_module)
    monkeypatch.setattr(cli, "AoFPrecomputeRunner", MagicMock(return_value=fake_runner))
    monkeypatch.setattr(sys, "argv", ["aof_precompute_cli.py", "--database-url", "sqlite:///:memory:"])

    result = cli.main()
    captured = capsys.readouterr()

    assert result == 0
    assert "Precompute run finished. run_id=123" in captured.out
    assert "Scenario mappings:" in captured.out
    assert "failure_boundary=aggregation" in captured.out
    assert "failure_reason=aggregation failed" in captured.out
