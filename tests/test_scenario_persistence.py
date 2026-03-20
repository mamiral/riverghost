"""Tests for scenario fingerprint persistence across app restarts."""

import json
import os
import sys

import pytest

# Phase 4: AoFScenarioCacheStore removed as part of cache infrastructure cleanup
# These tests are preserved for reference but cannot run without the deleted modules
pytest.skip("Scenario cache store removed in Phase 4", allow_module_level=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

# from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
# from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiRunState
# from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


class _FastSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.88}


def _make_store(tmp_path):
    return AoFScenarioCacheStore(
        db_path=str(tmp_path / "scenario_persistence.sqlite3"),
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


def test_scenario_fingerprint_persisted_on_run_creation(tmp_path):
    """Verify scenario fingerprint is stored when a run is created."""
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    # Create session with BTN scenario
    context = _context(provider, position="BTN")
    fingerprint = runner.build_scenario_fingerprint(context)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    
    # Bind the run (this creates the DB record)
    runner.bind_gui_run(session)

    # Verify scenario fingerprint was stored
    checkpoint = store.get_gui_checkpoint_cursor(int(session.run_id or 0))
    assert checkpoint is not None
    assert checkpoint.get("scenario_fingerprint") == fingerprint
    
    # Verify fingerprint contains BTN
    fp_data = json.loads(checkpoint["scenario_fingerprint"])
    assert fp_data["position"] == "BTN"


def test_scenario_restoration_finds_paused_run_with_different_scenario(tmp_path):
    """Verify paused run is found even if current scenario differs."""
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    # Create and pause precompute in BTN scenario
    btn_context = _context(provider, position="BTN")
    btn_fingerprint = runner.build_scenario_fingerprint(btn_context)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=btn_fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.bind_gui_run(session)
    runner.run_gui_scenario(session=session, context=btn_context, max_cells=3)
    runner.pause_gui_session(session)

    # Now app "restarts" and user is viewing UTG scenario (default)
    utg_context = _context(provider, position="UTG")
    utg_fingerprint = runner.build_scenario_fingerprint(utg_context)
    
    # Restore should find the BTN precompute (not matching current UTG fingerprint)
    # because it looks for latest PAUSED run regardless of fingerprint
    restored = runner.restore_latest_gui_session(scenario_fingerprint=utg_fingerprint)
    
    assert restored is not None
    assert restored.run_state == GuiRunState.PAUSED
    # Crucially: restored session should have BTN fingerprint, not UTG
    assert restored.scenario_fingerprint == btn_fingerprint
    
    # Verify the stored fingerprint contains BTN
    fp_data = json.loads(restored.scenario_fingerprint)
    assert fp_data["position"] == "BTN"


def test_scenario_restoration_preserves_all_context(tmp_path):
    """Verify all scenario context details are preserved."""
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    # Create with specific context
    context = {
        "position": "SB",
        "metric": "EQUITY",
        "position_actions": {"UTG": "FOLD", "BTN": "CALL", "SB": "RAISE", "BB": "CHECK"},
    }
    fingerprint = runner.build_scenario_fingerprint(context)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.bind_gui_run(session)
    runner.pause_gui_session(session)

    # Restore
    restored = runner.restore_gui_session(run_id=int(session.run_id or 0), scenario_fingerprint="")
    
    # Parse and verify all context is preserved
    fp_data = json.loads(restored.scenario_fingerprint)
    assert fp_data["position"] == "SB"
    assert fp_data["metric"] == "EQUITY"
    assert fp_data["position_actions"]["BTN"] == "CALL"
    assert fp_data["position_actions"]["SB"] == "RAISE"


def test_paused_run_not_restored_for_different_scenario_if_explicitly_checked(tmp_path):
    """Verify explicit fingerprint check still blocks resume on scenario mismatch."""
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    runner = AoFPrecomputeRunner(provider, _make_store(tmp_path))

    btn_context = _context(provider, position="BTN")
    btn_fingerprint = runner.build_scenario_fingerprint(btn_context)
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=btn_fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.pause_gui_session(session)

    # Try to resume with different scenario should fail
    utg_context = _context(provider, position="UTG")
    with pytest.raises(ValueError):
        runner.resume_gui_session(session, current_context=utg_context)
