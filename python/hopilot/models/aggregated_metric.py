"""
AggregatedMetric model for poker analysis database.

Represents computed statistics and metrics for each matrix cell.
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from hopilot.models.base import BaseModel


class AggregatedMetric(BaseModel):
    """
    Represents computed statistics for a matrix cell.

    Contains aggregated data from multiple simulations including
    equity calculations, jackpot statistics, and convergence metrics.
    """

    __tablename__ = "aggregated_metrics"
    __table_args__ = {"sqlite_autoincrement": True}

    cell_id = Column(Integer, ForeignKey("matrix_cells.id"), unique=True, nullable=False)
    equity = Column(Numeric(5, 4), nullable=True)  # Standard win probability (0.0000-1.0000)
    win_probability = Column(Numeric(5, 4), nullable=True)  # Alternative win probability metric
    ev = Column(Numeric(10, 4), nullable=True)  # Expected value calculation
    jackpot_adjusted_ev = Column(Numeric(10, 4), nullable=True)  # EV including jackpots
    jackpot_frequency = Column(Numeric(5, 4), nullable=True)  # Frequency of jackpots (0.0000-1.0000)
    avg_jackpot_payout = Column(Numeric(10, 2), nullable=True)  # Average jackpot payout amount
    sample_count = Column(Integer, nullable=True)  # Number of games/samples used to compute this cell
    convergence_status = Column(String(20), nullable=True)  # Convergence assessment
    last_updated = Column(String(27), nullable=False)  # ISO timestamp

    # Note: Relationship defined on MatrixCell side to avoid backref conflicts
    # matrix_cell = relationship("MatrixCell", backref="aggregated_metric")

    def __init__(self, **kwargs):
        """Initialize aggregated metric with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate aggregated metric data."""
        if not self.cell_id:
            raise ValueError("Cell ID is required")

        if not self.last_updated:
            raise ValueError("Last updated timestamp is required")

        # Validate equity range
        if self.equity is not None and not (0 <= self.equity <= 1):
            raise ValueError("Equity must be between 0 and 1")

        # Validate jackpot frequency range
        if self.jackpot_frequency is not None and not (0 <= self.jackpot_frequency <= 1):
            raise ValueError("Jackpot frequency must be between 0 and 1")

        if self.sample_count is not None and self.sample_count < 0:
            raise ValueError("Sample count cannot be negative")

        # Validate payout amounts
        if self.avg_jackpot_payout is not None and self.avg_jackpot_payout < 0:
            raise ValueError("Average jackpot payout cannot be negative")

    @property
    def equity_percentage(self) -> Optional[float]:
        """Get equity as a percentage (0-100)."""
        return float(self.equity * 100) if self.equity is not None else None

    @property
    def jackpot_frequency_percentage(self) -> Optional[float]:
        """Get jackpot frequency as a percentage (0-100)."""
        return float(self.jackpot_frequency * 100) if self.jackpot_frequency is not None else None

    @property
    def ev_improvement(self) -> Optional[Decimal]:
        """
        Calculate the improvement in EV due to jackpots.

        Returns:
            EV improvement amount, or None if data unavailable
        """
        if self.jackpot_adjusted_ev is not None and self.equity is not None:
            return self.jackpot_adjusted_ev - self.equity
        return None

    @property
    def is_converged(self) -> bool:
        """Check if this cell's metrics have converged."""
        if not self.convergence_status:
            return False
        return self.convergence_status.lower() in ['converged', 'stable', 'complete']

    @property
    def expected_jackpot_value(self) -> Optional[Decimal]:
        """
        Calculate expected value from jackpots.

        Returns:
            Expected jackpot value, or None if data unavailable
        """
        if self.jackpot_frequency is not None and self.avg_jackpot_payout is not None:
            return self.jackpot_frequency * self.avg_jackpot_payout
        return None

    def update_from_simulations(self, simulations_data: Dict[str, Any]) -> None:
        """
        Update metrics from simulation results.

        Args:
            simulations_data: Dictionary with simulation statistics
        """
        # Update equity
        if 'equity' in simulations_data:
            self.equity = Decimal(str(simulations_data['equity']))

        # Update jackpot metrics
        if 'jackpot_frequency' in simulations_data:
            self.jackpot_frequency = Decimal(str(simulations_data['jackpot_frequency']))

        if 'avg_jackpot_payout' in simulations_data:
            self.avg_jackpot_payout = Decimal(str(simulations_data['avg_jackpot_payout']))

        if 'sample_count' in simulations_data:
            self.sample_count = int(simulations_data['sample_count'])

        # Calculate jackpot-adjusted EV
        if self.equity is not None and self.expected_jackpot_value is not None:
            self.jackpot_adjusted_ev = self.equity + self.expected_jackpot_value

        # Update convergence status
        if 'convergence_status' in simulations_data:
            self.convergence_status = simulations_data['convergence_status']

        # Update timestamp
        from datetime import UTC, datetime
        self.last_updated = datetime.now(UTC).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["equity_percentage"] = self.equity_percentage
        result["jackpot_frequency_percentage"] = self.jackpot_frequency_percentage
        result["ev_improvement"] = float(self.ev_improvement) if self.ev_improvement is not None else None
        result["is_converged"] = self.is_converged
        result["expected_jackpot_value"] = float(self.expected_jackpot_value) if self.expected_jackpot_value is not None else None
        return result

    def __repr__(self) -> str:
        """String representation."""
        equity_str = f"{self.equity:.4f}" if self.equity is not None else "None"
        return f"<AggregatedMetric(cell_id={self.cell_id}, equity={equity_str}, converged={self.is_converged})>"