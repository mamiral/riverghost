import os
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile, RunnerPhase, MatrixSweepAggregationError
from hopilot.gto.matrix_sweep_contract import MatrixSweepContractError


def test_run_delegates_to_matrix_sweep_service_and_persists_scenario_link() -> None:
    provider = MagicMock()
    provider._build_context = MagicMock(return_value={
        "position": "UTG",
        "metric": "EV",
        "action": "ALL_IN",
        "position_actions": {"UTG": "ALL_IN", "BB": "FOLD", "SB": "FOLD", "BTN": "FOLD"},
        "pot_size": 20.0,
        "bet_amount": 10.0,
        "strict_current_action": False,
        "game_type": "nlhe",
    })

    runner = AoFPrecomputeRunner(provider=provider, database_url="sqlite:///:memory:")
    runner._execute_matrix_sweep = MagicMock(return_value={
        "simulation_id": 1,
        "matrix_id": 1,
        "raw_game_states_written": 0,
        "raw_players_written": 0,
        "matrix_cells_written": 169,
        "aggregated_metrics_written": 169,
        "failed_combinations": 0,
        "unmapped_hero_records": 0,
        "status": "aggregated",
    })

    profile = PrecomputeProfile(
        positions=("UTG",),
        metrics=("EV",),
        strict_modes=(False,),
        simulations_per_cell=1,
    )

    result = runner.run(profile=profile, max_scenarios=1)

    assert result == 0
    runner._execute_matrix_sweep.assert_called_once()
    provider._build_context.assert_called_once()
    assert runner.last_job_session_id is not None and runner.last_job_session_id > 0

    with runner.database_repository.connection.session_scope() as session:
        job_count = session.execute(text("SELECT COUNT(*) FROM precompute_job_sessions")).scalar()
        assert job_count == 1

        link_row = session.execute(
            text("SELECT status, simulation_id, matrix_id FROM scenario_run_links")
        ).first()
        assert link_row is not None
        assert link_row[0] == "COMPLETED"
        assert link_row[1] == 1
        assert link_row[2] == 1


def test_scenario_failure_boundaries_are_classified_and_persisted() -> None:
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

    runner = AoFPrecomputeRunner(provider=provider, database_url="sqlite:///:memory:")
    runner._execute_matrix_sweep = MagicMock(side_effect=[
        {"simulation_id": 1, "matrix_id": 1, "raw_game_states_written": 0, "raw_players_written": 0, "matrix_cells_written": 169, "aggregated_metrics_written": 169, "failed_combinations": 0, "unmapped_hero_records": 0, "status": "aggregated"},
        MatrixSweepContractError("scenario invalid"),
    ])

    profile = PrecomputeProfile(
        positions=("UTG", "BTN"),
        metrics=("EV",),
        strict_modes=(False,),
        simulations_per_cell=1,
    )

    result = runner.run(profile=profile, max_scenarios=2)

    assert result == 0
    assert runner._execute_matrix_sweep.call_count == 2

    with runner.database_repository.connection.session_scope() as session:
        links = session.execute(text("SELECT status, failure_boundary, failure_reason FROM scenario_run_links ORDER BY scenario_index")).fetchall()
        assert len(links) == 2
        assert links[0][0] == "COMPLETED"
        assert links[0][1] is None
        assert links[1][0] == "FAILED"
        assert links[1][1] == "orchestration"
        assert "scenario invalid" in links[1][2]


def test_failed_scenarios_do_not_retry() -> None:
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

    runner = AoFPrecomputeRunner(provider=provider, database_url="sqlite:///:memory:")
    runner._execute_matrix_sweep = MagicMock(side_effect=MatrixSweepContractError("validation failed"))

    profile = PrecomputeProfile(
        positions=("UTG",),
        metrics=("EV",),
        strict_modes=(False,),
        simulations_per_cell=1,
    )

    result = runner.run(profile=profile, max_scenarios=1)

    assert result == 0
    runner._execute_matrix_sweep.assert_called_once()
    with runner.database_repository.connection.session_scope() as session:
        failed_links = session.execute(text("SELECT COUNT(*) FROM scenario_run_links WHERE status = 'FAILED' ")).scalar()
        assert failed_links == 1


def test_aggregation_failures_are_classified_as_aggregation_boundary() -> None:
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

    runner = AoFPrecomputeRunner(provider=provider, database_url="sqlite:///:memory:")
    runner._execute_matrix_sweep = MagicMock(side_effect=MatrixSweepAggregationError("aggregation failed"))

    profile = PrecomputeProfile(
        positions=("UTG",),
        metrics=("EV",),
        strict_modes=(False,),
        simulations_per_cell=1,
    )

    result = runner.run(profile=profile, max_scenarios=1)

    assert result == 0
    runner._execute_matrix_sweep.assert_called_once()
    with runner.database_repository.connection.session_scope() as session:
        failed_links = session.execute(
            text("SELECT status, failure_boundary, failure_reason FROM scenario_run_links")
        ).fetchall()
        assert len(failed_links) == 1
        assert failed_links[0][0] == "FAILED"
        assert failed_links[0][1] == "aggregation"
        assert "aggregation failed" in failed_links[0][2]


def test_running_job_progress_reflects_pending_scenario_state() -> None:
    runner = AoFPrecomputeRunner(database_url="sqlite:///:memory:")
    job_session_id = runner.database_repository.create_precompute_job_session(
        scenario_fingerprint="test",
        requested_scenarios=2,
    )

    scenario_key = "UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False"
    runner.database_repository.create_scenario_run_link(
        job_session_id=job_session_id,
        scenario_index=0,
        scenario_key=scenario_key,
        scenario_contract={},
        status="RUNNING",
    )

    progress = runner.get_job_progress(job_session_id)

    assert progress["run_state"] == "RUNNING"
    assert progress["total_scenarios"] == 2
    assert progress["completed_scenarios"] == 0
    assert progress["failure_count"] == 0
    assert progress["phase"] == RunnerPhase.SOLVER_WRITE.value
    assert progress["active_scenario_key"] == scenario_key
    assert progress["completed_scenarios"] + progress["failure_count"] <= progress["total_scenarios"]


def test_run_updates_job_progress_after_successful_scenario() -> None:
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

    runner = AoFPrecomputeRunner(provider=provider, database_url="sqlite:///:memory:")
    runner._execute_matrix_sweep = MagicMock(return_value={
        "simulation_id": 1,
        "matrix_id": 1,
        "raw_game_states_written": 0,
        "raw_players_written": 0,
        "matrix_cells_written": 169,
        "aggregated_metrics_written": 169,
        "failed_combinations": 0,
        "unmapped_hero_records": 0,
        "status": "aggregated",
    })

    profile = PrecomputeProfile(
        positions=("UTG",),
        metrics=("EV",),
        strict_modes=(False,),
        simulations_per_cell=1,
    )

    result = runner.run(profile=profile, max_scenarios=1)

    assert result == 0
    progress = runner.get_job_progress(runner.last_job_session_id)

    assert progress["run_state"] == "COMPLETED"
    assert progress["completed_scenarios"] == 1
    assert progress["total_scenarios"] == 1
    assert progress["failure_count"] == 0
    assert progress["active_scenario_key"] is None
    assert progress["phase"] == "orchestration"
    assert isinstance(progress["elapsed_seconds"], float)
