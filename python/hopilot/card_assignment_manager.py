"""
Card Assignment Manager for HoPilot Poker Simulator

This module provides a centralized system for managing card assignments and range constraints
in the poker simulator GUI. It ensures that cards cannot be assigned to multiple positions
and handles the interaction between ranges and specific card assignments.
"""

from typing import List, Optional, Set, Dict
from hopilot.logging_config import get_logger
from hopilot.hand_range import HandRange

logger = get_logger(__name__)


class CardAssignmentManager:
    """
    Manages card assignments and range constraints across the poker game.

    Design Pattern: Observer Pattern - notifies listeners when assignments change
    """

    def __init__(self):
        self.logger = get_logger(__name__)

        # Card assignments
        self.hero_cards: List[Optional[str]] = [None, None]
        self.hero_range: Optional[str] = None
        self.villain_cards: List[List[Optional[str]]] = []
        self.villain_ranges: List[Optional[str]] = []
        self.board_cards: List[Optional[str]] = [None, None, None, None, None]

        # Observers for change notifications
        self._observers: List[callable] = []

    def add_observer(self, observer: callable):
        """Add an observer to be notified of assignment changes."""
        self._observers.append(observer)

    def remove_observer(self, observer: callable):
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_observers(self):
        """Notify all observers of changes."""
        for observer in self._observers:
            try:
                observer()
            except Exception as e:
                self.logger.error(f"Error notifying observer: {e}")

    def set_hero_card(self, index: int, card: Optional[str]):
        """Set a specific hero hole card."""
        self.hero_cards[index] = card
        if card:  # If setting a specific card
            self.hero_range = None  # Clear range
        self._notify_observers()

    def set_hero_range(self, range_str: Optional[str]):
        """Set hero range. Clears specific cards if setting a range."""
        self.hero_range = range_str
        if range_str:  # If setting a range
            self.hero_cards = [None, None]  # Clear specific cards
        self._notify_observers()

    def set_villain_cards(self, index: int, cards: List[Optional[str]]):
        """Set villain hole cards."""
        while len(self.villain_cards) <= index:
            self.villain_cards.append([None, None])
        self.villain_cards[index] = cards.copy()
        if any(cards):  # If any specific cards are set
            self.villain_ranges[index] = None  # Clear range
        self._notify_observers()

    def set_villain_card(self, villain_index: int, card_index: int, card: Optional[str]):
        """Set a specific villain hole card."""
        while len(self.villain_cards) <= villain_index:
            self.villain_cards.append([None, None])
        self.villain_cards[villain_index][card_index] = card
        if card:  # If setting a specific card
            self.villain_ranges[villain_index] = None  # Clear range
        self._notify_observers()

    def set_villain_range(self, index: int, range_str: Optional[str]):
        """Set villain range."""
        while len(self.villain_ranges) <= index:
            self.villain_ranges.append(None)
        self.villain_ranges[index] = range_str
        if range_str:  # If setting a range
            while len(self.villain_cards) <= index:
                self.villain_cards.append([None, None])
            self.villain_cards[index] = [None, None]  # Clear specific cards
        self._notify_observers()

    def set_board_card(self, index: int, card: Optional[str]):
        """Set a board card."""
        self.board_cards[index] = card
        self._notify_observers()

    def get_blocked_cards(self) -> Set[str]:
        """
        Get all cards that are blocked from assignment.

        This includes:
        - All specifically assigned cards
        - All cards that are part of any player's range
        """
        blocked = set()

        # Add specifically assigned cards
        for card in self.hero_cards:
            if card:
                blocked.add(card)

        for villain in self.villain_cards:
            for card in villain:
                if card:
                    blocked.add(card)

        for card in self.board_cards:
            if card:
                blocked.add(card)

        # Add cards from ranges
        if self.hero_range:
            try:
                range_cards = HandRange.parse_shorthand(self.hero_range)
                for card1, card2 in range_cards:
                    blocked.add(card1)
                    blocked.add(card2)
            except Exception as e:
                self.logger.error(f"Error parsing hero range '{self.hero_range}': {e}")

        for villain_range in self.villain_ranges:
            if villain_range:
                try:
                    range_cards = HandRange.parse_shorthand(villain_range)
                    for card1, card2 in range_cards:
                        blocked.add(card1)
                        blocked.add(card2)
                except Exception as e:
                    self.logger.error(f"Error parsing villain range '{villain_range}': {e}")

        return blocked

    def can_assign_card(self, card: str) -> bool:
        """Check if a card can be assigned (not blocked)."""
        return card not in self.get_blocked_cards()

    def can_assign_range(self, range_str: str) -> bool:
        """Check if a range can be assigned (no conflicts with existing assignments)."""
        try:
            range_cards = HandRange.parse_shorthand(range_str)
            blocked_cards = self.get_blocked_cards()

            # Check if any cards in the range are already blocked
            for card1, card2 in range_cards:
                if card1 in blocked_cards or card2 in blocked_cards:
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error parsing range '{range_str}': {e}")
            return False

    def get_available_cards(self) -> Set[str]:
        """Get all cards that are available for assignment."""
        all_cards = {f"{rank}{suit}" for rank in "23456789TJQKA" for suit in "shcd"}
        return all_cards - self.get_blocked_cards()

    def get_hero_state(self) -> Dict:
        """Get hero's current state."""
        return {
            'cards': self.hero_cards.copy(),
            'range': self.hero_range
        }

    def get_villain_state(self, index: int) -> Dict:
        """Get villain's current state."""
        while len(self.villain_cards) <= index:
            self.villain_cards.append([None, None])
        while len(self.villain_ranges) <= index:
            self.villain_ranges.append(None)

        return {
            'cards': self.villain_cards[index].copy(),
            'range': self.villain_ranges[index]
        }

    def get_board_state(self) -> List[Optional[str]]:
        """Get board's current state."""
        return self.board_cards.copy()