"""Unit tests for PrecomputeJobPersistenceService."""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.precompute_job_persistence import PrecomputeJobPersistenceService


def test_create_job_session_forwards_to_repository() -> None:
    repository = MagicMock()
    repository.create_precompute_job_session.return_value = 42
    service = PrecomputeJobPersistenceService(repository)

    result = service.create_job_session(scenario_fingerprint="abc123", requested_scenarios=5)

    repository.create_precompute_job_session.assert_called_once_with(
        scenario_fingerprint="abc123",
        requested_scenarios=5,
    )
    assert result == 42


def test_create_scenario_link_forwards_to_repository() -> None:
    repository = MagicMock()
    repository.create_scenario_run_link.return_value = 13
    service = PrecomputeJobPersistenceService(repository)

    result = service.create_scenario_link(
        job_session_id=1,
        scenario_index=0,
        scenario_key="UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
        scenario_contract={"selected_position": "UTG"},
        status="PENDING",
    )

    repository.create_scenario_run_link.assert_called_once_with(
        job_session_id=1,
        scenario_index=0,
        scenario_key="UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
        scenario_contract={"selected_position": "UTG"},
        status="PENDING",
    )
    assert result == 13


def test_mark_link_running_updates_status() -> None:
    repository = MagicMock()
    service = PrecomputeJobPersistenceService(repository)

    service.mark_link_running(7)

    repository.update_scenario_run_link.assert_called_once_with(7, status="RUNNING")


def test_mark_link_completed_updates_ids() -> None:
    repository = MagicMock()
    service = PrecomputeJobPersistenceService(repository)

    service.mark_link_completed(7, simulation_id=100, matrix_id=200)

    repository.update_scenario_run_link.assert_called_once_with(
        7,
        status="COMPLETED",
        simulation_id=100,
        matrix_id=200,
    )


def test_mark_link_failed_records_failure_diagnostics() -> None:
    repository = MagicMock()
    service = PrecomputeJobPersistenceService(repository)

    service.mark_link_failed(7, failure_boundary="solver_write", failure_reason="timeout")

    repository.update_scenario_run_link.assert_called_once_with(
        7,
        status="FAILED",
        failure_boundary="solver_write",
        failure_reason="timeout",
    )


def test_finalize_job_sets_terminal_state_completed() -> None:
    repository = MagicMock()
    service = PrecomputeJobPersistenceService(repository)

    service.finalize_job(1, completed_scenarios=3, failed_scenarios=0, canceled=False)

    repository.update_precompute_job_session.assert_called_once()
    kwargs = repository.update_precompute_job_session.call_args.kwargs
    assert kwargs["run_state"] == "COMPLETED"
    assert kwargs["completed_scenarios"] == 3
    assert kwargs["failed_scenarios"] == 0


def test_finalize_job_sets_terminal_state_failed() -> None:
    repository = MagicMock()
    service = PrecomputeJobPersistenceService(repository)

    service.finalize_job(1, completed_scenarios=2, failed_scenarios=1, canceled=False)

    kwargs = repository.update_precompute_job_session.call_args.kwargs
    assert kwargs["run_state"] == "FAILED"


def test_finalize_job_sets_terminal_state_canceled() -> None:
    repository = MagicMock()
    service = PrecomputeJobPersistenceService(repository)

    service.finalize_job(1, completed_scenarios=2, failed_scenarios=1, canceled=True)

    kwargs = repository.update_precompute_job_session.call_args.kwargs
    assert kwargs["run_state"] == "CANCELED"
