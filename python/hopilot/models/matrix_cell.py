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
    hand_matrix = relationship("HandMatrix", backref="matrix_cells")
    game_states = relationship("GameState", backref="matrix_cell", cascade="all, delete-orphan")
    aggregated_metric = relationship("AggregatedMetric", backref="matrix_cell", uselist=False, cascade="all, delete-orphan")

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

    @property
    def total_simulations(self) -> int:
        """Get total number of simulations run for this cell."""
        return len(self.game_states)

    @property
    def convergence_data(self) -> List[Dict[str, Any]]:
        """
        Get convergence data for analysis.

        Returns:
            List of timestamped equity points
        """
        return [
            {
                "timestamp": gs.timestamp.isoformat(),
                "equity": gs.equity if hasattr(gs, 'equity') else None
            }
            for gs in sorted(self.game_states, key=lambda x: x.timestamp)
        ]

    def get_game_states(self, limit: int = None) -> List:
        """
        Get game states for this cell.

        Args:
            limit: Maximum number of states to return

        Returns:
            List of GameState instances
        """
        states = sorted(self.game_states, key=lambda x: x.timestamp)
        if limit:
            return states[:limit]
        return states

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["hero_hand"] = self.hero_hand
        result["villain_hand"] = self.villain_hand
        result["total_simulations"] = self.total_simulations
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"<MatrixCell(id={self.id}, matrix_id={self.matrix_id}, pos=({self.row_index},{self.col_index}), hands='{self.hand_combination}')>"