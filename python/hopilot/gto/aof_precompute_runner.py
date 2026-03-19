from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from itertools import product
import json
import time
from typing import Any

from hopilot.gto.aof_browser_data_provider import (
    AoFBrowserDataProvider,
    STATUS_ERROR,
    STATUS_TIMEOUT,
)
from hopilot.gto.aof_hand_matrix import format_metric_value
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, AggregationService
from hopilot.logging_config import get_logger


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
    def __init__(self, provider: AoFBrowserDataProvider, store: AoFScenarioCacheStore | None, aggregation_db_path: str | None = None):
        self.logger = get_logger(__name__)
        self.provider = provider
        self.store = store
        self.aggregation_service = AggregationService(aggregation_db_path) if aggregation_db_path else None

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
        if self.store is None:
            return session
        if session.run_id is None:
            session.run_id = int(self.store.begin_run(total_scenarios=session.total_cells, scenario_fingerprint=session.scenario_fingerprint))
        self.store.persist_gui_checkpoint(
            session.run_id,
            resume_cursor=session.next_cell_index,
            completed_cells=session.completed_cells,
            failed_cells=session.failed_cells,
            status=session.run_state.value,
        )
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
        if self.store is None:
            return None
        checkpoint = self.store.get_gui_checkpoint_cursor(run_id)
        if checkpoint is None:
            return None
        run = self.store.get_run(run_id)
        if run is None:
            return None
        # Use the stored fingerprint if available, otherwise use the provided one
        stored_fingerprint = checkpoint.get("scenario_fingerprint") or scenario_fingerprint
        session = GuiPrecomputeRunSession(
            run_id=int(run_id),
            scenario_fingerprint=stored_fingerprint,
            run_state=GuiRunState(str(checkpoint["status"])),
            simulations_per_cell=1000,
            total_cells=169,
            completed_cells=int(checkpoint["completed_cells"]),
            failed_cells=int(checkpoint["failed_cells"]),
            next_cell_index=int(checkpoint["resume_cursor"]),
        )
        session.validate()
        
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

    def restore_latest_gui_session(self, *, scenario_fingerprint: str) -> GuiPrecomputeRunSession | None:
        if self.store is None:
            return None
        latest_run_id = self.store.get_latest_run_id(statuses=(GuiRunState.RUNNING.value, GuiRunState.PAUSED.value))
        if latest_run_id is None:
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
                equity = win_prob + (ties / total_sims * 0.5) if total_sims > 0 else 0.0
                ev = sum(outcome['ev_chips'] for outcome in individual_outcomes) / total_sims if total_sims > 0 else 0.0

                metrics = {
                    "WIN_LOSE_PROBABILITY": round(win_prob, 4),
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

        # Store individual outcomes if available
        individual_outcomes = cell.get("individual_outcomes", [])
        if individual_outcomes and self.aggregation_service:
            try:
                from hopilot.gto.aof_scenario_cache_store import SimulationOutcome, RunData
                from datetime import datetime, UTC

                # Convert individual outcomes to SimulationOutcome objects
                simulation_outcomes = []
                for outcome in individual_outcomes:
                    sim_outcome = SimulationOutcome(
                        hero_hand=outcome['hero_hand'],
                        villain_hand=outcome['villain_hand'],
                        outcome=outcome['outcome'],
                        hero_equity=outcome['hero_equity'],
                        ev_chips=outcome['ev_chips'],
                        board_cards=outcome.get('board_cards', ''),
                    )
                    simulation_outcomes.append(sim_outcome)

                if simulation_outcomes:
                    # Create scenario key from context
                    scenario_key = self._build_scenario_key(context)

                    # Create run data
                    run_data = RunData(
                        timestamp=datetime.now(UTC),
                        sim_count=len(simulation_outcomes),
                        combo_samples=4,  # Default value
                        timeout=30.0,  # Default value
                        seed=42,  # Default value
                        outcomes=simulation_outcomes
                    )

                    # Store the run
                    self.aggregation_service.store_run(scenario_key, run_data)
                    self.logger.info("Stored %d individual outcomes for hand %s", len(simulation_outcomes), hand_key)

            except Exception as exc:
                self.logger.warning("Failed to store individual outcomes for hand %s: %s", hand_key, exc)

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
        if self.store is None or session.run_id is None:
            return
        self.store.persist_gui_checkpoint(
            session.run_id,
            resume_cursor=session.next_cell_index,
            completed_cells=session.completed_cells,
            failed_cells=session.failed_cells,
            status=session.run_state.value,
        )
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
                        scenarios.append(
                            {
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
        if self.store is None:
            raise RuntimeError("AoFPrecomputeRunner.run requires a configured cache store")
        profile = profile or PrecomputeProfile()
        scenarios = self.enumerate_scenarios(profile)
        if max_scenarios is not None:
            scenarios = scenarios[: int(max_scenarios)]

        if run_id is None:
            run_id = self.store.begin_run(total_scenarios=len(scenarios))
            resume_idx = 0
        else:
            previous = self.store.get_run(run_id)
            resume_idx = int(previous.resume_cursor or 0) if previous else 0

        completed = 0
        failed = 0
        for idx in range(resume_idx, len(scenarios)):
            scenario = scenarios[idx]
            context = self.provider._build_context(  # pylint: disable=protected-access
                position=scenario["position"],
                metric=scenario["metric"],
                position_actions=scenario["position_actions"],
                strict_current_action=scenario["strict_current_action"],
            )
            key = self.provider._build_solver_equivalence_key(context)  # pylint: disable=protected-access
            runtime_signature = self.provider._runtime_signature(context)  # pylint: disable=protected-access

            if self.store.has_current(key, runtime_signature):
                self.store.record_write_result(run_id=run_id, scenario_key_hash=key, outcome="SKIPPED_CURRENT")
                completed += 1
                self.store.update_run_progress(run_id, completed=completed, failed=failed, resume_cursor=idx + 1)
                continue

            try:
                payload = self.provider.get_matrix_payload(
                    position=scenario["position"],
                    metric=scenario["metric"],
                    position_actions=scenario["position_actions"],
                    strict_current_action=scenario["strict_current_action"],
                )
                statuses = {cell.get("status") for cell in payload.get("cells", [])}
                if "TIMEOUT" in statuses or "ERROR" in statuses:
                    failed += 1
                    self.store.record_write_result(run_id=run_id, scenario_key_hash=key, outcome="FAILED", error_message="degraded_status")
                else:
                    completed += 1
                    self.store.record_write_result(run_id=run_id, scenario_key_hash=key, outcome="UPDATED")
            except Exception as exc:  # pragma: no cover - defensive path for precompute jobs
                failed += 1
                self.store.record_write_result(run_id=run_id, scenario_key_hash=key, outcome="FAILED", error_message=str(exc))

            self.store.update_run_progress(run_id, completed=completed, failed=failed, resume_cursor=idx + 1)

        status = "FAILED" if failed > 0 else "COMPLETED"
        self.store.finalize_run(run_id, status=status)
        self.logger.info("AoF precompute run complete run_id=%s completed=%s failed=%s", run_id, completed, failed)
        return run_id
