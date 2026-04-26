"""Regression tests for matrix sweep precompute and legacy solver boundaries."""

import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.database.persistence import MockPersistenceStrategy
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner
from hopilot.poker_analyzer import PokerAnalyzer
from tests.integration.matrix_sweep_db_utils import build_matrix_sweep_contract, create_matrix_sweep_db_fixture


def test_precompute_runner_routes_matrix_sweep_through_matrix_sweep_service() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        runner = AoFPrecomputeRunner(database_url=fixture.database_url)

        result = runner.run_matrix_sweep(build_matrix_sweep_contract(selected_position="UTG"))

        assert result["status"] == "completed"
        assert result["matrix_cells_written"] == 169
        assert result["aggregated_metrics_written"] == 169
    finally:
        fixture.cleanup()


def test_solver_rejects_legacy_matrix_cell_coupled_sweep_entrypoint() -> None:
    solver = AllInFoldGTOSolver(PokerAnalyzer(), MockPersistenceStrategy())

    with pytest.raises(ValueError, match="MatrixSweepService"):
        solver.evaluate_hand_key(
            hand_key="AA",
            num_opponents=1,
            pot_size=20.0,
            bet_amount=10.0,
            matrix_cell_id=1,
        )