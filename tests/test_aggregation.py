"""
Unit tests for aggregation engine.

Tests the logic for computing MatrixCells and AggregatedMetrics
from GameStates data.
"""

import pytest
from unittest.mock import Mock
from hopilot.gto.aggregation_engine import AggregationEngine


class TestAggregationEngine:
    """Test aggregation engine helper behavior."""

    @pytest.fixture
    def aggregation_engine(self):
        return AggregationEngine("sqlite:///:memory:")

    def test_game_state_matches_cell_pair(self, aggregation_engine):
        game_state = Mock()
        game_state.players = [Mock(is_hero=True, hole_cards="AsAh")]

        assert aggregation_engine._game_state_matches_cell(game_state, 0, 0)
        assert not aggregation_engine._game_state_matches_cell(game_state, 1, 1)

    def test_game_state_matches_cell_suited(self, aggregation_engine):
        game_state = Mock()
        game_state.players = [Mock(is_hero=True, hole_cards="AsKs")]

        assert aggregation_engine._game_state_matches_cell(game_state, 0, 1)
        assert not aggregation_engine._game_state_matches_cell(game_state, 1, 0)

    def test_game_state_matches_cell_offsuit(self, aggregation_engine):
        game_state = Mock()
        game_state.players = [Mock(is_hero=True, hole_cards="KsAh")]

        assert aggregation_engine._game_state_matches_cell(game_state, 1, 0)
        assert not aggregation_engine._game_state_matches_cell(game_state, 0, 1)

    def test_calculate_aggregate_metrics_hero_wins(self, aggregation_engine):
        """Test metrics calculation when hero wins all games."""
        mock_game_state = Mock()
        mock_game_state.outcome = 'win'
        mock_game_state.pot_size = 1.0

        metrics = aggregation_engine._calculate_aggregate_metrics([mock_game_state])

        assert metrics == (1.0, 1.0)

    def test_calculate_aggregate_metrics_hero_losses(self, aggregation_engine):
        """Test metrics calculation when hero loses all games."""
        mock_game_state = Mock()
        mock_game_state.outcome = 'loss'
        mock_game_state.pot_size = 1.0

        metrics = aggregation_engine._calculate_aggregate_metrics([mock_game_state])

        assert metrics == (0.0, -1.0)


