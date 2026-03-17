"""
HandMatrix model for poker analysis database.

Represents the 13x13 matrix structure for each simulation,
containing all possible hand matchups.
"""

from typing import Any, Dict, List

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from hopilot.models.base import BaseModel


class HandMatrix(BaseModel):
    """
    Represents the hand matrix structure for a simulation.

    Contains the grid of all possible hand matchups and links
    to individual matrix cells.
    """

    __tablename__ = "hand_matrices"

    simulation_id = Column(Integer, ForeignKey("simulations.id"), unique=True, nullable=False)
    matrix_size = Column(String(10), default="13x13", nullable=False)

    # Relationships
    simulation = relationship("Simulation", backref="hand_matrix")
    matrix_cells = relationship("MatrixCell", backref="hand_matrix", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        """Initialize hand matrix with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate hand matrix data."""
        if not self.simulation_id:
            raise ValueError("Simulation ID is required")

        # Validate matrix size format
        if not self._is_valid_matrix_size(self.matrix_size):
            raise ValueError(f"Invalid matrix size format: {self.matrix_size}")

    @staticmethod
    def _is_valid_matrix_size(size: str) -> bool:
        """Check if matrix size format is valid (e.g., '13x13')."""
        try:
            rows, cols = size.split('x')
            return int(rows) > 0 and int(cols) > 0
        except (ValueError, AttributeError):
            return False

    @property
    def rows(self) -> int:
        """Get number of rows in matrix."""
        return int(self.matrix_size.split('x')[0])

    @property
    def cols(self) -> int:
        """Get number of columns in matrix."""
        return int(self.matrix_size.split('x')[1])

    @property
    def total_cells(self) -> int:
        """Get total number of cells in matrix."""
        return self.rows * self.cols

    def get_cell(self, row: int, col: int):
        """
        Get matrix cell at specified position.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            MatrixCell instance or None
        """
        for cell in self.matrix_cells:
            if cell.row_index == row and cell.col_index == col:
                return cell
        return None

    def get_cells(self) -> List:
        """
        Get all matrix cells ordered by position.

        Returns:
            List of MatrixCell instances
        """
        return sorted(
            self.matrix_cells,
            key=lambda c: (c.row_index, c.col_index)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["rows"] = self.rows
        result["cols"] = self.cols
        result["total_cells"] = self.total_cells
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"<HandMatrix(id={self.id}, simulation_id={self.simulation_id}, size={self.matrix_size})>"