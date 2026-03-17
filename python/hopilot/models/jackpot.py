"""
Jackpot model for poker analysis database.

Represents special payout events triggered by specific hand combinations.
"""

from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from hopilot.models.base import BaseModel


class Jackpot(BaseModel):
    """
    Represents a jackpot payout event in a poker game.

    Jackpots are special bonuses paid for achieving specific hand
    combinations (e.g., straight flush, royal flush) as defined
    by poker platforms like GGPoker.
    """

    __tablename__ = "jackpots"

    game_state_id = Column(Integer, ForeignKey("game_states.id"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    jackpot_type = Column(String(50), nullable=False, index=True)
    payout_amount = Column(Numeric(10, 2), nullable=False)
    cards_used = Column(JSON, nullable=False)  # Cards that formed the jackpot hand
    triggered_at = Column(String(27), nullable=False)  # ISO timestamp

    # Relationships
    game_state = relationship("GameState", backref="jackpots")
    player = relationship("Player", backref="jackpots")

    def __init__(self, **kwargs):
        """Initialize jackpot with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate jackpot data."""
        if not self.game_state_id:
            raise ValueError("Game state ID is required")

        if not self.player_id:
            raise ValueError("Player ID is required")

        if not self.jackpot_type or not self.jackpot_type.strip():
            raise ValueError("Jackpot type cannot be empty")

        if self.payout_amount <= 0:
            raise ValueError("Payout amount must be positive")

        if not self.cards_used or not isinstance(self.cards_used, list):
            raise ValueError("Cards used must be a non-empty list")

        # Validate jackpot types (extensible)
        valid_types = [
            'royal_flush', 'straight_flush', 'four_of_a_kind',
            'full_house', 'flush', 'straight', 'three_of_a_kind',
            'two_pair', 'one_pair', 'high_card'
        ]
        if self.jackpot_type not in valid_types:
            # Allow custom jackpot types for future platform features
            pass

    @property
    def payout_multiplier(self) -> int:
        """
        Get the payout multiplier for this jackpot type.

        Returns:
            Multiplier value (e.g., 100 for 100x pot bonus)
        """
        multipliers = {
            'royal_flush': 500,
            'straight_flush': 100,
            'four_of_a_kind': 50,
            'full_house': 10,
            'flush': 5,
            'straight': 4,
            'three_of_a_kind': 3,
            'two_pair': 2,
            'one_pair': 1,
            'high_card': 0,
        }
        return multipliers.get(self.jackpot_type, 0)

    @property
    def cards_used_count(self) -> int:
        """Get the number of cards used to form this jackpot."""
        return len(self.cards_used) if self.cards_used else 0

    @property
    def is_platform_bonus(self) -> bool:
        """
        Check if this is a platform-specific bonus jackpot.

        Platform bonuses typically require specific card combinations
        and offer high multipliers.
        """
        high_value_types = ['royal_flush', 'straight_flush', 'four_of_a_kind']
        return self.jackpot_type in high_value_types and self.payout_multiplier >= 50

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["payout_multiplier"] = self.payout_multiplier
        result["cards_used_count"] = self.cards_used_count
        result["is_platform_bonus"] = self.is_platform_bonus
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"<Jackpot(id={self.id}, type={self.jackpot_type}, payout={self.payout_amount}, player_id={self.player_id})>"