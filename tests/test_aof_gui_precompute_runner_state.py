import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiRunState


class _FastSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.62, "equity": 0.59, "ev": 0.91, "individual_outcomes": [{"hero_hand": kwargs.get("hand_key", "AA"), "villain_hand": "RANDOM", "outcome": "WIN", "hero_equity": 0.62, "ev_chips": 0.91, "board_cards": ""}]}


class _TimeoutOnFirstSolver:
    def __init__(self):
        self.calls = 0

    def evaluate_hand_key(self, *args, **kwargs):
        self.calls += 1
        hand_key = kwargs.get("hand_key")
        if self.calls == 1:
            return {"status": "TIMEOUT"}
        return {"status": "AVAILABLE", "win_probability": 0.62, "equity": 0.59, "ev": 0.91, "individual_outcomes": [{"hero_hand": hand_key, "villain_hand": "RANDOM", "outcome": "WIN", "hero_equity": 0.62, "ev_chips": 0.91, "board_cards": ""}]}


class _NoOutcomesSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.62, "equity": 0.59, "ev": 0.91, "individual_outcomes": []}


def _build_context(provider: BrowserDatabaseProvider) -> dict:
    # Use canonical scenario for UTG
    return provider._build_context(  # pylint: disable=protected-access
        position="UTG",
        metric="EV",
    )


def test_sequential_cell_progression_with_per_cell_callback_assertions():
    # Phase 4: Provider now requires database_url
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)
    runner._solver = _FastSolver()  # Mock solver for testing

    context = _build_context(provider)
    total_cells = 13
    session = runner.create_gui_session(
        simulations_per_cell=1000,
        scenario_fingerprint=runner.build_scenario_fingerprint(context),
        total_cells=total_cells,
    )
    runner.transition_session_state(session, GuiRunState.RUNNING)

    seen_indices: list[int] = []

    def _on_cell(cell: dict) -> None:
        seen_indices.append(int(cell["row"]) * 13 + int(cell["col"]))

    processed = runner.run_gui_scenario(session=session, context=context, on_cell_complete=_on_cell)

    assert processed == total_cells
    assert len(seen_indices) == total_cells
    assert seen_indices == list(range(total_cells))
    assert session.run_state == GuiRunState.COMPLETED


def test_matrix_immediate_update_for_completed_cells():
    # Phase 4: Provider now requires database_url
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)
    runner._solver = _FastSolver()  # Mock solver for testing

    context = _build_context(provider)
    session = runner.create_gui_session(
        simulations_per_cell=1000,
        scenario_fingerprint=runner.build_scenario_fingerprint(context),
        total_cells=169,
    )
    runner.transition_session_state(session, GuiRunState.RUNNING)

    first = runner.run_gui_cell(session=session, context=context)
    second = runner.run_gui_cell(session=session, context=context)

    assert first is not None
    assert second is not None
    assert first["row"] == 0 and first["col"] == 0
    assert second["row"] == 0 and second["col"] == 1
    assert first["status"] == "AVAILABLE"
    assert second["status"] == "AVAILABLE"


def test_telemetry_accuracy_for_progress_elapsed_eta_and_failures():
    # Phase 4: Provider now requires database_url
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)
    runner._solver = _FastSolver()  # Mock solver for testing

    context = _build_context(provider)
    session = runner.create_gui_session(
        simulations_per_cell=1000,
        scenario_fingerprint=runner.build_scenario_fingerprint(context),
        total_cells=169,
    )
    session.completed_cells = 20
    session.failed_cells = 5
    session.elapsed_active_ms = 25000

    snapshot = runner.get_progress_snapshot(session, current_cell_label="AKo")
    assert snapshot["completed_cells"] == 25
    assert snapshot["failure_count"] == 5
    assert snapshot["elapsed_seconds"] == 25.0
    assert snapshot["eta_seconds"] is not None


def test_timeout_and_error_paths_increment_failures_and_continue():
    # Phase 4: Provider now requires database_url
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)
    runner._solver = _TimeoutOnFirstSolver()  # Mock solver for testing

    context = _build_context(provider)
    session = runner.create_gui_session(
        simulations_per_cell=1000,
        scenario_fingerprint=runner.build_scenario_fingerprint(context),
        total_cells=169,
    )
    runner.transition_session_state(session, GuiRunState.RUNNING)

    processed = runner.run_gui_scenario(session=session, context=context, max_cells=5)

    assert processed == 5
    assert session.failed_cells == 1
    assert session.completed_cells == 4
    assert session.next_cell_index == 5

    def test_available_cell_without_individual_outcomes_raises_guard():
        database_url = "sqlite:///:memory:"
        provider = BrowserDatabaseProvider(database_url=database_url)
        runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)
        runner._solver = _NoOutcomesSolver()

        context = _build_context(provider)
        session = runner.create_gui_session(
            simulations_per_cell=1000,
            scenario_fingerprint=runner.build_scenario_fingerprint(context),
            total_cells=1,
        )
        runner.transition_session_state(session, GuiRunState.RUNNING)

        with pytest.raises(ValueError, match=r"Cannot persist AVAILABLE cell"):
            runner.run_gui_cell(session=session, context=context)