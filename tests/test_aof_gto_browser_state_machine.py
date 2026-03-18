# Unit tests for AOF GTO Browser state machine
# Feature: 001-gui-state-refactor

import pytest
from unittest.mock import Mock, patch

from hopilot.aof_gto_browser import GuiApplication
from hopilot.state_machine_config import SimulationState, SimulationTrigger


class TestGuiApplicationStateMachine:
    """Test state machine behavior in GuiApplication."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('pygame.init'), \
             patch('pygame.display.set_mode'), \
             patch('pygame.font.SysFont'):
            self.app = GuiApplication()

    def test_initial_state_is_idle(self):
        """Test that application starts in idle state."""
        assert self.app.state == SimulationState.IDLE

    def test_start_simulation_transition(self):
        """Test start simulation transition."""
        # Should be able to start from idle
        assert self.app.may_start_simulation()

        # Mock the callbacks
        with patch.object(self.app, 'validate_scenario', return_value=True), \
             patch.object(self.app, 'has_valid_config', return_value=True), \
             patch.object(self.app, 'prepare_resources'), \
             patch.object(self.app, 'notify_simulation_started'):

            self.app.start_simulation()
            assert self.app.state == SimulationState.RUNNING

    def test_pause_simulation_transition(self):
        """Test pause simulation transition."""
        # First start simulation
        with patch.object(self.app, 'validate_scenario', return_value=True), \
             patch.object(self.app, 'has_valid_config', return_value=True):
            self.app.start_simulation()
            assert self.app.state == SimulationState.RUNNING

        # Should be able to pause
        assert self.app.may_pause_simulation()

        with patch.object(self.app, 'cancel_pending_work'):
            self.app.pause_simulation()
            assert self.app.state == SimulationState.PAUSED

    def test_resume_simulation_transition(self):
        """Test resume simulation transition."""
        # Start and pause first
        with patch.object(self.app, 'validate_scenario', return_value=True), \
             patch.object(self.app, 'has_valid_config', return_value=True), \
             patch.object(self.app, 'cancel_pending_work'):
            self.app.start_simulation()
            self.app.pause_simulation()
            assert self.app.state == SimulationState.PAUSED

        # Should be able to resume
        assert self.app.may_resume_simulation()

        with patch.object(self.app, 'context_matches', return_value=True), \
             patch.object(self.app, 'restart_workers'):
            self.app.resume_simulation()
            assert self.app.state == SimulationState.RUNNING

    def test_stop_simulation_transition(self):
        """Test stop simulation transition."""
        # Start simulation first
        with patch.object(self.app, 'validate_scenario', return_value=True), \
             patch.object(self.app, 'has_valid_config', return_value=True):
            self.app.start_simulation()
            assert self.app.state == SimulationState.RUNNING

        # Should be able to stop
        assert self.app.may_stop_simulation()

        with patch.object(self.app, 'initiate_shutdown'):
            self.app.stop_simulation()
            assert self.app.state == SimulationState.STOPPING

    def test_invalid_transitions_blocked(self):
        """Test that invalid transitions are blocked."""
        # Cannot pause from idle
        assert not self.app.may_pause_simulation()

        # Cannot resume from idle
        assert not self.app.may_resume_simulation()

        # Cannot stop from idle
        assert not self.app.may_stop_simulation()

    def test_error_handling(self):
        """Test error handling in state transitions."""
        # Mock a callback to raise an exception
        with patch.object(self.app, 'validate_scenario', side_effect=Exception("Test error")), \
             patch.object(self.app, 'has_valid_config', return_value=True):
            # The exception should be caught by on_exception handler
            self.app.start_simulation()

        # Should still be in idle state after error
        assert self.app.state == SimulationState.IDLE

        # Error should be recorded
        assert self.app.last_error == "Test error"