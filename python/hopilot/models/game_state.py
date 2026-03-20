"""
GameState model for poker analysis database.

Represents detailed records of each simulated hand with outcomes
and references to all related entities.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from hopilot.models.base import BaseModel


class GameState(BaseModel):
    """
    Represents a single simulated poker hand.

    Contains all information about a hand simulation including
    players, bets, board cards, and outcome.
    """

    __tablename__ = "game_states"

    cell_id = Column(Integer, ForeignKey("matrix_cells.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    round = Column(String(10), default="preflop", nullable=False)
    pot_size = Column(Numeric(10, 2), nullable=False)
    board_cards_id = Column(Integer, ForeignKey("board_cards.id"), nullable=False)
    outcome = Column(String(20), nullable=True)

    # Relationships
    # Note: Using relationship without backref since MatrixCell.game_states manages the relationship
    matrix_cell = relationship("MatrixCell", overlaps="game_states")
    players = relationship("Player", cascade="all, delete-orphan", overlaps="game_state")
    bets = relationship("Bet", backref="game_state", cascade="all, delete-orphan")
    board_cards = relationship("BoardCard", backref="game_states")
    jackpots = relationship("Jackpot", backref="game_state", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        """Initialize game state with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate game state data."""
        if not self.cell_id:
            raise ValueError("Cell ID is required")

        if not self.timestamp:
            raise ValueError("Timestamp is required")

        if self.pot_size < 0:
            raise ValueError("Pot size cannot be negative")

        if self.round not in ["preflop"]:
            raise ValueError("Round must be 'preflop' for all-in-or-fold games")

        if not self.board_cards_id:
            raise ValueError("Board cards ID is required")

    @property
    def hero_player(self):
        """Get the hero player."""
        for player in self.players:
            if player.is_hero:
                return player
        return None

    @property
    def villain_player(self):
        """Get the villain player."""
        for player in self.players:
            if not player.is_hero:
                return player
        return None

    @property
    def total_bets(self) -> Decimal:
        """Get total amount bet in this game state."""
        return sum(bet.amount for bet in self.bets)

    @property
    def player_count(self) -> int:
        """Get number of players in this game state."""
        return len(self.players)

    @property
    def has_jackpot(self) -> bool:
        """Check if this game state triggered any jackpots."""
        return len(self.jackpots) > 0

    @property
    def jackpot_payout(self) -> Decimal:
        """Get total jackpot payout for this game state."""
        return sum(jackpot.payout_amount for jackpot in self.jackpots)

    def get_player_bets(self, player_id: int) -> List:
        """
        Get all bets for a specific player.

        Args:
            player_id: Player ID

        Returns:
            List of Bet instances
        """
        return [bet for bet in self.bets if bet.player_id == player_id]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["total_bets"] = float(self.total_bets)
        result["player_count"] = self.player_count
        result["has_jackpot"] = self.has_jackpot
        result["jackpot_payout"] = float(self.jackpot_payout)
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"<GameState(id={self.id}, cell_id={self.cell_id}, pot={self.pot_size}, outcome={self.outcome})>"