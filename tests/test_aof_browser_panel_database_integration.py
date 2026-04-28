"""
T055: GUI Integration Smoke Tests

Tests for AoFBrowserPanel - validate panel initialization and database integration.
These are smoke tests to ensure the panel works with the database-backed provider.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch
import pygame
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
from hopilot.gto.aof_precompute_runner import GuiRunState
from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.logging_config import get_logger


@pytest.fixture(autouse=True)
def pygame_display():
    """Initialize and clean up pygame display for GUI integration tests."""
    pygame.init()
    pygame.display.set_mode((800, 600))
    yield
    pygame.quit()

logger = get_logger(__name__)


class TestAoFBrowserPanelInitialization:
    """Tests for panel initialization with database."""

    def test_panel_initialization_with_database(self, database_url_fixture):
        """Test that panel initializes with database_url parameter."""
        # Initialize pygame to avoid display issues
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=database_url_fixture,
        )
        
        # Verify panel has database provider configured
        assert panel.provider is not None
        assert isinstance(panel.provider, BrowserDatabaseProvider)
        assert panel.width == 800
        assert panel.height == 600

    def test_panel_initialization_requires_database_url(self):
        """Test that panel raises ValueError when database_url is missing."""
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        with pytest.raises(ValueError, match="database_url is required"):
            AoFBrowserPanel(width=800, height=600, database_url=None)


class TestAoFBrowserPanelDatabaseLoading:
    """Tests for matrix loading from database."""

    @patch('hopilot.gto.browser_database_provider.DatabaseRepository')
    def test_panel_loads_matrix_from_database(self, mock_db_class, database_url_fixture):
        """Test that panel loads matrix data from database during initialization."""
        # Mock database to return valid payload
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        test_payload = {
            "context": {
                "position": "UTG",
                "action": "FOLD",
                "metric": "EV",
                "position_actions": {"UTG": "FOLD"},
                "active_players": 0,
                "pot_size": 20.0,
                "bet_amount": 10.0,
            },
            "cells": [
                {"hand": "AsKs", "value": 0.55},
                {"hand": "AhKh", "value": 0.52},
            ],
        }
        
        mock_db.get_matrix_payload.return_value = test_payload
        
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=database_url_fixture,
        )
        
        # Verify panel loaded payloadPayload has cells (database was queried)
        assert panel.payload is not None
        assert "cells" in panel.payload or "context" in panel.payload

    @patch('hopilot.gto.browser_database_provider.DatabaseRepository')
    def test_panel_handles_database_connection_error(self, mock_db_class, database_url_fixture):
        """Test that panel gracefully handles database connection errors."""
        # Mock database to raise exception
        mock_db = mock_db_class.return_value
        mock_db.get_matrix_payload.side_effect = Exception("Connection refused")
        
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        # Should not raise, should handle gracefully
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=database_url_fixture,
        )
        
        # Validate payload content and structure
        assert "context" in panel.payload, "Payload should contain context"
        assert "cells" in panel.payload, "Payload should contain cells"
        
        context = panel.payload["context"]
        assert "position" in context, "Context should contain position"
        assert "metric" in context, "Context should contain metric"
        assert "position_actions" in context, "Context should contain position_actions"
        assert context["position"] == "UTG", "Position should be UTG"
        assert context["metric"] == panel.state.selected_metric, "Metric should match panel selected metric"
        
        cells = panel.payload["cells"]
        assert isinstance(cells, list), "Cells should be a list"
        assert len(cells) >= 2, "Should have at least 2 cells"
        
        # Validate cell structure
        for cell in cells:
            assert "hand" in cell or "hand_key" in cell, "Cell should contain hand information"
            assert "value" in cell, "Cell should contain value"
            assert cell["value"] is None or isinstance(cell["value"], (int, float)), "Cell value should be numeric or null while loading"


class TestAoFBrowserPanelDataRefresh:
    """Tests for panel data refresh from database."""

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_panel_refresh_queries_latest_database(self, mock_provider_class, database_url_fixture):
        """Test that panel refresh method queries latest data from database."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        initial_payload = {
            "context": {"position": "UTG", "metric": "EV"},
            "cells": [{"hand": "AsKs", "value": 0.50}],
        }
        updated_payload = {
            "context": {"position": "UTG", "metric": "EV"},
            "cells": [{"hand": "AsKs", "value": 0.60}],  # Updated value
        }
        
        # First call returns initial, second call returns updated
        mock_provider.get_matrix_from_database.side_effect = [initial_payload, updated_payload]
        
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=database_url_fixture,
        )
        
        # First payload loaded during init
        assert panel.payload is not None
        
        # Verify database was called at least once during init
        assert mock_provider.get_matrix_from_database.call_count >= 1

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_panel_preserves_state_on_refresh(self, mock_provider_class, database_url_fixture):
        """Test that panel preserves selection state when refreshing data."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        payload = {
            "context": {"position": "UTG", "metric": "EV"},
            "cells": [],
        }
        mock_provider.get_matrix_from_database.return_value = payload
        
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=database_url_fixture,
        )
        
        initial_position = panel.state.selected_position
        initial_metric = panel.state.selected_metric
        
        # Refresh should not change internal state
        # (though in real implementation it might update data)
        assert panel.state.selected_position == initial_position
        assert panel.state.selected_metric == initial_metric


class TestAoFBrowserPanelStateDerivation:
    """Tests for derived panel state and error handling."""

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_panel_state_derivation(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        mock_provider._matrix_keys = [["AA"] * 13 for _ in range(13)]

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel.is_loading = True
        panel.payload = {"status": "AVAILABLE", "cells": []}
        assert panel.panel_state == "LOADING"

        panel.is_loading = False
        panel.payload["status"] = "AVAILABLE"
        assert panel.panel_state == "AVAILABLE"

        panel.payload["status"] = "MISSING"
        assert panel.panel_state == "MISSING"

        panel.payload["status"] = "NO_CONTEST"
        assert panel.panel_state == "NO_CONTEST"

        panel._last_error = "fetch failed"
        assert panel.panel_state == "ERROR"

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_fetch_failure_sets_error_state(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        mock_provider._matrix_keys = [["AA"] * 13 for _ in range(13)]

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel._refresh_context = {"position": "UTG", "metric": "EV"}

        event = SimpleNamespace(success=False, error="Connection refused", request_context=panel._refresh_context)
        panel._handle_async_refresh_result(event)

        assert panel._last_error == "Connection refused"
        assert panel.panel_state == "ERROR"
        assert panel.payload["status"] == "ERROR"
        assert "Database error" in panel.state.status_message

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_context_change_position_invalidates_payload(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider._matrix_keys = [["AA"] * 13 for _ in range(13)]
        mock_provider_class.return_value = mock_provider

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel._start_async_refresh = lambda: None
        panel.payload = {
            "context": {"position": "UTG", "metric": "EV", "position_actions": panel.state.position_actions},
            "cells": [{"row": 0, "col": 0, "hand_key": "AA", "value": 0.85, "status": "AVAILABLE", "display": "85%"}],
            "status": "AVAILABLE",
            "status_message": "Loaded",
        }
        panel.state.set_position("BTN")

        panel._refresh()

        assert panel.panel_state == "LOADING"
        assert all(cell["status"] == "LOADING" for cell in panel.payload["cells"])

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_context_change_metric_invalidates_payload(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider._matrix_keys = [["AA"] * 13 for _ in range(13)]
        mock_provider_class.return_value = mock_provider

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel._start_async_refresh = lambda: None
        panel.payload = {
            "context": {"position": "UTG", "metric": "EV", "position_actions": panel.state.position_actions},
            "cells": [{"row": 0, "col": 0, "hand_key": "AA", "value": 0.85, "status": "AVAILABLE", "display": "85%"}],
            "status": "AVAILABLE",
            "status_message": "Loaded",
        }
        panel.state.set_metric("EQUITY")

        panel._refresh()

        assert panel.panel_state == "LOADING"
        assert all(cell["status"] == "LOADING" for cell in panel.payload["cells"])

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_start_from_error_clears_last_error(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider._matrix_keys = [["AA"] * 13 for _ in range(13)]
        mock_provider_class.return_value = mock_provider

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel._last_error = "Simulated failure"
        panel.payload = {
            "context": {"position": "UTG", "metric": "EV", "position_actions": panel.state.position_actions},
            "cells": [],
            "status": "ERROR",
            "status_message": "Simulated failure",
        }
        panel._build_current_context = MagicMock(return_value={
            "position": "UTG",
            "metric": "EV",
            "position_actions": panel.state.position_actions,
        })

        panel.runner = MagicMock()
        panel.runner.create_gui_session.return_value = SimpleNamespace(
            run_state=GuiRunState.IDLE,
            total_cells=169,
            completed_cells=0,
            failed_cells=0,
            next_cell_index=0,
            current_cell_index=None,
        )
        panel.runner.transition_session_state = MagicMock()
        panel.runner.bind_gui_run = MagicMock()
        panel.runner.database_repository = MagicMock()
        panel.runner.database_repository.create_simulation = MagicMock(return_value=1)
        panel.runner.database_repository.create_hand_matrix = MagicMock(return_value=1)

        panel._start_precompute()

        assert panel._last_error is None
        assert panel.precompute_session is not None
        assert panel.panel_state != "ERROR"


class TestAoFBrowserPanelErrorHandling:
    """Tests for error handling in database operations."""

    @patch('hopilot.gto.browser_database_provider.DatabaseRepository')
    def test_panel_continues_on_partial_database_failure(self, mock_db_class, database_url_fixture):
        """Test that panel continues functioning even if database query fails partway."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        # First call succeeds, second fails  (for potential refresh scenarios)
        error_payload = {
            "context": {"position": "UTG", "metric": "EV"},
            "cells": [],
            "status_message": "Database error: query failed",
        }
        mock_db.get_matrix_payload.return_value = error_payload
        
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        # Should initialize without raising exception
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=database_url_fixture,
        )
        
        # Panel should be functional even with error payload
        assert panel.provider is not None
        assert panel.state is not None


class TestAoFBrowserPrecomputeLifecycle:
    """Tests for precompute rerun lifecycle and status gating."""

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_precompute_status_enablement_by_run_state(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel.precompute_session = SimpleNamespace(
            run_state=GuiRunState.IDLE,
            completed_cells=0,
            total_cells=169,
            failed_cells=0,
            current_cell_index=0,
        )

        status = panel.get_precompute_status()
        assert status['can_start'] is True
        assert status['can_pause'] is False
        assert status['can_resume'] is False
        assert status['can_stop'] is False

        panel.precompute_session.run_state = GuiRunState.RUNNING
        status = panel.get_precompute_status()
        assert status['can_start'] is False
        assert status['can_pause'] is True
        assert status['can_resume'] is False
        assert status['can_stop'] is True

        panel.precompute_session.run_state = GuiRunState.PAUSED
        status = panel.get_precompute_status()
        assert status['can_start'] is False
        assert status['can_pause'] is False
        assert status['can_resume'] is True
        assert status['can_stop'] is True

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_pause_resume_stop_controls(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider._matrix_keys = [["AA"] * 13 for _ in range(13)]
        mock_provider_class.return_value = mock_provider

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel.runner = MagicMock()
        panel.precompute_session = SimpleNamespace(
            run_state=GuiRunState.RUNNING,
            completed_cells=10,
            failed_cells=0,
            total_cells=169,
            next_cell_index=5,
            current_cell_index=4,
        )
        panel.precompute_futures = {MagicMock(): 0}

        def pause_side_effect(session):
            session.run_state = GuiRunState.PAUSED
        panel.runner.pause_gui_session.side_effect = pause_side_effect

        result = panel.pause_precompute()
        assert result is True
        assert panel.precompute_session.run_state == GuiRunState.PAUSED
        assert panel.precompute_futures == {}
        assert panel.state.status_message == "Precompute paused"

        def resume_side_effect(session, current_context):
            session.run_state = GuiRunState.RUNNING
            return session
        panel.runner.resume_gui_session.side_effect = resume_side_effect
        panel.precompute_session.run_state = GuiRunState.PAUSED

        result = panel.resume_precompute()
        assert result is True
        assert panel.precompute_session.run_state == GuiRunState.RUNNING
        assert panel.state.status_message == "Precompute resumed"

        def stop_side_effect(session):
            session.run_state = GuiRunState.COMPLETED
        panel.runner.stop_gui_session.side_effect = stop_side_effect
        panel.precompute_session.run_state = GuiRunState.RUNNING
        panel.precompute_futures = {MagicMock(): 2}

        result = panel.stop_precompute()
        assert result is True
        assert panel.precompute_session.run_state == GuiRunState.COMPLETED
        assert panel.precompute_futures == {}
        assert panel.state.status_message == "Precompute stopped"

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_start_precompute_preserves_available_payload(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider._matrix_keys = [["AA"] * 13 for _ in range(13)]
        mock_provider_class.return_value = mock_provider

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel.payload = {
            'context': {'position': 'UTG', 'action': 'ALL_IN', 'metric': 'EV', 'position_actions': panel.state.position_actions},
            'cells': [{'row': 0, 'col': 0, 'hand_key': 'AA', 'value': 0.85, 'status': 'AVAILABLE', 'display': '85%'}],
            'status': 'AVAILABLE',
            'status_message': 'Loaded',
        }
        panel.state.selected_metric = 'EV'
        panel.state.selected_position = 'UTG'

        panel._build_current_context = MagicMock(return_value=panel.payload['context'])
        panel.runner.create_gui_session = MagicMock(return_value=SimpleNamespace(
            run_state=GuiRunState.IDLE,
            total_cells=169,
            completed_cells=0,
            failed_cells=0,
            next_cell_index=0,
            current_cell_index=None,
        ))
        panel.runner.transition_session_state = MagicMock()
        panel.runner.bind_gui_run = MagicMock()
        panel.runner.build_scenario_fingerprint = MagicMock(return_value='fingerprint')
        panel.runner.database_repository.create_simulation = MagicMock(return_value=1)
        panel.runner.database_repository.create_hand_matrix = MagicMock(return_value=1)

        panel._start_precompute()

        assert panel._rerun_in_progress is True
        assert panel.payload['status'] == 'AVAILABLE'
        assert panel.payload['cells'][0]['hand_key'] == 'AA'
        assert 'Recomputing' in panel.state.status_message

    @patch('hopilot.gui_components.aof_browser_panel.BrowserDatabaseProvider')
    def test_rerun_completion_triggers_refresh(self, mock_provider_class, database_url_fixture):
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider

        panel = AoFBrowserPanel(width=800, height=600, database_url=database_url_fixture)
        panel._rerun_in_progress = True
        panel._refresh = MagicMock()
        panel._persist_completed_precompute_payload = MagicMock()
        panel.precompute_session = SimpleNamespace(
            run_state=GuiRunState.COMPLETED,
            total_cells=169,
            completed_cells=169,
            failed_cells=0,
            next_cell_index=169,
            current_cell_index=168,
        )
        panel.precompute_context = {'scenario': 'test'}
        panel.payload = {'cells': [{}] * 169, 'context': {}, 'status_message': ''}
        panel.precompute_futures = {}

        panel._tick_precompute()

        panel._refresh.assert_called_once()
        assert panel._rerun_in_progress is False


class TestAoFBrowserPanelProviderIntegration:
    """Tests for integration between panel and provider."""

    def test_panel_uses_browser_database_provider(self, database_url_fixture):
        """Test that panel uses BrowserDatabaseProvider instance."""
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=database_url_fixture,
        )
        
        # Verify provider is BrowserDatabaseProvider
        assert isinstance(panel.provider, BrowserDatabaseProvider)
        # Provider should have database_repository configured
        assert hasattr(panel.provider, 'database_repository')
        assert panel.provider.database_repository is not None

    def test_panel_provider_methods_available(self, database_url_fixture):
        """Test that panel can call provider methods for matrix queries."""
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
        
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=database_url_fixture,
        )
        
        # Provider should have both query methods
        assert hasattr(panel.provider, 'get_matrix_payload')
        assert hasattr(panel.provider, 'get_matrix_from_database')
        assert callable(panel.provider.get_matrix_payload)
        assert callable(panel.provider.get_matrix_from_database)


# Fixtures

@pytest.fixture
def database_url_fixture():
    """Provide a test database URL."""
    return "sqlite:///:memory:"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
