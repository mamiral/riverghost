"""Adapter for converting between domain objects and PokerKit string formats.

This adapter provides a clean interface for converting between domain Card/Hand objects
and PokerKit string representations, isolating the domain layer from external dependencies.
"""

from aof_gto_browser_ii.shared.domain.card import Card
from aof_gto_browser_ii.shared.domain.hand import Hand


class CardAdapter:
    """Adapter for PokerKit string format conversions.

    Provides static methods to convert between domain objects and PokerKit strings.
    This isolates the domain layer from PokerKit library dependencies.
    """

    @staticmethod
    def to_pokerkit(card: Card) -> str:
        """Convert domain Card to PokerKit string format.

        Args:
            card: Domain Card object

        Returns:
            PokerKit string representation (e.g., "As", "Kh", "2d", "Tc")
        """
        return card.to_string()

    @staticmethod
    def from_pokerkit(card_string: str) -> Card:
        """Convert PokerKit string format to domain Card.

        Args:
            card_string: PokerKit card string (e.g., "As", "Kh", "2d", "Tc")

        Returns:
            Domain Card object

        Raises:
            ValueError: If card_string is invalid
        """
        return Card.from_string(card_string)

    @staticmethod
    def to_pokerkit_hand(hand: Hand) -> tuple[str, str]:
        """Convert domain Hand to PokerKit hand format.

        Args:
            hand: Domain Hand object

        Returns:
            Tuple of two PokerKit card strings
        """
        card1_str, card2_str = hand.to_strings()
        return (card1_str, card2_str)

    @staticmethod
    def from_pokerkit_hand(card1_string: str, card2_string: str) -> Hand:
        """Convert PokerKit hand format to domain Hand.

        Args:
            card1_string: First card in PokerKit format
            card2_string: Second card in PokerKit format

        Returns:
            Domain Hand object

        Raises:
            ValueError: If card strings are invalid or cards are duplicates
        """
        return Hand.from_strings(card1_string, card2_string)