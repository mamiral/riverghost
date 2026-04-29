"""Unit tests for precompute reconciliation and deterministic job state repair."""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.precompute_job_persistence import PrecomputeJobPersistenceService
from hopilot.gto.precompute_reconciliation import reconcile_job_tracking, PrecomputeJobReconciliationResult


class TestPrecomputeReconciliation:
    def test_reconcile_job_tracking_returns_counts_and_final_state(self):
        job_session = MagicMock(
            id=1,
            requested_scenarios=2,
            completed_scenarios=0,
            failed_scenarios=0,
        )
        links = [
            MagicMock(status="COMPLETED"),
            MagicMock(status="FAILED"),
        ]

        result = reconcile_job_tracking(job_session, links, canceled=False)

        assert isinstance(result, PrecomputeJobReconciliationResult)
        assert result.completed_scenarios == 1
        assert result.failed_scenarios == 1
        assert result.pending_scenarios == 0
        assert result.running_scenarios == 0
        assert result.final_run_state == "FAILED"
        assert result.corrected is True

    def test_reconcile_job_tracking_preserves_canceled_state(self):
        job_session = MagicMock(
            id=2,
            requested_scenarios=3,
            completed_scenarios=1,
            failed_scenarios=1,
        )
        links = [
            MagicMock(status="COMPLETED"),
            MagicMock(status="RUNNING"),
            MagicMock(status="PENDING"),
        ]

        result = reconcile_job_tracking(job_session, links, canceled=True)

        assert result.final_run_state == "CANCELED"
        assert result.canceled is True
        assert result.pending_scenarios == 1
        assert result.running_scenarios == 1

    def test_reconcile_job_tracking_is_deterministic_for_identical_inputs(self):
        job_session = MagicMock(
            id=3,
            requested_scenarios=2,
            completed_scenarios=0,
            failed_scenarios=0,
        )
        links = [
            MagicMock(status="COMPLETED"),
            MagicMock(status="FAILED"),
        ]

        first = reconcile_job_tracking(job_session, links, canceled=False)
        second = reconcile_job_tracking(job_session, links, canceled=False)

        assert first == second
        assert first.completed_scenarios == 1
        assert first.failed_scenarios == 1

    def test_reconcile_job_session_updates_session_counts(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'jobs.db'}"
        repository = DatabaseRepository(database_url=db_url)
        persistence = PrecomputeJobPersistenceService(repository)

        job_session_id = repository.create_precompute_job_session(
            scenario_fingerprint="test-fingerprint",
            requested_scenarios=2,
        )

        scenario_link_id = repository.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=0,
            scenario_key="UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
            scenario_contract={"selected_position": "UTG"},
            status="PENDING",
        )
        repository.update_scenario_run_link(
            scenario_link_id,
            status="COMPLETED",
            simulation_id=1,
            matrix_id=2,
        )
        failed_link_id = repository.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=1,
            scenario_key="BTN:ALL_IN-FOLD-FOLD-FOLD:EV:False",
            scenario_contract={"selected_position": "BTN"},
            status="PENDING",
        )
        repository.update_scenario_run_link(
            failed_link_id,
            status="FAILED",
            failure_boundary="solver_write",
            failure_reason="timeout",
        )

        result = persistence.reconcile_job_session(job_session_id, canceled=False)

        assert result.completed_scenarios == 1
        assert result.failed_scenarios == 1
        assert result.corrected is True

        session = repository.get_precompute_job_session(job_session_id)
        assert session.completed_scenarios == 1
        assert session.failed_scenarios == 1

    def test_reconcile_job_session_no_correction_when_counts_match(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'jobs.db'}"
        repository = DatabaseRepository(database_url=db_url)
        persistence = PrecomputeJobPersistenceService(repository)

        job_session_id = repository.create_precompute_job_session(
            scenario_fingerprint="test-fingerprint",
            requested_scenarios=1,
        )

        scenario_link_id = repository.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=0,
            scenario_key="UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
            scenario_contract={"selected_position": "UTG"},
            status="PENDING",
        )
        repository.update_scenario_run_link(
            scenario_link_id,
            status="COMPLETED",
            simulation_id=1,
            matrix_id=2,
        )

        # Manually match the persisted job session counts to the link counts
        repository.update_precompute_job_session(
            job_session_id,
            completed_scenarios=1,
            failed_scenarios=0,
        )

        result = persistence.reconcile_job_session(job_session_id, canceled=False)

        assert result.corrected is False
        session = repository.get_precompute_job_session(job_session_id)
        assert session.completed_scenarios == 1
        assert session.failed_scenarios == 0
