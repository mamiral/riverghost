"""
Unit tests for aggregation engine.

Tests the logic for computing MatrixCells and AggregatedMetrics
from GameStates data.
"""

import pytest
from unittest.mock import Mock, MagicMock
from decimal import Decimal
from hopilot.database.aggregation import AggregationEngine
from hopilot.models import GameState, Player, AggregatedMetric


class TestAggregationEngine:
    """Test aggregation engine functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def aggregation_engine(self, mock_session):
        """Create aggregation engine with mock session."""
        return AggregationEngine(mock_session)

    def test_aggregate_matrix_cell_no_game_states(self, aggregation_engine, mock_session):
        """Test aggregation when no game states exist."""
        # Mock empty query result
        mock_session.query.return_value.filter.return_value.all.return_value = []

        result = aggregation_engine.aggregate_matrix_cell(1)

        assert result is None
        mock_session.query.assert_called_once()

    def test_aggregate_matrix_cell_with_game_states(self, aggregation_engine, mock_session):
        """Test aggregation with game states."""
        # Create mock game states
        mock_game_state = Mock()
        mock_game_state.cell_id = 1
        mock_game_state.outcome = 'hero_win'
        mock_game_state.players = [Mock(is_hero=True)]
        mock_game_state.jackpots = []

        mock_session.query.return_value.filter.return_value.all.return_value = [mock_game_state]
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock the add and commit operations
        mock_session.add = Mock()
        mock_session.commit = Mock()

        result = aggregation_engine.aggregate_matrix_cell(1)

        assert result is not None
        assert isinstance(result, AggregatedMetric)
        assert result.cell_id == 1
        assert result.equity == Decimal('1.0000')  # Hero won 1 out of 1 games
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_compute_aggregated_metrics_hero_wins(self, aggregation_engine):
        """Test metrics computation when hero wins all games."""
        # Create mock game states
        mock_game_state = Mock()
        mock_game_state.outcome = 'hero_win'
        mock_game_state.players = [Mock(is_hero=True)]
        mock_game_state.jackpots = []

        game_states = [mock_game_state]

        metrics = aggregation_engine._compute_aggregated_metrics(game_states)

        assert metrics['equity'] == Decimal('1.0000')
        assert metrics['win_probability'] == Decimal('1.0000')
        assert metrics['ev'] == Decimal('1.0000')
        assert metrics['jackpot_frequency'] == Decimal('0.0000')
        assert metrics['convergence_status'] == 'insufficient_data'

    def test_compute_aggregated_metrics_hero_losses(self, aggregation_engine):
        """Test metrics computation when hero loses all games."""
        # Create mock game states
        mock_game_state = Mock()
        mock_game_state.outcome = 'hero_loss'
        mock_game_state.players = [Mock(is_hero=True)]
        mock_game_state.jackpots = []

        game_states = [mock_game_state]

        metrics = aggregation_engine._compute_aggregated_metrics(game_states)

        assert metrics['equity'] == Decimal('0.0000')
        assert metrics['win_probability'] == Decimal('0.0000')
        assert metrics['ev'] == Decimal('-1.0000')

    def test_compute_aggregated_metrics_with_jackpots(self, aggregation_engine):
        """Test metrics computation with jackpot events."""
        # Create mock game states with jackpots
        mock_game_state = Mock()
        mock_game_state.outcome = 'hero_win'
        mock_game_state.players = [Mock(is_hero=True)]

        mock_jackpot = Mock()
        mock_jackpot.payout_amount = 100.0
        mock_jackpot.jackpot_type = 'straight_flush'
        mock_game_state.jackpots = [mock_jackpot]

        game_states = [mock_game_state]

        metrics = aggregation_engine._compute_aggregated_metrics(game_states)

        assert metrics['jackpot_frequency'] == Decimal('1.0000')
        assert metrics['avg_jackpot_payout'] == Decimal('100.00')
        assert metrics['jackpot_adjusted_ev'] == Decimal('101.0000')  # 1.0 + (1.0 * 100.0)

    def test_assess_convergence_insufficient_data(self, aggregation_engine):
        """Test convergence assessment with insufficient data."""
        samples = [0.5, 0.6, 0.4]  # Less than 10 samples
        status = aggregation_engine._assess_convergence(samples)
        assert status == 'insufficient_data'

    def test_assess_convergence_converged(self, aggregation_engine):
        """Test convergence assessment when data is converged."""
        # Create 10 samples with very low variance
        samples = [0.5] * 10
        status = aggregation_engine._assess_convergence(samples)
        assert status == 'converged'

    def test_assess_convergence_diverging(self, aggregation_engine):
        """Test convergence assessment when data is diverging."""
        # Create samples with high variance
        samples = [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6, 0.5, 0.5]
        status = aggregation_engine._assess_convergence(samples)
        assert status == 'diverging'

    def test_get_matrix_cell_stats_no_data(self, aggregation_engine, mock_session):
        """Test getting stats when no aggregated metrics exist."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = aggregation_engine.get_matrix_cell_stats(1)

        assert result is None

    def test_get_matrix_cell_stats_with_data(self, aggregation_engine, mock_session):
        """Test getting comprehensive stats for a matrix cell."""
        # Mock aggregated metric
        mock_aggregated = Mock()
        mock_aggregated.cell_id = 1
        mock_aggregated.equity = Decimal('0.6500')
        mock_aggregated.ev = Decimal('0.3000')
        mock_aggregated.jackpot_adjusted_ev = Decimal('0.3500')
        mock_aggregated.jackpot_frequency = Decimal('0.0500')
        mock_aggregated.convergence_status = 'converging'
        mock_aggregated.last_updated = '2024-01-01T12:00:00'

        # Mock query results
        mock_session.query.return_value.filter.return_value.first.return_value = mock_aggregated
        # Mock the count calls - need to handle both queries
        mock_session.query.return_value.filter.return_value.count.side_effect = [100]  # game states count
        mock_session.query.return_value.join.return_value.filter.return_value.count.return_value = 5  # jackpots count

        result = aggregation_engine.get_matrix_cell_stats(1)

        assert result is not None
        assert result['matrix_cell_id'] == 1
        assert result['game_states_count'] == 100
        assert result['jackpots_count'] == 5
        assert result['equity'] == 0.65
        assert result['ev'] == 0.3
        assert result['jackpot_adjusted_ev'] == 0.35
        assert result['jackpot_frequency'] == 0.05
        assert result['convergence_status'] == 'converging'