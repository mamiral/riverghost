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
from hopilot.models import (
    GameState, Player, Bet, BoardCard, Jackpot
)
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

    def store_game_state(self, simulation_id: int, matrix_cell_id: int,
                        timestamp: str, round_name: str, pot_size: float,
                        board_cards: List[str], outcome: str) -> int:
        """
        Store a game state in the database.
        """
        session = self._get_session()

        # Create board cards (always create a record, use placeholders if no cards)
        board = BoardCard(
            flop1=board_cards[0] if len(board_cards) > 0 else '??',
            flop2=board_cards[1] if len(board_cards) > 1 else '??',
            flop3=board_cards[2] if len(board_cards) > 2 else '??',
            turn=board_cards[3] if len(board_cards) > 3 else '??',
            river=board_cards[4] if len(board_cards) > 4 else '??'
        )
        session.add(board)
        session.flush()  # Get board ID

        # Create game state
        game_state = GameState(
            cell_id=matrix_cell_id,
            timestamp=datetime.fromisoformat(timestamp),
            round=round_name,
            pot_size=pot_size,
            board_cards_id=board.id,
            outcome=outcome
        )
        session.add(game_state)
        session.flush()  # Get game state ID

        self.logger.debug(f"Stored game state {game_state.id} for cell {matrix_cell_id}")
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
                    is_hero: bool) -> int:
        """
        Store a player in the database.
        """
        session = self._get_session()

        player = Player(
            game_state_id=game_state_id,
            position=position,
            hole_cards=''.join(hole_cards),
            stack_size=stack_size,
            is_hero=is_hero
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
        Store board cards in the database.
        """
        session = self._get_session()

        board = BoardCard(
            flop1=flop1,
            flop2=flop2,
            flop3=flop3,
            turn=turn,
            river=river
        )
        session.add(board)
        session.flush()

        self.logger.debug(f"Stored board cards {board.id}")
        return board.id

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