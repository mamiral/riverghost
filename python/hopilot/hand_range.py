"""
Hand Range Abstraction Layer for HoPilot

This module provides parsing, expansion, and display utilities for poker hand ranges
using professional shorthand notation (e.g., "AKs", "QJo", "22", "A5s-A2s", "KTs+").
"""

from typing import List, Set, Dict, Optional, Tuple
import re
from hopilot.logging_config import get_logger

logger = get_logger(__name__)

# Rank order for poker (Ace high)
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
RANK_VALUES = {rank: i for i, rank in enumerate(RANKS)}

SUITS = ['s', 'h', 'd', 'c']
SUIT_NAMES = {'s': 'spades', 'h': 'hearts', 'd': 'diamonds', 'c': 'clubs'}


class HandRange:
    """
    Class for parsing and expanding poker hand ranges.
    """

    @staticmethod
    def parse_shorthand(shorthand: str) -> List[Tuple[str, str]]:
        """
        Parse shorthand notation and return list of (card1, card2) tuples.
        Cards are in format like 'As', 'Kh', etc.

        Examples:
        - "AKs" -> [('As', 'Ks'), ('Ah', 'Kh'), ('Ad', 'Kd'), ('Ac', 'Kc')]
        - "AKo" -> all offsuit AK combinations
        - "22" -> all pocket twos combinations
        - "A5s-A2s" -> A5s, A4s, A3s, A2s
        - "KTs+" -> KTs and higher suited hands (KQ, KJ, KT)
        """
        shorthand = shorthand.strip().upper()

        # Handle ranges with '+'
        if '+' in shorthand:
            return HandRange._parse_plus_range(shorthand)

        # Handle ranges with '-'
        if '-' in shorthand:
            return HandRange._parse_dash_range(shorthand)

        # Handle single hand specifications
        return HandRange._parse_single_hand(shorthand)

    @staticmethod
    def _parse_single_hand(hand: str) -> List[Tuple[str, str]]:
        """Parse a single hand like 'AKs', 'QJo', '22'"""
        if len(hand) == 2:
            # Pocket pair like '22', 'AA'
            rank1 = hand[0]
            rank2 = hand[1]
            if rank1 != rank2:
                logger.warning(f"Invalid pocket pair: {hand}")
                return []
            return HandRange._expand_pair(rank1)

        elif len(hand) == 3:
            # Two cards with suited/offsuit like 'AKs', 'QJo'
            rank1 = hand[0]
            rank2 = hand[1]
            suited = hand[2].lower()

            if suited not in ['s', 'o']:
                logger.warning(f"Invalid suited indicator: {hand}")
                return []

            if rank1 == rank2:
                # This would be a pair, but with s/o doesn't make sense
                logger.warning(f"Pair with suited/offsuit doesn't make sense: {hand}")
                return []

            return HandRange._expand_two_cards(rank1, rank2, suited == 's')

        else:
            logger.warning(f"Invalid hand format: {hand}")
            return []

    @staticmethod
    def _parse_dash_range(range_str: str) -> List[Tuple[str, str]]:
        """Parse range like 'A5s-A2s' or '22-99'"""
        parts = range_str.split('-')
        if len(parts) != 2:
            logger.warning(f"Invalid range format: {range_str}")
            return []

        start_hand = parts[0]
        end_hand = parts[1]

        # For now, assume same format for start and end
        start_hands = HandRange._parse_single_hand(start_hand)
        end_hands = HandRange._parse_single_hand(end_hand)

        if not start_hands or not end_hands:
            return []

        # Get the ranks involved
        start_rank1 = start_hands[0][0][0]  # First card's rank
        start_rank2 = start_hands[0][1][0]  # Second card's rank
        end_rank1 = end_hands[0][0][0]
        end_rank2 = end_hands[0][1][0]

        # Assume it's Axs-Ays where x > y
        if start_rank1 != 'A' or end_rank1 != 'A' or start_rank2 == end_rank2:
            logger.warning(f"Unsupported range format: {range_str}")
            return []

        # Get the range of second ranks
        start_idx = RANK_VALUES[start_rank2]
        end_idx = RANK_VALUES[end_rank2]

        if start_idx <= end_idx:
            logger.warning(f"Invalid range order: {range_str}")
            return []

        # Determine if suited or offsuit
        suited = 's' in start_hand.lower()

        result = []
        for i in range(end_idx, start_idx + 1):
            rank = RANKS[i]
            result.extend(HandRange._expand_two_cards('A', rank, suited))

        return result

    @staticmethod
    def _parse_plus_range(range_str: str) -> List[Tuple[str, str]]:
        """Parse range like 'KTs+' """
        base_hand = range_str[:-1]  # Remove '+'
        base_hands = HandRange._parse_single_hand(base_hand)

        if not base_hands:
            return []

        # Assume it's suited connectors like 'KTs+'
        # Meaning KT, KJ, KQ suited and higher
        # But this is complex, for now just return the base
        logger.warning(f"Plus ranges not fully implemented: {range_str}")
        return base_hands

    @staticmethod
    def _expand_pair(rank: str) -> List[Tuple[str, str]]:
        """Expand pocket pair to all suit combinations"""
        cards = []
        for suit1 in SUITS:
            for suit2 in SUITS:
                if suit1 != suit2:
                    card1 = f"{rank}{suit1}"
                    card2 = f"{rank}{suit2}"
                    cards.append((card1, card2))
        return cards

    @staticmethod
    def _expand_two_cards(rank1: str, rank2: str, suited: bool) -> List[Tuple[str, str]]:
        """Expand two different ranks to all suit combinations"""
        cards = []
        for suit1 in SUITS:
            for suit2 in SUITS:
                if suited and suit1 == suit2:
                    card1 = f"{rank1}{suit1}"
                    card2 = f"{rank2}{suit2}"
                    cards.append((card1, card2))
                elif not suited and suit1 != suit2:
                    card1 = f"{rank1}{suit1}"
                    card2 = f"{rank2}{suit2}"
                    cards.append((card1, card2))
        return cards

    @staticmethod
    def shorthand_from_cards(cards: List[str]) -> str:
        """
        Convert explicit cards to shorthand notation.
        cards: list of 2 card strings like ['As', 'Kh']
        Returns shorthand like 'AKo' or 'AKs'
        """
        if len(cards) != 2:
            return ""

        card1, card2 = cards
        rank1 = card1[0]
        suit1 = card1[1]
        rank2 = card2[0]
        suit2 = card2[1]

        # Ensure consistent ordering: higher rank first
        if RANK_VALUES[rank1] < RANK_VALUES[rank2]:
            rank1, rank2 = rank2, rank1
            suit1, suit2 = suit2, suit1

        suited = suit1 == suit2
        suited_str = 's' if suited else 'o'

        if rank1 == rank2:
            return f"{rank1}{rank2}"
        else:
            return f"{rank1}{rank2}{suited_str}"


def expand_range_to_hands(range_str: str) -> List[List[str]]:
    """
    Expand a range string to list of hole card combinations.
    Each combination is a list of 2 card strings.

    Example: "AKs" -> [['As', 'Ks'], ['Ah', 'Kh'], ...]
    """
    tuples = HandRange.parse_shorthand(range_str)
    return [[card1, card2] for card1, card2 in tuples]


def validate_range_syntax(range_str: str) -> bool:
    """
    Validate if a range string has correct syntax.
    """
    try:
        hands = expand_range_to_hands(range_str)
        return len(hands) > 0
    except:
        return False