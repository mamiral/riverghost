"""
Jackpot detection and analysis for poker games.

Provides functionality to detect jackpot-eligible hands and calculate
payouts based on platform-specific rules.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from hopilot.logging_config import get_logger
from hopilot.models import GameState, Player

logger = get_logger(__name__)


class JackpotDetector:
    """
    Detects and evaluates jackpot conditions in poker hands.

    Supports various jackpot types as defined by poker platforms,
    with extensible rules for future jackpot types.
    """

    # Jackpot definitions with multipliers and detection rules
    JACKPOT_RULES = {
        'royal_flush': {
            'multiplier': 500,
            'description': 'Royal flush (A-K-Q-J-10 same suit)',
            'detector': '_detect_royal_flush'
        },
        'straight_flush': {
            'multiplier': 100,
            'description': 'Straight flush (5 consecutive cards same suit)',
            'detector': '_detect_straight_flush'
        },
        'four_of_a_kind': {
            'multiplier': 50,
            'description': 'Four of a kind',
            'detector': '_detect_four_of_a_kind'
        },
        'full_house': {
            'multiplier': 10,
            'description': 'Full house (3 of a kind + pair)',
            'detector': '_detect_full_house'
        },
        'flush': {
            'multiplier': 5,
            'description': 'Flush (5 cards same suit)',
            'detector': '_detect_flush'
        },
        'straight': {
            'multiplier': 4,
            'description': 'Straight (5 consecutive cards)',
            'detector': '_detect_straight'
        },
        'three_of_a_kind': {
            'multiplier': 3,
            'description': 'Three of a kind',
            'detector': '_detect_three_of_a_kind'
        },
        'two_pair': {
            'multiplier': 2,
            'description': 'Two pair',
            'detector': '_detect_two_pair'
        },
        'one_pair': {
            'multiplier': 1,
            'description': 'One pair',
            'detector': '_detect_one_pair'
        }
    }

    def __init__(self):
        """Initialize jackpot detector."""
        self.logger = get_logger(__name__)

    def detect_jackpots(self, game_state: GameState) -> List[Dict]:
        """
        Detect all jackpot conditions for a game state.

        Args:
            game_state: GameState instance with players and board cards

        Returns:
            List of jackpot dictionaries with type, payout, and cards used
        """
        jackpots = []

        # Check each player for jackpot conditions
        for player in [game_state.hero_player, game_state.villain_player]:
            if player:
                player_jackpots = self._detect_player_jackpots(player, game_state)
                jackpots.extend(player_jackpots)

        return jackpots

    def _detect_player_jackpots(self, player: Player, game_state: GameState) -> List[Dict]:
        """
        Detect jackpots for a specific player.

        Args:
            player: Player instance
            game_state: GameState instance

        Returns:
            List of jackpot dictionaries for this player
        """
        jackpots = []

        # Parse hole cards from string format (e.g., "AsKh")
        hole_cards = self._parse_hole_cards(player.hole_cards)
        if not hole_cards or len(hole_cards) != 2:
            return jackpots

        # Get board cards from the board_cards relationship
        board_card_obj = game_state.board_cards
        board_cards = [
            board_card_obj.flop1,
            board_card_obj.flop2,
            board_card_obj.flop3,
            board_card_obj.turn,
            board_card_obj.river
        ]

        all_cards = hole_cards + board_cards

        # Check each jackpot type
        for jackpot_type, rules in self.JACKPOT_RULES.items():
            detector_method = getattr(self, rules['detector'])
            is_jackpot, cards_used = detector_method(all_cards, hole_cards)

            if is_jackpot:
                payout = self._calculate_payout(jackpot_type, game_state.pot_size)
                jackpots.append({
                    'jackpot_type': jackpot_type,
                    'payout_amount': payout,
                    'cards_used': cards_used,
                    'hole_cards_contributed': self._hole_cards_contribute(cards_used, hole_cards)
                })

        return jackpots

    def _parse_hole_cards(self, hole_cards_str: str) -> List[str]:
        """
        Parse hole cards from string format.

        Args:
            hole_cards_str: Hole cards as string (e.g., "AsKh")

        Returns:
            List of individual card strings
        """
        if not hole_cards_str or len(hole_cards_str) != 4:
            return []

        # Split into two cards of 2 characters each
        return [hole_cards_str[:2], hole_cards_str[2:]]

    def _calculate_payout(self, jackpot_type: str, pot_size: Decimal) -> Decimal:
        """
        Calculate jackpot payout based on pot size and multiplier.

        Args:
            jackpot_type: Type of jackpot
            pot_size: Current pot size

        Returns:
            Payout amount
        """
        multiplier = self.JACKPOT_RULES[jackpot_type]['multiplier']
        return pot_size * multiplier

    def _hole_cards_contribute(self, cards_used: List[str], hole_cards: List[str]) -> bool:
        """
        Check if hole cards contribute to the jackpot hand.

        Args:
            cards_used: Cards that formed the jackpot
            hole_cards: Player's hole cards

        Returns:
            True if hole cards are part of the jackpot
        """
        return any(card in cards_used for card in hole_cards)

    # Jackpot detection methods
    def _detect_royal_flush(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect royal flush (A-K-Q-J-10 same suit)."""
        # Royal flush requires specific high cards
        royal_ranks = ['A', 'K', 'Q', 'J', 'T']

        for suit in ['s', 'h', 'd', 'c']:
            suit_cards = [card for card in all_cards if card.endswith(suit)]
            suit_ranks = [card[0] for card in suit_cards]

            if all(rank in suit_ranks for rank in royal_ranks):
                # Find the actual cards used
                royal_cards = [f"{rank}{suit}" for rank in royal_ranks if f"{rank}{suit}" in suit_cards]
                if len(royal_cards) >= 5:  # At least 5 cards for royal flush
                    return True, royal_cards[:5]

        return False, []

    def _detect_straight_flush(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect straight flush (5 consecutive cards same suit)."""
        # Check each suit for straights
        for suit in ['s', 'h', 'd', 'c']:
            suit_cards = [card for card in all_cards if card.endswith(suit)]
            if len(suit_cards) >= 5:
                # Convert to rank values for straight detection
                rank_values = self._cards_to_values(suit_cards)
                if self._has_straight(rank_values):
                    # Find the straight cards
                    straight_cards = self._find_straight_cards(suit_cards, rank_values)
                    if straight_cards:
                        return True, straight_cards

        return False, []

    def _detect_four_of_a_kind(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect four of a kind."""
        rank_counts = self._count_ranks(all_cards)
        for rank, count in rank_counts.items():
            if count >= 4:
                # Find the four cards
                four_cards = [card for card in all_cards if card.startswith(rank)][:4]
                return True, four_cards

        return False, []

    def _detect_full_house(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect full house (3 of a kind + pair)."""
        rank_counts = self._count_ranks(all_cards)

        three_kind = None
        pair = None

        for rank, count in rank_counts.items():
            if count >= 3 and three_kind is None:
                three_kind = rank
            elif count >= 2 and pair is None:
                pair = rank

        if three_kind and pair:
            # Find the cards
            three_cards = [card for card in all_cards if card.startswith(three_kind)][:3]
            pair_cards = [card for card in all_cards if card.startswith(pair)][:2]
            return True, three_cards + pair_cards

        return False, []

    def _detect_flush(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect flush (5 cards same suit)."""
        for suit in ['s', 'h', 'd', 'c']:
            suit_cards = [card for card in all_cards if card.endswith(suit)]
            if len(suit_cards) >= 5:
                return True, suit_cards[:5]

        return False, []

    def _detect_straight(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect straight (5 consecutive cards)."""
        rank_values = self._cards_to_values(all_cards)
        if self._has_straight(rank_values):
            straight_cards = self._find_straight_cards(all_cards, rank_values)
            if straight_cards:
                return True, straight_cards

        return False, []

    def _detect_three_of_a_kind(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect three of a kind."""
        rank_counts = self._count_ranks(all_cards)
        for rank, count in rank_counts.items():
            if count >= 3:
                three_cards = [card for card in all_cards if card.startswith(rank)][:3]
                return True, three_cards

        return False, []

    def _detect_two_pair(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect two pair."""
        rank_counts = self._count_ranks(all_cards)
        pairs = [rank for rank, count in rank_counts.items() if count >= 2]

        if len(pairs) >= 2:
            # Find the cards for two pairs
            pair1_cards = [card for card in all_cards if card.startswith(pairs[0])][:2]
            pair2_cards = [card for card in all_cards if card.startswith(pairs[1])][:2]
            return True, pair1_cards + pair2_cards

        return False, []

    def _detect_one_pair(self, all_cards: List[str], hole_cards: List[str]) -> Tuple[bool, List[str]]:
        """Detect one pair."""
        rank_counts = self._count_ranks(all_cards)
        for rank, count in rank_counts.items():
            if count >= 2:
                pair_cards = [card for card in all_cards if card.startswith(rank)][:2]
                return True, pair_cards

        return False, []

    # Helper methods
    def _cards_to_values(self, cards: List[str]) -> List[int]:
        """Convert cards to numerical values for straight detection."""
        rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                   'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        return sorted([rank_map[card[0]] for card in cards])

    def _has_straight(self, values: List[int]) -> bool:
        """Check if values contain a 5-card straight."""
        for i in range(len(values) - 4):
            if values[i:i+5] == list(range(values[i], values[i] + 5)):
                return True
        # Check for A-2-3-4-5 straight (Ace low)
        if set([14, 2, 3, 4, 5]).issubset(set(values)):
            return True
        return False

    def _find_straight_cards(self, cards: List[str], values: List[int]) -> List[str]:
        """Find the actual cards that form a straight."""
        # This is a simplified implementation
        # In a full implementation, you'd need more sophisticated logic
        # to handle suit preferences and exact straight identification
        return cards[:5]  # Simplified

    def _count_ranks(self, cards: List[str]) -> Dict[str, int]:
        """Count occurrences of each rank."""
        counts = {}
        for card in cards:
            rank = card[0]
            counts[rank] = counts.get(rank, 0) + 1
        return counts