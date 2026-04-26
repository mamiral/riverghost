"""
MatrixCell model for poker analysis database.

Represents individual cells in the hand matrix containing
specific hand matchups and their simulation results.
"""

from typing import Any, Dict, List

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from hopilot.models.base import BaseModel


class MatrixCell(BaseModel):
    """
    Represents a single cell in the hand matrix.

    Contains information about a specific hand matchup and
    links to all game states simulated for this matchup.
    """

    __tablename__ = "matrix_cells"

    matrix_id = Column(Integer, ForeignKey("hand_matrices.id"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    col_index = Column(Integer, nullable=False)
    hand_combination = Column(String(50), nullable=False)

    # Relationships
    # Note: game_states relationship removed - GameState has no cell_id (GameStates-first architecture)
    # Cell identity is resolved in post-processing by reading GameState rows and grouping by hand matchup
    # aggregated_metric relationship still exists for storing aggregated results
    aggregated_metric = relationship("AggregatedMetric", uselist=False, cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('matrix_id', 'row_index', 'col_index', name='uq_matrix_cells_matrix_id_row_col'),
        Index('ix_matrix_cells_matrix_id_row_col', 'matrix_id', 'row_index', 'col_index'),
    )

    def __init__(self, **kwargs):
        """Initialize matrix cell with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate matrix cell data."""
        if not self.matrix_id:
            raise ValueError("Matrix ID is required")

        if not (0 <= self.row_index <= 12):
            raise ValueError("Row index must be between 0 and 12")

        if not (0 <= self.col_index <= 12):
            raise ValueError("Column index must be between 0 and 12")

        if not self.hand_combination or not self.hand_combination.strip():
            raise ValueError("Hand combination cannot be empty")

        # Validate hand combination format (basic check)
        if 'vs' not in self.hand_combination:
            raise ValueError("Hand combination must contain 'vs' separator")

    @property
    def hero_hand(self) -> str:
        """Get hero's hand from combination."""
        return self.hand_combination.split(' vs ')[0].strip()

    @property
    def villain_hand(self) -> str:
        """Get villain's hand from combination."""
        return self.hand_combination.split(' vs ')[1].strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["hero_hand"] = self.hero_hand
        result["villain_hand"] = self.villain_hand
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"<MatrixCell(id={self.id}, matrix_id={self.matrix_id}, pos=({self.row_index},{self.col_index}), hands='{self.hand_combination}')>"