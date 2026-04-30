from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, selectinload

from hopilot.database import DatabaseConnection
from hopilot.gto.repository_errors import GameStateRepositoryError
from hopilot.gto.repository_interfaces import GameStateRepositoryInterface
from hopilot.gto.repository_validation import (
    validate_bet_data,
    validate_game_state_data,
    validate_jackpot_data,
    validate_player_data,
)
from hopilot.logging_config import get_logger
from hopilot.models import Bet, GameState, Jackpot, Player

logger = get_logger(__name__)


class GameStateRepository(GameStateRepositoryInterface):
    def __init__(self, db_connection: DatabaseConnection, session: Optional[Session] = None):
        self.db_connection = db_connection
        self.session = session

    @contextmanager
    def _session_scope(self) -> Session:
        if self.session is not None:
            yield self.session
            return
        with self.db_connection.session_scope() as session:
            yield session

    def _resolve_board_cards_str(self, game_state_data: Dict[str, Any]) -> str:
        board_cards_str = game_state_data.get("board_cards_str")
        if board_cards_str is None:
            raise ValueError("Missing required field: board_cards_str")
        return board_cards_str

    def _validate_player_payload(self, player_data: Dict[str, Any], game_state_id: int) -> None:
        if "position" not in player_data or not str(player_data["position"]).strip():
            raise ValueError("Player position cannot be empty")

        hole_cards = player_data.get("hole_cards")
        if not isinstance(hole_cards, str) or len(hole_cards) != 4:
            raise ValueError(f"Hole cards must be a 4-character string, got: {hole_cards}")

        if "stack_size" not in player_data or player_data["stack_size"] < 0:
            raise ValueError("Player stack_size must be a non-negative number")

    def _raise_domain_error(self, operation: str, exc: Exception) -> None:
        logger.error("GameStateRepository.%s failed: %s", operation, exc, exc_info=True)
        raise GameStateRepositoryError(f"GameStateRepository {operation} failed") from exc

    def create_game_state(self, game_state_data: Dict[str, Any]) -> int:
        try:
            with self._session_scope() as session:
                validate_game_state_data(game_state_data, session)
                game_state = GameState(
                    timestamp=game_state_data.get("timestamp", datetime.now(timezone.utc)),
                    round=game_state_data.get("round", "preflop"),
                    pot_size=game_state_data["pot_size"],
                    board_cards_str=self._resolve_board_cards_str(game_state_data),
                    outcome=game_state_data.get("outcome"),
                )
                session.add(game_state)
                session.flush()

                game_state_id = game_state.id
                for player_data in game_state_data.get("players", []):
                    self._validate_player_payload(player_data, game_state_id)
                    player = Player(
                        game_state_id=game_state_id,
                        position=player_data["position"],
                        hole_cards=player_data["hole_cards"],
                        stack_size=player_data["stack_size"],
                        is_hero=player_data.get("is_hero", False),
                    )
                    session.add(player)
                    session.flush()

                if self.session is None:
                    session.commit()
                return game_state_id
        except ValueError:
            raise
        except Exception as exc:
            self._raise_domain_error("create_game_state", exc)

    def update_game_state(self, game_state_id: int, updates: Dict[str, Any]) -> None:
        try:
            with self._session_scope() as session:
                game_state = session.get(GameState, game_state_id)
                if game_state is None:
                    raise ValueError(f"GameState with ID {game_state_id} not found")

                allowed_fields = {"round", "pot_size", "outcome", "board_cards_str"}
                for key, value in updates.items():
                    if key in allowed_fields:
                        setattr(game_state, key, value)
                if self.session is None:
                    session.commit()
        except ValueError:
            raise
        except Exception as exc:
            self._raise_domain_error("update_game_state", exc)

    def get_game_state(self, game_state_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self._session_scope() as session:
                game_state = (
                    session.query(GameState)
                    .options(
                        selectinload(GameState.players),
                        selectinload(GameState.bets),
                        selectinload(GameState.jackpots),
                    )
                    .filter(GameState.id == game_state_id)
                    .first()
                )
                if not game_state:
                    return None

                return {
                    "id": game_state.id,
                    "timestamp": game_state.timestamp,
                    "round": game_state.round,
                    "pot_size": float(game_state.pot_size),
                    "board_cards_str": game_state.board_cards_str,
                    "outcome": game_state.outcome,
                    "players": [
                        {
                            "id": player.id,
                            "position": player.position,
                            "hole_cards": player.hole_cards,
                            "stack_size": float(player.stack_size) if player.stack_size is not None else None,
                            "is_hero": player.is_hero,
                        }
                        for player in game_state.players
                    ],
                    "bets": [
                        {
                            "id": bet.id,
                            "player_id": bet.player_id,
                            "amount": float(bet.amount),
                            "action_type": bet.action_type,
                            "round": bet.round,
                        }
                        for bet in game_state.bets
                    ],
                    "jackpots": [
                        {
                            "id": jackpot.id,
                            "jackpot_type": jackpot.jackpot_type,
                            "payout_amount": float(jackpot.payout_amount),
                            "qualifying_cards": jackpot.qualifying_cards,
                        }
                        for jackpot in game_state.jackpots
                    ],
                }
        except Exception as exc:
            self._raise_domain_error("get_game_state", exc)

    def bulk_insert_game_states(self, game_states: List[Dict[str, Any]]) -> List[int]:
        ids: List[int] = []
        try:
            with self._session_scope() as session:
                for game_state_data in game_states:
                    validate_game_state_data(game_state_data, session)
                    game_state = GameState(
                        timestamp=game_state_data.get("timestamp", datetime.now(timezone.utc)),
                        round=game_state_data.get("round", "preflop"),
                        pot_size=game_state_data["pot_size"],
                        board_cards_str=self._resolve_board_cards_str(game_state_data),
                        outcome=game_state_data.get("outcome"),
                    )
                    session.add(game_state)
                    session.flush()
                    ids.append(game_state.id)
                if self.session is None:
                    session.commit()
                return ids
        except ValueError:
            raise
        except Exception as exc:
            self._raise_domain_error("bulk_insert_game_states", exc)

    def create_player(self, player_data: Dict[str, Any]) -> int:
        try:
            with self._session_scope() as session:
                validate_player_data(player_data, session)
                player = Player(
                    game_state_id=player_data["game_state_id"],
                    position=player_data["position"],
                    hole_cards=player_data["hole_cards"],
                    stack_size=player_data["stack_size"],
                    is_hero=player_data.get("is_hero", False),
                )
                session.add(player)
                session.flush()
                if self.session is None:
                    session.commit()
                return player.id
        except ValueError:
            raise
        except Exception as exc:
            self._raise_domain_error("create_player", exc)

    def create_bet(self, bet_data: Dict[str, Any]) -> int:
        try:
            with self._session_scope() as session:
                validate_bet_data(bet_data, session)
                bet = Bet(
                    game_state_id=bet_data["game_state_id"],
                    player_id=bet_data["player_id"],
                    amount=bet_data["amount"],
                    action_type=bet_data.get("action_type", "raise"),
                    round=bet_data.get("round", "preflop"),
                )
                session.add(bet)
                session.flush()
                if self.session is None:
                    session.commit()
                return bet.id
        except ValueError:
            raise
        except Exception as exc:
            self._raise_domain_error("create_bet", exc)

    def create_jackpot(self, jackpot_data: Dict[str, Any]) -> int:
        try:
            with self._session_scope() as session:
                validate_jackpot_data(jackpot_data, session)
                jackpot = Jackpot(
                    game_state_id=jackpot_data["game_state_id"],
                    player_id=jackpot_data["player_id"],
                    jackpot_type=jackpot_data.get("jackpot_type", "UNKNOWN"),
                    payout_amount=jackpot_data.get("payout_amount", 0.0),
                    qualifying_cards=jackpot_data.get("qualifying_cards", []),
                )
                session.add(jackpot)
                session.flush()
                if self.session is None:
                    session.commit()
                return jackpot.id
        except ValueError:
            raise
        except Exception as exc:
            self._raise_domain_error("create_jackpot", exc)

    def get_run_raw_projection(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> List[Dict[str, Any]]:
        try:
            with self._session_scope() as session:
                game_states = (
                    session.query(GameState)
                    .options(selectinload(GameState.players))
                    .filter(
                        GameState.id >= raw_game_state_id_start,
                        GameState.id <= raw_game_state_id_end,
                    )
                    .order_by(GameState.id.asc())
                    .all()
                )

                projection = []
                for game_state in game_states:
                    hero_player = next((player for player in game_state.players if player.is_hero), None)
                    projection.append(
                        {
                            "game_state_id": game_state.id,
                            "timestamp": game_state.timestamp.isoformat() if game_state.timestamp else None,
                            "round": game_state.round,
                            "pot_size": float(game_state.pot_size) if game_state.pot_size is not None else 0.0,
                            "board_cards_str": game_state.board_cards_str or "",
                            "outcome": game_state.outcome,
                            "hero_hole_cards": hero_player.hole_cards if hero_player else None,
                            "players": [
                                {
                                    "player_id": player.id,
                                    "position": player.position,
                                    "hole_cards": player.hole_cards,
                                    "stack_size": float(player.stack_size) if player.stack_size is not None else 0.0,
                                    "is_hero": bool(player.is_hero),
                                }
                                for player in game_state.players
                            ],
                        }
                    )
                return projection
        except Exception as exc:
            self._raise_domain_error("get_run_raw_projection", exc)
