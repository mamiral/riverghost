"""Hand domain model with 2-card poker hands."""

from dataclasses import dataclass
from typing import List
from aof_gto_browser_ii.shared.domain.card import Card, Rank
from aof_gto_browser_ii.shared.exceptions.validation_errors import ValidationError


@dataclass(frozen=True)
class Hand:
    """Immutable representation of a 2-card poker hand."""

    card1: Card
    card2: Card

    def __post_init__(self):
        """Validate that both cards are different."""
        if self.card1 == self.card2:
            raise ValidationError("Hand cannot have duplicate cards")

    def __eq__(self, other: object) -> bool:
        """Hand equality is order-independent (same two cards regardless of order)."""
        if not isinstance(other, Hand):
            return NotImplemented
        # Two hands are equal if they contain the same two cards (order doesn't matter)
        cards_self = {self.card1, self.card2}
        cards_other = {other.card1, other.card2}
        return cards_self == cards_other

    def __hash__(self) -> int:
        """Hash based on the set of cards (order-independent)."""
        # Use frozenset for order-independent hashing
        return hash(frozenset({self.card1, self.card2}))

    @staticmethod
    def from_strings(card1_str: str, card2_str: str) -> "Hand":
        """Create Hand from two card string representations."""
        card1 = Card.from_string(card1_str)
        card2 = Card.from_string(card2_str)
        return Hand(card1=card1, card2=card2)

    @staticmethod
    def from_tuple(card_tuple: tuple[str, str]) -> "Hand":
        """Create Hand from a tuple of two card strings."""
        return Hand.from_strings(card_tuple[0], card_tuple[1])

    def to_strings(self) -> tuple[str, str]:
        """Return tuple of card string representations for DTO transport."""
        return (self.card1.to_string(), self.card2.to_string())

    def to_shorthand(self) -> str:
        """Return standardized shorthand notation (AKs, 22, QJo, etc.).

        Algorithm:
        1. Determine higher and lower ranks
        2. Check if suited (same suit)
        3. Return notation: higher_rank + lower_rank + 's'/'o' or just ranks for pairs
        """
        rank1, rank2 = self.card1.rank, self.card2.rank
        suit1, suit2 = self.card1.suit, self.card2.suit

        # For pairs, just return the rank twice
        if rank1 == rank2:
            return f"{rank1.char}{rank1.char}"

        # Determine higher and lower ranks
        if rank1.value > rank2.value:
            high_rank, low_rank = rank1, rank2
            high_suit, low_suit = suit1, suit2
        else:
            high_rank, low_rank = rank2, rank1
            high_suit, low_suit = suit2, suit1

        # Check if suited
        if high_suit == low_suit:
            return f"{high_rank.char}{low_rank.char}s"
        else:
            return f"{high_rank.char}{low_rank.char}o"

    def to_cards(self) -> List[Card]:
        """Return list of the two cards."""
        return [self.card1, self.card2]

    def is_pair(self) -> bool:
        """Return True if both cards have the same rank (pair)."""
        return self.card1.rank == self.card2.rank

    def is_suited(self) -> bool:
        """Return True if both cards have the same suit."""
        return self.card1.suit == self.card2.suit

    def is_offsuit(self) -> bool:
        """Return True if cards have different suits."""
        return self.card1.suit != self.card2.suit

    def num_combos(self) -> int:
        """Return number of possible combinations for this hand type.

        - Pairs: 6 combos (each suit can pair with any other suit)
        - Suited: 4 combos (4 suits for the off-suit card)
        - Offsuit: 12 combos (4 suits × 3 remaining suits for second card)
        """
        if self.is_pair():
            return 6
        elif self.is_suited():
            return 4
        else:
            return 12

    def is_broadway(self) -> bool:
        """Return True if both ranks are broadway cards (T, J, Q, K, A)."""
        broadway_ranks = {Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE}
        return self.card1.rank in broadway_ranks and self.card2.rank in broadway_ranks

    def is_connected(self) -> bool:
        """Return True if ranks differ by exactly 1 (connected)."""
        rank_diff = abs(self.card1.rank.value - self.card2.rank.value)
        return rank_diff == 1

    def is_gapped(self) -> bool:
        """Return True if ranks differ by 2 or 3 (gapped)."""
        rank_diff = abs(self.card1.rank.value - self.card2.rank.value)
        return rank_diff in (2, 3)

    def __str__(self) -> str:
        """String representation using shorthand notation."""
        return self.to_shorthand()

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"Hand.from_strings('{self.card1.to_string()}', '{self.card2.to_string()}')"