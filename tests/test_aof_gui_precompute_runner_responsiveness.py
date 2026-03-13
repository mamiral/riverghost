import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiRunState
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


class _FastSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.6, "equity": 0.57, "ev": 0.82}


def _make_store(tmp_path):
    return AoFScenarioCacheStore(
        db_path=str(tmp_path / "aof_gui_precompute.sqlite3"),
        signatures=CacheSignatures(
            schema_version="1",
            solver_signature="aof-solver-v1",
            policy_signature="aof-cache-policy-v1",
            runtime_signature="runtime-v1",
        ),
    )


def _make_context(provider: AoFBrowserDataProvider) -> dict:
    return provider._build_context(  # pylint: disable=protected-access
        position="UTG",
        metric="EV",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
    )


def test_pause_transition_acknowledged_within_one_second(tmp_path):
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    runner = AoFPrecomputeRunner(provider, _make_store(tmp_path))
    context = _make_context(provider)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=runner.build_scenario_fingerprint(context))
    runner.transition_session_state(session, GuiRunState.RUNNING)

    start = time.perf_counter()
    runner.pause_gui_session(session)
    elapsed = time.perf_counter() - start

    assert session.run_state == GuiRunState.PAUSED
    assert elapsed <= 1.0


def test_stop_transition_acknowledged_within_one_second(tmp_path):
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    runner = AoFPrecomputeRunner(provider, _make_store(tmp_path))
    context = _make_context(provider)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=runner.build_scenario_fingerprint(context))
    runner.transition_session_state(session, GuiRunState.RUNNING)

    start = time.perf_counter()
    runner.stop_gui_session(session)
    elapsed = time.perf_counter() - start

    assert session.run_state == GuiRunState.PAUSED
    assert elapsed <= 1.0
