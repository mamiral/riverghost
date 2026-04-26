from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from hopilot.models.base import BaseModel


class PrecomputeJobSession(BaseModel):
    __tablename__ = "precompute_job_sessions"

    scenario_fingerprint = Column(String(1024), nullable=False)
    run_state = Column(String(32), nullable=False, index=True)
    requested_scenarios = Column(Integer, nullable=False, default=0)
    completed_scenarios = Column(Integer, nullable=False, default=0)
    failed_scenarios = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    elapsed_active_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def _validate(self) -> None:
        if not self.scenario_fingerprint or not self.scenario_fingerprint.strip():
            raise ValueError("scenario_fingerprint cannot be empty")
        if self.run_state not in {
            "IDLE",
            "RUNNING",
            "PAUSED",
            "STOPPING",
            "COMPLETED",
            "FAILED",
            "CANCELED",
        }:
            raise ValueError(f"Invalid run_state: {self.run_state}")
        if self.requested_scenarios < 0:
            raise ValueError("requested_scenarios must be >= 0")
        if self.completed_scenarios < 0:
            raise ValueError("completed_scenarios must be >= 0")
        if self.failed_scenarios < 0:
            raise ValueError("failed_scenarios must be >= 0")
        if self.completed_scenarios + self.failed_scenarios > self.requested_scenarios:
            raise ValueError("completed_scenarios + failed_scenarios cannot exceed requested_scenarios")
        if self.elapsed_active_ms < 0:
            raise ValueError("elapsed_active_ms must be >= 0")
