"""
Bet model for poker analysis database.

Represents all-in betting actions recorded for each game state.
"""

from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from hopilot.models.base import BaseModel


class Bet(BaseModel):
    """
    Represents a betting action in a poker game state.

    For all-in-or-fold games, bets are typically all-in raises.
    """

    __tablename__ = "bets"

    game_state_id = Column(Integer, ForeignKey("game_states.id"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    action_type = Column(String(10), default="raise", nullable=False)

    # Relationships
    game_state = relationship("GameState", backref="bets")
    player = relationship("Player", backref="bets")

    def __init__(self, **kwargs):
        """Initialize bet with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate bet data."""
        if not self.game_state_id:
            raise ValueError("Game state ID is required")

        if not self.player_id:
            raise ValueError("Player ID is required")

        if self.amount <= 0:
            raise ValueError("Bet amount must be positive")

        if self.action_type not in ["fold", "call", "raise"]:
            raise ValueError("Action type must be 'fold', 'call', or 'raise'")

    @property
    def is_all_in(self) -> bool:
        """Check if this bet puts player all-in."""
        if self.player:
            return self.amount >= self.player.stack_size
        return False

    @property
    def bet_percentage(self) -> float:
        """Get bet amount as percentage of player's stack."""
        if self.player and self.player.stack_size > 0:
            return float(self.amount / self.player.stack_size)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["is_all_in"] = self.is_all_in
        result["bet_percentage"] = self.bet_percentage
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"<Bet(id={self.id}, player_id={self.player_id}, amount={self.amount}, action={self.action_type})>"