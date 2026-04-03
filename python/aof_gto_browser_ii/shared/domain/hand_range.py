"""HandRange domain model with complex poker range notation parsing."""

from dataclasses import dataclass
from typing import List
from aof_gto_browser_ii.shared.domain.hand import Hand
from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit
from aof_gto_browser_ii.shared.exceptions.validation_errors import RangeError


@dataclass(frozen=True)
class HandRange:
    """Immutable collection of poker hands with complex notation parsing."""

    hands: List[Hand]
    notation: str

    def __post_init__(self):
        """Validate that all hands are unique."""
        if len(set(self.hands)) != len(self.hands):
            raise ValueError("HandRange cannot have duplicate hands")

    @staticmethod
    def from_shorthand(notation: str) -> "HandRange":
        """Parse complex hand range notation into HandRange.

        Supports notation like:
        - "*" (all possible hands)
        - "AKs" (single suited hand)
        - "22+" (pairs from 22 to AA)
        - "AKs+" (suited hands from AK down)
        - "A5s-A2s" (suited range)
        - "AKs+,QQ+,A5s-A2s" (complex combinations)

        Algorithm:
        1. Parse: Split on comma/semicolon, strip whitespace
        2. Expand: For each component, detect type and expand
        3. Deduplicate: Remove duplicate hands, preserve order
        """
        if not notation or not notation.strip():
            raise RangeError("Empty range notation")

        # Special case: "*" means all possible hands
        if notation.strip() == "*":
            return HandRange._create_all_hands()

        # Step 1: Parse components
        components = [comp.strip() for comp in notation.replace(';', ',').split(',') if comp.strip()]

        all_hands = []

        # Step 2: Expand each component
        for component in components:
            hands = HandRange._expand_component(component)
            all_hands.extend(hands)

        # Step 3: Deduplicate while preserving order
        seen_shorthands = set()
        unique_hands = []
        for hand in all_hands:
            shorthand = hand.to_shorthand()
            if shorthand not in seen_shorthands:
                seen_shorthands.add(shorthand)
                unique_hands.append(hand)

        if not unique_hands:
            raise RangeError(f"No valid hands found in notation: {notation}")

        return HandRange(hands=unique_hands, notation=notation)

    @staticmethod
    def _create_all_hands() -> "HandRange":
        """Create a HandRange containing all possible 2-card poker hands."""
        from aof_gto_browser_ii.shared.domain.card import Rank, Suit

        all_hands = []

        # Get all ranks in descending order for consistent ordering
        ranks = list(Rank)[::-1]  # Reverse to get ACE first
        suits = list(Suit)

        # Generate all possible combinations of 2 distinct cards
        # Use nested loops to ensure we don't create duplicates
        for i in range(len(ranks)):
            rank1 = ranks[i]
            for j in range(len(ranks)):
                rank2 = ranks[j]

                if rank1.value > rank2.value:  # Only high-low combinations, not low-high
                    # Suited combinations (4 possibilities)
                    for suit in suits:
                        card1 = Card(rank1, suit)
                        card2 = Card(rank2, suit)
                        all_hands.append(Hand(card1=card1, card2=card2))

                    # Offsuit combinations (12 possibilities: 4 suits × 3 other suits)
                    for suit1 in suits:
                        for suit2 in suits:
                            if suit1 != suit2:
                                card1 = Card(rank1, suit1)
                                card2 = Card(rank2, suit2)
                                all_hands.append(Hand(card1=card1, card2=card2))

                elif rank1 == rank2:  # Pairs
                    # Only add pairs once (when i == j)
                    if i == j:
                        all_hands.extend(HandRange._create_pair_hands(rank1))

        return HandRange(hands=all_hands, notation="*")

    @staticmethod
    def _expand_component(component: str) -> List[Hand]:
        """Expand a single range component into list of hands."""
        component = component.strip()

        # Handle plus notation: "22+", "AKs+"
        if component.endswith('+'):
            return HandRange._expand_plus_notation(component[:-1])

        # Handle dash range: "A5s-A2s", "22-99"
        if '-' in component:
            return HandRange._expand_dash_range(component)

        # Handle single hand: "AKs", "22", "AKo"
        return HandRange._expand_single_hand(component)

    @staticmethod
    def _expand_plus_notation(base: str) -> List[Hand]:
        """Expand plus notation like '22' or 'AKs'."""
        hands = []

        if len(base) == 2 and base[0] == base[1]:
            # Pair plus: "22+" → 22,33,44,...,AA
            start_rank = HandRange._parse_rank_char(base[0])
            for rank_value in range(start_rank.value, Rank.ACE.value + 1):
                rank = Rank(rank_value)
                # Add the pair (6 combinations)
                hands.extend(HandRange._create_pair_hands(rank))
        else:
            # Suited plus: "AKs+" → AKs,AQs,AJs,...,A2s
            if len(base) != 3 or base[2] != 's':
                raise RangeError(f"Invalid suited plus notation: '{base}+'")
            high_char, low_char, suit_indicator = base[0], base[1], base[2]

            high_rank = HandRange._parse_rank_char(high_char)
            low_rank = HandRange._parse_rank_char(low_char)

            # Generate suited hands: high card paired with all ranks from low_rank down to 2
            for rank_value in range(Rank.TWO.value, low_rank.value + 1):
                rank = Rank(rank_value)
                # Create suited hand with high card and this lower rank
                card1 = Card(high_rank, Suit.SPADES)
                card2 = Card(rank, Suit.SPADES)
                hand = Hand(card1=card1, card2=card2)
                hands.append(hand)

        return hands

    @staticmethod
    def _expand_dash_range(range_str: str) -> List[Hand]:
        """Expand dash range like 'A5s-A2s' or '22-99'."""
        if range_str.count('-') != 1:
            raise RangeError(f"Invalid range format: '{range_str}'")

        start_str, end_str = range_str.split('-')

        if len(start_str) == 2 and len(end_str) == 2 and start_str[0] == start_str[1]:
            # Pair range: "22-99"
            start_rank = HandRange._parse_rank_char(start_str[0])
            end_rank = HandRange._parse_rank_char(end_str[0])
            hands = []
            for rank_value in range(start_rank.value, end_rank.value + 1):
                rank = Rank(rank_value)
                hands.extend(HandRange._create_pair_hands(rank))
            return hands
        elif len(start_str) == 3 and len(end_str) == 3 and start_str[2] == 's' and end_str[2] == 's':
            # Suited range: "A5s-A2s"
            start_high = HandRange._parse_rank_char(start_str[0])
            start_low = HandRange._parse_rank_char(start_str[1])
            end_high = HandRange._parse_rank_char(end_str[0])
            end_low = HandRange._parse_rank_char(end_str[1])

            if start_high != end_high:
                raise RangeError(f"Range must have same high card: '{range_str}'")

            hands = []
            for rank_value in range(end_low.value, start_low.value + 1):
                rank = Rank(rank_value)
                card1 = Card(start_high, Suit.SPADES)
                card2 = Card(rank, Suit.SPADES)
                hand = Hand(card1=card1, card2=card2)
                hands.append(hand)
            return hands
        else:
            raise RangeError(f"Unsupported range format: '{range_str}'")

    @staticmethod
    def _expand_single_hand(hand_str: str) -> List[Hand]:
        """Expand single hand like 'AKs', '22', 'AKo'."""
        if len(hand_str) == 2 and hand_str[0] == hand_str[1]:
            # Pair: "22"
            rank = HandRange._parse_rank_char(hand_str[0])
            return HandRange._create_pair_hands(rank)
        elif len(hand_str) == 3:
            # Two-card hand: "AKs", "AKo"
            high_char, low_char, suit_char = hand_str[0], hand_str[1], hand_str[2]
            high_rank = HandRange._parse_rank_char(high_char)
            low_rank = HandRange._parse_rank_char(low_char)

            if suit_char == 's':
                # Suited: "AKs" - 4 combinations
                return HandRange._create_suited_hands(high_rank, low_rank)
            elif suit_char == 'o':
                # Offsuit: "AKo" - 12 combinations
                return HandRange._create_offsuit_hands(high_rank, low_rank)
            else:
                raise RangeError(f"Invalid suit indicator '{suit_char}' in '{hand_str}'")
        else:
            raise RangeError(f"Invalid hand format: '{hand_str}'")

    @staticmethod
    def _parse_rank_char(char: str) -> Rank:
        """Parse rank character to Rank enum."""
        rank_map = {
            '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
            '6': Rank.SIX, '7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE,
            'T': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN, 'K': Rank.KING, 'A': Rank.ACE
        }
        if char not in rank_map:
            raise RangeError(f"Invalid rank character: '{char}'")
        return rank_map[char]

    @staticmethod
    def _create_pair_hands(rank: Rank) -> List[Hand]:
        """Create all 6 possible pair hands for a rank."""
        hands = []
        suits = [Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS]
        for i in range(len(suits)):
            for j in range(i + 1, len(suits)):
                card1 = Card(rank, suits[i])
                card2 = Card(rank, suits[j])
                hands.append(Hand(card1=card1, card2=card2))
        return hands

    @staticmethod
    def _create_suited_hands(high_rank: Rank, low_rank: Rank) -> List[Hand]:
        """Create all 4 suited combinations for two ranks."""
        hands = []
        suits = [Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS]
        for suit in suits:
            card1 = Card(high_rank, suit)
            card2 = Card(low_rank, suit)
            hands.append(Hand(card1=card1, card2=card2))
        return hands

    @staticmethod
    def _create_offsuit_hands(high_rank: Rank, low_rank: Rank) -> List[Hand]:
        """Create all 12 offsuit combinations for two ranks."""
        hands = []
        suits = [Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS]
        for suit1 in suits:
            for suit2 in suits:
                if suit1 != suit2:
                    card1 = Card(high_rank, suit1)
                    card2 = Card(low_rank, suit2)
                    hands.append(Hand(card1=card1, card2=card2))
        return hands

    def to_shorthand(self) -> str:
        """Return the original notation string."""
        return self.notation

    def to_strings(self) -> List[tuple[str, str]]:
        """Return list of (card1_str, card2_str) tuples for DTO transport."""
        return [hand.to_strings() for hand in self.hands]

    def size(self) -> int:
        """Return number of unique hand types (1-169)."""
        return len(self.hands)

    def num_combos(self) -> int:
        """Return total number of card combinations (1-1326)."""
        return sum(hand.num_combos() for hand in self.hands)

    def contains(self, hand: Hand) -> bool:
        """Return True if the hand is in this range."""
        return hand in self.hands

    @staticmethod
    def union(range1: "HandRange", range2: "HandRange") -> "HandRange":
        """Return union of two ranges."""
        combined_hands = range1.hands + range2.hands
        combined_notation = f"{range1.notation} ∪ {range2.notation}"
        return HandRange(hands=combined_hands, notation=combined_notation)

    @staticmethod
    def intersection(range1: "HandRange", range2: "HandRange") -> "HandRange":
        """Return intersection of two ranges."""
        common_hands = [hand for hand in range1.hands if hand in range2.hands]
        combined_notation = f"{range1.notation} ∩ {range2.notation}"
        return HandRange(hands=common_hands, notation=combined_notation)

    def __str__(self) -> str:
        """String representation using shorthand notation."""
        return self.notation

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"HandRange.from_shorthand('{self.notation}')"

    def __hash__(self) -> int:
        """Hash based on the notation string."""
        return hash(self.notation)