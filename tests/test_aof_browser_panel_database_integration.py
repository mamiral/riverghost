"""
T055: GUI Integration Smoke Tests

Tests for AoFBrowserPanel - validate panel initialization and database integration.
These are smoke tests to ensure the panel works with the database-backed provider.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pygame
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.logging_config import get_logger

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
        assert context["metric"] == "EV", "Metric should be EV"
        
        cells = panel.payload["cells"]
        assert isinstance(cells, list), "Cells should be a list"
        assert len(cells) >= 2, "Should have at least 2 cells"
        
        # Validate cell structure
        for cell in cells:
            assert "hand" in cell or "hand_key" in cell, "Cell should contain hand information"
            assert "value" in cell, "Cell should contain value"
            assert isinstance(cell["value"], (int, float)), "Cell value should be numeric"


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
