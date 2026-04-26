"""
Mock persistence strategy for testing.

This strategy records all persistence calls without actually storing data,
enabling unit tests to verify that the solver calls the correct persistence methods.
"""

from typing import List, Dict, Any, Optional
from hopilot.logging_config import get_logger
from .base import GameStatePersistence

logger = get_logger(__name__)


class MockPersistenceStrategy(GameStatePersistence):
    """
    Mock persistence strategy for unit testing.

    Records all method calls and their arguments without performing
    actual data storage. Enables verification that the solver
    interacts correctly with the persistence interface.
    """

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        """Reset all call records."""
        self.store_game_state_calls = []
        self.store_player_calls = []
        self.store_bet_calls = []
        self.store_board_cards_calls = []
        self.store_jackpot_calls = []
        self.commit_calls = 0
        self.rollback_calls = 0

        # Mock return values
        self._next_game_state_id = 1
        self._next_player_id = 1
        self._next_bet_id = 1
        self._next_board_id = 1
        self._next_jackpot_id = 1

    def store_game_state(self, timestamp: str, round_name: str, pot_size: float,
                        board_cards: List[str], outcome: str) -> int:
        """
        Record game state storage call.
        """
        call_record = {
            'timestamp': timestamp,
            'round_name': round_name,
            'pot_size': pot_size,
            'board_cards': board_cards,
            'outcome': outcome
        }
        self.store_game_state_calls.append(call_record)

        game_state_id = self._next_game_state_id
        self._next_game_state_id += 1

        self.logger.debug(f"Mock stored game state {game_state_id}")
        return game_state_id

    def update_game_state_outcome(self, game_state_id: int, outcome: str) -> None:
        """
        Record game state outcome update call.
        """
        call_record = {
            'game_state_id': game_state_id,
            'outcome': outcome
        }
        if not hasattr(self, 'update_game_state_outcome_calls'):
            self.update_game_state_outcome_calls = []
        self.update_game_state_outcome_calls.append(call_record)

        self.logger.debug(f"Mock updated game state {game_state_id} outcome to {outcome}")

    def store_player(self, game_state_id: int, position: str,
                    hole_cards: List[str], stack_size: float,
                    is_hero: bool, hand_class: Optional[str] = None,
                    final_strength: Optional[int] = None) -> int:
        """
        Record player storage call.
        """
        call_record = {
            'game_state_id': game_state_id,
            'position': position,
            'hole_cards': hole_cards,
            'stack_size': stack_size,
            'is_hero': is_hero,
            'hand_class': hand_class,
            'final_strength': final_strength
        }
        self.store_player_calls.append(call_record)

        player_id = self._next_player_id
        self._next_player_id += 1

        self.logger.debug(f"Mock stored player {player_id} in game state {game_state_id}")
        return player_id

    def store_bet(self, game_state_id: int, player_id: int,
                 amount: float, action_type: str, round_name: str = "preflop") -> int:
        """
        Record bet storage call.
        """
        call_record = {
            'game_state_id': game_state_id,
            'player_id': player_id,
            'amount': amount,
            'action_type': action_type,
            'round_name': round_name
        }
        self.store_bet_calls.append(call_record)

        bet_id = self._next_bet_id
        self._next_bet_id += 1

        self.logger.debug(f"Mock stored bet {bet_id} for player {player_id} in game state {game_state_id}")
        return bet_id

    def store_board_cards(self, flop1: str, flop2: str, flop3: str,
                         turn: str, river: str) -> int:
        """
        Record board cards storage call.
        """
        call_record = {
            'flop1': flop1,
            'flop2': flop2,
            'flop3': flop3,
            'turn': turn,
            'river': river
        }
        self.store_board_cards_calls.append(call_record)

        board_id = self._next_board_id
        self._next_board_id += 1

        self.logger.debug(f"Mock stored board cards {board_id}")
        return board_id

    def store_jackpot(self, game_state_id: int, player_id: int,
                     jackpot_type: str, payout_amount: float,
                     cards_used: List[str]) -> int:
        """
        Record jackpot storage call.
        """
        call_record = {
            'game_state_id': game_state_id,
            'player_id': player_id,
            'jackpot_type': jackpot_type,
            'payout_amount': payout_amount,
            'cards_used': cards_used
        }
        self.store_jackpot_calls.append(call_record)

        jackpot_id = self._next_jackpot_id
        self._next_jackpot_id += 1

        self.logger.debug(f"Mock stored jackpot {jackpot_id} for player {player_id} in game state {game_state_id}")
        return jackpot_id

    def commit_transaction(self) -> None:
        """
        Record commit call.
        """
        self.commit_calls += 1
        self.logger.debug(f"Mock commit called (total: {self.commit_calls})")

    def rollback_transaction(self) -> None:
        """
        Record rollback call.
        """
        self.rollback_calls += 1
        self.logger.debug(f"Mock rollback called (total: {self.rollback_calls})")

    def close(self) -> None:
        """
        Mock close - no resources to clean up.
        """
        self.logger.debug("Mock persistence strategy closed")

    # Helper methods for testing

    def assert_game_state_stored(self, matrix_cell_id: int, count: int = 1):
        """Assert that game states were stored for a specific cell."""
        matching_calls = [call for call in self.store_game_state_calls
                         if call['matrix_cell_id'] == matrix_cell_id]
        assert len(matching_calls) == count, f"Expected {count} game states for cell {matrix_cell_id}, got {len(matching_calls)}"

    def assert_player_stored(self, game_state_id: int, count: int = 1):
        """Assert that players were stored for a specific game state."""
        matching_calls = [call for call in self.store_player_calls
                         if call['game_state_id'] == game_state_id]
        assert len(matching_calls) == count, f"Expected {count} players for game state {game_state_id}, got {len(matching_calls)}"

    def assert_jackpot_stored(self, game_state_id: int, jackpot_type: str):
        """Assert that a jackpot was stored for a specific game state."""
        matching_calls = [call for call in self.store_jackpot_calls
                         if call['game_state_id'] == game_state_id and call['jackpot_type'] == jackpot_type]
        assert len(matching_calls) >= 1, f"Expected jackpot {jackpot_type} for game state {game_state_id}"