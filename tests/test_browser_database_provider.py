"""
T054: Browser Provider Unit Tests

Tests for BrowserDatabaseProvider - the minimal database-only interface for GUI matrix queries.
Validate context building, error handling, and database read integration.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import (
    BrowserDatabaseProvider,
    STATUS_AVAILABLE,
    STATUS_MISSING,
)
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class TestBrowserDatabaseProviderContextBuilding:
    """Tests for context building logic."""

    def test_build_context_normalizes_position_actions(self):
        """Test that context builder normalizes position actions properly."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        position_actions = {
            "UTG": "FOLD",
            "BTN": "ALL_IN",
            "SB": "FOLD",
        }
        
        context = provider._build_context(
            position="UTG",
            metric="EV",
            position_actions=position_actions,
        )
        
        # Verify context structure
        assert context["position"] == "UTG"
        assert context["action"] == "FOLD"
        assert context["metric"] == "EV"
        assert context["position_actions"]["UTG"] == "FOLD"
        assert context["position_actions"]["BTN"] == "ALL_IN"
        assert context["active_players"] == 1  # Only BTN is ALL_IN
        assert context["pot_size"] == 20.0  # Default
        assert context["bet_amount"] == 10.0  # Default
        assert context["effective_mode"] == "analysis"

    def test_build_context_with_strict_mode(self):
        """Test context builder sets effective_mode correctly for strict mode."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        context = provider._build_context(
            position="UTG",
            metric="EV",
            strict_current_action=True,
        )
        
        assert context["effective_mode"] == "strict-current-action"

    def test_build_context_active_players_count(self):
        """Test that active_players correctly counts only ALL_IN actions."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        position_actions = {
            "UTG": "FOLD",
            "BTN": "ALL_IN",
            "SB": "ALL_IN",
            "BB": "FOLD",
        }
        
        context = provider._build_context(
            position="UTG",
            metric="EV",
            position_actions=position_actions,
        )
        
        assert context["active_players"] == 2  # BTN and SB are ALL_IN


class TestBrowserDatabaseProviderValidation:
    """Tests for input validation and error handling."""

    def test_get_matrix_payload_invalid_position_raises_and_returns_missing(self):
        """Test that invalid position triggers validation error and returns MISSING payload."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        payload = provider.get_matrix_payload(
            position="INVALID_POS",
            metric="EV",
        )
        
        # Should return status payload, not raise
        assert payload["cells"] == []
        assert "Invalid position" in payload.get("status_message", "")
        assert "Invalid context" in payload.get("status_message", "")

    def test_get_matrix_payload_invalid_metric_raises_and_returns_missing(self):
        """Test that invalid metric triggers validation error and returns MISSING payload."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="INVALID_METRIC",
        )
        
        # Should return status payload, not raise
        assert payload["cells"] == []
        assert "Invalid metric" in payload.get("status_message", "")

    def test_build_context_invalid_position_raises(self):
        """Test that _build_context raises ValueError for invalid position."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        with pytest.raises(ValueError, match="Invalid position"):
            provider._build_context(position="INVALID_POS", metric="EV")

    def test_build_context_invalid_metric_raises(self):
        """Test that _build_context raises ValueError for invalid metric."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        with pytest.raises(ValueError, match="Invalid metric"):
            provider._build_context(position="UTG", metric="INVALID_METRIC")


class TestBrowserDatabaseProviderDatabaseIntegration:
    """Tests for database query integration."""

    @patch('hopilot.gto.browser_database_provider.DatabaseRepository')
    def test_get_matrix_payload_valid_context_queries_database(self, mock_db_class):
        """Test that valid context triggers database query."""
        # Mock database repository
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        expected_payload = {
            "context": {
                "position": "UTG",
                "action": "FOLD",
                "metric": "EV",
                "position_actions": {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
                "active_players": 1,
                "pot_size": 20.0,
                "bet_amount": 10.0,
            },
            "cells": [
                {"hand": "AsKs", "value": 0.55},
                {"hand": "AhKh", "value": 0.52},
            ],
            "status_message": None,
        }
        mock_db.get_matrix_payload.return_value = expected_payload
        
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )
        
        # Verify database was called
        assert mock_db.get_matrix_payload.called
        assert len(payload["cells"]) == 2
        assert payload["cells"][0]["hand"] == "AsKs"

    @patch('hopilot.gto.browser_database_provider.DatabaseRepository')
    def test_get_matrix_payload_database_failure_returns_missing(self, mock_db_class):
        """Test that database errors are caught and return graceful MISSING payload."""
        # Mock database repository to raise exception
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_matrix_payload.side_effect = Exception("Database connection failed")
        
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
        )
        
        # Should return status payload with error message
        assert payload["cells"] == []
        assert "Database error" in payload.get("status_message", "")

    @patch('hopilot.gto.browser_database_provider.DatabaseRepository')
    def test_get_matrix_payload_preserves_context_on_error(self, mock_db_class):
        """Test that error payload includes context for debugging."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_matrix_payload.side_effect = Exception("Query failed")
        
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        payload = provider.get_matrix_payload(
            position="BTN",
            metric="EQUITY",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )
        
        # Verify context is preserved in error payload
        assert "context" in payload
        assert payload["context"]["position"] == "BTN"
        assert payload["context"]["metric"] == "EQUITY"


class TestBrowserDatabaseProviderStatusPayloads:
    """Tests for status payload generation."""

    def test_build_status_payload_structure(self):
        """Test that _build_status_payload creates correct structure."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        context = {
            "position": "UTG",
            "action": "CALL",
            "metric": "EV",
            "position_actions": {},
            "active_players": 0,
            "pot_size": 20.0,
            "bet_amount": 10.0,
        }
        
        payload = provider._build_status_payload(
            context=context,
            status="MISSING",
            message="No data available",
        )
        
        assert payload["context"] == context
        assert payload["cells"] == []
        assert payload["status_message"] == "No data available"

    def test_get_matrix_payload_invalid_context_preserves_parameters(self):
        """Test that error payload includes all input parameters for debugging."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        position_actions = {"UTG": "FOLD", "BTN": "ALL_IN"}
        payload = provider.get_matrix_payload(
            position="INVALID",
            metric="EV",
            position_actions=position_actions,
            pot_size=50.0,
            bet_amount=25.0,
        )
        
        # Verify context includes normalized parameters
        assert payload["context"]["position"] == "INVALID"
        assert payload["context"]["pot_size"] == 50.0
        assert payload["context"]["bet_amount"] == 25.0
        assert payload["cells"] == []


class TestBrowserDatabaseProviderCallbacks:
    """Tests for callback handling in database queries."""

    @patch('hopilot.gto.browser_database_provider.DatabaseRepository')
    def test_get_matrix_payload_passes_callback_to_database(self, mock_db_class):
        """Test that cell completion callback is passed through to database query."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        callback = MagicMock()
        expected_payload = {
            "context": {},
            "cells": [],
            "status_message": None,
        }
        mock_db.get_matrix_payload.return_value = expected_payload
        
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            on_cell_complete=callback,
        )
        
        # Verify callback was passed to database
        assert mock_db.get_matrix_payload.called
        call_kwargs = mock_db.get_matrix_payload.call_args[1]
        assert call_kwargs.get("on_cell_complete") == callback


class TestBrowserDatabaseProviderInitialization:
    """Tests for provider initialization."""

    def test_provider_initialization_with_database_url(self):
        """Test that provider initializes with database_url parameter."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        assert hasattr(provider, 'database_repository')
        assert provider.database_repository is not None
        assert hasattr(provider, 'logger')
        assert hasattr(provider, '_matrix_keys')

    def test_provider_stores_matrix_keys(self):
        """Test that provider caches matrix keys for performance."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        assert provider._matrix_keys is not None
        assert isinstance(provider._matrix_keys, (list, dict))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
