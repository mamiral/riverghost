#!/usr/bin/env python3
"""
Comprehensive tests for the Aggregation Engine.

Tests the core aggregation functionality with various GameState datasets,
performance requirements, and edge cases.
"""

import os
import sys
import tempfile
import time

import pytest

# Add python directory to path for local package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.aggregation_engine import AggregationEngine
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.matrix_cells_derivation import MatrixCellsDerivationEngine
from hopilot.gto.aof_hand_matrix import hand_key_from_index


def build_hole_cards_for_hand_key(hand_key: str) -> str:
    if len(hand_key) == 2:
        return f"{hand_key[0]}s{hand_key[1]}h"

    rank_one, rank_two, suitedness = hand_key[0], hand_key[1], hand_key[2]
    if suitedness == 's':
        return f"{rank_one}s{rank_two}s"
    return f"{rank_one}s{rank_two}h"


def generate_hero_hole_cards(row_idx: int, col_idx: int) -> str:
    return build_hole_cards_for_hand_key(hand_key_from_index(row_idx, col_idx))


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / 'test.db'
    db_url = f'sqlite:///{db_path}'

    conn = DatabaseConnection(db_url)
    conn.create_tables()

    yield db_url

    try:
        conn.close()
    except Exception:
        pass


@pytest.fixture
def populated_test_db(test_db):
    repo = DatabaseRepository(test_db)
    derivation_engine = MatrixCellsDerivationEngine(test_db)

    sim_params = '{"num_simulations": 1000, "matrix_size": "13x13", "game_type": "NLHE"}'
    sim_id = repo.create_simulation(sim_params)
    matrix_id = repo.create_hand_matrix(sim_id)

    test_data = []
    hand_combinations = [
        ("AA vs AK", 0, 1, 50),
        ("KK vs QQ", 1, 2, 25),
        ("AK vs AQ", 2, 3, 10),
        ("JJ vs TT", 3, 4, 5),
    ]

    for hand_combo, row_idx, col_idx, num_samples in hand_combinations:
        cell_id = derivation_engine._ensure_matrix_cell_exists(matrix_id, row_idx, col_idx, hand_combo)
        hero_hole_cards = generate_hero_hole_cards(row_idx, col_idx)

        for i in range(num_samples):
            outcome = 'win' if i % 3 == 0 else ('loss' if i % 3 == 1 else 'tie')
            gs_id = repo.create_game_state({
                'pot_size': 1000 + (i * 100),
                'board_cards_str': 'As,Ks,Qs,Js,Ts',
                'round': 'preflop',
                'outcome': outcome,
            })

            repo.create_player({
                'game_state_id': gs_id,
                'position': 'UTG',
                'hole_cards': hero_hole_cards,
                'stack_size': 10000,
                'is_hero': True,
            })
            repo.create_player({
                'game_state_id': gs_id,
                'position': 'BTN',
                'hole_cards': 'KdKh',
                'stack_size': 10000,
                'is_hero': False,
            })

        test_data.append({
            'hand_combo': hand_combo,
            'cell_id': cell_id,
            'matrix_id': matrix_id,
            'row_idx': row_idx,
            'col_idx': col_idx,
            'expected_samples': num_samples,
        })

    return test_data


class TestAggregationEngine:
    """Comprehensive tests for the AggregationEngine."""

    def test_basic_aggregation_single_cell(self, test_db, populated_test_db):
        engine = AggregationEngine(test_db)
        test_case = populated_test_db[0]

        result = engine.compute_matrix_cell_from_game_states(
            test_case['matrix_id'],
            test_case['row_idx'],
            test_case['col_idx'],
            min_samples=10,
        )

        assert isinstance(result, dict)
        assert result['total_games'] == test_case['expected_samples']
        assert 0.0 <= result['equity'] <= 1.0
        assert isinstance(result['ev'], float)

    def test_aggregation_insufficient_samples(self, test_db, populated_test_db):
        engine = AggregationEngine(test_db)
        test_case = populated_test_db[3]

        result = engine.compute_matrix_cell_from_game_states(
            test_case['matrix_id'],
            test_case['row_idx'],
            test_case['col_idx'],
            min_samples=10,
        )

        assert result is None

    def test_aggregation_nonexistent_cell(self, test_db):
        engine = AggregationEngine(test_db)

        result = engine.compute_matrix_cell_from_game_states(999, 0, 0, min_samples=1)
        assert result is None

    def test_aggregation_mathematical_correctness(self, test_db, populated_test_db):
        engine = AggregationEngine(test_db)
        test_case = populated_test_db[0]

        result = engine.compute_matrix_cell_from_game_states(
            test_case['matrix_id'],
            test_case['row_idx'],
            test_case['col_idx'],
            min_samples=1,
        )

        expected_equity = (17 + 16 * 0.5) / 50
        assert abs(result['equity'] - expected_equity) < 0.01

    def test_aggregation_performance_small_dataset(self, test_db, populated_test_db):
        engine = AggregationEngine(test_db)
        start_time = time.time()

        for test_case in populated_test_db:
            if test_case['expected_samples'] >= 10:
                result = engine.compute_matrix_cell_from_game_states(
                    test_case['matrix_id'],
                    test_case['row_idx'],
                    test_case['col_idx'],
                    min_samples=10,
                )
                assert isinstance(result, dict)

        assert time.time() - start_time < 1.0

    def test_aggregation_with_jackpots(self, test_db):
        repo = DatabaseRepository(test_db)
        engine = AggregationEngine(test_db)
        derivation_engine = MatrixCellsDerivationEngine(test_db)

        sim_params = '{"num_simulations": 100, "matrix_size": "13x13", "game_type": "NLHE"}'
        sim_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(sim_id)

        hero_hole_cards = generate_hero_hole_cards(0, 0)
        derivation_engine._ensure_matrix_cell_exists(matrix_id, 0, 0, "AA vs KK")

        gs_id = repo.create_game_state({
            'pot_size': 1000,
            'board_cards_str': 'As,Ks,Qs,Js,Ts',
            'round': 'preflop',
            'outcome': 'jackpot_win',
        })

        hero_player_id = repo.create_player({
            'game_state_id': gs_id,
            'position': 'UTG',
            'hole_cards': hero_hole_cards,
            'stack_size': 10000,
            'is_hero': True,
        })
        repo.create_player({
            'game_state_id': gs_id,
            'position': 'BTN',
            'hole_cards': 'KdKh',
            'stack_size': 10000,
            'is_hero': False,
        })

        repo.create_jackpot({
            'game_state_id': gs_id,
            'player_id': hero_player_id,
            'jackpot_type': 'ROYAL_FLUSH',
            'payout_amount': 5000,
            'qualifying_cards': ['As', 'Ks', 'Qs', 'Js', 'Ts'],
            'payout_multiplier': 500,
        })

        result = engine.compute_matrix_cell_from_game_states(matrix_id, 0, 0, min_samples=1)
        assert isinstance(result, dict)
        assert result['total_games'] == 1

    def test_aggregation_edge_cases(self, test_db):
        engine = AggregationEngine(test_db)
        assert engine.compute_matrix_cell_from_game_states(-1, 0, 0, min_samples=1) is None
        assert engine.compute_matrix_cell_from_game_states(1, 999, 999, min_samples=1) is None

    def test_aggregation_data_consistency(self, test_db, populated_test_db):
        engine = AggregationEngine(test_db)
        test_case = populated_test_db[0]

        results = [
            engine.compute_matrix_cell_from_game_states(
                test_case['matrix_id'],
                test_case['row_idx'],
                test_case['col_idx'],
                min_samples=10,
            )
            for _ in range(3)
        ]

        assert all(result is not None for result in results)
        for result in results[1:]:
            assert result['equity'] == results[0]['equity']
            assert result['ev'] == results[0]['ev']
            assert result['total_games'] == results[0]['total_games']


class TestAggregationIntegration:
    """Integration tests for the aggregation system."""

    def test_full_aggregation_pipeline(self, test_db, populated_test_db):
        derivation_engine = MatrixCellsDerivationEngine(test_db)

        test_case = populated_test_db[0]
        result = derivation_engine.derive_matrix_cells_from_aggregations(
            test_case['matrix_id'],
            min_samples=10,
        )

        assert result['created_cells'] >= 1

    def test_aggregation_with_matrix_derivation(self, test_db, populated_test_db):
        derivation_engine = MatrixCellsDerivationEngine(test_db)
        aggregation_engine = AggregationEngine(test_db)

        test_case = populated_test_db[0]
        derivation_result = derivation_engine.derive_matrix_cells_from_aggregations(
            test_case['matrix_id'],
            min_samples=10,
        )

        assert derivation_result['created_cells'] >= 1

        agg_result = aggregation_engine.compute_matrix_cell_from_game_states(
            test_case['matrix_id'],
            test_case['row_idx'],
            test_case['col_idx'],
            min_samples=10,
        )

        assert agg_result is not None
        assert agg_result['total_games'] == test_case['expected_samples']
