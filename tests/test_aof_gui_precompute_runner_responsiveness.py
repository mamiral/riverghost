import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiRunState


class _FastSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.6, "equity": 0.57, "ev": 0.82}


def _make_store(tmp_path):
    # Phase 4: Scenario store removed, return None for in-memory testing
    return None


def _make_context(provider: BrowserDatabaseProvider) -> dict:
    return provider._build_context(  # pylint: disable=protected-access
        position="UTG",
        metric="EV",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
    )


def test_pause_transition_acknowledged_within_one_second(tmp_path):
    # Phase 4: Provider now requires database_url
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    # provider._solver = _FastSolver()  # Phase 4: Solver mocking removed
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)
    context = _make_context(provider)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=runner.build_scenario_fingerprint(context))
    runner.transition_session_state(session, GuiRunState.RUNNING)

    start = time.perf_counter()
    runner.pause_gui_session(session)
    elapsed = time.perf_counter() - start

    assert session.run_state == GuiRunState.PAUSED
    assert elapsed <= 1.0


def test_stop_transition_acknowledged_within_one_second(tmp_path):
    # Phase 4: Provider now requires database_url
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    # provider._solver = _FastSolver()  # Phase 4: Solver mocking removed
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)
    context = _make_context(provider)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=runner.build_scenario_fingerprint(context))
    runner.transition_session_state(session, GuiRunState.RUNNING)

    start = time.perf_counter()
    runner.stop_gui_session(session)
    elapsed = time.perf_counter() - start

    assert session.run_state == GuiRunState.COMPLETED
    assert elapsed <= 1.0
