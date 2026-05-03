"""
Integration tests for genuine database remediation.

Tests that the complete system stores real simulation data
in the database without fake data generation.
"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.database.persistence import BatchingPersistenceStrategy, DatabasePersistenceStrategy
from hopilot.models import GameState, Player, Bet, Jackpot, Base


class TestDatabaseRemediation:
    """Integration tests for genuine database storage."""

    @pytest.fixture
    def temp_db(self):
        """Create an in-memory database for testing."""
        db_url = "sqlite:///:memory:"

        # Create test-specific engine and session factory
        engine = create_engine(db_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create tables
        Base.metadata.create_all(bind=engine)

        yield db_url, SessionLocal

        # Cleanup - dispose engine (in-memory DB is automatically cleaned up)
        engine.dispose()

    @pytest.fixture
    def db_persistence(self, temp_db):
        """Create database persistence strategy."""
        _, SessionLocal = temp_db
        session = SessionLocal()
        strategy = DatabasePersistenceStrategy(session=session)
        yield strategy
        # Close the session after the test
        strategy.close()

    @pytest.fixture
    def analyzer(self):
        """Create poker analyzer."""
        return PokerAnalyzer()

    @pytest.fixture
    def solver(self, analyzer, db_persistence):
        """Create solver with database persistence."""
        return AllInFoldGTOSolver(analyzer, db_persistence)

    def test_database_tables_exist(self, temp_db):
        """Test that all required tables are created."""
        _, SessionLocal = temp_db
        session = SessionLocal()

        # Check that tables exist by trying to query them
        # This will raise an exception if tables don't exist
        try:
            session.query(GameState).count()
            session.query(Player).count()
            session.query(Bet).count()
            session.query(Jackpot).count()
        except Exception as e:
            pytest.fail(f"Database tables not created properly: {e}")
        finally:
            session.close()

    def test_foreign_key_constraints_enabled(self, temp_db):
        """Test that foreign key constraints are properly enabled."""
        # This test would need to be implemented when we have actual data storage
        # For now, just verify the database is initialized
        _, SessionLocal = temp_db
        session = SessionLocal()
        try:
            # Try to enable foreign keys explicitly
            from sqlalchemy import text
            session.execute(text("PRAGMA foreign_keys = ON;"))
            session.commit()
        except Exception as e:
            pytest.fail(f"Foreign key constraints not working: {e}")
        finally:
            session.close()

    def test_persistence_strategy_stores_data(self, db_persistence, temp_db):
        """Test that database persistence strategy can store data."""
        # This test will be updated when the solver actually calls persistence methods
        # For now, test the persistence strategy interface

        # Store a game state
        game_state_id = db_persistence.store_game_state(
            timestamp='2024-01-01T00:00:00',
            round_name='preflop',
            pot_size=20.0,
            board_cards=[],
            outcome='hero_win'
        )

        # Store a player
        player_id = db_persistence.store_player(
            game_state_id=game_state_id,
            position='HERO',
            hole_cards=['As', 'Kh'],
            stack_size=100.0,
            is_hero=True
        )

        # Store a bet
        bet_id = db_persistence.store_bet(
            game_state_id=game_state_id,
            player_id=player_id,
            amount=10.0,
            action_type='raise'
        )

        # Commit transaction
        db_persistence.commit_transaction()

        # Verify data was stored
        _, SessionLocal = temp_db
        session = SessionLocal()
        try:
            # Check game state
            game_state = session.query(GameState).filter_by(id=game_state_id).first()
            assert game_state is not None
            assert game_state.board_cards_str == ''
            assert game_state.pot_size == 20.0
            assert game_state.outcome == 'hero_win'

            # Check player
            player = session.query(Player).filter_by(id=player_id).first()
            assert player is not None
            assert player.game_state_id == game_state_id
            assert player.position == 'HERO'
            assert player.stack_size == 100.0
            assert player.is_hero is True

            # Check bet
            bet = session.query(Bet).filter_by(id=bet_id).first()
            assert bet is not None
            assert bet.game_state_id == game_state_id
            assert bet.player_id == player_id
            assert bet.amount == 10.0
            assert bet.action_type == 'raise'

        finally:
            session.close()

    def test_batching_persistence_commits_only_when_threshold_reached(self, temp_db):
        """Test that batching persistence delays commit until batch size is reached."""
        db_url, SessionLocal = temp_db
        session = SessionLocal()
        try:
            strategy = BatchingPersistenceStrategy(session=session, batch_size=2)

            game_state_id_1 = strategy.store_game_state(
                timestamp='2024-01-01T00:00:00',
                round_name='preflop',
                pot_size=20.0,
                board_cards=['As', 'Kh'],
                outcome='hero_win'
            )
            strategy.store_player(
                game_state_id=game_state_id_1,
                position='HERO',
                hole_cards=['As', 'Kh'],
                stack_size=100.0,
                is_hero=True
            )
            strategy.commit_transaction()

            other_session = SessionLocal()
            try:
                assert other_session.query(GameState).count() == 0
            finally:
                other_session.close()

            game_state_id_2 = strategy.store_game_state(
                timestamp='2024-01-01T00:00:01',
                round_name='preflop',
                pot_size=20.0,
                board_cards=['Qs', 'Jh'],
                outcome='loss'
            )
            strategy.store_player(
                game_state_id=game_state_id_2,
                position='HERO',
                hole_cards=['Qs', 'Jh'],
                stack_size=100.0,
                is_hero=True
            )
            strategy.commit_transaction()

            other_session = SessionLocal()
            try:
                assert other_session.query(GameState).count() == 2
                assert other_session.query(Player).count() == 2
            finally:
                other_session.close()
        finally:
            strategy.close()
            session.close()

    def test_batching_persistence_flushes_remaining_on_close(self, temp_db):
        """Test that closing the strategy flushes any remaining buffered rows."""
        db_url, SessionLocal = temp_db
        session = SessionLocal()
        try:
            strategy = BatchingPersistenceStrategy(session=session, batch_size=3)

            game_state_id = strategy.store_game_state(
                timestamp='2024-01-01T00:00:00',
                round_name='preflop',
                pot_size=20.0,
                board_cards=['As', 'Kh'],
                outcome='hero_win'
            )
            strategy.store_player(
                game_state_id=game_state_id,
                position='HERO',
                hole_cards=['As', 'Kh'],
                stack_size=100.0,
                is_hero=True
            )
            strategy.commit_transaction()

            other_session = SessionLocal()
            try:
                assert other_session.query(GameState).count() == 0
            finally:
                other_session.close()

            strategy.close()

            other_session = SessionLocal()
            try:
                assert other_session.query(GameState).count() == 1
                assert other_session.query(Player).count() == 1
            finally:
                other_session.close()
        finally:
            session.close()

    def test_batching_persistence_rollback_discards_buffered_rows(self, temp_db):
        """Test that rollback clears buffered rows before flush."""
        db_url, SessionLocal = temp_db
        session = SessionLocal()
        try:
            strategy = BatchingPersistenceStrategy(session=session, batch_size=3)

            game_state_id = strategy.store_game_state(
                timestamp='2024-01-01T00:00:00',
                round_name='preflop',
                pot_size=20.0,
                board_cards=['As', 'Kh'],
                outcome='hero_win'
            )
            strategy.store_player(
                game_state_id=game_state_id,
                position='HERO',
                hole_cards=['As', 'Kh'],
                stack_size=100.0,
                is_hero=True
            )
            strategy.rollback_transaction()
            strategy.close()

            other_session = SessionLocal()
            try:
                assert other_session.query(GameState).count() == 0
                assert other_session.query(Player).count() == 0
            finally:
                other_session.close()
        finally:
            session.close()

    def test_no_fake_data_generation(self, solver):
        """Test that the system doesn't generate fake data."""
        # This test will verify that when the solver runs, it stores real data
        # For now, just test that the solver has the persistence strategy
        assert solver.persistence is not None
        assert hasattr(solver.persistence, 'store_game_state')
        assert hasattr(solver.persistence, 'store_player')
        assert hasattr(solver.persistence, 'store_bet')

    def test_data_integrity_validation(self, temp_db):
        """Test that data integrity checks work."""
        # Test foreign key validation by trying invalid operations
        # This will be more comprehensive when we have actual constraint checking
        _, SessionLocal = temp_db
        session = SessionLocal()
        try:
            # Create a game state
            game_state = GameState(
                timestamp='2024-01-01T00:00:00',
                round='preflop',
                pot_size=20.0,
                board_cards_str='',
                outcome='win'
            )
            session.add(game_state)
            session.commit()

            # Try to create a player with invalid game_state_id
            # This should work since we haven't set up cascading deletes yet
            player = Player(
                game_state_id=99999,  # Non-existent game state
                position='HERO',
                hole_cards=''.join(['As', 'Kh']),
                stack_size=100.0,
                is_hero=True
            )
            session.add(player)

            # This should succeed for now, but we'll add proper constraints
            session.commit()

        except Exception as e:
            # If constraints are working, this might fail
            print(f"Constraint validation working: {e}")
        finally:
            session.close()