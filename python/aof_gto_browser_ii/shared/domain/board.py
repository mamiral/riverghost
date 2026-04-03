from dataclasses import dataclass
from typing import List, Optional
from aof_gto_browser_ii.shared.domain.card import Card


@dataclass(frozen=True)
class Board:
    """Immutable board representation with 0-5 community cards in street order.

    The board represents community cards in poker, progressing through streets:
    - Preflop: 0 cards
    - Flop: 3 cards
    - Turn: 4 cards
    - River: 5 cards

    Cards must be unique (no duplicates) and ordered by street appearance.
    """

    cards: List[Card]

    def __post_init__(self) -> None:
        """Validate board constraints after initialization."""
        if len(self.cards) > 5:
            raise ValueError(f"Board cannot have more than 5 cards, got {len(self.cards)}")

        # Check for duplicate cards
        seen_cards = set()
        for card in self.cards:
            if card in seen_cards:
                raise ValueError(f"Board contains duplicate card: {card}")
            seen_cards.add(card)

    @classmethod
    def from_strings(cls, card_strings: List[str]) -> "Board":
        """Create a Board from a list of card string representations.

        Args:
            card_strings: List of card strings (e.g., ["As", "Kh", "Qd"])

        Returns:
            Board instance with parsed cards

        Raises:
            ValueError: If any card string is invalid
        """
        cards = [Card.from_string(card_str) for card_str in card_strings]
        return cls(cards)

    def to_strings(self) -> List[str]:
        """Convert board cards to string representations.

        Returns:
            List of card strings in board order
        """
        return [card.to_string() for card in self.cards]

    def num_cards(self) -> int:
        """Get the number of cards on the board.

        Returns:
            Number of cards (0-5)
        """
        return len(self.cards)

    def is_empty(self) -> bool:
        """Check if the board has no cards (preflop).

        Returns:
            True if no cards on board
        """
        return len(self.cards) == 0

    def is_flop(self) -> bool:
        """Check if the board has exactly 3 cards (flop).

        Returns:
            True if exactly 3 cards on board
        """
        return len(self.cards) == 3

    def is_turn(self) -> bool:
        """Check if the board has exactly 4 cards (turn).

        Returns:
            True if exactly 4 cards on board
        """
        return len(self.cards) == 4

    def is_river(self) -> bool:
        """Check if the board has exactly 5 cards (river).

        Returns:
            True if exactly 5 cards on board
        """
        return len(self.cards) == 5

    def is_complete(self) -> bool:
        """Check if the board is complete with 5 cards.

        Returns:
            True if 5 cards on board
        """
        return len(self.cards) == 5

    def get_street(self) -> str:
        """Get the current street name based on card count.

        Returns:
            Street name: "preflop", "flop", "turn", "river", or "unknown"
        """
        if len(self.cards) == 0:
            return "preflop"
        elif len(self.cards) == 3:
            return "flop"
        elif len(self.cards) == 4:
            return "turn"
        elif len(self.cards) == 5:
            return "river"
        else:
            return "unknown"

    def get_flop(self) -> Optional[tuple[Card, Card, Card]]:
        """Get the flop cards (first 3 cards).

        Returns:
            Tuple of 3 cards if flop is available, None otherwise
        """
        if len(self.cards) >= 3:
            return (self.cards[0], self.cards[1], self.cards[2])
        return None

    def get_turn(self) -> Optional[Card]:
        """Get the turn card (4th card).

        Returns:
            Turn card if available, None otherwise
        """
        if len(self.cards) >= 4:
            return self.cards[3]
        return None

    def get_river(self) -> Optional[Card]:
        """Get the river card (5th card).

        Returns:
            River card if available, None otherwise
        """
        if len(self.cards) >= 5:
            return self.cards[4]
        return None

    def contains_card(self, card: Card) -> bool:
        """Check if a specific card is on the board.

        Args:
            card: Card to check for

        Returns:
            True if card is on the board
        """
        return card in self.cards

    def all_board_cards(self) -> List[Card]:
        """Get a copy of all board cards.

        Returns:
            Copy of the cards list
        """
        return self.cards.copy()

    def __hash__(self) -> int:
        """Hash based on the tuple of cards for immutability."""
        return hash(tuple(self.cards))

    def __str__(self) -> str:
        """String representation as space-separated card strings."""
        return " ".join(self.to_strings())

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"Board(cards={self.to_strings()})"