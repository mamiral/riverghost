"""
Database persistence strategy using SQLAlchemy.

This strategy implements genuine data storage in the SQLite database
with proper foreign key constraints and transaction management.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from hopilot.logging_config import get_logger
from .base import GameStatePersistence
from hopilot.models import GameState, Player, Bet, Jackpot
from hopilot.models.player import HandClass
from hopilot.db import get_session

logger = get_logger(__name__)


class DatabasePersistenceStrategy(GameStatePersistence):
    """
    Production persistence strategy using SQLAlchemy ORM.

    Stores complete game state data in the database with proper
    relationships and constraints. Ensures genuine data capture
    for the GameStates-first architecture.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize with optional session.

        Args:
            session: SQLAlchemy session to use. If None, gets from global factory.
        """
        super().__init__()
        self._session = session
        self._owns_session = session is None

    def _get_session(self) -> Session:
        """Get the current session, creating one if needed."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def store_game_state(self, timestamp: str, round_name: str, pot_size: float,
                        board_cards: List[str], outcome: str) -> int:
        """
        Store a game state in the database.
        """
        session = self._get_session()

        # Create game state with board cards as comma-separated string
        board_cards_str = ','.join(board_cards) if board_cards else ''
        game_state = GameState(
            timestamp=datetime.fromisoformat(timestamp),
            round=round_name,
            pot_size=pot_size,
            board_cards_str=board_cards_str,
            outcome=outcome
        )
        session.add(game_state)
        session.flush()  # Get game state ID

        self.logger.debug(f"Stored game state {game_state.id}")
        return game_state.id

    def update_game_state_outcome(self, game_state_id: int, outcome: str) -> None:
        """
        Update the outcome of an existing game state.
        """
        session = self._get_session()
        
        game_state = session.query(GameState).filter(GameState.id == game_state_id).first()
        if game_state:
            game_state.outcome = outcome
            self.logger.debug(f"Updated game state {game_state_id} outcome to {outcome}")
        else:
            self.logger.warning(f"Game state {game_state_id} not found for outcome update")

    def store_player(self, game_state_id: int, position: str,
                    hole_cards: List[str], stack_size: float,
                    is_hero: bool, hand_class: Optional[str] = None,
                    final_strength: Optional[int] = None) -> int:
        """
        Store a player in the database.
        """
        session = self._get_session()

        hand_class_enum = None
        if hand_class is not None:
            hand_class_enum = HandClass(hand_class)

        player = Player(
            game_state_id=game_state_id,
            position=position,
            hole_cards=''.join(hole_cards),
            stack_size=stack_size,
            is_hero=is_hero,
            hand_class=hand_class_enum,
            final_strength=final_strength
        )
        session.add(player)
        session.flush()

        self.logger.debug(f"Stored player {player.id} in game state {game_state_id}")
        return player.id

    def store_bet(self, game_state_id: int, player_id: int,
                 amount: float, action_type: str, round_name: str = "preflop") -> int:
        """
        Store a bet in the database.
        """
        session = self._get_session()

        bet = Bet(
            game_state_id=game_state_id,
            player_id=player_id,
            amount=amount,
            action_type=action_type,
            round=round_name
        )
        session.add(bet)
        session.flush()

        self.logger.debug(f"Stored bet {bet.id} for player {player_id} in game state {game_state_id}")
        return bet.id

    def store_board_cards(self, flop1: str, flop2: str, flop3: str,
                         turn: str, river: str) -> int:
        """
        Legacy board card persistence is no longer supported.

        This method remains for interface compatibility, but it does not
        persist a separate BoardCard record in the active GameStates-first model.
        """
        self.logger.warning(
            "store_board_cards() is deprecated and not supported in the current architecture."
        )
        return -1

    def store_jackpot(self, game_state_id: int, player_id: int,
                     jackpot_type: str, payout_amount: float,
                     cards_used: List[str]) -> int:
        """
        Store a jackpot event in the database.
        """
        session = self._get_session()

        jackpot = Jackpot(
            game_state_id=game_state_id,
            player_id=player_id,
            jackpot_type=jackpot_type,
            payout_amount=payout_amount,
            cards_used=cards_used
        )
        session.add(jackpot)
        session.flush()

        self.logger.debug(f"Stored jackpot {jackpot.id} for player {player_id} in game state {game_state_id}")
        return jackpot.id

    def commit_transaction(self) -> None:
        """
        Commit the current transaction.
        """
        if self._session is not None:
            try:
                self._session.commit()
                self.logger.debug("Transaction committed")
            except Exception as e:
                self.logger.error(f"Transaction commit failed: {e}")
                self._session.rollback()
                raise

    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.
        """
        if self._session is not None:
            self._session.rollback()
            self.logger.debug("Transaction rolled back")

    def close(self) -> None:
        """
        Close the database session if owned by this instance.
        """
        if self._owns_session and self._session is not None:
            self._session.close()
            self._session = None
            self.logger.debug("Database session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._owns_session and self._session is not None:
            self._session.close()