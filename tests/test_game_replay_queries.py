import pytest
import sys
import os
from datetime import datetime, timezone

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.game_replay_queries import GameReplayQueryEngine
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.replay_query_service import ReplayQueryService
from hopilot.models import GameState, Player

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

        # Create raw GameState and players for replay
        with repo.connection.session_scope() as session:
            game_state = GameState(
                timestamp=datetime.now(timezone.utc),
                round='preflop',
                pot_size=1000,
                board_cards_str='As,Ks,Qs,Js,Ts',
                outcome='win',
            )
            session.add(game_state)
            session.flush()

            session.add(Player(
                game_state_id=game_state.id,
                position='UTG',
                hole_cards='AsAh',
                stack_size=100.0,
                is_hero=True,
            ))
            session.add(Player(
                game_state_id=game_state.id,
                position='BTN',
                hole_cards='KdKh',
                stack_size=100.0,
                is_hero=False,
            ))
            gs_id = game_state.id

        # Note: Skipping bet creation for now since it requires a player
        # In a real scenario, bets would be created during simulation

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


def test_replay_query_service_statuses():
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test_db_status')
    os.makedirs(temp_dir, exist_ok=True)
    db_path = os.path.join(temp_dir, 'test.db')
    db_url = f'sqlite:///{db_path}'

    try:
        conn = DatabaseConnection(db_url)
        conn.create_tables()
        repo = DatabaseRepository(db_url)
        service = ReplayQueryService(repo)

        with repo.connection.session_scope() as session:
            game_state = GameState(
                timestamp=datetime.now(timezone.utc),
                round='preflop',
                pot_size=20.0,
                board_cards_str='As,Ks,Qd',
                outcome='hero_win',
            )
            session.add(game_state)
            session.flush()
            session.add(Player(
                game_state_id=game_state.id,
                position='UTG',
                hole_cards='AsAh',
                stack_size=100.0,
                is_hero=True,
            ))
            session.add(Player(
                game_state_id=game_state.id,
                position='BTN',
                hole_cards='KdKh',
                stack_size=100.0,
                is_hero=False,
            ))

        readable = service.replay_game_state(game_state.id)
        assert readable['status'] == 'AVAILABLE'
        assert readable['game_state_id'] == game_state.id
        assert readable['board_cards'] == ['As', 'Ks', 'Qd']
        assert any(player['is_hero'] for player in readable['players'])

        not_found = service.replay_game_state(game_state.id + 1)
        assert not_found['status'] == 'NOT_FOUND'

        with repo.connection.session_scope() as session:
            missing_players = GameState(
                timestamp=datetime.now(timezone.utc),
                round='preflop',
                pot_size=15.0,
                board_cards_str='Ah,Kh,Qh',
                outcome='hero_loss',
            )
            session.add(missing_players)
            session.flush()
            missing_id = missing_players.id

        no_players = service.replay_game_state(missing_id)
        assert no_players['status'] == 'UNREADABLE'
        assert 'Missing required Player rows' in no_players['status_message']

    finally:
        try:
            if 'conn' in locals():
                conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception:
            pass


def test_replay_query_service_empty_board_cards_str():
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test_db_empty')
    os.makedirs(temp_dir, exist_ok=True)
    db_path = os.path.join(temp_dir, 'test.db')
    db_url = f'sqlite:///{db_path}'

    try:
        conn = DatabaseConnection(db_url)
        conn.create_tables()
        repo = DatabaseRepository(db_url)
        service = ReplayQueryService(repo)

        with repo.connection.session_scope() as session:
            game_state = GameState(
                timestamp=datetime.now(timezone.utc),
                round='preflop',
                pot_size=50.0,
                board_cards_str='',
                outcome='hero_loss',
            )
            session.add(game_state)
            session.flush()
            session.add(Player(
                game_state_id=game_state.id,
                position='UTG',
                hole_cards='AsAh',
                stack_size=100.0,
                is_hero=True,
            ))
            session.add(Player(
                game_state_id=game_state.id,
                position='BTN',
                hole_cards='KdKh',
                stack_size=100.0,
                is_hero=False,
            ))

        result = service.replay_game_state(game_state.id)
        assert result['status'] == 'AVAILABLE'
        assert result['board_cards'] == []
        assert result['sequence'][0]['event_type'] == 'game_start'
        assert result['sequence'][-1]['event_type'] == 'game_end'

    finally:
        try:
            if 'conn' in locals():
                conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception:
            pass


def test_game_replay_engine_delegates_to_truthful_service():
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test_db_delegate')
    os.makedirs(temp_dir, exist_ok=True)
    db_path = os.path.join(temp_dir, 'test.db')
    db_url = f'sqlite:///{db_path}'

    try:
        conn = DatabaseConnection(db_url)
        conn.create_tables()
        repo = DatabaseRepository(db_url)
        engine = GameReplayQueryEngine(db_url)

        with repo.connection.session_scope() as session:
            game_state = GameState(
                timestamp=datetime.now(timezone.utc),
                round='preflop',
                pot_size=40.0,
                board_cards_str='As,Ks',
                outcome='hero_win',
            )
            session.add(game_state)
            session.flush()
            session.add(Player(
                game_state_id=game_state.id,
                position='UTG',
                hole_cards='AsAh',
                stack_size=100.0,
                is_hero=True,
            ))
            session.add(Player(
                game_state_id=game_state.id,
                position='BTN',
                hole_cards='KdKh',
                stack_size=100.0,
                is_hero=False,
            ))

        replay = engine.replay_game_sequence(game_state.id)
        assert replay is not None
        assert replay['game_state_id'] == game_state.id
        assert replay['final_outcome'] == 'hero_win'
        assert replay['final_pot_size'] == 40.0
        assert isinstance(replay['sequence'], list)

    finally:
        try:
            if 'conn' in locals():
                conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception:
            pass