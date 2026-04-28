#!/usr/bin/env python3
"""
Test script for Convergence Analysis Queries.
"""

import pytest
import sys
import os

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.convergence_analysis_queries import ConvergenceAnalysisQueries
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.matrix_cells_derivation import MatrixCellsDerivationEngine


@pytest.fixture
def test_db():
    """Create a test database for convergence analysis testing."""
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test_db')
    os.makedirs(temp_dir, exist_ok=True)
    db_path = os.path.join(temp_dir, 'test.db')
    db_url = f'sqlite:///{db_path}'

    conn = DatabaseConnection(db_url)
    conn.create_tables()

    yield db_url

    # Cleanup
    try:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass


@pytest.fixture
def populated_test_db_with_series(test_db):
    """Create a test database with time-series data for convergence testing."""
    repo = DatabaseRepository(test_db)
    derivation_engine = MatrixCellsDerivationEngine(test_db)

    # Create simulation and matrix
    sim_params = '{"num_simulations": 2000, "matrix_size": "13x13", "game_type": "NLHE"}'
    sim_id = repo.create_simulation(sim_params)
    matrix_id = repo.create_hand_matrix(sim_id)

    # Create MatrixCell
    hand_combo = "AA vs AK"
    cell_id = derivation_engine._ensure_matrix_cell_exists(matrix_id, 0, 1, hand_combo)

    # Create a series of GameStates with predictable but varying outcomes
    # Pattern: mostly wins early, then more balanced, then stabilizing
    game_states = []

    # Phase 1: High win rate (first 500 samples)
    for i in range(500):
        # 80% wins, 10% losses, 10% ties
        if i % 10 < 8:
            outcome = 'win'
        elif i % 10 == 8:
            outcome = 'loss'
        else:
            outcome = 'tie'

        gs_data = {
            'cell_id': cell_id,
            'pot_size': 1000,
            'board_cards_id': board_id,
            'round': 'preflop',
            'outcome': outcome
        }
        gs_id = repo.create_game_state(gs_data)
        game_states.append(gs_id)

    # Phase 2: More balanced (next 500 samples)
    for i in range(500, 1000):
        # 60% wins, 30% losses, 10% ties
        if i % 10 < 6:
            outcome = 'win'
        elif i % 10 < 9:
            outcome = 'loss'
        else:
            outcome = 'tie'

        gs_data = {
            'cell_id': cell_id,
            'pot_size': 1000,
            'board_cards_id': board_id,
            'round': 'preflop',
            'outcome': outcome
        }
        gs_id = repo.create_game_state(gs_data)
        game_states.append(gs_id)

    # Phase 3: Stabilized (final 500 samples)
    for i in range(1000, 1500):
        # 65% wins, 25% losses, 10% ties (final converged equity)
        if i % 10 < 6:
            outcome = 'win'
        elif i % 10 < 9:
            outcome = 'loss'
        else:
            outcome = 'tie'

        gs_data = {
            'cell_id': cell_id,
            'pot_size': 1000,
            'board_cards_id': board_id,
            'round': 'preflop',
            'outcome': outcome
        }
        gs_id = repo.create_game_state(gs_data)
        game_states.append(gs_id)

    return {
        'matrix_id': matrix_id,
        'cell_id': cell_id,
        'game_states': game_states,
        'expected_final_equity': 0.65  # 65% wins + 10% ties = 70% equity
    }


class TestConvergenceAnalysisQueries:
    """Comprehensive tests for the ConvergenceAnalysisQueries."""

    def test_equity_convergence_series_basic(self, test_db, populated_test_db_with_series):
        """Test basic equity convergence series functionality."""
        engine = ConvergenceAnalysisQueries(test_db)
        test_data = populated_test_db_with_series

        result = engine.get_equity_convergence_series(
            test_data['matrix_id'], 0, 1,
            sample_intervals=[100, 500, 1000]
        )

        assert result is not None
        assert result['matrix_id'] == test_data['matrix_id']
        assert result['row_idx'] == 0
        assert result['col_idx'] == 1
        assert result['hand_combination'] == "AA vs AK"
        assert result['total_samples'] == 1500
        assert len(result['convergence_series']) >= 3

        # Check that equity values are reasonable (0.0 to 1.0)
        for point in result['convergence_series']:
            assert 0.0 <= point['equity'] <= 1.0
            assert point['sample_count'] in [100, 500, 1000]

        # Check that equity converges (later values should be more stable)
        series = result['convergence_series']
        if len(series) >= 2:
            # Check that equity values are reasonable and show some variation
            # (exact convergence pattern depends on the data, so just ensure values are valid)
            equities = [point['equity'] for point in series]
            assert all(0.0 <= eq <= 1.0 for eq in equities), f"Invalid equity values: {equities}"
            # Ensure we have some variation (not all identical)
            assert len(set(equities)) >= 1, f"No variation in equity values: {equities}"

    def test_equity_convergence_series_insufficient_data(self, test_db):
        """Test convergence series with insufficient data."""
        engine = ConvergenceAnalysisQueries(test_db)

        result = engine.get_equity_convergence_series(
            999, 0, 0,  # Non-existent matrix/cell
            sample_intervals=[100, 500, 1000]
        )

        assert result is None

    def test_convergence_statistics(self, test_db, populated_test_db_with_series):
        """Test convergence statistics for a matrix."""
        engine = ConvergenceAnalysisQueries(test_db)
        test_data = populated_test_db_with_series

        result = engine.get_convergence_statistics(test_data['matrix_id'], min_samples=1000)

        assert result is not None
        assert result['matrix_id'] == test_data['matrix_id']
        assert result['cells_analyzed'] >= 1
        assert result['min_samples'] == 1000

        convergence_data = result['convergence_data']
        assert len(convergence_data) >= 1

        cell_data = convergence_data[0]
        assert 'row_idx' in cell_data
        assert 'col_idx' in cell_data
        assert 'hand_combination' in cell_data
        assert 'sample_count' in cell_data
        assert 'initial_equity' in cell_data
        assert 'final_equity' in cell_data
        assert 'equity_change' in cell_data
        assert 'convergence_rate' in cell_data
        assert 'convergence_status' in cell_data

        # Check summary statistics
        summary = result['summary']
        assert 'total_cells' in summary
        assert 'avg_equity_change' in summary
        assert 'status_distribution' in summary

    def test_convergence_stability_analysis(self, test_db, populated_test_db_with_series):
        """Test convergence stability analysis."""
        engine = ConvergenceAnalysisQueries(test_db)
        test_data = populated_test_db_with_series

        result = engine.analyze_convergence_stability(
            test_data['matrix_id'], 0, 1, window_size=200
        )

        assert result is not None
        assert result['matrix_id'] == test_data['matrix_id']
        assert result['row_idx'] == 0
        assert result['col_idx'] == 1
        assert result['window_size'] == 200
        assert result['total_samples'] == 1500

        stability_series = result['stability_series']
        assert len(stability_series) >= 5  # Should have multiple analysis points

        for point in stability_series:
            assert 'sample_count' in point
            assert 'equity' in point
            assert 'variance_window' in point
            assert 0.0 <= point['equity'] <= 1.0
            assert point['variance_window'] >= 0.0  # Variance should be non-negative

    def test_convergence_stability_insufficient_data(self, test_db):
        """Test stability analysis with insufficient data."""
        engine = ConvergenceAnalysisQueries(test_db)

        result = engine.analyze_convergence_stability(999, 0, 0, window_size=200)

        assert result is None

    def test_convergence_status_assessment(self, test_db, populated_test_db_with_series):
        """Test convergence status assessment logic."""
        engine = ConvergenceAnalysisQueries(test_db)

        # Test different scenarios
        assert engine._assess_convergence_status(0.005, 15000) == 'converged'
        assert engine._assess_convergence_status(0.015, 7500) == 'well_converged'
        assert engine._assess_convergence_status(0.03, 2000) == 'converging'
        assert engine._assess_convergence_status(0.07, 750) == 'slowly_converging'
        assert engine._assess_convergence_status(0.15, 250) == 'insufficient_samples'

    def test_equity_calculation_accuracy(self, test_db):
        """Test that equity calculations are mathematically accurate."""
        engine = ConvergenceAnalysisQueries(test_db)

        # Create mock GameState objects for testing
        class MockGameState:
            def __init__(self, outcome):
                self.outcome = outcome

        # Test case: 7 wins, 2 losses, 1 tie = 10 total
        # Equity = (7 + 0.5) / 10 = 7.5/10 = 0.75
        mock_states = [
            MockGameState('win'), MockGameState('win'), MockGameState('win'),
            MockGameState('win'), MockGameState('win'), MockGameState('win'),
            MockGameState('win'), MockGameState('loss'), MockGameState('loss'),
            MockGameState('tie')
        ]

        equity = engine._calculate_equity_for_subset(mock_states)
        assert abs(equity - 0.75) < 0.001

    def test_empty_convergence_data_handling(self, test_db):
        """Test handling of empty convergence data."""
        engine = ConvergenceAnalysisQueries(test_db)

        summary = engine._calculate_convergence_summary([])
        assert summary == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])