"""
ConvergenceSnapshot model for tracking metric convergence during aggregation.

Stores incremental convergence data for each matrix cell during aggregation,
enabling real-time monitoring and historical convergence curve plotting.
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, Numeric, String

from hopilot.models.base import BaseModel


class ConvergenceSnapshot(BaseModel):
    """
    Represents a snapshot of convergence metrics at a specific sample count.

    Tracks how equity, win probability, and EV change as more samples are processed
    during matrix cell aggregation.
    """

    __tablename__ = "convergence_snapshots"

    cell_id = Column(Integer, ForeignKey("matrix_cells.id"), nullable=False)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False)
    sample_count = Column(Integer, nullable=False)
    equity = Column(Numeric(5, 4), nullable=True)  # Standard win probability (0.0000-1.0000)
    win_probability = Column(Numeric(5, 4), nullable=True)  # Alternative win probability metric
    ev = Column(Numeric(10, 4), nullable=True)  # Expected value calculation
    timestamp = Column(String(27), nullable=False)  # ISO format timestamp

    __table_args__ = (
        Index('idx_convergence_cell_samples', 'cell_id', 'sample_count'),
        Index('idx_convergence_simulation', 'simulation_id'),
    )