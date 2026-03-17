"""
Simulation model for poker analysis database.

Represents individual Monte Carlo simulation runs with metadata and parameters.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.sqlite import JSON

from hopilot.models.base import BaseModel


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
    parameters = Column(JSON, nullable=False)

    def __init__(self, **kwargs):
        """Initialize simulation with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate simulation data."""
        if not self.name or not self.name.strip():
            raise ValueError("Simulation name cannot be empty")

        if not self.parameters:
            raise ValueError("Simulation parameters cannot be empty")

        # Validate required parameter fields
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