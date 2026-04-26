"""MatrixCell model for poker analysis database."""

import re
from typing import Any, Dict, List, Optional, cast

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
        {'sqlite_autoincrement': True},
    )

    def __init__(self, **kwargs):
        """Initialize matrix cell with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate matrix cell data."""
        matrix_id = cast(Optional[int], self.matrix_id)
        row_index = cast(Optional[int], self.row_index)
        col_index = cast(Optional[int], self.col_index)
        hand_combination = cast(Optional[str], self.hand_combination)

        if matrix_id is None:
            raise ValueError("Matrix ID is required")

        if row_index is None or not 0 <= row_index <= 12:
            raise ValueError("Row index must be between 0 and 12")

        if col_index is None or not 0 <= col_index <= 12:
            raise ValueError("Column index must be between 0 and 12")

        if not isinstance(hand_combination, str) or not hand_combination.strip():
            raise ValueError("Hand combination cannot be empty")

        if not self._is_valid_hand_combination(hand_combination.strip()):
            raise ValueError("Hand combination must be a canonical cell label or a 'hero vs villain' string")

    @staticmethod
    def _is_valid_hand_combination(value: str) -> bool:
        if " vs " in value:
            hero_hand, villain_hand = value.split(" vs ", 1)
            return bool(hero_hand.strip() and villain_hand.strip())

        if re.fullmatch(r"([AKQJT98765432])\1", value):
            return True

        return re.fullmatch(r"[AKQJT98765432]{2}[so]", value) is not None

    @property
    def hero_hand(self) -> str:
        """Get hero's hand from combination."""
        if ' vs ' in self.hand_combination:
            return self.hand_combination.split(' vs ')[0].strip()
        return self.hand_combination.strip()

    @property
    def villain_hand(self) -> Optional[str]:
        """Get villain's hand from combination."""
        if ' vs ' not in self.hand_combination:
            return None
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