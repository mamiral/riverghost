"""Card domain model with Rank and Suit enums."""

from dataclasses import dataclass
from enum import IntEnum, Enum


class Rank(IntEnum):
    """Card rank as integer quasi-enum (2-14, where A=14)."""

    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def char(self) -> str:
        """Single-character representation of the rank."""
        rank_chars = {
            2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
            10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"
        }
        return rank_chars[self.value]


class Suit(str, Enum):
    """Card suit with string values for database/API stability."""

    SPADES = "s"
    HEARTS = "h"
    DIAMONDS = "d"
    CLUBS = "c"

    @property
    def full_name(self) -> str:
        """Full name of the suit."""
        suit_names = {
            "s": "Spades",
            "h": "Hearts",
            "d": "Diamonds",
            "c": "Clubs"
        }
        return suit_names[self.value]


@dataclass(frozen=True)
class Card:
    """Immutable representation of a single playing card."""

    rank: Rank
    suit: Suit

    @staticmethod
    def from_string(s: str) -> "Card":
        """Parse card from string format.

        Accepts shorthand: "As", "Kh", "2d", "Tc"
        Accepts long form: "Ace of Spades", "King of Hearts"
        Case-insensitive and whitespace-trimmed.
        """
        # Normalize input
        s = s.strip().upper()

        # Handle long form: "ACE OF SPADES"
        if " OF " in s:
            rank_str, suit_str = s.split(" OF ", 1)
            rank_str = rank_str.strip()
            suit_str = suit_str.strip()
        else:
            # Handle shorthand: "AS", "KH", "2D", "TC"
            if len(s) != 2:
                raise ValueError(f"Invalid card format: '{s}'")
            rank_str = s[0]
            suit_str = s[1]

        # Parse rank
        rank_map = {
            "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
            "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
            "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE,
            "TEN": Rank.TEN, "JACK": Rank.JACK, "QUEEN": Rank.QUEEN,
            "KING": Rank.KING, "ACE": Rank.ACE,
            "TWO": Rank.TWO, "THREE": Rank.THREE, "FOUR": Rank.FOUR, "FIVE": Rank.FIVE,
            "SIX": Rank.SIX, "SEVEN": Rank.SEVEN, "EIGHT": Rank.EIGHT, "NINE": Rank.NINE
        }

        if rank_str not in rank_map:
            raise ValueError(f"Invalid rank: '{rank_str}'")
        rank = rank_map[rank_str]

        # Parse suit
        suit_map = {
            "S": Suit.SPADES, "H": Suit.HEARTS, "D": Suit.DIAMONDS, "C": Suit.CLUBS,
            "SPADES": Suit.SPADES, "HEARTS": Suit.HEARTS, "DIAMONDS": Suit.DIAMONDS, "CLUBS": Suit.CLUBS
        }

        if suit_str not in suit_map:
            raise ValueError(f"Invalid suit: '{suit_str}'")
        suit = suit_map[suit_str]

        return Card(rank=rank, suit=suit)

    def to_string(self) -> str:
        """Return normalized shorthand string format like 'As', 'Kh'."""
        return f"{self.rank.char}{self.suit.value}"

    def __str__(self) -> str:
        """String representation using shorthand format."""
        return self.to_string()

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"Card(rank={self.rank.name}, suit={self.suit.name})"

    def is_ace(self) -> bool:
        """Return True if this is an ace."""
        return self.rank == Rank.ACE