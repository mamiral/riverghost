from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from hopilot.database import DatabaseConnection
from hopilot.gto.repository_errors import PrecomputeJobRepositoryError
from hopilot.gto.repository_interfaces import PrecomputeJobRepositoryInterface
from hopilot.logging_config import get_logger
from hopilot.models import PrecomputeJobSession, ScenarioRunLink


logger = get_logger(__name__)


class PrecomputeJobRepository(PrecomputeJobRepositoryInterface):
    def __init__(self, db_connection: DatabaseConnection, session: Optional[Session] = None):
        self.db_connection = db_connection
        self.session = session

    @contextmanager
    def _session_scope(self) -> Session:
        if self.session is not None:
            yield self.session
            return
        with self.db_connection.session_scope() as session:
            yield session

    def _raise_domain_error(self, operation: str, exc: Exception) -> None:
        logger.error("PrecomputeJobRepository.%s failed: %s", operation, exc, exc_info=True)
        raise PrecomputeJobRepositoryError(f"PrecomputeJobRepository {operation} failed") from exc

    def create_precompute_job_session(self, scenario_fingerprint: str, requested_scenarios: int) -> int:
        try:
            with self._session_scope() as session:
                job = PrecomputeJobSession(
                    scenario_fingerprint=scenario_fingerprint,
                    run_state="RUNNING",
                    requested_scenarios=requested_scenarios,
                    completed_scenarios=0,
                    failed_scenarios=0,
                    elapsed_active_ms=0,
                )
                session.add(job)
                session.flush()
                return job.id
        except Exception as exc:
            self._raise_domain_error("create_precompute_job_session", exc)

    def update_precompute_job_session(self, job_session_id: int, **updates: Any) -> None:
        try:
            with self._session_scope() as session:
                job = session.get(PrecomputeJobSession, job_session_id)
                if job is None:
                    raise ValueError(f"PrecomputeJobSession with ID {job_session_id} not found")
                for key, value in updates.items():
                    setattr(job, key, value)
                session.flush()
        except ValueError:
            raise
        except Exception as exc:
            self._raise_domain_error("update_precompute_job_session", exc)

    def get_precompute_job_session(self, job_session_id: int) -> Optional[PrecomputeJobSession]:
        with self._session_scope() as session:
            return session.get(PrecomputeJobSession, job_session_id)

    def create_scenario_run_link(
        self,
        job_session_id: int,
        scenario_index: int,
        scenario_key: str,
        scenario_contract: Dict[str, Any],
        status: str = "PENDING",
    ) -> int:
        try:
            with self._session_scope() as session:
                link = ScenarioRunLink(
                    job_session_id=job_session_id,
                    scenario_index=scenario_index,
                    scenario_key=scenario_key,
                    scenario_contract=scenario_contract,
                    status=status,
                )
                session.add(link)
                session.flush()
                return link.id
        except Exception as exc:
            self._raise_domain_error("create_scenario_run_link", exc)

    def update_scenario_run_link(self, scenario_link_id: int, **updates: Any) -> None:
        try:
            with self._session_scope() as session:
                link = session.get(ScenarioRunLink, scenario_link_id)
                if link is None:
                    raise ValueError(f"ScenarioRunLink with ID {scenario_link_id} not found")
                for key, value in updates.items():
                    setattr(link, key, value)
                session.flush()
        except ValueError:
            raise
        except Exception as exc:
            self._raise_domain_error("update_scenario_run_link", exc)

    def get_scenario_run_links_for_job(self, job_session_id: int) -> List[ScenarioRunLink]:
        with self._session_scope() as session:
            return (
                session.query(ScenarioRunLink)
                .filter(ScenarioRunLink.job_session_id == job_session_id)
                .order_by(ScenarioRunLink.scenario_index.asc())
                .all()
            )

    def get_scenario_run_link(self, scenario_link_id: int) -> Optional[ScenarioRunLink]:
        with self._session_scope() as session:
            return session.get(ScenarioRunLink, scenario_link_id)
