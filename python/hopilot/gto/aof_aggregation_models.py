from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hopilot.gto.aof_scenario_cache_models import Base, utc_now


class ScenarioModel(Base):
    __tablename__ = "aof_aggregation_scenario"

    scenario_key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    position: Mapped[str] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=True)
    opponents: Mapped[int] = mapped_column(Integer, nullable=True)
    pot: Mapped[float] = mapped_column(Float, nullable=True)
    bet: Mapped[float] = mapped_column(Float, nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    runs: Mapped[list["RunModel"]] = relationship("RunModel", back_populates="scenario")


class RunModel(Base):
    __tablename__ = "aof_aggregation_run"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_key: Mapped[str] = mapped_column(
        String(64), ForeignKey("aof_aggregation_scenario.scenario_key"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    sim_count: Mapped[int] = mapped_column(Integer, nullable=False)  # Total simulations in this run
    combo_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout: Mapped[float] = mapped_column(Float, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)

    scenario: Mapped[ScenarioModel] = relationship("ScenarioModel", back_populates="runs")
    outcomes: Mapped[list["SimulationOutcomeModel"]] = relationship("SimulationOutcomeModel", back_populates="run")


class SimulationOutcomeModel(Base):
    """Stores individual simulation outcomes for aggregation."""
    __tablename__ = "aof_simulation_outcomes"

    outcome_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("aof_aggregation_run.run_id"), nullable=False, index=True
    )
    hero_hand: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # treys format
    villain_hand: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # treys format
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)  # 'WIN', 'LOSS', 'TIE'
    hero_equity: Mapped[float] = mapped_column(Float, nullable=False)  # 1.0 for win, 0.0 for loss, 0.5 for tie
    ev_chips: Mapped[float] = mapped_column(Float, nullable=False)  # EV in chips for this simulation
    board_cards: Mapped[str] = mapped_column(String(64), nullable=True)  # Optional: final board if needed

    run: Mapped[RunModel] = relationship("RunModel", back_populates="outcomes")