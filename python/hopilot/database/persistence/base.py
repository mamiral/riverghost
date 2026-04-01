"""
Abstract base class for GameState persistence strategies.

This module defines the Strategy pattern interface for pluggable persistence
behaviors in the genuine GameStates-first architecture.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class GameStatePersistence(ABC):
    """
    Abstract base class for game state persistence strategies.

    Defines the interface that all persistence strategies must implement.
    This enables pluggable storage backends (database, in-memory, mock, etc.)
    while maintaining consistent behavior for the solver.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def store_game_state(self, simulation_id: int, matrix_cell_id: int,
                        timestamp: str, round_name: str, pot_size: float,
                        board_cards: List[str], outcome: str) -> int:
        """
        Store a game state and return its ID.

        Args:
            simulation_id: ID of the parent simulation
            matrix_cell_id: ID of the matrix cell this game state belongs to
            timestamp: ISO format timestamp
            round_name: Game round (preflop, flop, turn, river)
            pot_size: Total pot size
            board_cards: List of board card strings
            outcome: Game outcome description

        Returns:
            The ID of the stored game state
        """
        pass

    @abstractmethod
    def update_game_state_outcome(self, game_state_id: int, outcome: str) -> None:
        """
        Update the outcome of an existing game state.

        Args:
            game_state_id: ID of the game state to update
            outcome: New outcome description
        """
        pass

    @abstractmethod
    def store_player(self, game_state_id: int, position: str,
                    hole_cards: List[str], stack_size: float,
                    is_hero: bool) -> int:
        """
        Store a player in a game state and return its ID.

        Args:
            game_state_id: ID of the parent game state
            position: Player position (0-5)
            hole_cards: List of hole card strings
            stack_size: Player's chip stack
            is_hero: Whether this is the hero player

        Returns:
            The ID of the stored player
        """
        pass

    @abstractmethod
    def store_bet(self, game_state_id: int, player_id: int,
                 amount: float, action_type: str, round_name: str = "preflop") -> int:
        """
        Store a bet action and return its ID.

        Args:
            game_state_id: ID of the parent game state
            player_id: ID of the player making the bet
            amount: Bet amount
            action_type: Type of action (fold, call, raise, all_in)

        Returns:
            The ID of the stored bet
        """
        pass

    @abstractmethod
    def store_board_cards(self, flop1: str, flop2: str, flop3: str,
                         turn: str, river: str) -> int:
        """
        Store board cards and return the board ID.

        Args:
            flop1, flop2, flop3: Flop cards
            turn: Turn card
            river: River card

        Returns:
            The ID of the stored board
        """
        pass

    @abstractmethod
    def store_jackpot(self, game_state_id: int, player_id: int,
                     jackpot_type: str, payout_amount: float,
                     cards_used: List[str]) -> int:
        """
        Store a jackpot event and return its ID.

        Args:
            game_state_id: ID of the game state where jackpot occurred
            player_id: ID of the player who won the jackpot
            jackpot_type: Type of jackpot (straight_flush, royal_flush, etc.)
            payout_amount: Jackpot payout amount
            cards_used: List of cards that formed the jackpot hand

        Returns:
            The ID of the stored jackpot
        """
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        """
        Commit the current transaction.

        Should be called after storing a complete game state
        to ensure data consistency.
        """
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.

        Should be called on errors to maintain data integrity.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close any resources held by the persistence strategy.

        Should be called when the strategy is no longer needed
        to free database connections and other resources.
        """
        pass