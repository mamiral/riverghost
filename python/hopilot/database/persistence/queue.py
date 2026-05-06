"""
Queue-based persistence strategy for single-writer raw sweep execution.

This strategy captures game state write operations in worker threads and
enqueues a payload for a dedicated writer thread to persist later.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import queue

from hopilot.database.persistence.base import GameStatePersistence


class QueuePersistenceStrategy(GameStatePersistence):
    """Queue-based persistence strategy for worker threads."""

    def __init__(self, write_queue: "queue.Queue[dict]", batch_id: Optional[str] = None):
        super().__init__()
        self._write_queue = write_queue
        self._batch_id = batch_id
        self._pending_game_state: Optional[Dict[str, Any]] = None
        self._pending_players: List[Dict[str, Any]] = []
        self._pending_bets: List[Dict[str, Any]] = []
        self._pending_jackpots: List[Dict[str, Any]] = []
        self._next_temp_game_state_id = -1
        self._next_temp_player_id = -1

    def store_game_state(self, timestamp: str, round_name: str, pot_size: float,
                         board_cards: List[str], outcome: str) -> int:
        if self._pending_game_state is not None:
            raise RuntimeError("Nested game state transaction detected")
        self._pending_game_state = {
            "timestamp": timestamp,
            "round": round_name,
            "pot_size": pot_size,
            "board_cards": list(board_cards),
            "outcome": outcome,
            "temp_id": self._next_temp_game_state_id,
        }
        self._next_temp_game_state_id -= 1
        return self._pending_game_state["temp_id"]

    def update_game_state_outcome(self, game_state_id: int, outcome: str) -> None:
        if self._pending_game_state and self._pending_game_state.get("temp_id") == game_state_id:
            self._pending_game_state["outcome"] = outcome
            return
        self.logger.warning("Attempted to update unknown queued game state %s", game_state_id)

    def store_player(self, game_state_id: int, position: str,
                     hole_cards: List[str], stack_size: float,
                     is_hero: bool, hand_class: Optional[str] = None,
                     final_strength: Optional[int] = None) -> int:
        player_id = self._next_temp_player_id
        self._next_temp_player_id -= 1
        self._pending_players.append({
            "temp_id": player_id,
            "game_state_id": game_state_id,
            "position": position,
            "hole_cards": list(hole_cards),
            "stack_size": stack_size,
            "is_hero": is_hero,
            "hand_class": hand_class,
            "final_strength": final_strength,
        })
        return player_id

    def store_bet(self, game_state_id: int, player_id: int,
                  amount: float, action_type: str, round_name: str = "preflop") -> int:
        bet = {
            "game_state_id": game_state_id,
            "player_id": player_id,
            "amount": amount,
            "action_type": action_type,
            "round": round_name,
        }
        self._pending_bets.append(bet)
        return len(self._pending_bets)

    def store_board_cards(self, flop1: str, flop2: str, flop3: str,
                          turn: str, river: str) -> int:
        self.logger.warning("store_board_cards() is not supported by QueuePersistenceStrategy")
        return -1

    def store_jackpot(self, game_state_id: int, player_id: int,
                      jackpot_type: str, payout_amount: float,
                      cards_used: List[str]) -> int:
        jackpot = {
            "game_state_id": game_state_id,
            "player_id": player_id,
            "jackpot_type": jackpot_type,
            "payout_amount": payout_amount,
            "cards_used": list(cards_used),
        }
        self._pending_jackpots.append(jackpot)
        return len(self._pending_jackpots)

    def commit_transaction(self) -> None:
        if self._pending_game_state is None:
            return
        payload = {
            "game_state": self._pending_game_state,
            "players": list(self._pending_players),
            "bets": list(self._pending_bets),
            "jackpots": list(self._pending_jackpots),
            "batch_id": self._batch_id,
        }
        self._write_queue.put(payload)
        self._pending_game_state = None
        self._pending_players.clear()
        self._pending_bets.clear()
        self._pending_jackpots.clear()

    def rollback_transaction(self) -> None:
        self._pending_game_state = None
        self._pending_players.clear()
        self._pending_bets.clear()
        self._pending_jackpots.clear()

    def close(self) -> None:
        self.rollback_transaction()
