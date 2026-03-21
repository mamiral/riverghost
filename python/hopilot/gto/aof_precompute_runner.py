from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from itertools import product
import json
import time
from typing import Any

from hopilot.gto.aof_hand_matrix import format_metric_value
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.logging_config import get_logger

# Phase 4: Status constants (previously from deleted provider)
STATUS_ERROR = "ERROR"
STATUS_TIMEOUT = "TIMEOUT"


@dataclass
class PrecomputeProfile:
    positions: tuple[str, ...] = ("UTG", "BTN", "SB", "BB")
    metrics: tuple[str, ...] = ("WIN_LOSE_PROBABILITY", "EV", "EQUITY", "EQR")
    strict_modes: tuple[bool, ...] = (False, True)


class GuiRunState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


_GUI_TRANSITIONS: dict[GuiRunState, set[GuiRunState]] = {
    GuiRunState.IDLE: {GuiRunState.RUNNING},
    GuiRunState.RUNNING: {GuiRunState.PAUSED, GuiRunState.STOPPING, GuiRunState.COMPLETED, GuiRunState.FAILED},
    GuiRunState.PAUSED: {GuiRunState.RUNNING, GuiRunState.IDLE, GuiRunState.STOPPING, GuiRunState.COMPLETED, GuiRunState.FAILED},
    GuiRunState.STOPPING: {GuiRunState.COMPLETED, GuiRunState.FAILED},
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
        self.database_repository = DatabaseRepository(database_url=database_url)
        # Session cache for in-memory testing and checkpoint restoration
        self._gui_sessions: dict[int, GuiPrecomputeRunSession] = {}
        self._next_run_id = 1  # Counter for assigning run IDs
        self.aggregation_service = None  # Phase 4: Aggregation service removed
        self.logger.info(f"AoFPrecomputeRunner initialized with database: {database_url}")

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

    def get_progress_snapshot(self, session: GuiPrecomputeRunSession, *, current_cell_label: str | None = None) -> dict[str, Any]:
        telemetry = self.build_runner_telemetry(session, current_cell_label=current_cell_label)
        current_cell = None
        if telemetry.current_cell_index is not None:
            current_cell = {"index": telemetry.current_cell_index, "hand_key": telemetry.current_cell_label}
        return {
            "run_state": telemetry.run_state.value,
            "completed_cells": telemetry.completed_cells,
            "total_cells": telemetry.total_cells,
            "current_cell": current_cell,
            "elapsed_seconds": telemetry.elapsed_seconds,
            "eta_seconds": telemetry.eta_seconds,
            "failure_count": telemetry.failure_count,
        }

    def run_gui_cell(
        self,
        *,
        session: GuiPrecomputeRunSession,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        if session.run_state != GuiRunState.RUNNING:
            return None

        if session.next_cell_index >= session.total_cells:
            self.transition_session_state(session, GuiRunState.COMPLETED)
            self._persist_gui_session_checkpoint(session)
            return None

        idx = int(session.next_cell_index)
        session.current_cell_index = idx
        cell, status_message = self.compute_gui_cell(context=context, cell_index=idx)
        session.next_cell_index = idx + 1
        self.apply_gui_cell_result(session=session, context=context, cell=cell, status_message=status_message)
        session.current_cell_index = None
        return cell

    def compute_gui_cell(self, *, context: dict[str, Any], cell_index: int) -> tuple[dict[str, Any], str | None]:
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
    ) -> tuple[list[dict[str, Any]] | None, str]:
        """Get individual simulation outcomes for a hand key."""
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

        # Call solver directly to get individual outcomes
        solved = self.provider._solver.evaluate_hand_key(  # pylint: disable=protected-access
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
        if not individual_outcomes:
            return None, solved_status

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
                
                self.database_repository.upsert_matrix_cell(
                    matrix_id=session.matrix_id,
                    row_idx=row_idx,
                    col_idx=col_idx,
                    hand_key=hand_combination,
                    metrics=db_metrics,
                    status=status
                )
                self.logger.debug("Stored cell %d,%d (%s) in database", row_idx, col_idx, hand_combination)
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
            elapsed_seconds=elapsed_seconds,
            eta_seconds=eta,
            failure_count=int(session.failed_cells),
            throughput_cells_per_minute=throughput,
            last_update_at=now_utc,
        )

    def _log_gui_lifecycle_event(self, event: str, **fields: Any) -> None:
        self.logger.info("AoF gui precompute event=%s fields=%s", event, fields)

    def _persist_scenario_results(self, scenario_key: str, payload: dict[str, Any]) -> None:
        """
        Phase 3: Persist precompute results to normalized database.
        
        Converts the solver payload (cells with metrics) into database records
        for HandMatrix and MatrixCell tables according to the normalized schema.
        """
        try:
            # Parse scenario key: format is position:actions:metric:strict_mode
            # where actions is hyphen-separated (action_UTG-action_BTN-action_SB-action_BB)
            parts = scenario_key.split(":")
            if len(parts) < 4:
                self.logger.warning(f"Cannot parse scenario key: {scenario_key}")
                return

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
                    hand_key = cell.get("hand_key")
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
            
        except Exception as e:
            self.logger.error(f"Failed to persist scenario results: {e}", exc_info=True)

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

        completed = 0
        failed = 0
        
        self.logger.info(f"Starting precompute run with {len(scenarios)} scenarios")
        
        for idx, scenario in enumerate(scenarios):
            try:
                scenario_key = scenario["scenario_key"]
                context = self.provider._build_context(  # pylint: disable=protected-access
                    position=scenario["position"],
                    metric=scenario["metric"],
                    position_actions=scenario["position_actions"],
                    strict_current_action=scenario["strict_current_action"],
                )
                
                # Get solver results
                payload = self.provider.get_matrix_payload(
                    position=scenario["position"],
                    metric=scenario["metric"],
                    position_actions=scenario["position_actions"],
                    strict_current_action=scenario["strict_current_action"],
                )
                
                # Check for errors/timeouts
                statuses = {cell.get("status") for cell in payload.get("cells", [])}
                if "TIMEOUT" in statuses or "ERROR" in statuses:
                    failed += 1
                    self.logger.warning(f"Scenario {scenario_key} failed with status: {statuses}")
                else:
                    # Store results in normalized database
                    self._persist_scenario_results(scenario_key, payload)
                    completed += 1
                    
            except Exception as exc:  # pragma: no cover
                failed += 1
                self.logger.error(f"Error processing scenario {idx}: {exc}")

        status = "FAILED" if failed > 0 else "COMPLETED"
        self.logger.info(f"Precompute run complete: completed={completed}, failed={failed}, status={status}")
        return 0
