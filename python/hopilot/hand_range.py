"""
Hand Range Abstraction Layer for HoPilot

This module provides parsing, expansion, and display utilities for poker hand ranges
using professional shorthand notation (e.g., "AKs", "QJo", "22", "A5s-A2s", "KTs+").
"""

from typing import List, Set, Dict, Optional, Tuple
import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from hopilot.logging_config import get_logger

logger = get_logger(__name__)

# Rank order for poker (Ace high)
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
RANK_VALUES = {rank: i for i, rank in enumerate(RANKS)}

SUITS = ['s', 'h', 'd', 'c']
SUIT_NAMES = {'s': 'spades', 'h': 'hearts', 'd': 'diamonds', 'c': 'clubs'}


class PokerRange(BaseModel):
    """Represents a collection of poker hands with metadata."""
    name: str
    description: Optional[str] = None
    hands: List[str]  # List of shorthand hand notations (e.g., ["AA", "AKs", "QQ"])
    tags: Optional[List[str]] = None  # e.g., ["broadway", "premium", "suited"]
    created: datetime = Field(default_factory=datetime.now)
    modified: datetime = Field(default_factory=datetime.now)

    @field_validator('hands')
    @classmethod
    def validate_hands(cls, v):
        """Ensure all hands are valid poker hand notations."""
        for hand in v:
            if not HandRange.is_valid_shorthand(hand):
                raise ValueError(f"Invalid hand notation: {hand}")
        return v

    def expand_to_cards(self) -> List[List[str]]:
        """Expand range to all possible card combinations."""
        return HandRange.expand_range_to_hands(self.hands)


class HandRange:
    """
    Class for parsing and expanding poker hand ranges.
    """

    @staticmethod
    def is_valid_shorthand(shorthand: str) -> bool:
        """
        Check if a shorthand notation is valid.
        
        Args:
            shorthand: Hand shorthand (e.g., "AKs", "22", "A5s-A2s")
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Import here to avoid circular import
            from hopilot.hand_range import expand_range_to_hands
            hands = expand_range_to_hands(shorthand)
            return len(hands) > 0
        except:
            return False

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

    Supports combined ranges with '+' separator.
    Example: "AKs+AQs+22" -> all combinations from AKs, AQs, and 22
    """
    if '+' in range_str:
        parts = [part.strip() for part in range_str.split('+') if part.strip()]
        all_hands = []
        for part in parts:
            tuples = HandRange.parse_shorthand(part)
            all_hands.extend([[card1, card2] for card1, card2 in tuples])
        return all_hands
    else:
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


def split_range_to_components(range_str: str) -> Set[str]:
    """
    Split a combined range string into individual matrix components.
    
    Example: "AKs+22" -> {"AKs", "22"}
    Returns set of strings that correspond to RangePicker matrix cells.
    """
    if not range_str:
        return set()
    
    components = set()
    
    try:
        # Expand the range to all individual hands
        hands = expand_range_to_hands(range_str)
        
        # For each hand, determine what matrix component it represents
        for hand in hands:
            if len(hand) == 2:
                # Two cards - determine if suited, offsuit, or pair
                card1, card2 = hand
                rank1 = card1[0]
                suit1 = card1[1]
                rank2 = card2[0]
                suit2 = card2[1]
                
                # Ensure consistent ordering (higher rank first)
                if RANK_VALUES[rank1] < RANK_VALUES[rank2]:
                    rank1, rank2 = rank2, rank1
                    suit1, suit2 = suit2, suit1
                
                if rank1 == rank2:
                    # Pocket pair
                    components.add(f"{rank1}{rank2}")
                elif suit1 == suit2:
                    # Suited
                    components.add(f"{rank1}{rank2}s")
                else:
                    # Offsuit
                    components.add(f"{rank1}{rank2}o")
    except Exception as e:
        logger.warning(f"Failed to parse range '{range_str}': {e}")
        # Fallback to simple splitting
        parts = [part.strip() for part in range_str.split('+') if part.strip()]
        for part in parts:
            if len(part) >= 2:
                components.add(part)
    
    return components

    @staticmethod
    def shorthand_from_cards(cards: List[str]) -> str:
        """
        Convert two cards to shorthand notation.

        Args:
            cards: List of two card names (e.g., ['As', 'Kh'])

        Returns:
            Shorthand string (e.g., 'AKs', 'AKo', 'AA')
        """
        if len(cards) != 2:
            return ""

        card1, card2 = cards
        rank1 = card1[0]
        suit1 = card1[1]
        rank2 = card2[0]
        suit2 = card2[1]

        # Ensure consistent ordering (higher rank first)
        if RANK_VALUES[rank1] < RANK_VALUES[rank2]:
            rank1, rank2 = rank2, rank1
            suit1, suit2 = suit2, suit1
        elif RANK_VALUES[rank1] == RANK_VALUES[rank2]:
            # For pairs, sort by suit for consistency
            if suit1 > suit2:
                suit1, suit2 = suit2, suit1

        if rank1 == rank2:
            # Pocket pair
            return f"{rank1}{rank2}"
        elif suit1 == suit2:
            # Suited
            return f"{rank1}{rank2}s"
        else:
            # Offsuit
            return f"{rank1}{rank2}o"