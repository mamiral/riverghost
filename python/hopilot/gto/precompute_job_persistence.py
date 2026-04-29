from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hopilot.gto.database_repository import DatabaseRepository


class PrecomputeJobPersistenceService:
    def __init__(self, database_repository: DatabaseRepository, logger: Any | None = None):
        self.database_repository = database_repository
        self.logger = logger

    def create_job_session(self, *, scenario_fingerprint: str, requested_scenarios: int) -> int:
        return self.database_repository.create_precompute_job_session(
            scenario_fingerprint=scenario_fingerprint,
            requested_scenarios=requested_scenarios,
        )

    def update_job_progress(
        self,
        job_session_id: int,
        *,
        completed_scenarios: int,
        failed_scenarios: int,
    ) -> None:
        self.database_repository.update_precompute_job_session(
            job_session_id,
            completed_scenarios=completed_scenarios,
            failed_scenarios=failed_scenarios,
        )

    def create_scenario_link(
        self,
        *,
        job_session_id: int,
        scenario_index: int,
        scenario_key: str,
        scenario_contract: dict[str, Any],
        status: str = "PENDING",
    ) -> int:
        return self.database_repository.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=scenario_index,
            scenario_key=scenario_key,
            scenario_contract=scenario_contract,
            status=status,
        )

    def mark_link_running(self, scenario_link_id: int) -> None:
        self.database_repository.update_scenario_run_link(
            scenario_link_id,
            status="RUNNING",
        )

    def mark_link_completed(
        self,
        scenario_link_id: int,
        *,
        simulation_id: int,
        matrix_id: int,
    ) -> None:
        self.database_repository.update_scenario_run_link(
            scenario_link_id,
            status="COMPLETED",
            simulation_id=simulation_id,
            matrix_id=matrix_id,
        )

    def update_scenario_contract(self, scenario_link_id: int, scenario_contract: dict[str, Any]) -> None:
        self.database_repository.update_scenario_run_link(
            scenario_link_id,
            scenario_contract=scenario_contract,
        )

    def get_job_session(self, job_session_id: int) -> Any:
        return self.database_repository.get_precompute_job_session(job_session_id)

    def mark_link_failed(
        self,
        scenario_link_id: int,
        *,
        failure_boundary: str,
        failure_reason: str,
    ) -> None:
        self.database_repository.update_scenario_run_link(
            scenario_link_id,
            status="FAILED",
            failure_boundary=failure_boundary,
            failure_reason=failure_reason,
        )

    def finalize_job(
        self,
        job_session_id: int,
        *,
        completed_scenarios: int,
        failed_scenarios: int,
        canceled: bool = False,
    ) -> None:
        final_state = "CANCELED" if canceled else ("FAILED" if failed_scenarios > 0 else "COMPLETED")
        self.database_repository.update_precompute_job_session(
            job_session_id,
            run_state=final_state,
            completed_scenarios=completed_scenarios,
            failed_scenarios=failed_scenarios,
            finished_at=datetime.now(timezone.utc),
        )
