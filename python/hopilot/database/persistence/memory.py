"""
In-memory persistence strategy for development and testing.

This strategy stores data in memory structures without database persistence,
useful for development iteration and integration testing without DB setup.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from hopilot.logging_config import get_logger
from .base import GameStatePersistence

logger = get_logger(__name__)


class InMemoryPersistenceStrategy(GameStatePersistence):
    """
    In-memory persistence strategy for development.

    Stores all data in Python data structures for fast access
    and easy inspection. Useful for development iteration and
    scenarios where database setup is not needed.
    """

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        """Reset all stored data."""
        self.game_states = {}
        self.players = {}
        self.bets = {}
        self.board_cards = {}
        self.jackpots = {}

        # ID generators
        self._next_game_state_id = 1
        self._next_player_id = 1
        self._next_bet_id = 1
        self._next_board_id = 1
        self._next_jackpot_id = 1

        # Transaction state
        self._transaction_buffer = []
        self._in_transaction = False

    def store_game_state(self, simulation_id: int, matrix_cell_id: int,
                        timestamp: str, round_name: str, pot_size: float,
                        board_cards: List[str], outcome: str) -> int:
        """
        Store a game state in memory.
        """
        game_state_id = self._next_game_state_id
        self._next_game_state_id += 1

        game_state = {
            'id': game_state_id,
            'simulation_id': simulation_id,
            'matrix_cell_id': matrix_cell_id,
            'timestamp': timestamp,
            'round': round_name,
            'pot_size': pot_size,
            'board_cards': board_cards,
            'outcome': outcome
        }

        self.game_states[game_state_id] = game_state

        if self._in_transaction:
            self._transaction_buffer.append(('game_state', game_state_id))

        self.logger.debug(f"In-memory stored game state {game_state_id} for cell {matrix_cell_id}")
        return game_state_id

    def update_game_state_outcome(self, game_state_id: int, outcome: str) -> None:
        """
        Update the outcome of an existing game state in memory.
        """
        if game_state_id in self.game_states:
            self.game_states[game_state_id]['outcome'] = outcome
            self.logger.debug(f"In-memory updated game state {game_state_id} outcome to {outcome}")
        else:
            self.logger.warning(f"Game state {game_state_id} not found for outcome update")

    def store_player(self, game_state_id: int, position: str,
                    hole_cards: List[str], stack_size: float,
                    is_hero: bool) -> int:
        """
        Store a player in memory.
        """
        player_id = self._next_player_id
        self._next_player_id += 1

        player = {
            'id': player_id,
            'game_state_id': game_state_id,
            'position': position,
            'hole_cards': hole_cards,
            'stack_size': stack_size,
            'is_hero': is_hero
        }

        self.players[player_id] = player

        if self._in_transaction:
            self._transaction_buffer.append(('player', player_id))

        self.logger.debug(f"In-memory stored player {player_id} in game state {game_state_id}")
        return player_id

    def store_bet(self, game_state_id: int, player_id: int,
                 amount: float, action_type: str, round_name: str = "preflop") -> int:
        """
        Store a bet in memory.
        """
        bet_id = self._next_bet_id
        self._next_bet_id += 1

        bet = {
            'id': bet_id,
            'game_state_id': game_state_id,
            'player_id': player_id,
            'amount': amount,
            'action_type': action_type,
            'round': round_name
        }

        self.bets[bet_id] = bet

        if self._in_transaction:
            self._transaction_buffer.append(('bet', bet_id))

        self.logger.debug(f"In-memory stored bet {bet_id} for player {player_id} in game state {game_state_id}")
        return bet_id

    def store_board_cards(self, flop1: str, flop2: str, flop3: str,
                         turn: str, river: str) -> int:
        """
        Store board cards in memory.
        """
        board_id = self._next_board_id
        self._next_board_id += 1

        board = {
            'id': board_id,
            'flop1': flop1,
            'flop2': flop2,
            'flop3': flop3,
            'turn': turn,
            'river': river
        }

        self.board_cards[board_id] = board

        if self._in_transaction:
            self._transaction_buffer.append(('board', board_id))

        self.logger.debug(f"In-memory stored board cards {board_id}")
        return board_id

    def store_jackpot(self, game_state_id: int, player_id: int,
                     jackpot_type: str, payout_amount: float,
                     cards_used: List[str]) -> int:
        """
        Store a jackpot event in memory.
        """
        jackpot_id = self._next_jackpot_id
        self._next_jackpot_id += 1

        jackpot = {
            'id': jackpot_id,
            'game_state_id': game_state_id,
            'player_id': player_id,
            'jackpot_type': jackpot_type,
            'payout_amount': payout_amount,
            'cards_used': cards_used
        }

        self.jackpots[jackpot_id] = jackpot

        if self._in_transaction:
            self._transaction_buffer.append(('jackpot', jackpot_id))

        self.logger.debug(f"In-memory stored jackpot {jackpot_id} for player {player_id} in game state {game_state_id}")
        return jackpot_id

    def commit_transaction(self) -> None:
        """
        Commit the current transaction (no-op for in-memory).
        """
        self._transaction_buffer.clear()
        self._in_transaction = False
        self.logger.debug("In-memory transaction committed")

    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction by removing buffered items.
        """
        for item_type, item_id in reversed(self._transaction_buffer):
            if item_type == 'game_state':
                self.game_states.pop(item_id, None)
            elif item_type == 'player':
                self.players.pop(item_id, None)
            elif item_type == 'bet':
                self.bets.pop(item_id, None)
            elif item_type == 'board':
                self.board_cards.pop(item_id, None)
            elif item_type == 'jackpot':
                self.jackpots.pop(item_id, None)

        self._transaction_buffer.clear()
        self._in_transaction = False
        self.logger.debug("In-memory transaction rolled back")

    def close(self) -> None:
        """
        In-memory close - clear all stored data.
        """
        self.reset()
        self.logger.debug("In-memory persistence strategy closed")

    # Query methods for development inspection

    def get_game_states_for_cell(self, matrix_cell_id: int) -> List[Dict]:
        """Get all game states for a specific matrix cell."""
        return [gs for gs in self.game_states.values()
                if gs['matrix_cell_id'] == matrix_cell_id]

    def get_players_for_game_state(self, game_state_id: int) -> List[Dict]:
        """Get all players for a specific game state."""
        return [p for p in self.players.values()
                if p['game_state_id'] == game_state_id]

    def get_jackpots_for_game_state(self, game_state_id: int) -> List[Dict]:
        """Get all jackpots for a specific game state."""
        return [j for j in self.jackpots.values()
                if j['game_state_id'] == game_state_id]

    def get_statistics(self) -> Dict[str, int]:
        """Get storage statistics."""
        return {
            'game_states': len(self.game_states),
            'players': len(self.players),
            'bets': len(self.bets),
            'board_cards': len(self.board_cards),
            'jackpots': len(self.jackpots)
        }