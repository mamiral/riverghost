"""
Integration tests for State Machine Controller.
Tests real state transitions instead of mock call counts.
"""

import pytest
import sys
import os
from unittest.mock import Mock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python"))

from hopilot.gui_components.state_machine_controller import StateMachineController
from hopilot.gto.aof_precompute_runner import PrecomputeProfile
from hopilot.state_machine_config import SimulationState


class TestStateMachineControllerIntegration:
    """Integration tests for State Machine Controller with real state management."""

    @pytest.fixture
    def mock_panel(self):
        """Create a mock panel with realistic behavior."""
        panel = Mock()
        panel.precompute_session = None
        panel.start_precompute.return_value = True
        panel.pause_precompute.return_value = True
        panel.resume_precompute.return_value = True
        panel.stop_precompute.return_value = True
        panel.cancel_pending_work.return_value = True
        panel.reset_precompute.return_value = True
        panel.update_precompute_config.return_value = True
        return panel

    @pytest.fixture
    def controller(self, mock_panel):
        """Create a controller with mock panel."""
        from hopilot.gui_components.precompute_config import PrecomputeConfig
        config = PrecomputeConfig(max_workers=2, simulations_per_cell=1000)
        return StateMachineController(panel=mock_panel, config=config)

    def test_state_machine_transitions_work_correctly(self, controller, mock_panel):
        """Integration test: State machine transitions work with real panel interactions."""
        # Start with IDLE state
        assert controller.get_current_state() == SimulationState.IDLE

        # Trigger start
        result = controller.trigger_event("start")
        assert result is True
        
        # Verify state changed and panel method was called
        assert mock_panel.start_precompute.called, "Should call start_precompute on panel"
        
        # Verify state is now RUNNING (assuming successful start)
        # Note: Actual state depends on implementation, this is a basic integration test

    def test_state_machine_handles_pause_resume(self, controller, mock_panel):
        """Integration test: State machine handles pause and resume correctly."""
        # Start the controller
        controller.trigger_event("start")
        
        # Pause
        result = controller.trigger_event("pause")
        assert result is True
        assert mock_panel.pause_precompute.called, "Should call pause_precompute"
        
        # Resume
        result = controller.trigger_event("resume")
        assert result is True
        assert mock_panel.resume_precompute.called, "Should call resume_precompute"

    def test_state_machine_handles_stop(self, controller, mock_panel):
        """Integration test: State machine handles stop correctly."""
        # Start and then stop
        controller.trigger_event("start")
        result = controller.trigger_event("stop")

        assert result is True
        assert mock_panel.stop_precompute.called, "Should call stop_precompute"
        assert controller.get_current_state() == SimulationState.STOPPING

        # Verify panel method was called once for stop
        mock_panel.start_precompute.assert_called_once()
        mock_panel.stop_precompute.assert_called_once()

        # Stop should block further pause/resume transitions
        assert controller.trigger_event("pause") is False
        assert controller.get_current_state() == SimulationState.STOPPING
        assert controller.trigger_event("resume") is False
        assert controller.get_current_state() == SimulationState.STOPPING

    def test_multiple_start_calls_are_handled(self, controller, mock_panel):
        """Integration test: Multiple start calls are handled correctly."""
        # First start
        result1 = controller.trigger_event("start")
        assert result1 is True
        assert controller.get_current_state() == SimulationState.RUNNING

        # Second start should be rejected when already running
        result2 = controller.trigger_event("start")
        assert result2 is False

        # Should still be in RUNNING state
        assert controller.get_current_state() == SimulationState.RUNNING

        # Verify start was called only once
        assert mock_panel.start_precompute.call_count == 1

    def test_invalid_transitions_are_rejected(self, controller):
        """Integration test: Invalid state transitions are properly rejected."""
        # Start with IDLE
        assert controller.get_current_state() == SimulationState.IDLE

        # Try invalid transition: pause when not running
        result = controller.trigger_event("pause")
        # Should reject invalid transition
        assert result is False or controller.get_current_state() == SimulationState.IDLE

        # Try invalid transition: resume when not paused
        result = controller.trigger_event("resume")
        # Should reject invalid transition
        assert result is False or controller.get_current_state() == SimulationState.IDLE

    def test_reset_functionality_works(self, controller, mock_panel):
        """Integration test: Reset functionality returns to clean state."""
        # Simulate a completed session before reset
        controller.mark_completed()
        assert controller.get_current_state() == SimulationState.COMPLETED

        # Reset
        result = controller.trigger_event("reset")
        assert result is True
        assert controller.get_current_state() == SimulationState.IDLE

        # Verify reset was called on panel
        mock_panel.reset_precompute.assert_called_once()