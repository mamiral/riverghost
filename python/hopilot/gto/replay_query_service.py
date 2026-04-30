"""Truthful replay and raw-hand query service for the raw GameState schema."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import selectinload

from hopilot.database import DatabaseConnection
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.aof_hand_matrix import hand_key_from_hole_cards
from hopilot.gto.matrix_sweep_contract import normalize_scenario_contract
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

    def __init__(
        self,
        db_connection: DatabaseConnection,
        simulation_repository: SimulationRepository,
        game_state_repository: GameStateRepository,
    ):
        self.db_connection = db_connection
        self.simulation_repository = simulation_repository
        self.game_state_repository = game_state_repository

    def replay_game_state(self, game_state_id: int) -> Dict[str, Any]:
        """Return a truthful replay view for one persisted GameState."""
        with self.db_connection.session_scope() as session:
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
            selected_run = self.simulation_repository.get_simulation_record(simulation_id)
            matches = [selected_run] if selected_run is not None else []
        elif hand_matrix_id is not None:
            selected_run = self.simulation_repository.get_simulation_for_hand_matrix(hand_matrix_id)
            matches = [selected_run] if selected_run is not None else []
        elif scenario_contract is not None:
            selected_run, matches = self._resolve_scenario_run_selection(
                scenario_contract,
                explicit_run_id=explicit_run_id,
            )
        else:
            return self._build_empty_scope_result(
                STATUS_NOT_FOUND,
                "No run selection criteria provided.",
                [],
            )

        if selected_run is None:
            if not matches:
                if simulation_id is not None or hand_matrix_id is not None:
                    return self._build_empty_scope_result(
                        STATUS_NOT_FOUND,
                        "No persisted run matches the requested run identifier.",
                        [],
                    )
                return self._build_empty_scope_result(
                    STATUS_NOT_FOUND,
                    "No persisted run matches the requested scenario contract.",
                    [],
                )

            if explicit_run_id is not None or scenario_contract is not None:
                return self._build_empty_scope_result(
                    STATUS_DISAMBIGUATION_REQUIRED,
                    f"{len(matches)} candidate runs matched the exact scenario contract; explicit run selection is required.",
                    matches,
                )

            return self._build_empty_scope_result(
                STATUS_NOT_FOUND,
                "No matching candidate runs were found.",
                matches,
            )

        if not self._is_run_boundary_readable(selected_run):
            return self._build_empty_scope_result(
                STATUS_EMPTY_SCOPE,
                "Run boundary is unreadable or incomplete for raw-hand inspection.",
                [selected_run],
            )

        raw_start = selected_run.parameters.get("raw_game_state_id_start")
        raw_end = selected_run.parameters.get("raw_game_state_id_end")
        if raw_start is None or raw_end is None:
            return self._build_empty_scope_result(
                STATUS_EMPTY_SCOPE,
                "Run boundary is missing raw_game_state_id_start or raw_game_state_id_end.",
                [selected_run],
            )

        game_states = self.game_state_repository.get_run_raw_projection(raw_start, raw_end)
        return {
            "status": STATUS_AVAILABLE,
            "status_message": "Run available for raw-hand inspection.",
            "matched_runs": [self._serialize_run_reference(selected_run)],
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

        return self._build_empty_scope_result(
            STATUS_NOT_FOUND,
            "Unable to resolve raw run from aggregated summary context.",
            [],
        )

    def _build_empty_scope_result(
        self,
        status: str,
        status_message: str,
        matched_runs: List[Simulation],
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "status_message": status_message,
            "matched_runs": [self._serialize_run_reference(run) for run in matched_runs] if matched_runs else [],
            "game_states": [],
        }

    def _serialize_run_reference(self, simulation: Simulation) -> Dict[str, Any]:
        return {
            "simulation_id": simulation.id,
            "name": simulation.name,
            "raw_game_state_id_start": simulation.parameters.get("raw_game_state_id_start"),
            "raw_game_state_id_end": simulation.parameters.get("raw_game_state_id_end"),
        }

    def _is_run_boundary_readable(self, simulation: Simulation) -> bool:
        try:
            parameters = normalize_scenario_contract(simulation.parameters)
        except Exception:
            return False

        return (
            parameters.get("raw_game_state_id_start") is not None
            and parameters.get("raw_game_state_id_end") is not None
        )

    def _resolve_scenario_run_selection(
        self,
        scenario_contract: Dict[str, Any],
        explicit_run_id: Optional[int] = None,
    ) -> tuple[Optional[Simulation], List[Simulation]]:
        matches = self.simulation_repository.list_matrix_sweep_runs_by_contract(scenario_contract)
        if explicit_run_id is not None:
            selected = next((run for run in matches if run.id == explicit_run_id), None)
            return selected, matches

        if len(matches) == 1:
            return matches[0], matches

        return None, matches

    def _build_replay_view(self, game_state: GameState) -> Dict[str, Any]:
        board_cards = self._parse_board_cards(game_state.board_cards_str)
        players = [self._build_player_view(player) for player in game_state.players]
        hero = next((player for player in players if player["is_hero"]), None)
        sequence = self._build_replay_sequence(game_state, board_cards)

        hand_combination = getattr(getattr(game_state, "matrix_cell", None), "hand_combination", None)
        if hand_combination is None:
            hand_combination = self._derive_hand_combination(game_state)

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
            hand_combination=hand_combination,
        )

        return replay_view.to_dict()

    def _derive_hand_combination(self, game_state: GameState) -> Optional[str]:
        hero_player = next((player for player in game_state.players if player.is_hero), None)
        villain_player = next((player for player in game_state.players if not player.is_hero), None)

        if hero_player is None or villain_player is None:
            return None

        try:
            hero_key = hand_key_from_hole_cards(hero_player.hole_cards)
            villain_key = hand_key_from_hole_cards(villain_player.hole_cards)
            return f"{hero_key} vs {villain_key}"
        except ValueError:
            return None

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
