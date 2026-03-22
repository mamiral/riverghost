#!/usr/bin/env python3
"""
Test script for Incremental Aggregation Engine.
"""

import sys
import os

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.incremental_aggregation import IncrementalAggregationEngine
from hopilot.models import MatrixCell, AggregatedMetric, GameState

from sqlalchemy import func

def test_incremental_aggregation():
    """Test the incremental aggregation engine."""

    print("Testing Incremental Aggregation Engine...")

    # Create temp DB
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test_db')
    os.makedirs(temp_dir, exist_ok=True)
    db_path = os.path.join(temp_dir, 'test.db')
    db_url = f'sqlite:///{db_path}'

    try:
        # Initialize
        conn = DatabaseConnection(db_url)
        conn.create_tables()
        repo = DatabaseRepository(db_url)
        engine = IncrementalAggregationEngine(db_url)

        # Create dependencies
        sim_params = '{"num_simulations": 1000, "matrix_size": "13x13", "game_type": "NLHE"}'
        sim_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(sim_id)

        # Create board cards
        board_id = repo.create_board_card({
            'flop1': 'As', 'flop2': 'Ks', 'flop3': 'Qs',
            'turn': 'Js', 'river': 'Ts'
        })

        # Create initial MatrixCell and some GameStates
        hand_combo = "AA vs AK"
        cell_id = engine.derivation_engine._ensure_matrix_cell_exists(matrix_id, 0, 1, hand_combo)

        # Create initial GameStates (5 wins, 5 losses)
        initial_game_states = []
        for i in range(10):
            outcome = 'win' if i < 5 else 'loss'
            gs_data = {
                'cell_id': cell_id,
                'pot_size': 1000,
                'board_cards_id': board_id,
                'round': 'preflop',
                'outcome': outcome
            }
            gs_id = repo.create_game_state(gs_data)
            initial_game_states.append(gs_id)

        print("Created initial test data")

        # Run initial derivation to create baseline metrics
        result = engine.derivation_engine.derive_matrix_cells_from_aggregations(matrix_id, min_samples=1)
        print(f"Initial derivation: {result['created_cells']} cells created")

        # Verify initial metrics
        with conn.session_scope() as session:
            metric = session.query(AggregatedMetric).join(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id,
                MatrixCell.row_index == 0,
                MatrixCell.col_index == 1
            ).first()

            if metric:
                # Get actual total games from database count
                matrix_cell = session.query(MatrixCell).filter(
                    MatrixCell.matrix_id == matrix_id,
                    MatrixCell.row_index == 0,
                    MatrixCell.col_index == 1
                ).first()
                initial_games = session.query(func.count(GameState.id)).filter(
                    GameState.cell_id == matrix_cell.id
                ).scalar() or 0

                print(f"Initial metrics - Equity: {metric.equity:.4f}, EV: {metric.ev:.2f}, Games: {initial_games}")
                initial_equity = float(metric.equity)
            else:
                print("No initial metrics found")
                assert False, "No initial metrics found"

        # Add more GameStates incrementally
        new_game_states = []
        for i in range(5):  # Add 5 more wins
            gs_data = {
                'cell_id': cell_id,
                'pot_size': 1000,
                'board_cards_id': board_id,
                'round': 'preflop',
                'outcome': 'win'
            }
            gs_id = repo.create_game_state(gs_data)
            new_game_states.append(gs_id)

        print("Added 5 additional GameStates")

        # Run incremental update
        print(f"About to update with {len(new_game_states)} new GameState IDs: {new_game_states}")
        update_result = engine.update_matrix_from_new_game_states(matrix_id, new_game_states)
        print(f"Incremental update result: {update_result}")

        # Verify updated metrics
        with conn.session_scope() as session:
            updated_metric = session.query(AggregatedMetric).join(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id,
                MatrixCell.row_index == 0,
                MatrixCell.col_index == 1
            ).first()

            if updated_metric:
                # Get actual total games from database count
                matrix_cell = session.query(MatrixCell).filter(
                    MatrixCell.matrix_id == matrix_id,
                    MatrixCell.row_index == 0,
                    MatrixCell.col_index == 1
                ).first()
                actual_total_games = session.query(func.count(GameState.id)).filter(
                    GameState.cell_id == matrix_cell.id
                ).scalar() or 0

                print(f"Updated metrics - Equity: {updated_metric.equity:.4f}, EV: {updated_metric.ev:.2f}, Games: {actual_total_games}")

                # Verify the update
                expected_total_games = initial_games + 5
                expected_equity = (initial_equity * initial_games + 1.0 * 5) / expected_total_games  # All new games are wins

                actual_equity = float(updated_metric.equity)

                assert abs(actual_total_games - expected_total_games) < 1, f"Total games mismatch: {actual_total_games} vs {expected_total_games}"
                assert abs(actual_equity - expected_equity) < 0.01, f"Equity mismatch: {actual_equity} vs {expected_equity}"

                print("Incremental update calculations verified")
            else:
                print("No updated metrics found")
                assert False, "No updated metrics found"

        # Test status reporting
        status = engine.get_incremental_update_status(matrix_id)
        print(f"Matrix status: {status['coverage_percentage']:.1f}% coverage, {status['total_cells']} total cells")

        # All tests passed
        assert True

    finally:
        # Cleanup
        try:
            if 'conn' in locals():
                conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")