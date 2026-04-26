"""Regression tests for matrix sweep precompute and legacy solver boundaries."""

import os
import sys
from unittest.mock import MagicMock

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from sqlalchemy import text

from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.database.persistence import MockPersistenceStrategy
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile
from hopilot.poker_analyzer import PokerAnalyzer
from tests.integration.matrix_sweep_db_utils import build_matrix_sweep_contract, create_matrix_sweep_db_fixture


def test_precompute_runner_routes_matrix_sweep_through_matrix_sweep_service() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    runner = None
    try:
        runner = AoFPrecomputeRunner(database_url=fixture.database_url)

        result = runner.run_matrix_sweep(build_matrix_sweep_contract(selected_position="UTG"))

        assert result["status"] == "aggregated"
        assert result["matrix_cells_written"] == 169
        assert result["aggregated_metrics_written"] == 169
    finally:
        if runner is not None:
            runner.database_repository.connection.close()
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


def test_precompute_runner_run_delegates_to_matrix_sweep_and_persists_job_links() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    runner = None
    try:
        provider = MagicMock()
        provider._build_context = MagicMock(return_value={
            "position": "UTG",
            "metric": "EV",
            "action": "ALL_IN",
            "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "strict_current_action": False,
            "game_type": "nlhe",
        })
        provider.get_matrix_payload = MagicMock()

        runner = AoFPrecomputeRunner(provider=provider, database_url=fixture.database_url)
        runner._execute_matrix_sweep = MagicMock(return_value={
            "simulation_id": 1,
            "matrix_id": 1,
            "raw_game_states_written": 0,
            "raw_players_written": 0,
            "matrix_cells_written": 169,
            "aggregated_metrics_written": 169,
            "failed_combinations": 0,
            "unmapped_hero_records": 0,
            "status": "completed",
        })

        profile = PrecomputeProfile(
            positions=("UTG",),
            metrics=("EV",),
            strict_modes=(True,),
            simulations_per_cell=1,
        )

        result = runner.run(profile=profile, max_scenarios=1)

        assert result == 0
        assert runner.last_job_session_id > 0
        provider.get_matrix_payload.assert_not_called()
        runner._execute_matrix_sweep.assert_called_once()

        with fixture.session_context() as session:
            job_count = session.execute(text("SELECT COUNT(*) FROM precompute_job_sessions")).scalar()
            assert job_count == 1

            link_row = session.execute(text("SELECT status, simulation_id, matrix_id FROM scenario_run_links")).first()
            assert link_row is not None
            assert link_row[0] == "COMPLETED"
            assert link_row[1] == 1
            assert link_row[2] == 1
    finally:
        if runner is not None:
            runner.database_repository.connection.close()
        fixture.cleanup()
