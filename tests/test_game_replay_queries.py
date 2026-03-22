import pytest
import sys
import os

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.game_replay_queries import GameReplayQueryEngine
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.matrix_cells_derivation import MatrixCellsDerivationEngine

def test_game_replay_queries():
    """Test the game replay query engine."""

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
        replay_engine = GameReplayQueryEngine(db_url)
        derivation_engine = MatrixCellsDerivationEngine(db_url)

        # Create test data
        sim_params = '{"num_simulations": 1000, "matrix_size": "13x13", "game_type": "NLHE"}'
        sim_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(sim_id)

        # Create board cards
        board_id = repo.create_board_card({
            'flop1': 'As', 'flop2': 'Ks', 'flop3': 'Qs',
            'turn': 'Js', 'river': 'Ts'
        })

        # Create MatrixCell and GameState
        hand_combo = "AA vs AK"
        cell_id = derivation_engine._ensure_matrix_cell_exists(matrix_id, 0, 1, hand_combo)

        # Create GameState with detailed data
        gs_data = {
            'cell_id': cell_id,
            'pot_size': 1000,
            'board_cards_id': board_id,
            'round': 'preflop',  # Must be preflop for AOF games
            'outcome': 'win'
        }
        gs_id = repo.create_game_state(gs_data)

        # Note: Skipping bet creation for now since it requires a player
        # In a real scenario, bets would be created during simulation

        # Test replay statistics
        stats = replay_engine.get_replay_statistics(matrix_id)
        assert stats['total_games'] == 1
        assert stats['unique_hand_combinations'] == 1
        assert stats['matrix_id'] == matrix_id

        # Test timeline summary
        summary = replay_engine.get_game_timeline_summary(gs_id)
        assert summary is not None
        assert summary['game_state_id'] == gs_id
        assert summary['outcome'] == 'win'
        assert summary['pot_size'] == 1000.0
        assert summary['event_counts']['bets'] == 0  # No bets created
        assert summary['event_counts']['board_cards'] == 5

        # Test full replay
        replay = replay_engine.replay_game_sequence(gs_id)
        assert replay is not None
        assert replay['game_state_id'] == gs_id
        assert replay['final_outcome'] == 'win'
        assert replay['final_pot_size'] == 1000.0
        assert len(replay['sequence']) >= 4  # At least game_start, flop, turn, river, game_end

        # Check sequence structure
        events = replay['sequence']
        event_types = [e['event_type'] for e in events]
        assert 'game_start' in event_types
        assert 'board_reveal' in event_types
        assert 'game_end' in event_types

        # Test hand combination filtering
        hand_replays = replay_engine.replay_games_by_hand_combination(matrix_id, hand_combo, limit=5)
        assert len(hand_replays) == 1
        assert hand_replays[0]['game_state_id'] == gs_id

    finally:
        # Cleanup
        try:
            if 'conn' in locals():
                conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception as e:
            pass  # Ignore cleanup errors in tests