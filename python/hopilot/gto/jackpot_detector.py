"""
Jackpot Detection Implementation (JACKPOT-002)

Implements jackpot detection logic during board card evaluation.
Detects qualifying jackpot hands and calculates payouts according to
the rules defined in jackpot_detection_rules.py.

PHASE 2: P1 - CRITICAL
- Implements jackpot detection during simulation runs
- Calculates correct payout amounts
- Properly identifies qualifying cards
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from specs.jackpot_detection_rules import (
    JACKPOT_RULES,
    JACKPOT_PRIORITY_ORDER,
    PLATFORM_RULES
)

logger = logging.getLogger(__name__)


@dataclass
class JackpotResult:
    """Result of jackpot detection for a hand."""
    jackpot_type: str
    payout_multiplier: int
    qualifying_cards: List[str]
    payout_amount: float
    detected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'jackpot_type': self.jackpot_type,
            'payout_multiplier': self.payout_multiplier,
            'qualifying_cards': self.qualifying_cards,
            'payout_amount': self.payout_amount,
            'detected': self.detected
        }


class JackpotDetector:
    """
    Detects jackpots in poker hands according to platform rules.

    Evaluates player hole cards + board cards to determine if any
    jackpot conditions are met, following priority order.
    """

    def __init__(self, platform: str = 'ggpoker'):
        """
        Initialize jackpot detector for specific platform.

        Args:
            platform: Target poker platform ('ggpoker', 'pokerstars', etc.)
        """
        self.platform = platform
        self.platform_rules = PLATFORM_RULES.get(platform, PLATFORM_RULES['ggpoker'])

        if not self.platform_rules['jackpot_enabled']:
            logger.warning(f"Jackpots not enabled for platform: {platform}")

    def detect_jackpot(self, hole_cards: List[str], board_cards: List[str],
                      pot_size: float) -> JackpotResult:
        """
        Detect jackpot in a poker hand.

        Args:
            hole_cards: Player's 2 hole cards (e.g., ['As', 'Kh'])
            board_cards: Board cards (0-5 cards: flop, turn, river)
            pot_size: Current pot size for payout calculation

        Returns:
            JackpotResult with detection details
        """
        if not self.platform_rules['jackpot_enabled']:
            return JackpotResult('high_card', 0, [], 0.0, False)

        # Combine all available cards
        all_cards = hole_cards + board_cards

        if len(all_cards) < 5:
            # Need at least 5 cards for most jackpots
            return JackpotResult('high_card', 0, [], 0.0, False)

        # Check for jackpots in priority order
        for jackpot_type in JACKPOT_PRIORITY_ORDER:
            if jackpot_type == 'high_card':
                # High card is always "detected" but pays nothing
                continue

            result = self._check_jackpot_type(jackpot_type, all_cards)
            if result:
                qualifying_cards, card_count = result
                rules = JACKPOT_RULES[jackpot_type]
                multiplier = rules['payout_multiplier']
                payout = pot_size * multiplier

                return JackpotResult(
                    jackpot_type=jackpot_type,
                    payout_multiplier=multiplier,
                    qualifying_cards=qualifying_cards,
                    payout_amount=payout,
                    detected=True
                )

        # No jackpot detected
        return JackpotResult('high_card', 0, [], 0.0, False)

    def _check_jackpot_type(self, jackpot_type: str, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """
        Check if cards qualify for specific jackpot type.

        Args:
            jackpot_type: Type of jackpot to check
            cards: All available cards

        Returns:
            Tuple of (qualifying_cards, card_count) if qualified, None otherwise
        """
        rules = JACKPOT_RULES[jackpot_type]

        if jackpot_type == 'royal_flush':
            return self._check_royal_flush(cards)
        elif jackpot_type == 'straight_flush':
            return self._check_straight_flush(cards)
        elif jackpot_type == 'four_of_a_kind':
            return self._check_four_of_a_kind(cards)
        elif jackpot_type == 'full_house':
            return self._check_full_house(cards)
        elif jackpot_type == 'flush':
            return self._check_flush(cards)
        elif jackpot_type == 'straight':
            return self._check_straight(cards)
        elif jackpot_type == 'three_of_a_kind':
            return self._check_three_of_a_kind(cards)
        elif jackpot_type == 'two_pair':
            return self._check_two_pair(cards)
        elif jackpot_type == 'one_pair':
            return self._check_one_pair(cards)
        else:
            return None

    def _check_royal_flush(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for royal flush (A,K,Q,J,T same suit)."""
        royal_ranks = ['A', 'K', 'Q', 'J', 'T']

        # Group cards by suit
        suit_groups = self._group_by_suit(cards)

        for suit, suit_cards in suit_groups.items():
            if len(suit_cards) >= 5:
                # Check if we have all royal ranks in this suit
                suit_ranks = [self._card_rank(card) for card in suit_cards]
                if all(rank in suit_ranks for rank in royal_ranks):
                    # Find the actual royal cards
                    royal_cards = []
                    for card in suit_cards:
                        if self._card_rank(card) in royal_ranks:
                            royal_cards.append(card)
                    if len(royal_cards) >= 5:
                        return royal_cards[:5], 5

        return None

    def _check_straight_flush(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for straight flush (5 consecutive cards same suit, not royal)."""
        # Group cards by suit
        suit_groups = self._group_by_suit(cards)

        for suit, suit_cards in suit_groups.items():
            if len(suit_cards) >= 5:
                # Check for consecutive sequences
                straight_cards = self._find_straight(suit_cards)
                if straight_cards and len(straight_cards) >= 5:
                    # Make sure it's not a royal flush
                    ranks = [self._card_rank(card) for card in straight_cards]
                    royal_ranks = ['A', 'K', 'Q', 'J', 'T']
                    if not all(rank in ranks for rank in royal_ranks):
                        return straight_cards[:5], 5

        return None

    def _check_four_of_a_kind(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for four of a kind (all 4 suits of same rank)."""
        rank_groups = self._group_by_rank(cards)

        for rank, rank_cards in rank_groups.items():
            if len(rank_cards) >= 4:
                return rank_cards[:4], 4

        return None

    def _check_full_house(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for full house (3 of a kind + pair)."""
        rank_groups = self._group_by_rank(cards)

        # Find trips and pairs
        trips = []
        pairs = []

        for rank, rank_cards in rank_groups.items():
            if len(rank_cards) >= 3:
                trips.append((rank, rank_cards[:3]))
            elif len(rank_cards) >= 2:
                pairs.append((rank, rank_cards[:2]))

        if trips and pairs:
            # Return trips + pair
            qualifying_cards = trips[0][1] + pairs[0][1]
            return qualifying_cards, 5
        elif len(trips) >= 2:
            # Two sets of trips (6+ cards of same rank)
            qualifying_cards = trips[0][1] + trips[1][1][:2]
            return qualifying_cards, 5

        return None

    def _check_flush(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for flush (5+ cards same suit)."""
        suit_groups = self._group_by_suit(cards)

        for suit, suit_cards in suit_groups.items():
            if len(suit_cards) >= 5:
                return suit_cards[:5], 5

        return None

    def _check_straight(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for straight (5 consecutive cards, mixed suits)."""
        straight_cards = self._find_straight(cards)
        if straight_cards and len(straight_cards) >= 5:
            return straight_cards[:5], 5

        return None

    def _check_three_of_a_kind(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for three of a kind."""
        rank_groups = self._group_by_rank(cards)

        for rank, rank_cards in rank_groups.items():
            if len(rank_cards) >= 3:
                return rank_cards[:3], 3

        return None

    def _check_two_pair(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for two pair."""
        rank_groups = self._group_by_rank(cards)

        pairs = []
        for rank, rank_cards in rank_groups.items():
            if len(rank_cards) >= 2:
                pairs.append(rank_cards[:2])

        if len(pairs) >= 2:
            return pairs[0] + pairs[1], 4

        return None

    def _check_one_pair(self, cards: List[str]) -> Optional[Tuple[List[str], int]]:
        """Check for one pair."""
        rank_groups = self._group_by_rank(cards)

        for rank, rank_cards in rank_groups.items():
            if len(rank_cards) >= 2:
                return rank_cards[:2], 2

        return None

    def _group_by_suit(self, cards: List[str]) -> Dict[str, List[str]]:
        """Group cards by suit."""
        suits = {}
        for card in cards:
            suit = card[1]  # Second character is suit
            if suit not in suits:
                suits[suit] = []
            suits[suit].append(card)
        return suits

    def _group_by_rank(self, cards: List[str]) -> Dict[str, List[str]]:
        """Group cards by rank."""
        ranks = {}
        for card in cards:
            rank = self._card_rank(card)
            if rank not in ranks:
                ranks[rank] = []
            ranks[rank].append(card)
        return ranks

    def _card_rank(self, card: str) -> str:
        """Get card rank (first character)."""
        return card[0]

    def _card_rank_value(self, card: str) -> int:
        """Get numerical value of card rank for straight checking."""
        rank = self._card_rank(card)
        rank_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10,
            'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        return rank_values.get(rank, 0)

    def _find_straight(self, cards: List[str]) -> Optional[List[str]]:
        """Find longest straight in cards."""
        if len(cards) < 5:
            return None

        # Get unique ranks sorted by value
        rank_values = {}
        for card in cards:
            rank = self._card_rank(card)
            value = self._card_rank_value(card)
            if rank not in rank_values:
                rank_values[rank] = (value, card)

        # Sort by rank value
        sorted_ranks = sorted(rank_values.values(), key=lambda x: x[0])

        # Check for consecutive sequences
        current_straight = []
        longest_straight = []

        for i, (value, card) in enumerate(sorted_ranks):
            if not current_straight:
                current_straight = [card]
            else:
                last_value = self._card_rank_value(current_straight[-1])
                if value == last_value + 1:
                    current_straight.append(card)
                elif value != last_value:
                    # Gap found, check if current straight is longest
                    if len(current_straight) > len(longest_straight):
                        longest_straight = current_straight[:]
                    current_straight = [card]

        # Check final straight
        if len(current_straight) > len(longest_straight):
            longest_straight = current_straight

        # Special case: wheel (A-2-3-4-5)
        if len(sorted_ranks) >= 5:
            wheel_ranks = ['A', '2', '3', '4', '5']
            wheel_cards = []
            for rank in wheel_ranks:
                if rank in rank_values:
                    wheel_cards.append(rank_values[rank][1])

            if len(wheel_cards) >= 5 and len(wheel_cards) > len(longest_straight):
                longest_straight = wheel_cards

        return longest_straight if len(longest_straight) >= 5 else None


# ============================================================================
# INTEGRATION FUNCTIONS
# ============================================================================

def detect_hand_jackpot(hole_cards: List[str], board_cards: List[str],
                        pot_size: float, platform: str = 'ggpoker') -> JackpotResult:
    """
    Convenience function to detect jackpot in a poker hand.

    Args:
        hole_cards: Player's 2 hole cards
        board_cards: Board cards (flop/turn/river)
        pot_size: Current pot size
        platform: Target platform

    Returns:
        JackpotResult with detection details
    """
    detector = JackpotDetector(platform)
    return detector.detect_jackpot(hole_cards, board_cards, pot_size)


def should_trigger_jackpot(jackpot_result: JackpotResult) -> bool:
    """
    Determine if jackpot should be triggered based on result.

    Args:
        jackpot_result: Result from jackpot detection

    Returns:
        True if jackpot should be awarded
    """
    return jackpot_result.detected and jackpot_result.payout_multiplier > 0