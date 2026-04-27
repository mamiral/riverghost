"""Truthful replay and raw-hand query service for the raw GameState schema."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import selectinload

from hopilot.gto.database_repository import DatabaseRepository
from hopilot.models import GameState, Player, Simulation
from hopilot.logging_config import get_logger

logger = get_logger(__name__)

STATUS_AVAILABLE = "AVAILABLE"
STATUS_EMPTY_SCOPE = "EMPTY_SCOPE"
STATUS_DISAMBIGUATION_REQUIRED = "DISAMBIGUATION_REQUIRED"
STATUS_NOT_FOUND = "NOT_FOUND"
STATUS_UNREADABLE = "UNREADABLE"


@dataclass(frozen=True)
class ReplayPlayerView:
    player_id: int
    position: str
    hole_cards: str
    stack_size: float
    is_hero: bool
    hand_class: Optional[str] = None
    final_strength: Optional[int] = None


@dataclass(frozen=True)
class ReplayView:
    status: str
    status_message: str
    game_state_id: int
    timestamp: Optional[str]
    round: str
    pot_size: float
    board_cards: List[str]
    outcome: Optional[str]
    players: List[ReplayPlayerView] = field(default_factory=list)
    hero_player: Optional[ReplayPlayerView] = None
    sequence: List[Dict[str, Any]] = field(default_factory=list)
    total_events: int = 0
    optional_details: Dict[str, Any] = field(default_factory=dict)
    hand_combination: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReplayQueryService:
    """Service for truthful replay and run-scoped raw-hand queries."""

    def __init__(self, repository: DatabaseRepository):
        self.repository = repository

    def replay_game_state(self, game_state_id: int) -> Dict[str, Any]:
        """Return a truthful replay view for one persisted GameState."""
        with self.repository.connection.session_scope() as session:
            game_state = (
                session.query(GameState)
                .options(selectinload(GameState.players))
                .filter(GameState.id == game_state_id)
                .first()
            )

            if game_state is None:
                return self._not_found_result(game_state_id)

            if not game_state.players:
                return self._unreadable_result(game_state_id, "Missing required Player rows for GameState")

            return self._build_replay_view(game_state)

    def query_raw_run(
        self,
        scenario_contract: Optional[Dict[str, Any]] = None,
        explicit_run_id: Optional[int] = None,
        simulation_id: Optional[int] = None,
        hand_matrix_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Query raw GameState rows scoped to one persisted run boundary."""
        selected_run: Optional[Simulation] = None
        matches: List[Simulation] = []

        if simulation_id is not None:
            selected_run = self.repository.get_simulation_record(simulation_id)
            matches = [selected_run] if selected_run is not None else []
        elif hand_matrix_id is not None:
            selected_run = self.repository.get_simulation_for_hand_matrix(hand_matrix_id)
            matches = [selected_run] if selected_run is not None else []
        elif scenario_contract is not None:
            selected_run, matches = self.repository.resolve_scenario_run_selection(
                scenario_contract,
                explicit_run_id=explicit_run_id,
            )
        else:
            return self.repository.build_empty_scope_result(
                STATUS_NOT_FOUND,
                "No run selection criteria provided.",
                [],
            )

        if selected_run is None:
            if not matches:
                if simulation_id is not None or hand_matrix_id is not None:
                    return self.repository.build_empty_scope_result(
                        STATUS_NOT_FOUND,
                        "No persisted run matches the requested run identifier.",
                        [],
                    )
                return self.repository.build_empty_scope_result(
                    STATUS_NOT_FOUND,
                    "No persisted run matches the requested scenario contract.",
                    [],
                )

            if explicit_run_id is not None or scenario_contract is not None:
                return self.repository.build_empty_scope_result(
                    STATUS_DISAMBIGUATION_REQUIRED,
                    f"{len(matches)} candidate runs matched the exact scenario contract; explicit run selection is required.",
                    matches,
                )

            return self.repository.build_empty_scope_result(
                STATUS_NOT_FOUND,
                "No matching candidate runs were found.",
                matches,
            )

        if not self.repository.is_run_boundary_readable(selected_run):
            return self.repository.build_empty_scope_result(
                STATUS_EMPTY_SCOPE,
                "Run boundary is unreadable or incomplete for raw-hand inspection.",
                [selected_run],
            )

        raw_start = selected_run.parameters.get("raw_game_state_id_start")
        raw_end = selected_run.parameters.get("raw_game_state_id_end")
        if raw_start is None or raw_end is None:
            return self.repository.build_empty_scope_result(
                STATUS_EMPTY_SCOPE,
                "Run boundary is missing raw_game_state_id_start or raw_game_state_id_end.",
                [selected_run],
            )

        game_states = self.repository.get_run_raw_projection(raw_start, raw_end)
        return {
            "status": STATUS_AVAILABLE,
            "status_message": "Run available for raw-hand inspection.",
            "matched_runs": [self.repository._serialize_run_reference(selected_run)],
            "game_states": game_states,
        }

    def query_raw_run_from_summary(
        self,
        matrix_sweep_summary: Dict[str, Any],
        explicit_run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Resolve an aggregated summary to a raw run and return the raw query payload."""
        simulation = matrix_sweep_summary.get("simulation")
        if isinstance(simulation, Simulation):
            return self.query_raw_run(simulation_id=simulation.id)

        hand_matrix = matrix_sweep_summary.get("hand_matrix")
        if hand_matrix is not None and getattr(hand_matrix, "id", None) is not None:
            return self.query_raw_run(hand_matrix_id=hand_matrix.id)

        scenario_contract = matrix_sweep_summary.get("scenario_contract")
        if scenario_contract is not None:
            return self.query_raw_run(
                scenario_contract=scenario_contract,
                explicit_run_id=explicit_run_id,
            )

        return self.repository.build_empty_scope_result(
            STATUS_NOT_FOUND,
            "Unable to resolve raw run from aggregated summary context.",
            [],
        )

    def _build_replay_view(self, game_state: GameState) -> Dict[str, Any]:
        board_cards = self._parse_board_cards(game_state.board_cards_str)
        players = [self._build_player_view(player) for player in game_state.players]
        hero = next((player for player in players if player["is_hero"]), None)
        sequence = self._build_replay_sequence(game_state, board_cards)

        replay_view = ReplayView(
            status=STATUS_AVAILABLE,
            status_message="Replay available from persisted GameState.",
            game_state_id=game_state.id,
            timestamp=game_state.timestamp.isoformat() if game_state.timestamp else None,
            round=game_state.round,
            pot_size=float(game_state.pot_size) if game_state.pot_size is not None else 0.0,
            board_cards=board_cards,
            outcome=game_state.outcome,
            players=[ReplayPlayerView(**player) for player in players],
            hero_player=ReplayPlayerView(**hero) if hero else None,
            sequence=sequence,
            total_events=len(sequence),
            optional_details={
                "availability": {
                    "bets": "available" if getattr(game_state, "bets", None) else "unavailable",
                    "jackpots": "available" if getattr(game_state, "jackpots", None) else "unavailable",
                },
                "bets": [],
                "jackpots": [],
            },
            hand_combination=getattr(getattr(game_state, "matrix_cell", None), "hand_combination", None),
        )

        return replay_view.to_dict()

    def _build_replay_sequence(self, game_state: GameState, board_cards: List[str]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        events.append({
            "event_type": "game_start",
            "timestamp": game_state.timestamp.isoformat() if game_state.timestamp else None,
            "round": game_state.round,
            "data": {
                "pot_size": float(game_state.pot_size) if game_state.pot_size is not None else 0.0,
                "player_count": len(game_state.players) if game_state.players else 0,
            },
        })

        if board_cards:
            if len(board_cards) >= 3:
                events.append({
                    "event_type": "board_reveal",
                    "timestamp": None,
                    "round": "flop",
                    "data": {
                        "cards": board_cards[:3],
                        "street": "flop",
                    },
                })
            if len(board_cards) >= 4:
                events.append({
                    "event_type": "board_reveal",
                    "timestamp": None,
                    "round": "turn",
                    "data": {
                        "card": board_cards[3],
                        "street": "turn",
                    },
                })
            if len(board_cards) >= 5:
                events.append({
                    "event_type": "board_reveal",
                    "timestamp": None,
                    "round": "river",
                    "data": {
                        "card": board_cards[4],
                        "street": "river",
                    },
                })

        if getattr(game_state, "bets", None):
            sorted_bets = sorted(game_state.bets, key=lambda b: (b.id, getattr(b, "round", "")))
            for bet in sorted_bets:
                events.append({
                    "event_type": "bet",
                    "timestamp": None,
                    "round": getattr(bet, "round", None),
                    "data": {
                        "player_id": getattr(bet, "player_id", None),
                        "action": getattr(bet, "action_type", None),
                        "amount": float(getattr(bet, "amount", 0.0)) if getattr(bet, "amount", None) is not None else 0.0,
                    },
                })

        events.append({
            "event_type": "game_end",
            "timestamp": None,
            "round": game_state.round,
            "data": {
                "outcome": game_state.outcome,
                "pot_size": float(game_state.pot_size) if game_state.pot_size is not None else 0.0,
            },
        })

        return events

    def _build_player_view(self, player: Player) -> Dict[str, Any]:
        return {
            "player_id": player.id,
            "position": player.position,
            "hole_cards": player.hole_cards,
            "stack_size": float(player.stack_size) if player.stack_size is not None else 0.0,
            "is_hero": bool(player.is_hero),
            "hand_class": player.hand_class.name if player.hand_class is not None else None,
            "final_strength": player.final_strength,
        }

    def _parse_board_cards(self, board_cards_str: Optional[str]) -> List[str]:
        if not board_cards_str:
            return []
        return [card.strip() for card in board_cards_str.split(",") if card.strip()]

    def _not_found_result(self, game_state_id: int) -> Dict[str, Any]:
        return {
            "status": STATUS_NOT_FOUND,
            "status_message": f"GameState {game_state_id} not found.",
            "game_state_id": game_state_id,
            "game_states": [],
        }

    def _unreadable_result(self, game_state_id: int, message: str) -> Dict[str, Any]:
        return {
            "status": STATUS_UNREADABLE,
            "status_message": message,
            "game_state_id": game_state_id,
            "game_states": [],
        }
