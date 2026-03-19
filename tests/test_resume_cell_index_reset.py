"""Tests to verify cells aren't skipped when resuming after exit."""

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
        db_path=str(tmp_path / "cell_skip_fix.sqlite3"),
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


def test_resume_from_paused_resets_next_cell_index_to_completed_cells(tmp_path):
    """Verify next_cell_index is reset to completed+failed on restore from PAUSED.
    
    Scenario: 
    - Worker threads dispatched cells 0,1,2 but none completed
    - Pause + exit app
    - Restore: next_cell_index should be 0 (completed + failed = 0 + 0)
    - Resume should reprocess cells 0,1,2, not skip to 3
    """
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    context = _context(provider)
    fingerprint = runner.build_scenario_fingerprint(context)
    
    # Create session with some cells marked as completed
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.bind_gui_run(session)
    
    # Simulate: dispatcher sent 3 cells to workers (next_cell_index=3)
    # but none competed yet (completed_cells=0)
    session.next_cell_index = 3
    session.completed_cells = 0
    session.failed_cells = 0
    runner._persist_gui_session_checkpoint(session)
    
    # Pause the session
    runner.pause_gui_session(session)
    
    # Now restore (simulating app restart)
    restored = runner.restore_gui_session(run_id=int(session.run_id or 0), scenario_fingerprint=fingerprint)
    
    # Verify next_cell_index was reset to completed + failed = 0
    # This prevents skipping cells that were dispatched but not completed
    assert restored is not None
    assert restored.run_state == GuiRunState.PAUSED
    assert restored.next_cell_index == 0, f"Expected next_cell_index=0, got {restored.next_cell_index}"
    assert restored.completed_cells == 0
    assert restored.failed_cells == 0


def test_resume_from_paused_preserves_completed_progress(tmp_path):
    """Verify that completed work is not redone when resuming.
    
    Scenario:
    - Cells 0-2: completed (3 completed)
    - Cells 3-4: dispatched but not completed (next_cell_index=5)
    - Pause + exit
    - Restore: next_cell_index should be 3 (completed=3, failed=0)
    - Resume reprocesses incomplete cells (3,4), not the completed ones
    """
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    context = _context(provider)
    fingerprint = runner.build_scenario_fingerprint(context)
    
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.bind_gui_run(session)
    
    # Simulate: 3 cells completed, 2 dispatched but not yet completed
    session.next_cell_index = 5
    session.completed_cells = 3
    session.failed_cells = 0
    runner._persist_gui_session_checkpoint(session)
    
    runner.pause_gui_session(session)
    
    restored = runner.restore_gui_session(run_id=int(session.run_id or 0), scenario_fingerprint=fingerprint)
    
    # Verify next_cell_index = completed + failed = 3 + 0 = 3
    assert restored is not None
    assert restored.next_cell_index == 3, f"Expected next_cell_index=3, got {restored.next_cell_index}"
    assert restored.completed_cells == 3
    assert restored.failed_cells == 0


def test_resume_from_paused_with_failed_cells(tmp_path):
    """Verify next_cell_index accounts for both completed and failed cells."""
    provider = AoFBrowserDataProvider(cache_enabled=False)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    context = _context(provider)
    fingerprint = runner.build_scenario_fingerprint(context)
    
    session = runner.create_gui_session(simulations_per_cell=1000, scenario_fingerprint=fingerprint)
    runner.transition_session_state(session, GuiRunState.RUNNING)
    runner.bind_gui_run(session)
    
    # Simulate: 2 completed, 1 failed, next_cell_index at 5
    session.next_cell_index = 5
    session.completed_cells = 2
    session.failed_cells = 1
    runner._persist_gui_session_checkpoint(session)
    
    runner.pause_gui_session(session)
    
    restored = runner.restore_gui_session(run_id=int(session.run_id or 0), scenario_fingerprint=fingerprint)
    
    # Verify next_cell_index = completed + failed = 2 + 1 = 3
    assert restored is not None
    assert restored.next_cell_index == 3, f"Expected next_cell_index=3, got {restored.next_cell_index}"
    assert restored.completed_cells == 2
    assert restored.failed_cells == 1
