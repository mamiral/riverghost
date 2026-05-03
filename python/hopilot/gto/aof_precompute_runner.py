from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from itertools import product
import json
import threading
import time
from typing import Any, Dict, Optional

from hopilot.gto.aof_hand_matrix import format_metric_value
from hopilot.database import DatabaseConnection
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.matrix_sweep_contract import MatrixSweepContractError
from hopilot.gto.precompute_job_persistence import PrecomputeJobPersistenceService
from hopilot.gto.precompute_job_repository import PrecomputeJobRepository
from hopilot.gto.precompute_orchestration import PrecomputeOrchestrationService
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.logging_config import get_logger
from hopilot.performance_monitor import performance_monitor
from hopilot.poker_analyzer import PokerAnalyzer

# Phase 4: Status constants (previously from deleted provider)
STATUS_ERROR = "ERROR"
STATUS_TIMEOUT = "TIMEOUT"


@dataclass
class PrecomputeProfile:
    positions: tuple[str, ...] = ("UTG", "BTN", "SB", "BB")
    metrics: tuple[str, ...] = ("WIN_LOSE_PROBABILITY", "EV", "EQUITY", "EQR")
    strict_modes: tuple[bool, ...] = (False, True)
    simulations_per_cell: int = 1000


class GuiRunState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class RunnerPhase(str, Enum):
    ORCHESTRATION = "orchestration"
    SOLVER_WRITE = "solver_write"
    AGGREGATION = "aggregation"
    FINALIZING = "finalizing"


class MatrixSweepAggregationError(Exception):
    """Raised when matrix sweep aggregation fails."""


class AofRepositoryShim:
    def __init__(self, db_connection: DatabaseConnection):
        self.connection = db_connection
        self.game_state_repository = GameStateRepository(db_connection)
        self.simulation_repository = SimulationRepository(db_connection)
        self.precompute_job_repository = PrecomputeJobRepository(db_connection)

    def create_game_state(self, game_state_data: dict[str, Any]) -> int:
        return self.game_state_repository.create_game_state(game_state_data)

    def create_player(self, player_data: dict[str, Any]) -> int:
        return self.game_state_repository.create_player(player_data)

    def create_bet(self, bet_data: dict[str, Any]) -> int:
        return self.game_state_repository.create_bet(bet_data)

    def create_jackpot(self, jackpot_data: dict[str, Any]) -> int:
        return self.game_state_repository.create_jackpot(jackpot_data)

    def create_simulation(self, parameters: dict[str, Any]) -> int:
        return self.simulation_repository.create_simulation(parameters)

    def create_hand_matrix(self, simulation_id: int, *, matrix_size: str = "13x13") -> int:
        return self.simulation_repository.create_hand_matrix(simulation_id, matrix_size=matrix_size)

    def get_max_simulation_id(self) -> int:
        return self.simulation_repository.get_max_simulation_id()

    def get_max_matrix_id(self) -> int:
        return self.simulation_repository.get_max_matrix_id()

    def get_latest_game_state_id(self) -> int:
        return self.simulation_repository.get_latest_game_state_id()

    def get_run_raw_counts(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> dict[str, int]:
        return self.simulation_repository.get_run_raw_counts(raw_game_state_id_start, raw_game_state_id_end)

    def get_session(self):
        return self.simulation_repository.get_session()

    def create_matrix_sweep_simulation(
        self,
        parameters: dict[str, Any],
        *,
        name: str | None = None,
        start_timestamp: datetime | None = None,
    ) -> int:
        return self.simulation_repository.create_matrix_sweep_simulation(
            parameters,
            name=name,
            start_timestamp=start_timestamp,
        )

    def update_matrix_sweep_simulation(
        self,
        simulation_id: int,
        *,
        parameters: dict[str, Any] | None = None,
        end_timestamp: datetime | None = None,
    ) -> None:
        return self.simulation_repository.update_matrix_sweep_simulation(
            simulation_id,
            parameters=parameters,
            end_timestamp=end_timestamp,
        )

    def get_simulation_record(self, simulation_id: int):
        return self.simulation_repository.get_simulation_record(simulation_id)

    def get_simulation_for_hand_matrix(self, hand_matrix_id: int):
        return self.simulation_repository.get_simulation_for_hand_matrix(hand_matrix_id)

    def get_run_game_states(self, raw_game_state_id_start: int, raw_game_state_id_end: int):
        return self.simulation_repository.get_run_game_states(raw_game_state_id_start, raw_game_state_id_end)

    def get_or_create_hand_matrix_for_simulation(
        self,
        simulation_id: int,
        *,
        matrix_size: str = "13x13",
    ) -> int:
        return self.simulation_repository.get_or_create_hand_matrix_for_simulation(
            simulation_id,
            matrix_size=matrix_size,
        )

    def delete_matrix_summaries(self, matrix_id: int) -> None:
        return self.simulation_repository.delete_matrix_summaries(matrix_id)

    def get_matrix_sweep_summary(self, simulation_id: int):
        return self.simulation_repository.get_matrix_sweep_summary(simulation_id)

    def get_cross_run_matrix_summary(self, scenario_contract: dict[str, Any]):
        return self.simulation_repository.get_cross_run_matrix_summary(scenario_contract)

    def find_matrix_sweep_run_by_contract(self, scenario_contract: dict[str, Any]):
        return self.simulation_repository.find_matrix_sweep_run_by_contract(scenario_contract)

    def list_matrix_sweep_runs_by_contract(self, scenario_contract: dict[str, Any]):
        return self.simulation_repository.list_matrix_sweep_runs_by_contract(scenario_contract)

    def upsert_matrix_cell(
        self,
        matrix_id: int,
        row_idx: int,
        col_idx: int,
        hand_key: str,
        metrics: dict[str, float],
        status: str,
    ) -> int:
        return self.simulation_repository.upsert_matrix_cell(
            matrix_id,
            row_idx=row_idx,
            col_idx=col_idx,
            hand_key=hand_key,
            metrics=metrics,
            status=status,
        )

    def create_precompute_job_session(self, scenario_fingerprint: str, requested_scenarios: int) -> int:
        return self.precompute_job_repository.create_precompute_job_session(scenario_fingerprint, requested_scenarios)

    def update_precompute_job_session(self, job_session_id: int, **updates: Any) -> None:
        return self.precompute_job_repository.update_precompute_job_session(job_session_id, **updates)

    def get_precompute_job_session(self, job_session_id: int):
        return self.precompute_job_repository.get_precompute_job_session(job_session_id)

    def create_scenario_run_link(
        self,
        job_session_id: int,
        scenario_index: int,
        scenario_key: str,
        scenario_contract: dict[str, Any],
        status: str = "PENDING",
    ) -> int:
        return self.precompute_job_repository.create_scenario_run_link(
            job_session_id,
            scenario_index,
            scenario_key,
            scenario_contract,
            status=status,
        )

    def update_scenario_run_link(self, scenario_link_id: int, **updates: Any) -> None:
        return self.precompute_job_repository.update_scenario_run_link(scenario_link_id, **updates)

    def get_scenario_run_links_for_job(self, job_session_id: int):
        return self.precompute_job_repository.get_scenario_run_links_for_job(job_session_id)


_GUI_TRANSITIONS: dict[GuiRunState, set[GuiRunState]] = {
    GuiRunState.IDLE: {GuiRunState.RUNNING},
    GuiRunState.RUNNING: {GuiRunState.PAUSED, GuiRunState.STOPPING, GuiRunState.COMPLETED, GuiRunState.FAILED},
    GuiRunState.PAUSED: {GuiRunState.RUNNING, GuiRunState.IDLE, GuiRunState.STOPPING, GuiRunState.COMPLETED, GuiRunState.FAILED},
    GuiRunState.STOPPING: {GuiRunState.COMPLETED, GuiRunState.FAILED, GuiRunState.CANCELED},
    GuiRunState.COMPLETED: {GuiRunState.IDLE, GuiRunState.RUNNING},
    GuiRunState.FAILED: {GuiRunState.IDLE, GuiRunState.RUNNING},
}


@dataclass
class GuiPrecomputeRunSession:
    run_id: int | None = None
    scenario_fingerprint: str = ""
    run_state: GuiRunState = GuiRunState.IDLE
    simulations_per_cell: int = 1000
    total_cells: int = 169
    completed_cells: int = 0
    failed_cells: int = 0
    next_cell_index: int = 0
    current_cell_index: int | None = None
    started_at: datetime | None = None
    paused_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_active_ms: int = 0
    sim_id: int | None = None
    matrix_id: int | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    _active_start_perf: float | None = field(default=None, repr=False)

    def validate(self) -> None:
        if self.simulations_per_cell < 1:
            raise ValueError("simulations_per_cell must be >= 1")
        if self.total_cells < 1:
            raise ValueError("total_cells must be >= 1")
        if self.completed_cells < 0 or self.failed_cells < 0:
            raise ValueError("completed_cells and failed_cells must be >= 0")
        if self.completed_cells + self.failed_cells > self.total_cells:
            raise ValueError("completed_cells + failed_cells cannot exceed total_cells")
        if self.next_cell_index < 0 or self.next_cell_index > self.total_cells:
            raise ValueError("next_cell_index out of range")
        if self.current_cell_index is not None and (self.current_cell_index < 0 or self.current_cell_index >= self.total_cells):
            raise ValueError("current_cell_index out of range")


@dataclass
class RunnerTelemetrySnapshot:
    run_state: GuiRunState
    completed_cells: int
    total_cells: int
    current_cell_index: int | None
    current_cell_label: str | None
    active_scenario_key: str | None
    phase: RunnerPhase
    elapsed_seconds: float
    eta_seconds: float | None
    failure_count: int
    throughput_cells_per_minute: float | None
    last_update_at: datetime


class AoFPrecomputeRunner:
    def __init__(self, provider: Any = None, database_url: str = None):
        """
        Initialize precompute runner.
        
        Phase 4: Provider is optional (database-only mode).
        """
        self.logger = get_logger(__name__)
        self.provider = provider  # May be None in Phase 4 CLI
        self.store = None  # Phase 4: Store removed, always None
        if database_url is None:
            raise ValueError("database_url is required")
        self.db_connection = DatabaseConnection(database_url)
        self.db_connection.create_tables()
        self.database_repository = AofRepositoryShim(self.db_connection)
        self.precompute_orchestration_service = PrecomputeOrchestrationService(
            provider=self.provider,
            database_repository=self.database_repository,
            logger=self.logger,
        )
        self.precompute_job_repository = PrecomputeJobRepository(self.db_connection)
        self.precompute_job_persistence_service = PrecomputeJobPersistenceService(
            self.precompute_job_repository,
            logger=self.logger,
        )
        
        # Initialize solver directly to avoid provider dependency
        self._solver = None
        
        # Session cache for in-memory testing and checkpoint restoration
        self._gui_sessions: dict[int, GuiPrecomputeRunSession] = {}
        self._next_run_id = 1  # Counter for assigning run IDs
        self.last_job_session_id: int | None = None
        self.aggregation_service = None  # Phase 4: Aggregation service removed
        self.logger.info(f"AoFPrecomputeRunner initialized with database: {database_url}")

    def _get_solver(self):
        """Get or create solver instance."""
        if self._solver is None:
            from hopilot.all_in_fold_gto import AllInFoldGTOSolver
            from hopilot.database.persistence import DatabasePersistenceStrategy
            from hopilot.poker_analyzer import PokerAnalyzer

            # Use the same session as the database repository
            session = self.database_repository.connection.get_session()
            persistence = DatabasePersistenceStrategy(session)
            analyzer = PokerAnalyzer()
            self._solver = AllInFoldGTOSolver(analyzer, persistence)
            self.logger.debug("Initialized AllInFoldGTOSolver for precompute")
        return self._solver

    def run_matrix_sweep(self, scenario_contract: dict[str, Any]) -> dict[str, Any]:
        """Execute one production matrix sweep through the dedicated sweep service."""
        from hopilot.database.persistence import BatchingPersistenceStrategy
        from hopilot.gto.matrix_sweep_service import MatrixSweepService
        from hopilot.poker_analyzer import PokerAnalyzer

        simulation_repository = SimulationRepository(self.db_connection)
        batch_size = min(max(1, int(scenario_contract.get("sims_per_combo", 120))), 1000)
        service = MatrixSweepService(
            simulation_repository,
            PokerAnalyzer(),
            lambda session: BatchingPersistenceStrategy(session=session, batch_size=batch_size),
        )
        return service.run_sweep(scenario_contract)

    def create_gui_session(
        self,
        *,
        simulations_per_cell: int,
        scenario_fingerprint: str,
        total_cells: int = 169,
    ) -> GuiPrecomputeRunSession:
        session = GuiPrecomputeRunSession(
            run_id=None,
            scenario_fingerprint=scenario_fingerprint,
            run_state=GuiRunState.IDLE,
            simulations_per_cell=int(simulations_per_cell),
            total_cells=int(total_cells),
            completed_cells=0,
            failed_cells=0,
            next_cell_index=0,
            current_cell_index=None,
        )
        session.validate()
        return session

    def bind_gui_run(self, session: GuiPrecomputeRunSession) -> GuiPrecomputeRunSession:
        # Phase 4: Assign run_id and cache session for persistence
        if session.run_id is None:
            session.run_id = self._next_run_id
            self._next_run_id += 1
        # Cache session for restoration later
        self._gui_sessions[session.run_id] = session
        return session

    def pause_gui_session(self, session: GuiPrecomputeRunSession) -> GuiPrecomputeRunSession:
        if session.run_state == GuiRunState.RUNNING:
            self.transition_session_state(session, GuiRunState.PAUSED)
            self._persist_gui_session_checkpoint(session)
        return session

    def stop_gui_session(self, session: GuiPrecomputeRunSession) -> GuiPrecomputeRunSession:
        if session.run_state == GuiRunState.RUNNING:
            self.transition_session_state(session, GuiRunState.STOPPING)
            self.transition_session_state(session, GuiRunState.COMPLETED)
            self._persist_gui_session_checkpoint(session)
        elif session.run_state == GuiRunState.PAUSED:
            self.transition_session_state(session, GuiRunState.STOPPING)
            self.transition_session_state(session, GuiRunState.COMPLETED)
            self._persist_gui_session_checkpoint(session)
        return session

    def resume_gui_session(self, session: GuiPrecomputeRunSession, *, current_context: dict[str, Any]) -> GuiPrecomputeRunSession:
        if session.run_state != GuiRunState.PAUSED:
            return session
        if self.build_scenario_fingerprint(current_context) != session.scenario_fingerprint:
            raise ValueError("resume blocked: scenario fingerprint mismatch")
        self.transition_session_state(session, GuiRunState.RUNNING)
        self._persist_gui_session_checkpoint(session)
        return session

    def reset_gui_session(self, session: GuiPrecomputeRunSession) -> GuiPrecomputeRunSession:
        if session.run_state in (GuiRunState.PAUSED, GuiRunState.COMPLETED, GuiRunState.FAILED):
            self.transition_session_state(session, GuiRunState.IDLE)
            self._persist_gui_session_checkpoint(session)
        return session

    def restore_gui_session(self, *, run_id: int, scenario_fingerprint: str) -> GuiPrecomputeRunSession | None:
        # Phase 4: Check cached sessions first (for in-memory testing)
        if run_id in self._gui_sessions:
            session = self._gui_sessions[run_id]
            # CRITICAL FIX: On restore from PAUSED state, reset next_cell_index to actual completed work
            # This prevents skipping cells that were dispatched but didn't complete before app exit
            # next_cell_index is the dispatch cursor, but incomplete futures are lost on app exit
            # So we resume from completed_cells + failed_cells (the actual checkpoint)
            if session.run_state == GuiRunState.PAUSED:
                session.next_cell_index = session.completed_cells + session.failed_cells
            
            self._log_gui_lifecycle_event(
                event="gui_precompute_checkpoint_restored",
                run_id=session.run_id,
                completed_cells=session.completed_cells,
                failed_cells=session.failed_cells,
                next_cell_index=session.next_cell_index,
                status=session.run_state.value,
            )
            return session
        return None

    def restore_latest_gui_session(self, *, scenario_fingerprint: str) -> GuiPrecomputeRunSession | None:
        # Phase 4: Find latest session with RUNNING or PAUSED state
        latest_run_id = None
        latest_session = None
        for run_id, session in self._gui_sessions.items():
            if session.run_state in (GuiRunState.RUNNING, GuiRunState.PAUSED):
                if latest_run_id is None or run_id > latest_run_id:
                    latest_run_id = run_id
                    latest_session = session
        
        if latest_session is None:
            return None
        return self.restore_gui_session(run_id=latest_run_id, scenario_fingerprint=scenario_fingerprint)

    @staticmethod
    def build_scenario_fingerprint(context: dict[str, Any]) -> str:
        payload = {
            "position": context.get("position"),
            "metric": context.get("metric"),
            "position_actions": context.get("position_actions", {}),
            "pot_size": context.get("pot_size"),
            "bet_amount": context.get("bet_amount"),
            "effective_mode": context.get("effective_mode"),
        }
        return json.dumps(payload, sort_keys=True)

    @staticmethod
    def build_job_fingerprint(profile: PrecomputeProfile) -> str:
        payload = {
            "positions": list(profile.positions),
            "metrics": list(profile.metrics),
            "strict_modes": list(profile.strict_modes),
            "simulations_per_cell": int(profile.simulations_per_cell),
        }
        return json.dumps(payload, sort_keys=True)

    def get_progress_snapshot(self, session: GuiPrecomputeRunSession, *, current_cell_label: str | None = None, active_scenario_key: str | None = None, phase: RunnerPhase = RunnerPhase.ORCHESTRATION) -> dict[str, Any]:
        telemetry = self.build_runner_telemetry(session, current_cell_label=current_cell_label, active_scenario_key=active_scenario_key, phase=phase)
        current_cell = None
        if telemetry.current_cell_index is not None:
            current_cell = {"index": telemetry.current_cell_index, "hand_key": telemetry.current_cell_label}
        return {
            "run_state": telemetry.run_state.value,
            "completed_cells": telemetry.completed_cells,
            "total_cells": telemetry.total_cells,
            "current_cell": current_cell,
            "active_scenario_key": telemetry.active_scenario_key,
            "phase": telemetry.phase.value,
            "elapsed_seconds": telemetry.elapsed_seconds,
            "eta_seconds": telemetry.eta_seconds,
            "failure_count": telemetry.failure_count,
        }

    def get_job_progress(self, job_session_id: int) -> dict[str, Any]:
        session = self.database_repository.get_precompute_job_session(job_session_id)
        if session is None:
            raise ValueError(f"Precompute job session {job_session_id} does not exist")

        links = self.database_repository.get_scenario_run_links_for_job(job_session_id)
        active_link = next((link for link in links if link.status == "RUNNING"), None)
        active_scenario_key = active_link.scenario_key if active_link is not None else None
        phase = RunnerPhase.ORCHESTRATION
        if active_link is not None and active_link.status == "RUNNING":
            phase = RunnerPhase.SOLVER_WRITE

        elapsed_seconds = 0.0
        if session.elapsed_active_ms is not None:
            elapsed_seconds = session.elapsed_active_ms / 1000.0

        eta_seconds = None
        processed = session.completed_scenarios + session.failed_scenarios
        if session.started_at and processed > 0:
            started_at = session.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)
            elapsed_seconds = (datetime.now(UTC) - started_at).total_seconds()
            if processed > 0:
                remaining = max(0, session.requested_scenarios - processed)
                eta_seconds = (elapsed_seconds / processed) * remaining

        return {
            "run_state": session.run_state,
            "completed_scenarios": session.completed_scenarios,
            "total_scenarios": session.requested_scenarios,
            "active_scenario_key": active_scenario_key,
            "phase": phase.value,
            "elapsed_seconds": elapsed_seconds,
            "eta_seconds": eta_seconds,
            "failure_count": session.failed_scenarios,
        }

    def get_job_scenario_mappings(self, job_session_id: int) -> list[dict[str, Any]]:
        links = self.database_repository.get_scenario_run_links_for_job(job_session_id)
        return [
            {
                "scenario_index": link.scenario_index,
                "scenario_key": link.scenario_key,
                "status": link.status,
                "simulation_id": link.simulation_id,
                "matrix_id": link.matrix_id,
                "failure_boundary": link.failure_boundary,
                "failure_reason": link.failure_reason,
            }
            for link in links
        ]

    def request_job_cancellation(self, job_session_id: int) -> None:
        self.database_repository.update_precompute_job_session(
            job_session_id,
            run_state="STOPPING",
        )

    def _is_job_cancel_requested(self, job_session_id: int) -> bool:
        session = self.database_repository.get_precompute_job_session(job_session_id)
        return session is not None and session.run_state == "STOPPING"

    def run_gui_cell(
        self,
        *,
        session: GuiPrecomputeRunSession,
        context: dict[str, Any],
        cell_index: int | None = None,
    ) -> dict[str, Any] | None:
        if session.run_state != GuiRunState.RUNNING:
            return None

        if cell_index is None:
            if session.next_cell_index >= session.total_cells:
                self.transition_session_state(session, GuiRunState.COMPLETED)
                self._persist_gui_session_checkpoint(session)
                return None

            idx = int(session.next_cell_index)
            session.next_cell_index = idx + 1
        else:
            idx = int(cell_index)

        session.current_cell_index = idx
        cell, status_message = self.compute_gui_cell(context=context, cell_index=idx, session=session)

        if session.run_state in (GuiRunState.RUNNING, GuiRunState.STOPPING, GuiRunState.COMPLETED):
            self.apply_gui_cell_result(session=session, context=context, cell=cell, status_message=status_message)

        session.current_cell_index = None
        return cell

    def compute_gui_cell(self, *, context: dict[str, Any], cell_index: int, session: GuiPrecomputeRunSession) -> tuple[dict[str, Any], str | None]:
        if session.run_state != GuiRunState.RUNNING:
            return {}, None

        row = int(cell_index) // 13
        col = int(cell_index) % 13
        hand_key = self.provider._matrix_keys[row][col]  # pylint: disable=protected-access
        metric = str(context["metric"])
        try:
            # Get individual simulation outcomes instead of aggregated metrics
            individual_outcomes, solved_status = self._get_individual_outcomes_for_hand(
                context,
                hand_key,
                int(context["timeout_ms"]),
                session,
            )

            if individual_outcomes:
                # Calculate aggregated metrics for backward compatibility
                wins = sum(1 for outcome in individual_outcomes if outcome['outcome'] == 'WIN')
                ties = sum(1 for outcome in individual_outcomes if outcome['outcome'] == 'TIE')
                total_sims = len(individual_outcomes)

                win_prob = wins / total_sims if total_sims > 0 else 0.0
                tie_prob = ties / total_sims if total_sims > 0 else 0.0
                loss_prob = 1.0 - win_prob - tie_prob
                equity = win_prob + (ties / total_sims * 0.5) if total_sims > 0 else 0.0
                ev = sum(outcome['ev_chips'] for outcome in individual_outcomes) / total_sims if total_sims > 0 else 0.0

                metrics = {
                    "WIN_LOSE_PROBABILITY": round(win_prob, 4),
                    "TIE_PROBABILITY": round(tie_prob, 4),
                    "LOSS_PROBABILITY": round(loss_prob, 4),
                    "EQUITY": round(equity, 4),
                    "EV": round(ev, 4),
                    "EQR": round(max(0.0, min(1.0, equity / max(1e-6, self.provider._baseline_equity(hand_key)))), 4),
                }
                value = metrics.get(metric)
                status = "AVAILABLE"
                status_message = None
            elif solved_status == "STOPPED":
                return {}, None
            elif solved_status == "TIMEOUT":
                metrics = {
                    "WIN_LOSE_PROBABILITY": None,
                    "TIE_PROBABILITY": None,
                    "LOSS_PROBABILITY": None,
                    "EQUITY": None,
                    "EV": None,
                    "EQR": None,
                }
                value = None
                status = "TIMEOUT"
                status_message = "Solver timeout"
                individual_outcomes = []
            else:
                metrics = {
                    "WIN_LOSE_PROBABILITY": None,
                    "TIE_PROBABILITY": None,
                    "LOSS_PROBABILITY": None,
                    "EQUITY": None,
                    "EV": None,
                    "EQR": None,
                }
                value = None
                status = "MISSING"
                status_message = "No simulation outcomes generated"
                individual_outcomes = []

        except Exception as exc:  # pragma: no cover - defensive execution path
            metrics = {
                "WIN_LOSE_PROBABILITY": None,
                "TIE_PROBABILITY": None,
                "LOSS_PROBABILITY": None,
                "EQUITY": None,
                "EV": None,
                "EQR": None,
            }
            value, status, status_message = None, "ERROR", str(exc)
            individual_outcomes = []

        return {
            "row": row,
            "col": col,
            "hand_key": hand_key,
            "metrics": metrics,
            "value": value,
            "status": status,
            "display": format_metric_value(metric, value),
            "individual_outcomes": individual_outcomes,  # Include individual outcomes
        }, status_message

    def _get_individual_outcomes_for_hand(
        self,
        context: dict[str, Any],
        hand_key: str,
        remaining_timeout_ms: int,
        session: GuiPrecomputeRunSession,
    ) -> tuple[list[dict[str, Any]] | None, str]:
        """Get individual simulation outcomes for a hand key."""
        if session.stop_event.is_set():
            return None, "STOPPED"

        action = context["action"]
        active_players = int(context["active_players"])
        pot_size = float(context["pot_size"])
        bet_amount = float(context["bet_amount"])

        # Selected all-in with no opponents is an uncontested capture.
        if action == "ALL_IN" and active_players == 1:
            # Return a single outcome for uncontested win
            return [{
                'hero_hand': hand_key,
                'villain_hand': 'NONE',  # No opponent
                'outcome': 'WIN',
                'hero_equity': 1.0,
                'ev_chips': pot_size,
                'board_cards': ''
            }], "AVAILABLE"

        num_opponents = self.provider._resolve_num_opponents(action, context["position_actions"])  # pylint: disable=protected-access

        # Use direct solver instead of provider solver
        solver = self._get_solver()
        solved = solver.evaluate_hand_key(
            hand_key=hand_key,
            num_opponents=num_opponents,
            pot_size=pot_size,
            bet_amount=bet_amount,
            timeout_ms=max(1, int(remaining_timeout_ms)),
        )

        solved_status = solved.get("status")
        if solved_status != "AVAILABLE":
            return None, solved_status

        # Extract individual outcomes from solver result
        individual_outcomes = solved.get("individual_outcomes", [])
        
        # If the solver says AVAILABLE but provides no individual outcomes,
        # do not fabricate data for GameState persistence.
        if not individual_outcomes:
            self.logger.warning(
                "Solver returned AVAILABLE without individual outcomes for hand_key=%s; skipping GameState storage",
                hand_key,
            )
            return None, "NO_INDIVIDUAL_OUTCOMES"

        return individual_outcomes, solved_status

    def apply_gui_cell_result(
        self,
        *,
        session: GuiPrecomputeRunSession,
        context: dict[str, Any],
        cell: dict[str, Any],
        status_message: str | None,
    ) -> None:
        status = str(cell.get("status"))
        hand_key = str(cell.get("hand_key"))
        cell_index = int(cell.get("row", 0)) * 13 + int(cell.get("col", 0))

        individual_outcomes = cell.get("individual_outcomes", [])
        if status == "AVAILABLE" and not individual_outcomes:
            raise ValueError(
                f"Cannot persist AVAILABLE cell {hand_key} without individual_outcomes"
            )

        # Store cell results in database
        if session.sim_id is not None and session.matrix_id is not None:
            try:
                row_idx = int(cell.get("row", 0))
                col_idx = int(cell.get("col", 0))
                metrics = cell.get("metrics", {})
                
                # Construct hand combination: hero vs random opponents
                hand_combination = f"{hand_key} vs Random"
                
                # Map metrics to database fields
                db_metrics = {
                    "equity": metrics.get("EQUITY", 0.5),
                    "jackpot_adjusted_ev": metrics.get("EV", 0.0),
                }
                
                # Get matrix cell ID for GameState creation
                cell_id = self.database_repository.upsert_matrix_cell(
                    matrix_id=session.matrix_id,
                    row_idx=row_idx,
                    col_idx=col_idx,
                    hand_key=hand_combination,
                    metrics=db_metrics,
                    status=status
                )
                self.logger.debug("Stored cell %d,%d (%s) in database", row_idx, col_idx, hand_combination)
                
                # SIM-001: Store individual simulation outcomes as GameStates
                individual_outcomes = cell.get("individual_outcomes", [])
                if individual_outcomes and status not in (STATUS_TIMEOUT, STATUS_ERROR):
                    self._store_individual_outcomes_as_game_states(
                        cell_id=cell_id,
                        individual_outcomes=individual_outcomes,
                        context=context
                    )
                
            except Exception as exc:
                self.logger.warning("Failed to store cell %d,%d in database: %s", cell.get("row", 0), cell.get("col", 0), exc)

        if status in (STATUS_TIMEOUT, STATUS_ERROR):
            session.failed_cells += 1
            self._log_gui_lifecycle_event(
                event="gui_precompute_cell_failed",
                run_id=session.run_id,
                cell_index=cell_index,
                hand_key=hand_key,
                status=status,
            )
        else:
            session.completed_cells += 1

        if status_message:
            context["status_message"] = status_message

        session.validate()
        if (session.completed_cells + session.failed_cells) >= session.total_cells and session.run_state == GuiRunState.RUNNING:
            self.transition_session_state(session, GuiRunState.COMPLETED)
        self._persist_gui_session_checkpoint(session)

    def mark_gui_dispatch(self, session: GuiPrecomputeRunSession) -> None:
        session.validate()
        self._persist_gui_session_checkpoint(session)

    def _persist_gui_session_checkpoint(self, session: GuiPrecomputeRunSession) -> None:
        # Phase 4: Update cached session
        if session.run_id is None:
            return
        # Update the cache with the latest session state
        self._gui_sessions[session.run_id] = session
        self._log_gui_lifecycle_event(
            event="gui_precompute_checkpoint_saved",
            run_id=session.run_id,
            completed_cells=session.completed_cells,
            failed_cells=session.failed_cells,
            next_cell_index=session.next_cell_index,
            status=session.run_state.value,
        )

    def _build_scenario_key(self, context: dict[str, Any]) -> str:
        """Build a scenario key from context for storing individual outcomes."""
        import hashlib
        import json

        # Create a simplified scenario key based on key context parameters
        scenario_data = {
            "position": context.get("position"),
            "action": context.get("action"),
            "active_players": context.get("active_players"),
            "pot_size": context.get("pot_size"),
            "bet_amount": context.get("bet_amount"),
            "position_actions": context.get("position_actions"),
        }
        encoded = json.dumps(scenario_data, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_hole_cards_for_storage(hole_cards: str | None) -> str | None:
        """Normalize solver output to a valid 4-character hole card string."""
        if not hole_cards or not isinstance(hole_cards, str):
            return None

        normalized = hole_cards.strip()
        if normalized.upper() in ("RANDOM", "NONE", "??"):
            return None

        # Valid 4-char card string requires rank+suit + rank+suit.
        if len(normalized) == 4:
            rank1, suit1, rank2, suit2 = normalized[0].upper(), normalized[1].lower(), normalized[2].upper(), normalized[3].lower()
            valid_ranks = "23456789TJQKA"
            valid_suits = "shdc"
            if rank1 in valid_ranks and suit1 in valid_suits and rank2 in valid_ranks and suit2 in valid_suits:
                return f"{rank1}{suit1}{rank2}{suit2}"
            return None

        if len(normalized) == 2:
            rank1, rank2 = normalized[0].upper(), normalized[1].upper()
            valid_ranks = "23456789TJQKA"
            if rank1 in valid_ranks and rank2 in valid_ranks:
                suit1 = "h"
                suit2 = "d"
                return f"{rank1}{suit1}{rank2}{suit2}"
            return None

        if len(normalized) == 3:
            rank1, rank2, suit_flag = normalized[0].upper(), normalized[1].upper(), normalized[2].lower()
            valid_ranks = "23456789TJQKA"
            if rank1 not in valid_ranks or rank2 not in valid_ranks:
                return None

            if suit_flag == "s":
                return f"{rank1}h{rank2}h"
            if suit_flag == "o":
                return f"{rank1}h{rank2}d"
            return None

        return None

    def _store_individual_outcomes_as_game_states(
        self,
        *,
        cell_id: int,
        individual_outcomes: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> None:
        """
        Store individual simulation outcomes as GameState records.
        
        SIM-001: Convert individual_outcomes from solver to GameStates-first architecture.
        PERF-002: Performance monitoring integrated for data capture operations.
        """
        analyzer = PokerAnalyzer()
        with performance_monitor.track_operation(
            "store_individual_outcomes",
            cell_id=cell_id,
            outcome_count=len(individual_outcomes)
        ):
            try:
                pot_size = float(context.get("pot_size", 1000))
                bet_amount = float(context.get("bet_amount", pot_size))
                
                for outcome in individual_outcomes:
                    # Build board card storage values
                    raw_board_cards = outcome.get("board_cards", "")
                    cards = [card.strip() for card in raw_board_cards.replace(',', ' ').split() if card.strip()]
                    if cards:
                        cards.extend(['??'] * max(0, 5 - len(cards)))
                        cards = cards[:5]
                        board_cards_str = ",".join(cards)
                    else:
                        cards = []
                        board_cards_str = ""

                    board_card_data = {
                        'flop1': cards[0] if len(cards) > 0 else '',
                        'flop2': cards[1] if len(cards) > 1 else '',
                        'flop3': cards[2] if len(cards) > 2 else '',
                        'turn': cards[3] if len(cards) > 3 else '',
                        'river': cards[4] if len(cards) > 4 else '',
                    }

                    # Use GameStates-first storage and avoid legacy BoardCard IDs
                    game_state_data = {
                        'round': 'preflop',
                        'pot_size': pot_size,
                        'board_cards_str': board_cards_str,
                        'outcome': outcome.get('outcome')
                    }

                    with performance_monitor.track_operation("create_game_state", cell_id=cell_id):
                        game_state_id = self.database_repository.create_game_state(game_state_data)

                    hero_hand = self._normalize_hole_cards_for_storage(outcome.get('hero_hand', 'AA'))
                    villain_hand = self._normalize_hole_cards_for_storage(outcome.get('villain_hand', 'NONE'))

                    if hero_hand is None:
                        self.logger.warning(
                            "Skipping individual outcome because hero_hand is not a valid hole card string: %s",
                            outcome.get('hero_hand')
                        )
                        continue

                    # Hero player
                    hero_hole_cards = [hero_hand[i:i+2] for i in range(0, len(hero_hand), 2)]
                    hero_hand_class = analyzer.get_hand_class_value(hero_hole_cards, cards)
                    hero_strength = analyzer.evaluate_hand(hero_hole_cards, cards)
                    hero_data = {
                        'game_state_id': game_state_id,
                        'position': 'hero',
                        'hole_cards': hero_hand,
                        'stack_size': pot_size,
                        'is_hero': True,
                        'hand_class': hero_hand_class,
                        'final_strength': hero_strength,
                    }

                    with performance_monitor.track_operation("create_player", game_state_id=game_state_id, is_hero=True):
                        hero_id = self.database_repository.create_player(hero_data)

                    villain_id = None
                    villain_ids: list[int] = []
                    villain_hands_list = outcome.get('villain_hands')
                    if isinstance(villain_hands_list, list) and villain_hands_list:
                        for idx, villain_hand_entry in enumerate(villain_hands_list):
                            normalized_villain_hand = self._normalize_hole_cards_for_storage(villain_hand_entry)
                            if normalized_villain_hand is None:
                                continue

                            villain_hole_cards = [normalized_villain_hand[i:i+2] for i in range(0, len(normalized_villain_hand), 2)]
                            villain_hand_class = analyzer.get_hand_class_value(villain_hole_cards, cards)
                            villain_strength = analyzer.evaluate_hand(villain_hole_cards, cards)
                            villain_data = {
                                'game_state_id': game_state_id,
                                'position': f'villain_{idx}',
                                'hole_cards': normalized_villain_hand,
                                'stack_size': pot_size,
                                'is_hero': False,
                                'hand_class': villain_hand_class,
                                'final_strength': villain_strength,
                            }

                            with performance_monitor.track_operation("create_player", game_state_id=game_state_id, is_hero=False):
                                vid = self.database_repository.create_player(villain_data)
                            villain_ids.append(vid)
                    else:
                        normalized_villain_hand = self._normalize_hole_cards_for_storage(villain_hand)
                        if normalized_villain_hand is not None:
                            villain_hole_cards = [normalized_villain_hand[i:i+2] for i in range(0, len(normalized_villain_hand), 2)]
                            villain_hand_class = analyzer.get_hand_class_value(villain_hole_cards, cards)
                            villain_strength = analyzer.evaluate_hand(villain_hole_cards, cards)
                            villain_data = {
                                'game_state_id': game_state_id,
                                'position': 'villain',
                                'hole_cards': normalized_villain_hand,
                                'stack_size': pot_size,
                                'is_hero': False,
                                'hand_class': villain_hand_class,
                                'final_strength': villain_strength,
                            }

                            with performance_monitor.track_operation("create_player", game_state_id=game_state_id, is_hero=False):
                                villain_id = self.database_repository.create_player(villain_data)
                                villain_ids.append(villain_id)

                    # Create Bets (all-in raises)
                    hero_bet_data = {
                        'game_state_id': game_state_id,
                        'player_id': hero_id,
                        'amount': bet_amount,
                        'action_type': 'raise',
                        'round': 'preflop'
                    }

                    with performance_monitor.track_operation("create_bet", game_state_id=game_state_id, player_id=hero_id):
                        self.database_repository.create_bet(hero_bet_data)

                    if villain_ids:
                        for vid in villain_ids:
                            villain_bet_data = {
                                'game_state_id': game_state_id,
                                'player_id': vid,
                                'amount': bet_amount,
                                'action_type': 'raise',
                                'round': 'preflop'
                            }

                            with performance_monitor.track_operation("create_bet", game_state_id=game_state_id, player_id=vid):
                                self.database_repository.create_bet(villain_bet_data)

                    # Check for jackpots
                    with performance_monitor.track_operation("check_jackpots", game_state_id=game_state_id):
                        self._check_and_create_jackpots_for_game_state(
                            game_state_id=game_state_id,
                            hero_hand=hero_hand,
                            villain_hand=villain_hand if villain_hand is not None else 'NONE',
                            board_cards=board_card_data,
                            pot_size=pot_size,
                            hero_id=hero_id,
                            villain_id=villain_id
                        )

            except Exception as exc:
                self.logger.warning("Failed to store individual outcomes as GameStates: %s", exc)
            # Don't fail the entire cell processing for GameState storage issues

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary for data capture operations.
        
        PERF-002: Provides performance metrics for monitoring and alerting.
        
        Returns:
            Dictionary with performance statistics for all tracked operations
        """
        return performance_monitor.get_performance_summary()

    def reset_performance_baseline(self, operation_name: Optional[str] = None) -> None:
        """
        Reset performance baseline for monitoring.
        
        Args:
            operation_name: Specific operation to reset, or None for all
        """
        performance_monitor.reset_baseline(operation_name)

    def _check_and_create_jackpots_for_game_state(
        self,
        *,
        game_state_id: int,
        hero_hand: str,
        villain_hand: str,
        board_cards: dict[str, str],
        pot_size: float,
        hero_id: int,
        villain_id: int | None,
    ) -> None:
        """
        Check for jackpots in the game state and create Jackpot records.
        
        Uses the jackpot detector to identify qualifying hands and create records.
        """
        try:
            from hopilot.gto.jackpot_detector import JackpotDetector
            
            detector = JackpotDetector()
            
            # Convert board cards to list format expected by detector
            board_cards_list = [
                board_cards['flop1'], board_cards['flop2'], board_cards['flop3'],
                board_cards['turn'], board_cards['river']
            ]
            board_cards_list = [card for card in board_cards_list if card and card != '??']
            
            # Check hero hand for jackpots
            if hero_hand and hero_hand != '????':
                hero_cards = [hero_hand[:2], hero_hand[2:]]  # Split hole cards
                hero_result = detector.detect_jackpot(hero_cards, board_cards_list, pot_size)
                if hero_result and hero_result.jackpot_type != 'high_card':
                    jackpot_data = {
                        'game_state_id': game_state_id,
                        'player_id': hero_id,
                        'jackpot_type': hero_result.jackpot_type,
                        'payout_amount': hero_result.payout_amount,
                        'qualifying_cards': hero_result.qualifying_cards
                    }
                    self.database_repository.create_jackpot(jackpot_data)
            
            # Check villain hand for jackpots (if specific hand, not random or placeholder)
            if villain_id and villain_hand and villain_hand != '????':
                villain_cards = [villain_hand[:2], villain_hand[2:]]  # Split hole cards
                villain_result = detector.detect_jackpot(villain_cards, board_cards_list, pot_size)
                if villain_result and villain_result.jackpot_type != 'high_card':
                    jackpot_data = {
                        'game_state_id': game_state_id,
                        'player_id': villain_id,
                        'jackpot_type': villain_result.jackpot_type,
                        'payout_amount': villain_result.payout_amount,
                        'qualifying_cards': villain_result.qualifying_cards
                    }
                    self.database_repository.create_jackpot(jackpot_data)
                    
        except Exception as exc:
            self.logger.warning("Failed to check/create jackpots for game state %d: %s", game_state_id, exc)

    def run_gui_scenario(
        self,
        *,
        session: GuiPrecomputeRunSession,
        context: dict[str, Any],
        on_cell_complete: Any | None = None,
        max_cells: int | None = None,
    ) -> int:
        processed = 0
        while session.run_state == GuiRunState.RUNNING:
            if max_cells is not None and processed >= max_cells:
                break
            cell = self.run_gui_cell(session=session, context=context)
            if cell is None:
                break
            processed += 1
            if on_cell_complete is not None:
                on_cell_complete(cell)
        return processed

    @staticmethod
    def can_transition_state(from_state: GuiRunState, to_state: GuiRunState) -> bool:
        return to_state in _GUI_TRANSITIONS[from_state]

    def transition_session_state(
        self,
        session: GuiPrecomputeRunSession,
        to_state: GuiRunState,
        *,
        now_utc: datetime | None = None,
        now_perf: float | None = None,
    ) -> GuiPrecomputeRunSession:
        if not self.can_transition_state(session.run_state, to_state):
            raise ValueError(f"invalid transition: {session.run_state.value} -> {to_state.value}")

        now_utc = now_utc or datetime.now(UTC)
        now_perf = time.perf_counter() if now_perf is None else float(now_perf)
        previous_state = session.run_state

        if previous_state == GuiRunState.RUNNING and session._active_start_perf is not None:
            elapsed = max(0.0, now_perf - session._active_start_perf)
            session.elapsed_active_ms += int(elapsed * 1000)
            session._active_start_perf = None

        session.run_state = to_state
        if to_state == GuiRunState.RUNNING:
            if session.started_at is None:
                session.started_at = now_utc
            session.paused_at = None
            session.finished_at = None
            session._active_start_perf = now_perf
        elif to_state == GuiRunState.PAUSED:
            session.paused_at = now_utc
            session.current_cell_index = None
        elif to_state in (GuiRunState.COMPLETED, GuiRunState.FAILED):
            session.finished_at = now_utc
            session.current_cell_index = None
        elif to_state == GuiRunState.IDLE:
            session.paused_at = None
            session.finished_at = None
            session.current_cell_index = None

        session.validate()
        self._log_gui_lifecycle_event(
            event=f"gui_precompute_{to_state.value.lower()}",
            run_id=session.run_id,
            from_state=previous_state.value,
            to_state=to_state.value,
            completed_cells=session.completed_cells,
            failed_cells=session.failed_cells,
            next_cell_index=session.next_cell_index,
        )
        return session

    def build_runner_telemetry(
        self,
        session: GuiPrecomputeRunSession,
        *,
        current_cell_label: str | None = None,
        active_scenario_key: str | None = None,
        phase: RunnerPhase = RunnerPhase.ORCHESTRATION,
        now_utc: datetime | None = None,
        now_perf: float | None = None,
    ) -> RunnerTelemetrySnapshot:
        now_utc = now_utc or datetime.now(UTC)
        now_perf = time.perf_counter() if now_perf is None else float(now_perf)

        elapsed_ms = int(session.elapsed_active_ms)
        if session.run_state == GuiRunState.RUNNING and session._active_start_perf is not None:
            elapsed_ms += int(max(0.0, now_perf - session._active_start_perf) * 1000)

        processed = int(session.completed_cells + session.failed_cells)
        elapsed_seconds = elapsed_ms / 1000.0
        throughput = None
        eta = None
        if elapsed_seconds > 0 and processed > 0:
            throughput = (processed / elapsed_seconds) * 60.0
            remaining = max(0, session.total_cells - processed)
            eta = remaining / (processed / elapsed_seconds)

        return RunnerTelemetrySnapshot(
            run_state=session.run_state,
            completed_cells=processed,
            total_cells=int(session.total_cells),
            current_cell_index=session.current_cell_index,
            current_cell_label=current_cell_label,
            active_scenario_key=active_scenario_key,
            phase=phase,
            elapsed_seconds=elapsed_seconds,
            eta_seconds=eta,
            failure_count=int(session.failed_cells),
            throughput_cells_per_minute=throughput,
            last_update_at=now_utc,
        )

    def _log_gui_lifecycle_event(self, event: str, **fields: Any) -> None:
        self.logger.info("AoF gui precompute event=%s fields=%s", event, fields)

    def _persist_scenario_results(self, scenario_key: str, payload: dict[str, Any]) -> dict[str, int] | None:
        """
        Phase 3: Persist precompute results to normalized database.
        
        Converts the solver payload (cells with metrics) into database records
        for HandMatrix and MatrixCell tables according to the normalized schema.
        Returns the simulation and matrix IDs when successful.
        """
        try:
            # Parse scenario key: format is position:actions:metric:strict_mode
            # where actions is hyphen-separated (action_UTG-action_BTN-action_SB-action_BB)
            parts = scenario_key.split(":")
            if len(parts) < 4:
                self.logger.warning(f"Cannot parse scenario key: {scenario_key}")
                return None

            position_str = parts[0].strip()
            actions_str = parts[1].strip()  # e.g., "FOLD-FOLD-FOLD-FOLD"
            metric_str = parts[2].strip()
            strict_str = parts[3].strip()
            
            # Create simulation record with required parameters per schema
            # Parameters must include: num_simulations, matrix_size, game_type
            import json
            parameters = json.dumps({
                "num_simulations": 120,  # Default from config
                "matrix_size": "13x13",  # Standard size
                "game_type": "cash",  # Default game type
                "position": position_str,
                "actions": actions_str,
                "metric": metric_str,
                "strict_mode": strict_str,
            })
            sim_id = self.database_repository.create_simulation(parameters)
            
            # Create hand matrix record (only needs simulation_id)
            matrix_id = self.database_repository.create_hand_matrix(sim_id)
            
            # Insert cells with computed metrics
            cells = payload.get("cells", [])
            for cell in cells:
                try:
                    row_idx = cell.get("row")
                    col_idx = cell.get("col")
                    raw_hand_key = cell.get("hand_key")
                    hand_key = str(raw_hand_key) if raw_hand_key is not None else "Unknown"
                    if " vs " not in hand_key:
                        hand_key = f"{hand_key} vs Random"
                    metrics = cell.get("metrics", {})
                    status = cell.get("status", "AVAILABLE")
                    
                    # Call upsert with new signature
                    self.database_repository.upsert_matrix_cell(
                        matrix_id=matrix_id,
                        row_idx=row_idx,
                        col_idx=col_idx,
                        hand_key=hand_key,
                        metrics=metrics,
                        status=status
                    )
                except Exception as cell_err:
                    self.logger.warning(f"Failed to persist cell {row_idx},{col_idx}: {cell_err}")
                    
            self.logger.info(f"Persisted scenario {scenario_key} to database (sim_id={sim_id}, matrix_id={matrix_id}, cells={len(cells)})")
            return {"simulation_id": sim_id, "matrix_id": matrix_id}
        except Exception as e:
            self.logger.error(f"Failed to persist scenario results: {e}", exc_info=True)
            return None

    def _position_to_id(self, position_str: str) -> int:
        """Map position string to ID (Phase 3 placeholder)."""
        position_map = {"UTG": 1, "BTN": 2, "SB": 3, "BB": 4}
        return position_map.get(position_str, 0)

    def _action_to_id(self, action_str: str) -> int:
        """Map action string to ID (Phase 3 placeholder)."""
        action_map = {"ALL_IN": 1, "FOLD": 2, "CALL": 3, "RAISE": 4}
        return action_map.get(action_str, 0)

    def enumerate_scenarios(self, profile: PrecomputeProfile) -> list[dict[str, Any]]:
        scenarios: list[dict[str, Any]] = []
        for position in profile.positions:
            for metric in profile.metrics:
                for strict_mode in profile.strict_modes:
                    for actions in product(("FOLD", "ALL_IN"), repeat=4):
                        position_actions = {
                            "UTG": actions[0],
                            "BTN": actions[1],
                            "SB": actions[2],
                            "BB": actions[3],
                        }
                        # Create scenario_key with all actions to ensure uniqueness
                        # Format: position:action_UTG:action_BTN:action_SB:action_BB:metric:strict_mode
                        # Persist code only parses first two parts (position:action) so this is backward compatible
                        actions_str = "-".join(actions)
                        scenario_key = f"{position}:{actions_str}:{metric}:{strict_mode}"
                        scenarios.append(
                            {
                                "scenario_key": scenario_key,
                                "position": position,
                                "metric": metric,
                                "position_actions": position_actions,
                                "strict_current_action": strict_mode,
                            }
                        )
        return scenarios

    def _build_matrix_sweep_contract(
        self,
        *,
        context: dict[str, Any],
        profile: PrecomputeProfile,
        job_session_id: int | None = None,
        scenario_key: str | None = None,
    ) -> dict[str, Any]:
        position_actions = dict(context.get("position_actions", {}))
        active_players = [
            pos for pos, action in position_actions.items() if action == "ALL_IN"
        ]
        if not active_players and context.get("position"):
            active_players = [context["position"]]

        sims_per_combo = int(profile.simulations_per_cell)
        contract = {
            "selected_position": str(context["position"]),
            "hero_action": str(context["action"]),
            "position_actions": position_actions,
            "active_players": active_players,
            "num_opponents": max(1, len(active_players) - 1),
            "pot_size": float(context.get("pot_size", 0.0)),
            "bet_amount": float(context.get("bet_amount", 0.0)),
            "sims_per_combo": sims_per_combo,
            "num_simulations": sims_per_combo,
            "matrix_size": "13x13",
            "game_type": str(context.get("game_type", "nlhe")),
            "run_kind": "matrix_sweep",
        }
        if job_session_id is not None:
            contract["precompute_job_session_id"] = job_session_id
        if scenario_key is not None:
            contract["scenario_key"] = scenario_key
        return contract

    def _execute_matrix_sweep(self, scenario_contract: dict[str, Any]) -> dict[str, Any]:
        from hopilot.database.persistence import BatchingPersistenceStrategy
        from hopilot.gto.matrix_sweep_service import MatrixSweepService

        batch_size = min(max(1, int(scenario_contract.get("sims_per_combo", 120))), 1000)
        service = MatrixSweepService(
            self.database_repository,
            PokerAnalyzer(),
            lambda session: BatchingPersistenceStrategy(session=session, batch_size=batch_size),
        )
        try:
            sweep_result = service.run_sweep(scenario_contract)
        except Exception as error:
            if isinstance(error, MatrixSweepAggregationError):
                raise
            raise

        return {
            "simulation_id": sweep_result["simulation_id"],
            "matrix_id": sweep_result["matrix_id"],
            "raw_game_states_written": sweep_result["raw_game_states_written"],
            "raw_players_written": sweep_result["raw_players_written"],
            "matrix_cells_written": sweep_result["matrix_cells_written"],
            "aggregated_metrics_written": sweep_result["aggregated_metrics_written"],
            "failed_combinations": sweep_result["failed_combinations"],
            "unmapped_hero_records": sweep_result["unmapped_hero_records"],
            "status": sweep_result["status"],
        }

    def run(
        self,
        profile: PrecomputeProfile | None = None,
        *,
        run_id: int | None = None,
        max_scenarios: int | None = None,
    ) -> int:
        profile = profile or PrecomputeProfile()
        scenarios = self.enumerate_scenarios(profile)
        if max_scenarios is not None:
            scenarios = scenarios[: int(max_scenarios)]

        if run_id is not None:
            self.logger.warning("Resume semantics for run_id are not supported in this migration path; starting a new job")
            run_id = None

        self.precompute_orchestration_service.provider = self.provider

        job_session_id = self.precompute_job_persistence_service.create_job_session(
            scenario_fingerprint=self.build_job_fingerprint(profile),
            requested_scenarios=len(scenarios),
        )

        completed = 0
        failed = 0
        self.last_job_session_id = job_session_id
        self.logger.info(f"Starting precompute run job_id={job_session_id} with {len(scenarios)} scenarios")

        for idx, scenario in enumerate(scenarios):
            if self._is_job_cancel_requested(job_session_id):
                self.logger.info("Cancellation requested for job_id=%s, stopping dispatch of new scenarios", job_session_id)
                break

            scenario_key = scenario["scenario_key"]
            scenario_link_id = self.precompute_job_persistence_service.create_scenario_link(
                job_session_id=job_session_id,
                scenario_index=idx,
                scenario_key=scenario_key,
                scenario_contract={},
                status="PENDING",
            )
            try:
                self.precompute_job_persistence_service.mark_link_running(scenario_link_id)

                context = self.precompute_orchestration_service.resolve_scenario_context(
                    scenario
                )

                contract = self.precompute_orchestration_service.build_matrix_sweep_contract(
                    context=context,
                    profile=profile,
                    job_session_id=job_session_id,
                    scenario_key=scenario_key,
                )
                self.precompute_job_persistence_service.update_scenario_contract(
                    scenario_link_id,
                    scenario_contract=contract,
                )
            except Exception as exc:
                self.precompute_job_persistence_service.mark_link_failed(
                    scenario_link_id,
                    failure_boundary="orchestration",
                    failure_reason=str(exc),
                )
                failed += 1
                self.precompute_job_persistence_service.update_job_progress(
                    job_session_id,
                    completed_scenarios=completed,
                    failed_scenarios=failed,
                )
                self.logger.error("Scenario %s failed during orchestration: %s", scenario_key, exc)
                continue

            try:
                sweep_result = self._execute_matrix_sweep(contract)
                self.precompute_job_persistence_service.mark_link_completed(
                    scenario_link_id,
                    simulation_id=sweep_result["simulation_id"],
                    matrix_id=sweep_result["matrix_id"],
                )
                completed += 1
            except MatrixSweepContractError as exc:
                self.precompute_job_persistence_service.mark_link_failed(
                    scenario_link_id,
                    failure_boundary="orchestration",
                    failure_reason=str(exc),
                )
                failed += 1
                self.logger.error("Scenario %s failed during orchestration: %s", scenario_key, exc)
            except MatrixSweepAggregationError as exc:
                self.precompute_job_persistence_service.mark_link_failed(
                    scenario_link_id,
                    failure_boundary="aggregation",
                    failure_reason=str(exc),
                )
                failed += 1
                self.logger.error("Scenario %s failed during aggregation: %s", scenario_key, exc)
            except Exception as exc:
                self.precompute_job_persistence_service.mark_link_failed(
                    scenario_link_id,
                    failure_boundary="solver_write",
                    failure_reason=str(exc),
                )
                failed += 1
                self.logger.error("Scenario %s failed during sweep execution: %s", scenario_key, exc)
            finally:
                self.precompute_job_persistence_service.update_job_progress(
                    job_session_id,
                    completed_scenarios=completed,
                    failed_scenarios=failed,
                )

        job_session = self.precompute_job_persistence_service.get_job_session(job_session_id)
        canceled = job_session is not None and job_session.run_state == "STOPPING"

        # Mandatory final reconciliation pass: recompute completed/failed counts
        # from persisted scenario links before terminal job finalization.
        reconciliation_result = self.precompute_job_persistence_service.reconcile_job_session(
            job_session_id,
            canceled=canceled,
        )
        completed = reconciliation_result.completed_scenarios
        failed = reconciliation_result.failed_scenarios

        if job_session and job_session.run_state == "STOPPING":
            final_state = "CANCELED"
        else:
            final_state = "FAILED" if failed > 0 else "COMPLETED"

        self.precompute_job_persistence_service.finalize_job(
            job_session_id,
            completed_scenarios=completed,
            failed_scenarios=failed,
            canceled=canceled,
        )

        self.logger.info(
            "Precompute run complete job_id=%s completed=%s failed=%s final_state=%s",
            job_session_id,
            completed,
            failed,
            final_state,
        )
        return 0

    def run_precompute(
        self,
        profile: PrecomputeProfile | None = None,
        *,
        max_scenarios: int | None = None,
    ) -> int:
        return self.run(profile=profile, max_scenarios=max_scenarios)
