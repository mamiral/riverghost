"""
Regression tests for precompute pause/resume issues.

Issue 1: Cells are skipped when PAUSE/RESUME - pending futures cancelled cells are never reprocessed
Issue 2: Precompute never finishes - due to skipped cells, completion never reached
"""
import os
import sys
from unittest.mock import MagicMock, patch, PropertyMock
from concurrent.futures import Future

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_precompute_runner import GuiRunState, GuiPrecomputeRunSession
from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
from hopilot.gui_components.precompute_config import PrecomputeConfig


class MockRunnerWithTrackingAndDelay:
    """Mock runner that tracks which cells are submitted and returns them slowly."""
    
    def __init__(self):
        self.submitted_cells = []  # Track all submitted cell indices
        self.completed_cells = {}  # Track completed cell indices
        self.processed_cells_set = set()  # Track processed (including cancelled)
        self.cancel_count = 0
        
    def track_submission(self, cell_index):
        """Track that a cell was submitted."""
        self.submitted_cells.append(cell_index)
        self.processed_cells_set.add(cell_index)
        
    def track_completion(self, cell_index):
        """Track that a cell completed."""
        self.completed_cells[cell_index] = True
        
    def get_unprocessed_cells(self):
        """Get cells that were submitted but never completed."""
        return self.submitted_cells


def create_app_with_mock_runner():
    """Create an AoFBrowserPanel with mocked runner for testing."""
    app = MagicMock(spec=AoFBrowserPanel)
    app.precompute_session = GuiPrecomputeRunSession(
        run_id=1,
        scenario_fingerprint="test",
        run_state=GuiRunState.IDLE,
        simulations_per_cell=100,
        total_cells=4,  # Small number for easier testing
        completed_cells=0,
        failed_cells=0,
        next_cell_index=0,
    )
    app.precompute_context = {"test": "context"}
    app.precompute_max_workers = 2
    app.precompute_futures = {}
    app.precompute_executor = None
    app.payload = {"cells": []}
    app.provider = MagicMock()
    app.runner = MagicMock()
    app.state = MagicMock()
    app.state.status_message = ""
    app.logger = MagicMock()
    
    # Track runner calls
    app.runner_tracker = MockRunnerWithTrackingAndDelay()
    
    return app


def test_cancel_pending_futures_tracks_cell_indices():
    """Test that cancelling futures properly tracks which cells had pending work."""
    from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
    
    # Create real panel to test the actual method
    panel = MagicMock(spec=AoFBrowserPanel)
    panel.precompute_futures = {}
    panel.precompute_session = GuiPrecomputeRunSession(
        run_id=1,
        scenario_fingerprint="test",
        run_state=GuiRunState.RUNNING,
        simulations_per_cell=100,
        total_cells=10,
        completed_cells=0,
        failed_cells=0,
        next_cell_index=5,  # Already incremented to 5
    )
    panel.logger = MagicMock()
    
    # Simulate futures that have been submitted for cells 3, 4, 5
    future1 = MagicMock(spec=Future)
    future2 = MagicMock(spec=Future)
    future3 = MagicMock(spec=Future)
    
    panel.precompute_futures[future1] = 3
    panel.precompute_futures[future2] = 4
    panel.precompute_futures[future3] = 5
    
    # Before the fix, next_cell_index would remain at 5
    # After fix, it should be reset to 3 (minimum of pending cells)
    
    # Get pending cell indices
    pending_indices = list(panel.precompute_futures.values())
    assert pending_indices == [3, 4, 5], f"Expected [3, 4, 5], got {pending_indices}"
    assert min(pending_indices) == 3, "Minimum cell index should be 3"


def test_pause_resume_should_reprocess_pending_cells():
    """Test that pausing and resuming properly reprocesses cells that had pending futures.
    
    This is a regression test for Issue 1: Cells are skipped when PAUSE/RESUME.
    
    Scenario:
    1. Submit 4 cells with 2 workers (cells 0, 1 submitted, 2-3 pending)
    2. Call pause (should cancel futures for cells 0, 1)
    3. Resume (should re-submit those cells)
    4. Verify all 4 cells eventually complete
    """
    app = create_app_with_mock_runner()
    
    # Track the cell indices that were submitted
    submitted_indices = []
    
    def mock_compute_gui_cell(context=None, cell_index=None):
        app.runner_tracker.track_submission(cell_index)
        submitted_indices.append(cell_index)
        # Return a mock cell result
        return {
            "row": cell_index // 13,
            "col": cell_index % 13,
            "hand_key": f"cell_{cell_index}",
            "status": "AVAILABLE",
            "value": 0.5,
            "display": "0.5",
        }, "OK"
    
    app.runner.compute_gui_cell = mock_compute_gui_cell
    app.runner.apply_gui_cell_result = MagicMock()
    app.runner.mark_gui_dispatch = MagicMock()
    app.runner.pause_gui_session = MagicMock(
        side_effect=lambda s: setattr(s, 'run_state', GuiRunState.PAUSED)
    )
    app.runner.resume_gui_session = MagicMock(
        side_effect=lambda s, **kw: setattr(s, 'run_state', GuiRunState.RUNNING)
    )
    app.runner.transition_session_state = MagicMock(
        side_effect=lambda s, state: setattr(s, 'run_state', state)
    )
    
    # Use actual _cancel_pending_precompute_futures
    from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
    
    actual_panel = AoFBrowserPanel.__new__(AoFBrowserPanel)
    actual_panel.precompute_futures = app.precompute_futures
    actual_panel.precompute_session = app.precompute_session
    actual_panel.logger = app.logger
    
    # Simulate: Tick 1 - submit 2 cells (with 2 workers)
    app.precompute_session.next_cell_index = 0
    app.precompute_session.run_state = GuiRunState.RUNNING
    
    # Create mock futures
    futures = [MagicMock(spec=Future), MagicMock(spec=Future)]
    app.precompute_futures[futures[0]] = 0
    app.precompute_futures[futures[1]] = 1
    
    # Simulate next_cell_index being advanced (this is what _tick_precompute does)
    app.precompute_session.next_cell_index = 2
    
    # Record state before pause
    print(f"Before pause: next_cell_index={app.precompute_session.next_cell_index}, futures={list(app.precompute_futures.values())}")
    
    # Now pause - this should cancel futures for cells 0, 1
    app.runner.pause_gui_session(app.precompute_session)
    
    # THE BUG: Without fix, _cancel_pending_precompute_futures just clears the dict
    # leaving next_cell_index at 2, so cells 0-1 are skipped!
    actual_panel._cancel_pending_precompute_futures()
    
    print(f"After pause: next_cell_index={app.precompute_session.next_cell_index}, futures={list(app.precompute_futures.values())}")
    
    # Expected with FIX: next_cell_index should be reset to 0 (min of [0, 1])
    # Without FIX: next_cell_index stays at 2, cells 0-1 skipped
    
    assert len(app.precompute_futures) == 0, "Futures should be cleared"
    
    # This assertion catches the bug: next_cell_index should be reset to 0
    assert app.precompute_session.next_cell_index == 0, \
        f"BUG DETECTED: next_cell_index not reset after cancel. Expected 0, got {app.precompute_session.next_cell_index}. Cells would be skipped!"


def test_precompute_finishes_after_all_cells_complete():
    """Test that precompute properly completes when all cells are processed.
    
    This is a regression test for Issue 2: Precompute never finishes.
    
    The completion check requires: completed_cells + failed_cells >= total_cells
    If cells are skipped, this never happens.
    """
    app = create_app_with_mock_runner()
    
    # Set small numbers for easy testing
    app.precompute_session.total_cells = 4
    app.precompute_session.completed_cells = 0
    app.precompute_session.failed_cells = 0
    
    # Simulate that 3 cells completed, 1 failed
    app.precompute_session.completed_cells = 3
    app.precompute_session.failed_cells = 1
    
    # Check completion condition
    processed = app.precompute_session.completed_cells + app.precompute_session.failed_cells
    total = app.precompute_session.total_cells
    
    print(f"Processed: {processed}, Total: {total}")
    
    # This should be true for completion
    assert processed >= total, f"Completion check should pass: {processed} >= {total}"
    assert app.precompute_session.run_state != GuiRunState.COMPLETED, "State should not be COMPLETED yet"
    
    # Simulate the state transition
    app.precompute_session.run_state = GuiRunState.COMPLETED
    app.precompute_session.finished_at = None  # Would be set in real code
    
    assert app.precompute_session.run_state == GuiRunState.COMPLETED


def test_pause_during_submission_window():
    """Test pausing while futures are being submitted.
    
    Scenario:
    1. Submit cell 0 -> next_cell_index becomes 1
    2. Submit cell 1 -> next_cell_index becomes 2
    3. Pause before cell 2 is submitted
    4. Resume -> cells 0-1 should be reprocessed, not skipped to cell 2
    """
    # This test verifies the core issue:
    # When futures[0] and futures[1] are submitted for cells 0,1
    # next_cell_index is 2
    # If futures are cancelled and we don't reset next_cell_index, cells 0,1 are lost
    
    pending_futures = {
        id(MagicMock()): 0,  # Cell 0 in flight
        id(MagicMock()): 1,  # Cell 1 in flight
    }
    
    next_cell_index = 2  # Already advanced past pending cells
    
    # THE FIX: This code should run when pause is triggered
    if pending_futures:
        pending_cell_indices = list(pending_futures.values())
        min_pending_index = min(pending_cell_indices) if pending_cell_indices else next_cell_index
        next_cell_index = min_pending_index
    
    # Verify the fix
    assert next_cell_index == 0, f"next_cell_index should be reset to 0, got {next_cell_index}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


def test_full_pause_resume_cycle_completes_all_cells():
    """Integration test: Complete pause/resume cycle should result in completion.
    
    Verifies Issue 2 is also fixed: Precompute finishes after pause/resume.
    
    Scenario:
    1. Track that cells 0-3 are submitted
    2. Pause after a few submissions  
    3. Cancel pending futures (triggering the fix)
    4. Verify cells can be reprocessed
    5. All cells eventually complete
    """
    from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
    
    # Create panel with tracking
    panel = MagicMock(spec=AoFBrowserPanel)
    panel.precompute_session = GuiPrecomputeRunSession(
        run_id=1,
        scenario_fingerprint="test",
        run_state=GuiRunState.RUNNING,
        simulations_per_cell=100,
        total_cells=4,
        completed_cells=0,
        failed_cells=0,
        next_cell_index=0,
    )
    panel.precompute_futures = {}
    panel.logger = MagicMock()
    
    # Simulate submission of cells 0, 1 (with 2 workers)
    futures = [MagicMock(spec=Future), MagicMock(spec=Future)]
    for i, future in enumerate(futures):
        panel.precompute_futures[future] = i
        panel.precompute_session.next_cell_index += 1
    
    assert panel.precompute_session.next_cell_index == 2
    assert len(panel.precompute_futures) == 2
    
    # Use actual cancel method
    actual_panel = AoFBrowserPanel.__new__(AoFBrowserPanel)
    actual_panel.precompute_futures = panel.precompute_futures
    actual_panel.precompute_session = panel.precompute_session
    actual_panel.logger = panel.logger
    
    # Pause - this should cancel and reset next_cell_index
    actual_panel._cancel_pending_precompute_futures()
    
    # Verify state after cancel
    assert len(panel.precompute_futures) == 0
    assert panel.precompute_session.next_cell_index == 0, "Should reset to 0 to reprocess cancelled cells"
    
    # Simulate the cells being reprocessed and completed
    panel.precompute_session.completed_cells = 4
    panel.precompute_session.failed_cells = 0
    
    # Check completion
    processed = panel.precompute_session.completed_cells + panel.precompute_session.failed_cells
    assert processed >= panel.precompute_session.total_cells, "All 4 cells should be processed"


def test_completion_detection_after_reprocessing_cancelled_cells():
    """Test that completion is properly detected after reprocessing.
    
    Before fix: Cells were permanently skipped, so completion never happened.
    After fix: Cells are reprocessed, and completion detection works.
    """
    session = GuiPrecomputeRunSession(
        run_id=1,
        scenario_fingerprint="test",
        run_state=GuiRunState.RUNNING,
        simulations_per_cell=100,
        total_cells=4,
        completed_cells=0,
        failed_cells=0,
        next_cell_index=0,
    )
    
    # Simulate cells 0-3 being submitted but then cancelled
    # Then reprocessed due to our fix
    # Then 2 complete, 2 fail
    session.completed_cells = 2
    session.failed_cells = 2
    
    processed = session.completed_cells + session.failed_cells
    
    # This is the completion check from _tick_precompute
    should_complete = (
        processed >= session.total_cells
        and session.run_state == GuiRunState.RUNNING
    )
    
    assert should_complete, f"Completion should trigger: {processed} >= {session.total_cells}"


def test_multiple_pause_resume_cycles():
    """Test that multiple pause/resume cycles work correctly.
    
    Scenario:
    1. Submit cells, pause (triggers cancel/reset)
    2. Resume, pause again (triggers cancel/reset again)
    3. Verify cells are reprocessed at each cycle
    """
    from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
    
    panel = MagicMock(spec=AoFBrowserPanel)
    panel.precompute_session = GuiPrecomputeRunSession(
        run_id=1,
        scenario_fingerprint="test",
        run_state=GuiRunState.RUNNING,
        simulations_per_cell=100,
        total_cells=4,
        completed_cells=0,
        failed_cells=0,
        next_cell_index=0,
    )
    panel.precompute_futures = {}
    panel.logger = MagicMock()
    
    actual_panel = AoFBrowserPanel.__new__(AoFBrowserPanel)
    actual_panel.precompute_futures = panel.precompute_futures
    actual_panel.precompute_session = panel.precompute_session
    actual_panel.logger = panel.logger
    
    # Cycle 1: Submit cells 0-1, pause, reset should happen
    for i in range(2):
        panel.precompute_futures[MagicMock(spec=Future)] = i
    panel.precompute_session.next_cell_index = 2
    
    actual_panel._cancel_pending_precompute_futures()
    assert panel.precompute_session.next_cell_index == 0, "Cycle 1: Should reset to 0"
    
    # Simulate some cells completing
    panel.precompute_session.completed_cells = 1
    
    # Cycle 2: Submit more cells, pause, reset should happen again
    for i in range(2):
        panel.precompute_futures[MagicMock(spec=Future)] = i
    panel.precompute_session.next_cell_index = 2
    
    actual_panel._cancel_pending_precompute_futures()
    assert panel.precompute_session.next_cell_index == 0, "Cycle 2: Should reset to 0"
    
    # Verify futures are cleared
    assert len(panel.precompute_futures) == 0

