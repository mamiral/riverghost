from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint

from hopilot.models.base import BaseModel


class ScenarioRunLink(BaseModel):
    __tablename__ = "scenario_run_links"
    __table_args__ = (
        UniqueConstraint("job_session_id", "scenario_index", name="uq_scenario_run_link"),
    )

    job_session_id = Column(Integer, ForeignKey("precompute_job_sessions.id"), nullable=False, index=True)
    scenario_index = Column(Integer, nullable=False)
    scenario_key = Column(String(1024), nullable=False)
    scenario_contract = Column(JSON, nullable=False)
    simulation_id = Column(Integer, nullable=True)
    matrix_id = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, index=True)
    failure_boundary = Column(String(32), nullable=True)
    failure_reason = Column(String(2048), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def _validate(self) -> None:
        if not self.scenario_key or not self.scenario_key.strip():
            raise ValueError("scenario_key cannot be empty")
        if self.status not in {"PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELED"}:
            raise ValueError(f"Invalid status: {self.status}")
        if self.status == "COMPLETED":
            if self.simulation_id is None or self.matrix_id is None:
                raise ValueError("Completed scenario run links require simulation_id and matrix_id")
        if self.status == "FAILED":
            if not self.failure_boundary or not self.failure_boundary.strip():
                raise ValueError("Failed scenario run links require failure_boundary")
            if not self.failure_reason or not self.failure_reason.strip():
                raise ValueError("Failed scenario run links require failure_reason")
