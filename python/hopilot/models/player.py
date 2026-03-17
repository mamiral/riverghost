"""
Player model for poker analysis database.

Represents player information and hole cards for each game state.
"""

from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from hopilot.models.base import BaseModel


class Player(BaseModel):
    """
    Represents a player in a poker game state.

    Contains player-specific information including hole cards,
    position, and stack size.
    """

    __tablename__ = "players"

    game_state_id = Column(Integer, ForeignKey("game_states.id"), nullable=False, index=True)
    position = Column(String(10), nullable=False)
    hole_cards = Column(String(10), nullable=False)
    stack_size = Column(Numeric(10, 2), nullable=False)
    is_hero = Column(Boolean, default=False, nullable=False)

    # Relationships
    game_state = relationship("GameState", backref="players")
    bets = relationship("Bet", backref="player", cascade="all, delete-orphan")
    jackpots = relationship("Jackpot", backref="player", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        """Initialize player with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate player data."""
        if not self.game_state_id:
            raise ValueError("Game state ID is required")

        if not self.position or not self.position.strip():
            raise ValueError("Position cannot be empty")

        if not self.hole_cards or not self.hole_cards.strip():
            raise ValueError("Hole cards cannot be empty")

        if self.stack_size < 0:
            raise ValueError("Stack size cannot be negative")

        # Validate hole cards format (basic check)
        if not self._is_valid_hole_cards(self.hole_cards):
            raise ValueError(f"Invalid hole cards format: {self.hole_cards}")

    @staticmethod
    def _is_valid_hole_cards(cards: str) -> bool:
        """Validate hole cards format (e.g., 'AsKh')."""
        if len(cards) != 4:  # Should be 4 characters: rank suit rank suit
            return False

        # Check ranks and suits
        try:
            rank1, suit1, rank2, suit2 = cards
            valid_ranks = "23456789TJQKA"
            valid_suits = "shdc"
            return (rank1 in valid_ranks and suit1 in valid_suits and
                    rank2 in valid_ranks and suit2 in valid_suits)
        except ValueError:
            return False

    @property
    def card1(self) -> str:
        """Get first hole card."""
        return self.hole_cards[:2]

    @property
    def card2(self) -> str:
        """Get second hole card."""
        return self.hole_cards[2:]

    @property
    def total_bet_amount(self) -> Decimal:
        """Get total amount bet by this player."""
        return sum(bet.amount for bet in self.bets)

    @property
    def remaining_stack(self) -> Decimal:
        """Get remaining stack after bets."""
        return self.stack_size - self.total_bet_amount

    @property
    def is_all_in(self) -> bool:
        """Check if player is all-in."""
        return self.total_bet_amount >= self.stack_size

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["card1"] = self.card1
        result["card2"] = self.card2
        result["total_bet_amount"] = float(self.total_bet_amount)
        result["remaining_stack"] = float(self.remaining_stack)
        result["is_all_in"] = self.is_all_in
        return result

    def __repr__(self) -> str:
        """String representation."""
        hero_indicator = " (hero)" if self.is_hero else ""
        return f"<Player(id={self.id}, position={self.position}, cards={self.hole_cards}{hero_indicator})>"