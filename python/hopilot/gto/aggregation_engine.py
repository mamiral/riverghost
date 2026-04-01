"""
Aggregation Engine for computing MatrixCells from GameStates.

This module implements the aggregation logic that derives MatrixCells
and AggregatedMetrics from stored GameStates data, restoring the
intended GameStates-first architecture.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from sqlalchemy import text, func, case, and_, or_
from sqlalchemy.orm import Session

import importlib.util
spec = importlib.util.spec_from_file_location("database_module", "hopilot/database.py")
database_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database_module)
DatabaseConnection = database_module.DatabaseConnection
from hopilot.models import GameState, MatrixCell, AggregatedMetric, Simulation, HandMatrix, Jackpot
from hopilot.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


class AggregationEngine:
    """
    Engine for computing MatrixCells and AggregatedMetrics from GameStates.

    This class implements the aggregation queries that derive matrix cells
    from individual game state data, providing the foundation for the
    GameStates-first architecture.
    """

    def __init__(self, database_url: str):
        """
        Initialize the aggregation engine.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.performance_monitor = PerformanceMonitor()

    def compute_matrix_cell_from_game_states(
        self,
        matrix_id: int,
        row_index: int,
        col_index: int,
        min_samples: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Compute aggregated metrics for a specific matrix cell from GameStates.

        This is the core aggregation query that groups GameStates by matrix cell
        and computes statistical metrics.

        Args:
            matrix_id: Hand matrix ID
            row_index: Row index in the matrix
            col_index: Column index in the matrix
            min_samples: Minimum number of game states required for aggregation

        Returns:
            Dictionary with aggregated metrics, or None if insufficient data
        """
        with self.performance_monitor.track_operation("compute_matrix_cell_aggregation"):
            with self.db_connection.session_scope() as session:
                # First, find the MatrixCell for this position
                matrix_cell = session.query(MatrixCell).filter(
                    and_(
                        MatrixCell.matrix_id == matrix_id,
                        MatrixCell.row_index == row_index,
                        MatrixCell.col_index == col_index
                    )
                ).first()

                if not matrix_cell:
                    logger.warning(f"No MatrixCell found for matrix_id={matrix_id}, row={row_index}, col={col_index}")
                    return None

                # Count total game states for this cell
                game_states_count = session.query(func.count(GameState.id)).filter(
                    GameState.cell_id == matrix_cell.id
                ).scalar()

                if game_states_count < min_samples:
                    logger.info(f"Insufficient samples for cell {matrix_cell.id}: {game_states_count} < {min_samples}")
                    return None

                # Core aggregation query with jackpot integration
                # First, get basic game state aggregations
                game_state_agg = session.query(
                    func.count(GameState.id).label('total_games'),
                    func.avg(
                        case(
                            (GameState.outcome.in_(['win', 'jackpot_win']), 1.0),
                            (GameState.outcome.in_(['loss', 'jackpot_loss']), 0.0),
                            (GameState.outcome.in_(['tie', 'jackpot_tie']), 0.5),
                            else_=0.0
                        )
                    ).label('equity'),
                    func.avg(
                        case(
                            (GameState.outcome.in_(['win', 'jackpot_win']), GameState.pot_size),
                            (GameState.outcome.in_(['loss', 'jackpot_loss']), -GameState.pot_size),
                            (GameState.outcome.in_(['tie', 'jackpot_tie']), 0.0),
                            else_=0.0
                        )
                    ).label('avg_ev')
                ).filter(GameState.cell_id == matrix_cell.id).first()

                # Get jackpot statistics by joining with jackpot table
                jackpot_agg = session.query(
                    func.count(func.distinct(GameState.id)).label('games_with_jackpots'),
                    func.avg(Jackpot.payout_amount).label('avg_jackpot_payout'),
                    func.sum(Jackpot.payout_amount).label('total_jackpot_payout')
                ).join(GameState, Jackpot.game_state_id == GameState.id
                ).filter(GameState.cell_id == matrix_cell.id).first()

                if not game_state_agg:
                    return None

                # Extract results
                total_games = game_state_agg.total_games
                equity = float(game_state_agg.equity) if game_state_agg.equity else 0.0
                avg_ev = float(game_state_agg.avg_ev) if game_state_agg.avg_ev else 0.0

                # Extract jackpot results
                games_with_jackpots = jackpot_agg.games_with_jackpots if jackpot_agg and jackpot_agg.games_with_jackpots else 0
                avg_jackpot_payout = float(jackpot_agg.avg_jackpot_payout) if jackpot_agg and jackpot_agg.avg_jackpot_payout else 0.0
                total_jackpot_payout = float(jackpot_agg.total_jackpot_payout) if jackpot_agg and jackpot_agg.total_jackpot_payout else 0.0

                # Calculate jackpot frequency
                jackpot_frequency = games_with_jackpots / total_games if total_games > 0 else 0.0

                # Calculate jackpot-adjusted EV
                # Method 1: Add expected jackpot winnings to base EV
                expected_jackpot_winnings = jackpot_frequency * avg_jackpot_payout
                jackpot_adjusted_ev = avg_ev + expected_jackpot_winnings

                # Alternative Method 2: Include jackpots in the EV calculation directly
                # This would require recalculating EV to include jackpot payouts in outcomes
                # For now, we use Method 1 as it's more conservative and clear

                # Convergence assessment
                if total_games >= 10000:
                    convergence_status = 'converged'
                elif total_games >= 1000:
                    convergence_status = 'converging'
                else:
                    convergence_status = 'insufficient_samples'

                # Prepare result dictionary
                result = {
                    'matrix_cell_id': matrix_cell.id,
                    'total_games': total_games,
                    'equity': equity,
                    'win_probability': equity,  # Alias for compatibility
                    'ev': avg_ev,
                    'jackpot_adjusted_ev': jackpot_adjusted_ev,
                    'jackpot_frequency': jackpot_frequency,
                    'avg_jackpot_payout': avg_jackpot_payout,
                    'total_jackpot_payout': total_jackpot_payout,
                    'games_with_jackpots': games_with_jackpots,
                    'convergence_status': convergence_status,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }

                logger.info(
                    f"Computed aggregation for cell {matrix_cell.id}: {total_games} games, "
                    f"equity={equity:.4f}, EV={avg_ev:.2f}, jackpot_freq={jackpot_frequency:.4f}, "
                    f"jackpot_adjusted_EV={jackpot_adjusted_ev:.2f}"
                )
                return result

    def get_aggregation_query_plan(
        self,
        matrix_id: int,
        row_index: int,
        col_index: int
    ) -> Dict[str, Any]:
        """
        Get the query execution plan for aggregation queries.

        This helps analyze performance and identify optimization opportunities.

        Args:
            matrix_id: Hand matrix ID
            row_index: Row index
            col_index: Column index

        Returns:
            Query plan analysis
        """
        with self.db_connection.session_scope() as session:
            # Get MatrixCell ID first
            matrix_cell = session.query(MatrixCell).filter(
                and_(
                    MatrixCell.matrix_id == matrix_id,
                    MatrixCell.row_index == row_index,
                    MatrixCell.col_index == col_index
                )
            ).first()

            if not matrix_cell:
                return {'error': 'MatrixCell not found'}

            # Analyze the aggregation query
            explain_query = text("""
                EXPLAIN QUERY PLAN
                SELECT
                    COUNT(gs.id) as total_games,
                    AVG(CASE
                        WHEN gs.outcome IN ('win', 'jackpot_win') THEN 1.0
                        WHEN gs.outcome IN ('loss', 'jackpot_loss') THEN 0.0
                        WHEN gs.outcome IN ('tie', 'jackpot_tie') THEN 0.5
                        ELSE 0.0
                    END) as equity,
                    AVG(CASE
                        WHEN gs.outcome IN ('win', 'jackpot_win') THEN gs.pot_size
                        WHEN gs.outcome IN ('loss', 'jackpot_loss') THEN -gs.pot_size
                        WHEN gs.outcome IN ('tie', 'jackpot_tie') THEN 0.0
                        ELSE 0.0
                    END) as avg_ev
                FROM game_states gs
                WHERE gs.cell_id = :cell_id
            """)

            result = session.execute(explain_query, {'cell_id': matrix_cell.id})
            plan_rows = result.fetchall()

            return {
                'query_plan': [{'detail': str(row)} for row in plan_rows],
                'matrix_cell_id': matrix_cell.id,
                'analysis': self._analyze_query_plan(plan_rows)
            }

    def _analyze_query_plan(self, plan_rows: List) -> Dict[str, Any]:
        """
        Analyze query execution plan for performance insights.

        Args:
            plan_rows: Raw query plan rows from EXPLAIN QUERY PLAN

        Returns:
            Performance analysis
        """
        analysis = {
            'uses_indexes': False,
            'full_table_scans': 0,
            'estimated_cost': 'unknown',
            'recommendations': []
        }

        for row in plan_rows:
            detail = row.detail if hasattr(row, 'detail') else str(row)

            # Check for index usage
            if 'INDEX' in detail.upper() or 'USING INDEX' in detail.upper():
                analysis['uses_indexes'] = True

            # Check for table scans
            if 'SCAN' in detail.upper():
                analysis['full_table_scans'] += 1

        # Generate recommendations
        if not analysis['uses_indexes']:
            analysis['recommendations'].append(
                "Consider adding indexes on game_states.cell_id for better aggregation performance"
            )

        if analysis['full_table_scans'] > 0:
            analysis['recommendations'].append(
                f"Query performs {analysis['full_table_scans']} table scan(s) - may need optimization"
            )

        return analysis
