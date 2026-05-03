"""
Batching persistence strategy for raw Monte Carlo game state writes.

This strategy buffers raw game state, player, bet, and jackpot data and
flushes them in batches to the database. It preserves the existing
`GameStatePersistence` interface while reducing transaction churn.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from hopilot.logging_config import get_logger
from hopilot.models import GameState, Player, Bet, Jackpot
from hopilot.models.player import HandClass
from .base import GameStatePersistence
from hopilot.db import get_session

logger = get_logger(__name__)


class BatchingPersistenceStrategy(GameStatePersistence):
    """Persistence strategy that commits raw rows in configurable batches."""

    def __init__(self, session: Optional[Session] = None, batch_size: int = 1000):
        super().__init__()
        self._session = session
        self._owns_session = session is None
        self._batch_size = max(1, int(batch_size))

        # Pending raw row payloads
        self._pending_game_states: List[Dict[str, Any]] = []
        self._pending_players: List[Dict[str, Any]] = []
        self._pending_bets: List[Dict[str, Any]] = []
        self._pending_jackpots: List[Dict[str, Any]] = []

        # Synthetic negative IDs for buffered game states and players
        self._next_temp_game_state_id = -1
        self._next_temp_player_id = -1
        self._next_temp_bet_id = -1
        self._next_temp_jackpot_id = -1

        self._pending_count = 0

    def _get_session(self) -> Session:
        if self._session is None:
            self._session = get_session()
        return self._session

    def _build_game_state_row(self, timestamp: str, round_name: str, pot_size: float,
                              board_cards: List[str], outcome: str) -> Dict[str, Any]:
        return {
            "temp_id": self._next_temp_game_state_id,
            "timestamp": datetime.fromisoformat(timestamp),
            "round": round_name,
            "pot_size": pot_size,
            "board_cards_str": ",".join(board_cards) if board_cards else "",
            "outcome": outcome,
        }

    def store_game_state(self, timestamp: str, round_name: str, pot_size: float,
                         board_cards: List[str], outcome: str) -> int:
        game_state_id = self._next_temp_game_state_id
        self._next_temp_game_state_id -= 1

        raw_row = self._build_game_state_row(timestamp, round_name, pot_size, board_cards, outcome)
        raw_row["temp_id"] = game_state_id
        self._pending_game_states.append(raw_row)
        self._pending_count += 1
        logger.debug("Buffered game state %s", game_state_id)
        return game_state_id

    def update_game_state_outcome(self, game_state_id: int, outcome: str) -> None:
        for game_state in self._pending_game_states:
            if game_state["temp_id"] == game_state_id:
                game_state["outcome"] = outcome
                logger.debug("Updated buffered game state outcome %s to %s", game_state_id, outcome)
                return

        session = self._get_session()
        game_state = session.query(GameState).filter(GameState.id == game_state_id).first()
        if game_state:
            game_state.outcome = outcome
            logger.debug("Updated persisted game state %s outcome to %s", game_state_id, outcome)
        else:
            self.logger.warning("Game state %s not found for outcome update", game_state_id)

    def store_player(self, game_state_id: int, position: str,
                     hole_cards: List[str], stack_size: float,
                     is_hero: bool, hand_class: Optional[str] = None,
                     final_strength: Optional[int] = None) -> int:
        player_id = self._next_temp_player_id
        self._next_temp_player_id -= 1

        raw_row = {
            "temp_id": player_id,
            "game_state_id": game_state_id,
            "position": position,
            "hole_cards": "".join(hole_cards),
            "stack_size": stack_size,
            "is_hero": is_hero,
            "hand_class": hand_class,
            "final_strength": final_strength,
        }
        self._pending_players.append(raw_row)
        logger.debug("Buffered player %s for game state %s", player_id, game_state_id)
        return player_id

    def store_bet(self, game_state_id: int, player_id: int,
                  amount: float, action_type: str, round_name: str = "preflop") -> int:
        bet_id = self._next_temp_bet_id
        self._next_temp_bet_id -= 1

        self._pending_bets.append({
            "temp_id": bet_id,
            "game_state_id": game_state_id,
            "player_id": player_id,
            "amount": amount,
            "action_type": action_type,
            "round": round_name,
        })
        logger.debug("Buffered bet %s for game state %s", bet_id, game_state_id)
        return bet_id

    def store_board_cards(self, flop1: str, flop2: str, flop3: str,
                          turn: str, river: str) -> int:
        logger.warning("store_board_cards() is not supported by BatchingPersistenceStrategy")
        return -1

    def store_jackpot(self, game_state_id: int, player_id: int,
                      jackpot_type: str, payout_amount: float,
                      cards_used: List[str]) -> int:
        jackpot_id = self._next_temp_jackpot_id
        self._next_temp_jackpot_id -= 1

        self._pending_jackpots.append({
            "temp_id": jackpot_id,
            "game_state_id": game_state_id,
            "player_id": player_id,
            "jackpot_type": jackpot_type,
            "payout_amount": payout_amount,
            "cards_used": cards_used,
        })
        logger.debug("Buffered jackpot %s for game state %s", jackpot_id, game_state_id)
        return jackpot_id

    def commit_transaction(self) -> None:
        if self._pending_count < self._batch_size:
            logger.debug("Commit deferred, batch size %s not reached (%s pending)", self._batch_size, self._pending_count)
            return
        self._flush_batch()

    def rollback_transaction(self) -> None:
        self._pending_game_states.clear()
        self._pending_players.clear()
        self._pending_bets.clear()
        self._pending_jackpots.clear()
        self._pending_count = 0
        if self._session is not None:
            try:
                self._session.rollback()
            except Exception:
                pass
        logger.debug("Rolled back buffered batch")

    def close(self) -> None:
        try:
            self._flush_batch()
        finally:
            if self._owns_session and self._session is not None:
                self._session.close()
                self._session = None
                logger.debug("Database session closed")

    def _resolve_game_state_id(self, game_state_id: int, temp_to_real: Dict[int, int]) -> int:
        return temp_to_real.get(game_state_id, game_state_id)

    def _flush_batch(self) -> None:
        if self._pending_count == 0:
            return

        session = self._get_session()
        temp_to_real: Dict[int, int] = {}

        game_state_objs = []
        for raw in self._pending_game_states:
            game_state = GameState(
                timestamp=raw["timestamp"],
                round=raw["round"],
                pot_size=raw["pot_size"],
                board_cards_str=raw["board_cards_str"],
                outcome=raw["outcome"],
            )
            session.add(game_state)
            game_state_objs.append((raw["temp_id"], game_state))

        session.flush()
        for temp_id, game_state in game_state_objs:
            temp_to_real[temp_id] = game_state.id

        player_id_map: Dict[int, int] = {}
        for raw in self._pending_players:
            game_state_id = self._resolve_game_state_id(raw["game_state_id"], temp_to_real)
            hand_class_enum = None
            if raw["hand_class"] is not None:
                hand_class_enum = HandClass(raw["hand_class"])
            player = Player(
                game_state_id=game_state_id,
                position=raw["position"],
                hole_cards=raw["hole_cards"],
                stack_size=raw["stack_size"],
                is_hero=raw["is_hero"],
                hand_class=hand_class_enum,
                final_strength=raw["final_strength"],
            )
            session.add(player)
            player_id_map[raw["temp_id"]] = player

        session.flush()
        for temp_id, player in player_id_map.items():
            player_id_map[temp_id] = player.id

        for raw in self._pending_bets:
            game_state_id = self._resolve_game_state_id(raw["game_state_id"], temp_to_real)
            player_id = player_id_map.get(raw["player_id"], raw["player_id"])
            bet = Bet(
                game_state_id=game_state_id,
                player_id=player_id,
                amount=raw["amount"],
                action_type=raw["action_type"],
                round=raw["round"],
            )
            session.add(bet)

        for raw in self._pending_jackpots:
            game_state_id = self._resolve_game_state_id(raw["game_state_id"], temp_to_real)
            player_id = player_id_map.get(raw["player_id"], raw["player_id"])
            jackpot = Jackpot(
                game_state_id=game_state_id,
                player_id=player_id,
                jackpot_type=raw["jackpot_type"],
                payout_amount=raw["payout_amount"],
                cards_used=raw["cards_used"],
            )
            session.add(jackpot)

        session.commit()
        logger.debug("Committed buffered batch of %s game states", len(self._pending_game_states))

        self._pending_game_states.clear()
        self._pending_players.clear()
        self._pending_bets.clear()
        self._pending_jackpots.clear()
        self._pending_count = 0
