from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


class ScenarioPayloadModel(Base):
    __tablename__ = "aof_scenario_payload"

    scenario_key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    context_json: Mapped[str] = mapped_column(Text, nullable=False)
    cells_json: Mapped[str] = mapped_column(Text, nullable=False)
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    metadata_row: Mapped["CacheMetadataModel"] = relationship(
        "CacheMetadataModel",
        back_populates="payload",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CacheMetadataModel(Base):
    __tablename__ = "aof_cache_metadata"

    scenario_key_hash: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("aof_scenario_payload.scenario_key_hash", ondelete="CASCADE"),
        primary_key=True,
    )
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    solver_signature: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_signature: Mapped[str] = mapped_column(String(128), nullable=False)
    runtime_signature: Mapped[str] = mapped_column(String(128), nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stale_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    payload: Mapped[ScenarioPayloadModel] = relationship("ScenarioPayloadModel", back_populates="metadata_row")


class OfflinePrecomputeRunModel(Base):
    __tablename__ = "aof_precompute_run"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_scenarios: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_scenarios: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_scenarios: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resume_cursor: Mapped[int | None] = mapped_column(Integer, nullable=True)

    write_results: Mapped[list["ScenarioWriteResultModel"]] = relationship(
        "ScenarioWriteResultModel",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class ScenarioWriteResultModel(Base):
    __tablename__ = "aof_precompute_write_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("aof_precompute_run.run_id", ondelete="SET NULL"), nullable=True)
    scenario_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run: Mapped[OfflinePrecomputeRunModel | None] = relationship("OfflinePrecomputeRunModel", back_populates="write_results")
