"""Simulation model for poker analysis database."""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.mutable import MutableDict

from hopilot.models.base import BaseModel


MATRIX_SWEEP_REQUIRED_PARAMS = [
    "selected_position",
    "hero_action",
    "position_actions",
    "active_players",
    "num_opponents",
    "pot_size",
    "bet_amount",
    "matrix_size",
    "game_type",
    "run_kind",
]


class SimulationParameters(MutableDict):
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, str):
            value = json.loads(value)
        return super().coerce(key, value)


class Simulation(BaseModel):
    """
    Represents a poker simulation run.

    Stores metadata about simulation execution including parameters,
    timing, and configuration.
    """

    __tablename__ = "simulations"

    name = Column(String(255), unique=True, nullable=False, index=True)
    start_timestamp = Column(DateTime, nullable=False)
    end_timestamp = Column(DateTime, nullable=True)
    parameters = Column(SimulationParameters.as_mutable(JSON), nullable=False)

    def __init__(self, **kwargs):
        """Initialize simulation with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate simulation data."""
        if not self.name or not self.name.strip():
            raise ValueError("Simulation name cannot be empty")

        if not self.parameters:
            raise ValueError("Simulation parameters cannot be empty")

        if not isinstance(self.parameters, dict):
            raise ValueError("Simulation parameters must be a mapping")

        if self.parameters.get("run_kind") == "matrix_sweep":
            missing_params = [key for key in MATRIX_SWEEP_REQUIRED_PARAMS if key not in self.parameters]
            if missing_params:
                raise ValueError(f"Missing required matrix sweep parameters: {missing_params}")

            if "sims_per_combo" not in self.parameters and "num_simulations" not in self.parameters:
                raise ValueError("Matrix sweep parameters must include sims_per_combo or num_simulations")

            if self.parameters.get("matrix_size") != "13x13":
                raise ValueError("Matrix sweep simulations must use matrix_size='13x13'")

            raw_start = self.parameters.get("raw_game_state_id_start")
            raw_end = self.parameters.get("raw_game_state_id_end")
            if raw_start is not None and raw_end is not None and raw_start > raw_end:
                raise ValueError("raw_game_state_id_start cannot be greater than raw_game_state_id_end")
        else:
            required_params = ["num_simulations", "matrix_size", "game_type"]
            if not all(key in self.parameters for key in required_params):
                raise ValueError(f"Missing required parameters: {required_params}")

        if self.end_timestamp and self.start_timestamp > self.end_timestamp:
            raise ValueError("End timestamp cannot be before start timestamp")

    @property
    def duration(self) -> Optional[float]:
        """
        Get simulation duration in seconds.

        Returns:
            Duration in seconds, or None if not completed
        """
        if not self.end_timestamp:
            return None
        return (self.end_timestamp - self.start_timestamp).total_seconds()

    @property
    def is_completed(self) -> bool:
        """Check if simulation has completed."""
        return self.end_timestamp is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["duration"] = self.duration
        result["is_completed"] = self.is_completed
        return result

    def __repr__(self) -> str:
        """String representation."""
        status = "completed" if self.is_completed else "running"
        return f"<Simulation(id={self.id}, name='{self.name}', status={status})>"