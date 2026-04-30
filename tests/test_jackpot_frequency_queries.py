#!/usr/bin/env python3
"""
Test script for Jackpot Frequency Analysis Queries.
"""

import pytest
import sys
import os

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.jackpot_frequency_queries import JackpotFrequencyQueries
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.matrix_cells_derivation import MatrixCellsDerivationEngine
from hopilot.gto.simulation_repository import SimulationRepository


@pytest.fixture
def test_db(tmp_path):
    """Create a test database for jackpot frequency testing."""
    db_path = tmp_path / 'test.db'
    db_url = f'sqlite:///{db_path}'

    conn = DatabaseConnection(db_url)
    conn.create_tables()

    yield conn

    # Cleanup
    try:
        conn.close()
    except Exception:
        pass


@pytest.fixture
def populated_test_db_with_jackpots(test_db):
    """Create a test database with jackpot data for analysis."""
    sim_repo = SimulationRepository(test_db)
    gs_repo = GameStateRepository(test_db)
    derivation_engine = MatrixCellsDerivationEngine(test_db.database_url)

    # Create simulation and matrix
    sim_params = '{"num_simulations": 2000, "matrix_size": "13x13", "game_type": "NLHE"}'
    sim_id = sim_repo.create_simulation(sim_params)
    matrix_id = sim_repo.create_hand_matrix(sim_id)

    # Create MatrixCell for an AKs hero hand coordinate.
    hand_combo = "AKs vs AA"
    cell_id = derivation_engine._ensure_matrix_cell_exists(matrix_id, 0, 1, hand_combo)

    # Create game states with some jackpots
    jackpot_games = 0
    total_games = 1000

    for i in range(total_games):
        gs_data = {
            'cell_id': cell_id,
            'pot_size': 1000,
            'board_cards_str': 'As,Ks,Qs,Js,Ts',
            'round': 'preflop',
            'outcome': 'win'  # All games win for simplicity
        }
        gs_id = gs_repo.create_game_state(gs_data)

        # Create a hero player for this game state so matrix mapping works.
        hero_player_data = {
            'game_state_id': gs_id,
            'position': 'hero',
            'hole_cards': 'AsKs',
            'stack_size': 10000,
            'is_hero': True
        }
        hero_player_id = gs_repo.create_player(hero_player_data)

        # Create a second player for realism.
        gs_repo.create_player({
            'game_state_id': gs_id,
            'position': 'villain',
            'hole_cards': 'KsKd',
            'stack_size': 10000,
            'is_hero': False
        })

        # Create jackpots for 5% of games
        if i % 20 == 0:  # Every 20th game has a jackpot
            jackpot_data = {
                'game_state_id': gs_id,
                'player_id': hero_player_id,
                'jackpot_type': 'ROYAL_FLUSH' if i % 40 == 0 else 'STRAIGHT_FLUSH',
                'payout_amount': 5000 if i % 40 == 0 else 1000,
                'qualifying_cards': ['As', 'Ks', 'Qs', 'Js', 'Ts'] if i % 40 == 0 else ['As', 'Ks', 'Qs', 'Js', '9s'],
                'payout_multiplier': 500 if i % 40 == 0 else 100
            }
            gs_repo.create_jackpot(jackpot_data)
            jackpot_games += 1

    return {
        'matrix_id': matrix_id,
        'cell_id': cell_id,
        'total_games': total_games,
        'jackpot_games': jackpot_games,
        'expected_frequency': jackpot_games / total_games
    }


class TestJackpotFrequencyQueries:
    """Comprehensive tests for the JackpotFrequencyQueries."""

    def test_jackpot_frequency_analysis_basic(self, test_db, populated_test_db_with_jackpots):
        """Test basic jackpot frequency analysis functionality."""
        engine = JackpotFrequencyQueries(test_db.database_url)
        test_data = populated_test_db_with_jackpots

        result = engine.get_jackpot_frequency_analysis(test_data['matrix_id'])

        assert result is not None
        assert result['matrix_id'] == test_data['matrix_id']
        assert result['total_games'] == test_data['total_games']
        assert result['total_jackpots'] == test_data['jackpot_games']
        assert abs(result['overall_frequency'] - test_data['expected_frequency']) < 0.001

        # Check jackpot types analysis
        assert 'jackpot_types' in result
        jackpot_types = result['jackpot_types']
        assert len(jackpot_types) > 0

        # Verify EV impact calculations
        for jt_stats in jackpot_types.values():
            assert 'count' in jt_stats
            assert 'frequency' in jt_stats
            assert 'avg_payout' in jt_stats
            assert 'ev_impact' in jt_stats
            assert jt_stats['ev_impact'] == jt_stats['frequency'] * jt_stats['avg_payout']

    def test_jackpot_frequency_analysis_insufficient_data(self, test_db):
        """Test jackpot frequency analysis with insufficient data."""
        engine = JackpotFrequencyQueries(test_db.database_url)

        result = engine.get_jackpot_frequency_analysis(999, min_samples=10000)

        assert result == {}

    def test_jackpot_ev_impact_by_hand(self, test_db, populated_test_db_with_jackpots):
        """Test EV impact analysis by hand combination."""
        engine = JackpotFrequencyQueries(test_db.database_url)
        test_data = populated_test_db_with_jackpots

        result = engine.get_jackpot_ev_impact_by_hand(test_data['matrix_id'])

        assert result is not None
        assert result['matrix_id'] == test_data['matrix_id']
        assert result['hands_analyzed'] >= 1

        hand_analysis = result['hand_analysis']
        assert len(hand_analysis) >= 1

        # Check that results are sorted by EV impact (descending)
        ev_impacts = [h['jackpot_ev_impact'] for h in hand_analysis]
        assert ev_impacts == sorted(ev_impacts, reverse=True)

        # Verify hand analysis structure
        hand = hand_analysis[0]
        assert 'row_idx' in hand
        assert 'col_idx' in hand
        assert 'hand_combination' in hand
        assert 'sample_count' in hand
        assert 'total_jackpots' in hand
        assert 'jackpot_frequency' in hand
        assert 'avg_jackpot_payout' in hand
        assert 'jackpot_ev_impact' in hand
        assert 'jackpot_types' in hand

    def test_jackpot_temporal_analysis(self, test_db, populated_test_db_with_jackpots):
        """Test temporal analysis of jackpot frequency."""
        engine = JackpotFrequencyQueries(test_db.database_url)
        test_data = populated_test_db_with_jackpots

        result = engine.get_jackpot_temporal_analysis(test_data['matrix_id'])

        assert result is not None
        assert result['matrix_id'] == test_data['matrix_id']
        assert result['total_samples'] == test_data['total_games']

        temporal_data = result['temporal_analysis']
        assert len(temporal_data) > 0

        # Check that temporal data is properly structured
        for point in temporal_data:
            assert 'sample_count' in point
            assert 'jackpot_count' in point
            assert 'frequency' in point
            assert 'frequency_percent' in point
            assert 'avg_payout' in point
            assert 'total_payout' in point

        # Check that sample counts are increasing
        sample_counts = [p['sample_count'] for p in temporal_data]
        assert sample_counts == sorted(sample_counts)

    def test_jackpot_ev_summary_calculation(self, test_db, populated_test_db_with_jackpots):
        """Test that EV summary calculations are correct."""
        engine = JackpotFrequencyQueries(test_db.database_url)
        test_data = populated_test_db_with_jackpots

        result = engine.get_jackpot_ev_impact_by_hand(test_data['matrix_id'])

        assert 'summary' in result
        summary = result['summary']

        assert 'total_hands' in summary
        assert 'avg_jackpot_ev_impact' in summary
        assert 'max_jackpot_ev_impact' in summary
        assert 'min_jackpot_ev_impact' in summary
        assert 'hands_with_jackpots' in summary
        assert 'highest_ev_hand' in summary
        assert 'lowest_ev_hand' in summary

        # Verify summary calculations
        hand_analysis = result['hand_analysis']
        if hand_analysis:
            expected_avg_ev = sum(h['jackpot_ev_impact'] for h in hand_analysis) / len(hand_analysis)
            assert abs(summary['avg_jackpot_ev_impact'] - expected_avg_ev) < 0.001

            expected_max_ev = max(h['jackpot_ev_impact'] for h in hand_analysis)
            assert abs(summary['max_jackpot_ev_impact'] - expected_max_ev) < 0.001

    def test_jackpot_frequency_mathematical_accuracy(self, test_db, populated_test_db_with_jackpots):
        """Test mathematical accuracy of jackpot frequency calculations."""
        engine = JackpotFrequencyQueries(test_db.database_url)
        test_data = populated_test_db_with_jackpots

        # Test frequency analysis
        freq_result = engine.get_jackpot_frequency_analysis(test_data['matrix_id'])

        # Manually verify calculations
        total_jackpots = freq_result['total_jackpots']
        total_games = freq_result['total_games']
        expected_frequency = total_jackpots / total_games

        assert abs(freq_result['overall_frequency'] - expected_frequency) < 0.001

        # Test EV impact calculation
        total_ev_impact = sum(jt['ev_impact'] for jt in freq_result['jackpot_types'].values())
        assert abs(freq_result['total_ev_impact'] - total_ev_impact) < 0.001

    def test_empty_jackpot_analysis(self, test_db):
        """Test analysis with no jackpot data."""
        engine = JackpotFrequencyQueries(test_db.database_url)

        # Create a matrix with no jackpots
        sim_repo = SimulationRepository(test_db)
        gs_repo = GameStateRepository(test_db)
        derivation_engine = MatrixCellsDerivationEngine(test_db.database_url)

        sim_params = '{"num_simulations": 100, "matrix_size": "13x13", "game_type": "NLHE"}'
        sim_id = sim_repo.create_simulation(sim_params)
        matrix_id = sim_repo.create_hand_matrix(sim_id)

        hand_combo = "22 vs 33"
        cell_id = derivation_engine._ensure_matrix_cell_exists(matrix_id, 0, 1, hand_combo)

        # Create games without jackpots
        for i in range(100):
            gs_data = {
                'cell_id': cell_id,
                'pot_size': 100,
                'board_cards_str': '2s,3s,4s,5s,6s',
                'round': 'preflop',
                'outcome': 'loss'
            }
            gs_id = gs_repo.create_game_state(gs_data)
            gs_repo.create_player({
                'game_state_id': gs_id,
                'position': 'hero',
                'hole_cards': 'AsKs',
                'stack_size': 1000,
                'is_hero': True
            })

        result = engine.get_jackpot_frequency_analysis(matrix_id, min_samples=50)

        assert result['total_jackpots'] == 0
        assert result['overall_frequency'] == 0.0
        assert result['total_ev_impact'] == 0.0
        assert len(result['jackpot_types']) == 0
