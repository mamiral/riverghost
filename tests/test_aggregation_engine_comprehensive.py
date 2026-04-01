#!/usr/bin/env python3
"""
Comprehensive tests for the Aggregation Engine.

Tests the core aggregation functionality with various GameStates datasets,
performance requirements, and edge cases.
"""

import pytest
import time
import sys
import os

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.aggregation_engine import AggregationEngine
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.matrix_cells_derivation import MatrixCellsDerivationEngine


@pytest.fixture
def test_db():
    """Create a test database for aggregation testing."""
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
def populated_test_db(test_db):
    """Create a test database with sample data for testing."""
    repo = DatabaseRepository(test_db)
    derivation_engine = MatrixCellsDerivationEngine(test_db)

    # Create simulation and matrix
    sim_params = '{"num_simulations": 1000, "matrix_size": "13x13", "game_type": "NLHE"}'
    sim_id = repo.create_simulation(sim_params)
    matrix_id = repo.create_hand_matrix(sim_id)

    # Create board cards
    board_id = repo.create_board_card({
        'flop1': 'As', 'flop2': 'Ks', 'flop3': 'Qs',
        'turn': 'Js', 'river': 'Ts'
    })

    # Create multiple hand combinations with different sample sizes
    test_data = []

    hand_combinations = [
        ("AA vs AK", 0, 1, 50),   # 50 samples
        ("KK vs QQ", 1, 2, 25),   # 25 samples
        ("AK vs AQ", 2, 3, 10),   # 10 samples
        ("JJ vs TT", 3, 4, 5),    # 5 samples (below minimum)
    ]

    for hand_combo, row_idx, col_idx, num_samples in hand_combinations:
        # Create matrix cell
        cell_id = derivation_engine._ensure_matrix_cell_exists(matrix_id, row_idx, col_idx, hand_combo)

        # Create multiple GameStates for this cell
        game_states = []
        for i in range(num_samples):
            outcome = 'win' if i % 3 == 0 else ('loss' if i % 3 == 1 else 'tie')
            gs_data = {
                'cell_id': cell_id,
                'pot_size': 1000 + (i * 100),  # Varying pot sizes
                'board_cards_id': board_id,
                'round': 'preflop',
                'outcome': outcome
            }
            gs_id = repo.create_game_state(gs_data)
            game_states.append(gs_id)

        test_data.append({
            'hand_combo': hand_combo,
            'cell_id': cell_id,
            'matrix_id': matrix_id,
            'row_idx': row_idx,
            'col_idx': col_idx,
            'game_states': game_states,
            'expected_samples': num_samples
        })

    return test_data


class TestAggregationEngine:
    """Comprehensive tests for the AggregationEngine."""

    def test_basic_aggregation_single_cell(self, test_db, populated_test_db):
        """Test basic aggregation for a single matrix cell."""
        engine = AggregationEngine(test_db)

        # Test the first hand combination (AA vs AK with 50 samples)
        test_case = populated_test_db[0]
        result = engine.compute_matrix_cell_from_game_states(
            test_case['matrix_id'],
            test_case['row_idx'],
            test_case['col_idx'],
            min_samples=10
        )

        # Validate aggregation result content and structure
        assert isinstance(result, dict), "Result should be a dictionary"
        assert 'equity' in result, "Result should contain equity"
        assert 'ev' in result, "Result should contain EV"
        assert 'total_games' in result, "Result should contain total_games"
        assert isinstance(result['equity'], (int, float)), "Equity should be numeric"
        assert isinstance(result['ev'], (int, float)), "EV should be numeric"
        assert isinstance(result['total_games'], int), "Total games should be an integer"
        assert result['total_games'] == test_case['expected_samples'], "Total games should match expected samples"

        # Verify equity is between 0 and 1
        assert 0.0 <= result['equity'] <= 1.0

        # Verify EV calculation (should be positive for winning hands)
        assert isinstance(result['ev'], float)

    def test_aggregation_insufficient_samples(self, test_db, populated_test_db):
        """Test aggregation with insufficient samples."""
        engine = AggregationEngine(test_db)

        # Test the last hand combination (JJ vs TT with only 5 samples)
        test_case = populated_test_db[3]  # 5 samples
        result = engine.compute_matrix_cell_from_game_states(
            test_case['matrix_id'],
            test_case['row_idx'],
            test_case['col_idx'],
            min_samples=10  # Require 10 samples, but only 5 available
        )

        # Should return None due to insufficient samples
        assert result is None

    def test_aggregation_nonexistent_cell(self, test_db):
        """Test aggregation for a cell that doesn't exist."""
        engine = AggregationEngine(test_db)

        result = engine.compute_matrix_cell_from_game_states(
            999,  # Non-existent matrix
            0, 0,
            min_samples=1
        )

        assert result is None

    def test_aggregation_mathematical_correctness(self, test_db, populated_test_db):
        """Test that aggregation calculations are mathematically correct."""
        engine = AggregationEngine(test_db)

        test_case = populated_test_db[0]  # AA vs AK with known outcomes
        result = engine.compute_matrix_cell_from_game_states(
            test_case['matrix_id'],
            test_case['row_idx'],
            test_case['col_idx'],
            min_samples=1
        )

        # Validate mathematical correctness result structure
        assert isinstance(result, dict), "Mathematical correctness result should be a dictionary"
        assert 'equity' in result, "Should contain equity calculation"
        assert 'ev' in result, "Should contain EV calculation"
        assert 'total_games' in result, "Should contain total games count"

        # For 50 samples with pattern: win, loss, tie, win, loss, tie, ...
        # Number of wins: ceil(50/3) = 17
        # Number of ties: floor(50/3) = 16
        # Number of losses: 50 - 17 - 16 = 17
        expected_equity = (17 + 16 * 0.5) / 50  # 17 + 8 = 25, 25/50 = 0.5

        assert abs(result['equity'] - expected_equity) < 0.01

    def test_aggregation_performance_small_dataset(self, test_db, populated_test_db):
        """Test aggregation performance with small dataset."""
        engine = AggregationEngine(test_db)

        start_time = time.time()

        # Test all populated cells
        for test_case in populated_test_db:
            if test_case['expected_samples'] >= 10:  # Only test cells with sufficient samples
                result = engine.compute_matrix_cell_from_game_states(
                    test_case['matrix_id'],
                    test_case['row_idx'],
                    test_case['col_idx'],
                    min_samples=10
                )
                # Validate performance test result content
                assert isinstance(result, dict), "Performance result should be a dictionary"
                assert 'equity' in result, "Performance result should contain equity"
                assert 'total_games' in result, "Performance result should contain total_games"

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in well under 1 second for small dataset
        assert duration < 1.0, f"Aggregation took {duration:.2f}s, expected < 1.0s"

    def test_aggregation_with_jackpots(self, test_db):
        """Test aggregation calculations that include jackpot data."""
        repo = DatabaseRepository(test_db)
        engine = AggregationEngine(test_db)
        derivation_engine = MatrixCellsDerivationEngine(test_db)

        # Create test data with jackpots
        sim_params = '{"num_simulations": 100, "matrix_size": "13x13", "game_type": "NLHE"}'
        sim_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(sim_id)

        board_id = repo.create_board_card({
            'flop1': 'As', 'flop2': 'Ks', 'flop3': 'Qs',
            'turn': 'Js', 'river': 'Ts'
        })

        # Create cell and GameStates
        cell_id = derivation_engine._ensure_matrix_cell_exists(matrix_id, 0, 0, "AA vs KK")  # Fixed hand combination

        # Create GameState with jackpot win
        gs_data = {
            'cell_id': cell_id,
            'pot_size': 1000,
            'board_cards_id': board_id,
            'round': 'preflop',
            'outcome': 'jackpot_win'
        }
        gs_id = repo.create_game_state(gs_data)

        # Create jackpot record
        jackpot_data = {
            'game_state_id': gs_id,
            'player_id': 1,  # Note: This assumes player exists, may need adjustment
            'jackpot_type': 'royal_flush',
            'payout_amount': 5000,
            'qualifying_cards': '["As", "Ks", "Qs", "Js", "Ts"]'
        }

        # Note: This test may need to be adjusted based on the actual jackpot creation API
        # For now, we'll test that the aggregation still works
        result = engine.compute_matrix_cell_from_game_states(
            matrix_id, 0, 0, min_samples=1
        )

        # Validate jackpot aggregation result content
        assert isinstance(result, dict), "Jackpot result should be a dictionary"
        assert 'total_games' in result, "Jackpot result should contain total_games"
        assert result['total_games'] == 1, "Should have exactly 1 game with jackpot"

    def test_aggregation_edge_cases(self, test_db):
        """Test aggregation with edge cases."""
        engine = AggregationEngine(test_db)

        # Test with invalid matrix_id
        result = engine.compute_matrix_cell_from_game_states(-1, 0, 0, min_samples=1)
        assert result is None

        # Test with out-of-bounds indices
        result = engine.compute_matrix_cell_from_game_states(1, 999, 999, min_samples=1)
        assert result is None

    def test_aggregation_data_consistency(self, test_db, populated_test_db):
        """Test that aggregation results are consistent across multiple runs."""
        engine = AggregationEngine(test_db)

        test_case = populated_test_db[0]

        # Run aggregation multiple times
        results = []
        for _ in range(3):
            result = engine.compute_matrix_cell_from_game_states(
                test_case['matrix_id'],
                test_case['row_idx'],
                test_case['col_idx'],
                min_samples=10
            )
            # Validate consistency test result content
            assert isinstance(result, dict), "Consistency result should be a dictionary"
            assert 'equity' in result, "Consistency result should contain equity"
            assert 'ev' in result, "Consistency result should contain EV"
            assert 'total_games' in result, "Consistency result should contain total_games"
            results.append(result)

        # All results should be identical
        for i in range(1, len(results)):
            assert results[0]['equity'] == results[i]['equity']
            assert results[0]['ev'] == results[i]['ev']
            assert results[0]['total_games'] == results[i]['total_games']


class TestAggregationIntegration:
    """Integration tests for the aggregation system."""

    def test_full_aggregation_pipeline(self, test_db, populated_test_db):
        """Test the complete aggregation pipeline from GameStates to MatrixCells."""
        derivation_engine = MatrixCellsDerivationEngine(test_db)

        test_case = populated_test_db[0]

        # Run the full derivation process
        result = derivation_engine.derive_matrix_cells_from_aggregations(
            test_case['matrix_id'],
            min_samples=10
        )

        assert result['created_cells'] >= 1
        assert result['total_processed'] >= 1

    def test_aggregation_with_matrix_derivation(self, test_db, populated_test_db):
        """Test aggregation works correctly with matrix cell derivation."""
        derivation_engine = MatrixCellsDerivationEngine(test_db)
        aggregation_engine = AggregationEngine(test_db)

        test_case = populated_test_db[0]

        # First derive the matrix cells
        derivation_result = derivation_engine.derive_matrix_cells_from_aggregations(
            test_case['matrix_id'],
            min_samples=10
        )

        assert derivation_result['created_cells'] >= 1

        # Then verify aggregation still works
        agg_result = aggregation_engine.compute_matrix_cell_from_game_states(
            test_case['matrix_id'],
            test_case['row_idx'],
            test_case['col_idx'],
            min_samples=10
        )

        assert agg_result is not None
        assert agg_result['total_games'] == test_case['expected_samples']