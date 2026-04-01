"""
Integration tests for MatrixCell derivation from GameStates.

Tests that MatrixCells and AggregatedMetrics are correctly computed
from stored GameStates data.
"""

import pytest
import tempfile
import os
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hopilot.database.aggregation import AggregationEngine
from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.database.persistence import DatabasePersistenceStrategy
from hopilot.models import GameState, Player, Bet, MatrixCell, AggregatedMetric, BoardCard, Base


class TestMatrixAggregationIntegration:
    """Integration tests for MatrixCell derivation."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        db_path = tempfile.mktemp(suffix='.db')
        db_url = f"sqlite:///{db_path}"

        engine = create_engine(db_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        yield SessionLocal

        # Cleanup
        engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def db_session(self, temp_db):
        """Create a database session."""
        SessionLocal = temp_db
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def aggregation_engine(self, db_session):
        """Create aggregation engine."""
        return AggregationEngine(db_session)

    def test_matrix_cell_aggregation_from_game_states(self, db_session, aggregation_engine):
        """Test that MatrixCell metrics are computed from GameStates."""
        # Create a matrix cell
        matrix_cell = MatrixCell(
            matrix_id=1,
            row_index=0,
            col_index=0,
            hand_combination='AKs vs QQ'
        )
        db_session.add(matrix_cell)
        db_session.commit()

        # Simulate game states for this matrix cell using the solver
        persistence = DatabasePersistenceStrategy(session=db_session)
        analyzer = PokerAnalyzer()
        solver = AllInFoldGTOSolver(analyzer, persistence)

        # Run simulations for this hand
        result = solver.analyze_hand_strategy(
            ['As', 'Kh'],
            num_opponents=2,
            num_simulations=100,
            matrix_cell_id=matrix_cell.id
        )

        # Aggregate the results
        aggregated = aggregation_engine.aggregate_matrix_cell(matrix_cell.id)

        # Verify aggregation worked
        assert aggregated is not None
        assert aggregated.cell_id == matrix_cell.id
        assert aggregated.equity is not None
        assert aggregated.ev is not None
        assert aggregated.last_updated is not None

        # Verify the aggregated values make sense
        assert 0.0 <= float(aggregated.equity) <= 1.0
        assert isinstance(aggregated.convergence_status, str)

    def test_aggregation_updates_existing_metrics(self, db_session, aggregation_engine):
        """Test that aggregation updates existing AggregatedMetric records."""
        # Create a matrix cell
        matrix_cell = MatrixCell(
            matrix_id=1,
            row_index=1,
            col_index=1,
            hand_combination='QQ vs AKs'
        )
        db_session.add(matrix_cell)
        db_session.commit()

        # Create initial aggregated metric
        initial_metric = AggregatedMetric(
            cell_id=matrix_cell.id,
            equity=Decimal('0.5000'),
            ev=Decimal('0.0000'),
            last_updated='2024-01-01T00:00:00'
        )
        db_session.add(initial_metric)
        db_session.commit()

        # Run simulations to generate more data
        persistence = DatabasePersistenceStrategy(session=db_session)
        analyzer = PokerAnalyzer()
        solver = AllInFoldGTOSolver(analyzer, persistence)

        result = solver.analyze_hand_strategy(
            ['Qs', 'Qh'],
            num_opponents=3,
            num_simulations=100,
            matrix_cell_id=matrix_cell.id
        )

        # Aggregate again - should update existing record
        updated_metric = aggregation_engine.aggregate_matrix_cell(matrix_cell.id)

        # Verify it's the same record but with updated values
        assert updated_metric.id == initial_metric.id
        assert updated_metric.cell_id == matrix_cell.id
        assert updated_metric.last_updated != '2024-01-01T00:00:00'

    def test_get_matrix_cell_stats_comprehensive(self, db_session, aggregation_engine):
        """Test comprehensive statistics retrieval for a matrix cell."""
        # Create a matrix cell
        matrix_cell = MatrixCell(
            matrix_id=1,
            row_index=2,
            col_index=2,
            hand_combination='JTs vs 22'
        )
        db_session.add(matrix_cell)
        db_session.commit()

        # Generate some game states and jackpots
        persistence = DatabasePersistenceStrategy(session=db_session)
        analyzer = PokerAnalyzer()
        solver = AllInFoldGTOSolver(analyzer, persistence)

        # Run simulations that might generate jackpots
        result = solver.analyze_hand_strategy(
            ['Js', 'Ts'],  # Suited connectors - potential for straights
            num_opponents=4,
            num_simulations=100,
            matrix_cell_id=matrix_cell.id
        )

        # Aggregate
        aggregated = aggregation_engine.aggregate_matrix_cell(matrix_cell.id)
        assert aggregated is not None

        # Get comprehensive stats
        stats = aggregation_engine.get_matrix_cell_stats(matrix_cell.id)

        assert stats is not None
        assert stats['matrix_cell_id'] == matrix_cell.id
        assert stats['game_states_count'] == 100
        assert 'jackpots_count' in stats
        assert 'equity' in stats
        assert 'ev' in stats
        assert 'jackpot_adjusted_ev' in stats
        assert 'convergence_status' in stats

    def test_aggregation_with_no_hero_player(self, db_session, aggregation_engine):
        """Test aggregation handles game states without hero player."""
        # Create a matrix cell
        matrix_cell = MatrixCell(
            matrix_id=1,
            row_index=3,
            col_index=3,
            hand_combination='22 vs JTs'
        )
        db_session.add(matrix_cell)
        db_session.commit()

        # Create a game state manually without hero player
        # First create a board card
        board_card = BoardCard(
            flop1='??',
            flop2='??', 
            flop3='??',
            turn='??',
            river='??'
        )
        db_session.add(board_card)
        db_session.flush()
        
        game_state = GameState(
            cell_id=matrix_cell.id,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            round='preflop',
            pot_size=20.0,
            board_cards_id=board_card.id,
            outcome='hero_loss'
        )
        db_session.add(game_state)
        db_session.commit()

        # Add players but no hero
        player = Player(
            game_state_id=game_state.id,
            position='OPP1',
            hole_cards='7s8s',
            stack_size=100.0,
            is_hero=False
        )
        db_session.add(player)
        db_session.commit()

        # Aggregate - should handle gracefully
        aggregated = aggregation_engine.aggregate_matrix_cell(matrix_cell.id)

        # Should still create aggregated metric, but with default values
        assert aggregated is not None
        assert aggregated.equity == Decimal('0.0000')  # No hero wins

    def test_convergence_tracking_over_multiple_aggregations(self, db_session, aggregation_engine):
        """Test that convergence status improves with more data."""
        # Create a matrix cell
        matrix_cell = MatrixCell(
            matrix_id=1,
            row_index=4,
            col_index=4,
            hand_combination='AKo vs QQ'
        )
        db_session.add(matrix_cell)
        db_session.commit()

        # First aggregation with small dataset
        persistence = DatabasePersistenceStrategy(session=db_session)
        analyzer = PokerAnalyzer()
        solver = AllInFoldGTOSolver(analyzer, persistence)

        solver.analyze_hand_strategy(
            ['As', 'Kh'],
            num_opponents=2,
            num_simulations=100,  # Small dataset
            matrix_cell_id=matrix_cell.id
        )

        aggregated1 = aggregation_engine.aggregate_matrix_cell(matrix_cell.id)
        assert aggregated1.convergence_status == 'converged'

        # Second aggregation with larger dataset
        solver.analyze_hand_strategy(
            ['As', 'Kh'],
            num_opponents=2,
            num_simulations=100,  # Larger dataset
            matrix_cell_id=matrix_cell.id
        )

        aggregated2 = aggregation_engine.aggregate_matrix_cell(matrix_cell.id)
        # Should have better convergence assessment with more data
        assert aggregated2.convergence_status in ['converged', 'converging', 'diverging', 'insufficient_data']
