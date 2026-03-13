import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiRunState
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


class _FastSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.88}


def _make_store(tmp_path):
    return AoFScenarioCacheStore(
        db_path=str(tmp_path / "aof_gui_resume.sqlite3"),
        signatures=CacheSignatures(
            schema_version="1",
            solver_signature="aof-solver-v1",
            policy_signature="aof-cache-policy-v1",
            runtime_signature="runtime-v1",
        ),
    )


def _context(provider: AoFBrowserDataProvider, *, position: str = "UTG") -> dict:
    return provider._build_context(  # pylint: disable=protected-access
        position=position,
        metric="EV",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
    )


def test_stop_persists_checkpoint_and_restart_restores_session(tmp_path):
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)
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
    assert restored.run_state == GuiRunState.PAUSED


def test_resume_blocked_on_scenario_fingerprint_mismatch(tmp_path):
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    runner = AoFPrecomputeRunner(provider, _make_store(tmp_path))

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
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

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
