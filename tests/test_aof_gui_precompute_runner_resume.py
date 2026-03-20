import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiRunState


class _FastSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.88}


def _make_store(tmp_path):
    # Phase 4: Scenario store removed, return None for in-memory testing
    return None


def _context(provider: BrowserDatabaseProvider, *, position: str = "UTG") -> dict:
    return provider._build_context(  # pylint: disable=protected-access
        position=position,
        metric="EV",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
    )


def test_stop_persists_checkpoint_and_restart_restores_session(tmp_path):
    # Phase 4: Provider now requires database_url, old cache_enabled parameter removed
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    # provider._solver = _FastSolver()  # Phase 4: Solver mocking removed
    store = _make_store(tmp_path)  # Kept for compatibility but not used
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)
    context = _context(provider)
    fingerprint = runner.build_scenario_fingerprint(context)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.bind_gui_run(session)

    runner.run_gui_scenario(session=session, context=context, max_cells=7)
    runner.stop_gui_session(session)

    restored = runner.restore_gui_session(run_id=int(session.run_id or 0), scenario_fingerprint=fingerprint)
    assert restored is not None
    assert restored.next_cell_index >= 7
    assert restored.run_state == GuiRunState.COMPLETED


def test_resume_blocked_on_scenario_fingerprint_mismatch(tmp_path):
    # Phase 4: Provider now requires database_url
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    # provider._solver = _FastSolver()  # Phase 4: Solver mocking removed
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)

    context = _context(provider, position="UTG")
    session = runner.create_gui_session(
        simulations_per_cell=1000,
        scenario_fingerprint=runner.build_scenario_fingerprint(context),
    )
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.pause_gui_session(session)

    mismatch_context = _context(provider, position="BB")
    with pytest.raises(ValueError):
        runner.resume_gui_session(session, current_context=mismatch_context)


def test_restore_latest_checkpoint_returns_most_recent_paused_run(tmp_path):
    # Phase 4: Provider now requires database_url
    database_url = "sqlite:///:memory:"
    provider = BrowserDatabaseProvider(database_url=database_url)
    # provider._solver = _FastSolver()  # Phase 4: Solver mocking removed
    store = _make_store(tmp_path)  # Kept for compatibility but not used
    runner = AoFPrecomputeRunner(provider=provider, database_url=database_url)

    context = _context(provider)
    fingerprint = runner.build_scenario_fingerprint(context)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.bind_gui_run(session)
    runner.run_gui_scenario(session=session, context=context, max_cells=3)
    runner.pause_gui_session(session)

    restored = runner.restore_latest_gui_session(scenario_fingerprint=fingerprint)
    assert restored is not None
    assert restored.run_id == session.run_id
    assert restored.next_cell_index >= 3
