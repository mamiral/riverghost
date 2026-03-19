"""Tests to verify precompute results are persisted on pause and stop."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
from hopilot.gto.aof_precompute_runner import GuiRunState


def test_pause_precompute_calls_persist_payload():
    """Verify that pause_precompute() calls _persist_completed_precompute_payload()."""
    # Create a mock panel with just the methods we need
    panel = MagicMock(spec=AoFBrowserPanel)
    panel.precompute_session = MagicMock()
    panel.precompute_session.run_state = GuiRunState.RUNNING
    panel.runner = MagicMock()
    panel._cancel_pending_precompute_futures = MagicMock()
    panel._persist_completed_precompute_payload = MagicMock()
    panel.state = MagicMock()
    panel.logger = MagicMock()
    
    # Bind the actual method to the mock  
    panel.pause_precompute = AoFBrowserPanel.pause_precompute.__get__(panel)
    
    # Call pause_precompute
    result = panel.pause_precompute()
    
    # Verify it succeeded and persistence was called
    assert result is True
    panel.runner.pause_gui_session.assert_called_once()
    panel._cancel_pending_precompute_futures.assert_called_once()
    panel._persist_completed_precompute_payload.assert_called_once()


def test_stop_precompute_calls_persist_payload():
    """Verify that stop_precompute() calls _persist_completed_precompute_payload()."""
    panel = MagicMock(spec=AoFBrowserPanel)
    panel.precompute_session = MagicMock()
    panel.precompute_session.run_state = GuiRunState.RUNNING
    panel.runner = MagicMock()
    panel._cancel_pending_precompute_futures = MagicMock()
    panel._persist_completed_precompute_payload = MagicMock()
    panel.state = MagicMock()
    panel.logger = MagicMock()
    
    panel.stop_precompute = AoFBrowserPanel.stop_precompute.__get__(panel)
    
    result = panel.stop_precompute()
    
    assert result is True
    panel.runner.stop_gui_session.assert_called_once()
    panel._cancel_pending_precompute_futures.assert_called_once()
    panel._persist_completed_precompute_payload.assert_called_once()


def test_pause_from_paused_state_does_nothing():
    """Verify that pause_precompute() does nothing if already paused."""
    panel = MagicMock(spec=AoFBrowserPanel)
    panel.precompute_session = MagicMock()
    panel.precompute_session.run_state = GuiRunState.PAUSED  # Already paused
    panel._persist_completed_precompute_payload = MagicMock()
    
    panel.pause_precompute = AoFBrowserPanel.pause_precompute.__get__(panel)
    
    result = panel.pause_precompute()
    
    assert result is False
    panel._persist_completed_precompute_payload.assert_not_called()


def test_stop_from_paused_state_persists():
    """Verify that stop_precompute() from PAUSED state also persists results."""
    panel = MagicMock(spec=AoFBrowserPanel)
    panel.precompute_session = MagicMock()
    panel.precompute_session.run_state = GuiRunState.PAUSED
    panel.runner = MagicMock()
    panel._cancel_pending_precompute_futures = MagicMock()
    panel._persist_completed_precompute_payload = MagicMock()
    panel.state = MagicMock()
    panel.logger = MagicMock()
    
    panel.stop_precompute = AoFBrowserPanel.stop_precompute.__get__(panel)
    
    result = panel.stop_precompute()
    
    assert result is True
    panel._persist_completed_precompute_payload.assert_called_once()
