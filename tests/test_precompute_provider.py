"""Tests for PrecomputeProvider."""

import sys
import os

# Add python directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
from unittest.mock import Mock, patch
from hopilot.gto.precompute_provider import PrecomputeProvider


@pytest.fixture
def mock_solver():
    """Create a mock AoFSolverAdapter for fast tests."""
    solver = Mock()
    
    def mock_evaluate(hand_key, num_opponents, pot_size, bet_amount, timeout_ms):
        # Return realistic but fixed equity value based on hand strength
        if hand_key.startswith('A'):
            equity = 0.65
        elif hand_key.startswith('K'):
            equity = 0.55
        else:
            equity = 0.45
        
        return {
            "status": "AVAILABLE",
            "equity": equity,
            "ev": (equity - 0.5) * 20,
            "individual_outcomes": [
                {
                    "hero_hand": hand_key,
                    "villain_hand": "RANDOM",
                    "outcome": "WIN" if i < equity * 10 else "LOSS",
                    "hero_equity": equity,
                    "ev_chips": (equity - 0.5) * 20,
                }
                for i in range(10)
            ],
        }
    
    solver.evaluate_hand_key = Mock(side_effect=mock_evaluate)
    return solver


@pytest.fixture
def provider_with_mock(mock_solver):
    """Create a PrecomputeProvider with mocked solver for fast tests."""
    db_url = "sqlite:///:memory:"
    provider = PrecomputeProvider(database_url=db_url)
    provider._solver = mock_solver  # Replace with mock
    return provider


@pytest.fixture
def provider():
    """Create a real PrecomputeProvider instance (slower, for integration tests)."""
    db_url = "sqlite:///:memory:"
    return PrecomputeProvider(database_url=db_url)


def test_provider_initialization(provider_with_mock):
    """Test that PrecomputeProvider initializes without errors."""
    assert provider_with_mock._solver is not None
    assert provider_with_mock._matrix_keys is not None
    assert len(provider_with_mock._matrix_keys) == 13
    # Check matrix_keys structure
    for row in provider_with_mock._matrix_keys:
        assert len(row) == 13


def test_resolve_num_opponents(provider_with_mock):
    """Test _resolve_num_opponents helper."""
    # Single player all-in (hero only, so 0 opponents)
    num_opp = provider_with_mock._resolve_num_opponents("ALL_IN", {"BTN": "ALL_IN"})
    assert num_opp == 1, "max(1, count-1) should give at least 1"
    
    # Two players all-in (hero + 1 opponent)
    num_opp = provider_with_mock._resolve_num_opponents("ALL_IN", {"BTN": "ALL_IN", "BB": "ALL_IN"})
    assert num_opp == 1
    
    # Multiple players (hero + 2 opponents)
    num_opp = provider_with_mock._resolve_num_opponents("ALL_IN", {"UTG": "ALL_IN", "BTN": "ALL_IN", "BB": "ALL_IN"})
    assert num_opp == 2


def test_build_context(provider_with_mock):
    """Test _build_context helper."""
    context = provider_with_mock._build_context(
        position="BTN",
        metric="EQUITY",
        position_actions={"BTN": "ALL_IN", "BB": "ALL_IN"},
        pot_size=20.0,
        bet_amount=10.0,
    )
    
    assert context["position"] == "BTN"
    assert context["metric"] == "EQUITY"
    assert context["pot_size"] == 20.0
    assert context["bet_amount"] == 10.0
    assert "position_actions" in context


def test_get_matrix_payload_structure(provider_with_mock):
    """Test that get_matrix_payload returns correct structure (with mocked solver)."""
    payload = provider_with_mock.get_matrix_payload(
        position="BTN",
        metric="EQUITY",
        position_actions={"BTN": "ALL_IN", "BB": "ALL_IN"},
        pot_size=20.0,
        bet_amount=10.0,
    )
    
    # Check top-level structure
    assert "context" in payload
    assert "cells" in payload
    assert "status" in payload
    assert "status_message" in payload
    
    # Check payload status
    assert payload["status"] == "AVAILABLE", f"Expected AVAILABLE but got {payload['status']}: {payload['status_message']}"
    
    # Check context
    assert payload["context"]["position"] == "BTN"
    assert payload["context"]["metric"] == "EQUITY"
    
    # Check cells structure
    cells = payload["cells"]
    assert isinstance(cells, list), f"cells should be list, got {type(cells)}"
    assert len(cells) == 169, f"Should have 169 cells, got {len(cells)}"
    
    # Check first cell structure
    if cells:
        cell = cells[0]
        assert "row" in cell
        assert "col" in cell
        assert "hand_key" in cell
        assert "metrics" in cell
        assert "status" in cell
        
        # Check metrics
        metrics = cell["metrics"]
        assert "win_equity" in metrics
        assert "lose_equity" in metrics
        assert "tie_equity" in metrics
        assert "EV" in metrics
        assert "EQUITY" in metrics
        
        # Check that values are reasonable
        assert 0.0 <= metrics["win_equity"] <= 1.0
        assert 0.0 <= metrics["lose_equity"] <= 1.0
        assert 0.0 <= metrics["tie_equity"] <= 1.0


def test_get_matrix_payload_all_cells_present(provider_with_mock):
    """Test that all 169 cells are returned (with mocked solver)."""
    payload = provider_with_mock.get_matrix_payload(
        position="BTN",
        metric="EQUITY",
        position_actions={"BTN": "ALL_IN", "BB": "ALL_IN"},
    )
    
    cells = payload["cells"]
    assert len(cells) == 169
    
    # Verify we have cells for each position
    hand_keys = {cell["hand_key"] for cell in cells}
    assert len(hand_keys) == 169, f"Expected 169 unique hand keys, got {len(hand_keys)}"


# Integration test with real solver (slower)
@pytest.mark.slow
def test_baseline_equity_real_solver(provider):
    """Test _baseline_equity with real solver (expensive)."""
    # Test a few hands
    for hand_key in ["AA", "AKs", "22"]:
        equity = provider._baseline_equity(hand_key)
        assert 0.0 <= equity <= 1.0, f"Baseline equity out of range for {hand_key}: {equity}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
