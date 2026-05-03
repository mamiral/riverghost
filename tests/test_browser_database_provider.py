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

    @patch('hopilot.gto.browser_database_provider.SimulationRepository')
    def test_get_matrix_payload_valid_context_queries_database(self, mock_db_class):
        """Test that valid context triggers aggregated run lookup."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.get_cross_run_matrix_summary.return_value = {
            "simulation": MagicMock(id=1),
            "hand_matrix": MagicMock(id=2),
            "matrix_cells": [
                MagicMock(row_index=row, col_index=col, hand_combination="AA", aggregated_metric=MagicMock(equity=0.55, win_probability=None, ev=None, jackpot_adjusted_ev=None))
                for row in range(13) for col in range(13)
            ],
            "aggregated_metrics": []
        }

        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EQUITY",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        assert mock_db.get_cross_run_matrix_summary.called
        assert payload["status"] == STATUS_AVAILABLE
        assert len(payload["cells"]) == 169
        assert payload["cells"][0]["status"] == STATUS_AVAILABLE

    @patch('hopilot.gto.browser_database_provider.SimulationRepository')
    def test_get_matrix_payload_builds_canonical_scenario_contract(self, mock_db_class):
        """Test that the provider builds the correct scenario contract for repository lookup."""
        from hopilot.gto.aof_hand_matrix import build_matrix_keys

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_cross_run_matrix_summary.return_value = {
            "simulation": MagicMock(id=1),
            "hand_matrix": MagicMock(id=2),
            "matrix_cells": [
                MagicMock(
                    row_index=row,
                    col_index=col,
                    hand_combination=build_matrix_keys()[row][col],
                    aggregated_metric=MagicMock(equity=0.55, win_probability=0.55, ev=0.75, jackpot_adjusted_ev=1.0)
                )
                for row in range(13) for col in range(13)
            ],
            "aggregated_metrics": []
        }

        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        assert payload["status"] == STATUS_AVAILABLE
        assert len(payload["cells"]) == 169

        called_contract = mock_db.get_cross_run_matrix_summary.call_args[0][0]
        assert called_contract["selected_position"] == "UTG"
        assert called_contract["hero_action"] == "FOLD"
        assert called_contract["position_actions"]["BTN"] == "ALL_IN"
        assert called_contract["active_players"] == ["BTN"]
        assert called_contract["num_opponents"] == 1
        assert called_contract["run_kind"] == "matrix_sweep"

    @patch('hopilot.gto.browser_database_provider.SimulationRepository')
    def test_get_matrix_payload_propagates_simulations_per_cell(self, mock_db_class):
        """Test that browser provider uses simulations_per_cell in scenario contracts."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_cross_run_matrix_summary.return_value = {
            "simulation": MagicMock(id=1),
            "hand_matrix": MagicMock(id=2),
            "matrix_cells": [
                MagicMock(row_index=row, col_index=col, hand_combination="AA", aggregated_metric=MagicMock(equity=0.55, win_probability=None, ev=None, jackpot_adjusted_ev=None))
                for row in range(13) for col in range(13)
            ],
            "aggregated_metrics": []
        }

        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
            simulations_per_cell=1000,
        )

        assert payload["status"] == STATUS_AVAILABLE
        called_contract = mock_db.get_cross_run_matrix_summary.call_args[0][0]
        assert called_contract["sims_per_combo"] == 1000
        assert called_contract["num_simulations"] == 1000

    @patch('hopilot.gto.browser_database_provider.SimulationRepository')
    def test_get_matrix_payload_database_failure_returns_missing(self, mock_db_class):
        """Test that repository failures return graceful MISSING payload."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_cross_run_matrix_summary.side_effect = Exception("Database connection failed")

        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN"},  # Avoid NO_CONTEST scenario
        )

        assert len(payload["cells"]) == 169
        assert all(cell["status"] == STATUS_MISSING for cell in payload["cells"])
        assert "Database error" in payload.get("status_message", "")

    @patch('hopilot.gto.browser_database_provider.SimulationRepository')
    def test_get_matrix_payload_preserves_context_on_error(self, mock_db_class):
        """Test that error payload includes context for debugging."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_cross_run_matrix_summary.side_effect = Exception("Query failed")

        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        payload = provider.get_matrix_payload(
            position="BTN",
            metric="EQUITY",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        assert "context" in payload
        assert payload["context"]["position"] == "BTN"
        assert payload["context"]["metric"] == "EQUITY"


class TestBrowserDatabaseProviderStatusPayloads:
    """Tests for status payload generation."""

    def test_build_status_payload_structure(self):
        """Test that status payloads have correct structure."""
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        
        # Test invalid position returns correct structure
        payload = provider.get_matrix_payload(
            position="INVALID_POS",
            metric="EV",
        )
        
        assert "context" in payload
        assert "cells" in payload
        assert "status" in payload
        assert "status_message" in payload
        assert payload["cells"] == []
        assert payload["status"] == "MISSING"
        assert "Invalid context" in payload["status_message"]

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

    @patch('hopilot.gto.browser_database_provider.SimulationRepository')
    def test_get_matrix_payload_invokes_callback_for_each_cell(self, mock_db_class):
        """Test that get_matrix_payload invokes the cell completion callback."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_cross_run_matrix_summary.return_value = {
            "simulation": MagicMock(id=1),
            "hand_matrix": MagicMock(id=2),
            "matrix_cells": [
                MagicMock(row_index=row, col_index=col, hand_combination="AA", aggregated_metric=MagicMock(equity=0.55, win_probability=None, ev=None, jackpot_adjusted_ev=None))
                for row in range(13) for col in range(13)
            ],
            "aggregated_metrics": []
        }

        callback = MagicMock()
        provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
        provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN"},  # Avoid NO_CONTEST
            on_cell_complete=callback,
        )

        assert mock_db.get_cross_run_matrix_summary.called
        assert callback.call_count == 169


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
