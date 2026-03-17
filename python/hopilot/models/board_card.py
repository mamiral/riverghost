"""
BoardCard model for poker analysis database.

Represents community cards dealt for each hand.
"""

from typing import Any, Dict, List

from sqlalchemy import Column, String, Text

from hopilot.models.base import BaseModel


class BoardCard(BaseModel):
    """
    Represents the community cards dealt in a poker hand.

    Contains flop (3 cards), turn (1 card), and river (1 card).
    """

    __tablename__ = "board_cards"

    flop1 = Column(String(2), nullable=False)
    flop2 = Column(String(2), nullable=False)
    flop3 = Column(String(2), nullable=False)
    turn = Column(String(2), nullable=False)
    river = Column(String(2), nullable=False)

    def __init__(self, **kwargs):
        """Initialize board cards with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate board card data."""
        cards = [self.flop1, self.flop2, self.flop3, self.turn, self.river]

        # Check all cards are present and valid
        for i, card in enumerate(cards):
            if not card or len(card) != 2:
                raise ValueError(f"Card {i+1} is invalid: {card}")

            if not self._is_valid_card(card):
                raise ValueError(f"Invalid card format: {card}")

        # Check for duplicates
        if len(set(cards)) != 5:
            raise ValueError("Board cards must not contain duplicates")

    @staticmethod
    def _is_valid_card(card: str) -> bool:
        """Validate single card format (e.g., 'As', 'Kh')."""
        if len(card) != 2:
            return False

        rank, suit = card[0], card[1]
        valid_ranks = "23456789TJQKA"
        valid_suits = "shdc"

        return rank in valid_ranks and suit in valid_suits

    @property
    def flop(self) -> List[str]:
        """Get flop cards."""
        return [self.flop1, self.flop2, self.flop3]

    @property
    def all_cards(self) -> List[str]:
        """Get all board cards in order."""
        return [self.flop1, self.flop2, self.flop3, self.turn, self.river]

    @property
    def street_cards(self) -> Dict[str, List[str]]:
        """Get cards by street."""
        return {
            "flop": self.flop,
            "turn": [self.turn],
            "river": [self.river]
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["flop"] = self.flop
        result["all_cards"] = self.all_cards
        result["street_cards"] = self.street_cards
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"<BoardCard(id={self.id}, flop={self.flop}, turn={self.turn}, river={self.river})>"