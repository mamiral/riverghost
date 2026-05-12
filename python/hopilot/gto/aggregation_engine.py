"""
Aggregation Engine for computing MatrixCells from GameStates.

This module implements the aggregation logic that derives MatrixCells
and AggregatedMetrics from stored GameStates data, restoring the
intended GameStates-first architecture.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from sqlalchemy import text, func, case, and_, or_, asc
from sqlalchemy.orm import Session, selectinload

from hopilot.database import DatabaseConnection
from hopilot.gto.aof_hand_matrix import hand_coordinates_from_hole_cards
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
        bb: float,
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
            bb: Big blind amount for posted blind adjustment
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

                # Derive game state membership from hero hole cards and matrix cell coordinates
                candidate_game_states = (
                    session.query(GameState)
                    .options(selectinload(GameState.players))
                    .order_by(asc(GameState.timestamp))
                    .all()
                )

                game_states = [
                    gs for gs in candidate_game_states
                    if self._game_state_matches_cell(gs, matrix_cell.row_index, matrix_cell.col_index)
                ]

                total_games = len(game_states)
                if total_games < min_samples:
                    logger.info(f"Insufficient samples for cell {matrix_cell.id}: {total_games} < {min_samples}")
                    return None

                equity, avg_ev = self._calculate_aggregate_metrics(game_states)

                jackpots = session.query(Jackpot).filter(Jackpot.game_state_id.in_([gs.id for gs in game_states])).all()
                games_with_jackpots = len({jp.game_state_id for jp in jackpots})
                avg_jackpot_payout = float(sum((jp.payout_amount or 0) for jp in jackpots) / len(jackpots)) if jackpots else 0.0
                total_jackpot_payout = float(sum((jp.payout_amount or 0) for jp in jackpots))

                # Calculate jackpot frequency
                jackpot_frequency = games_with_jackpots / total_games if total_games > 0 else 0.0

                # Calculate jackpot-adjusted EV
                # Method 1: Add expected jackpot winnings to base EV
                expected_jackpot_winnings = jackpot_frequency * avg_jackpot_payout
                jackpot_adjusted_ev = avg_ev + expected_jackpot_winnings

                # Adjust for posted blind (SB posts 0.5 * bb)
                posted_blind = 0.5 * bb
                adjusted_ev = avg_ev - posted_blind
                jackpot_adjusted_ev = jackpot_adjusted_ev - posted_blind

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
                    'ev': adjusted_ev,
                    'raw_ev': avg_ev,  # Keep raw EV for debugging
                    'jackpot_adjusted_ev': jackpot_adjusted_ev,
                    'jackpot_frequency': jackpot_frequency,
                    'avg_jackpot_payout': avg_jackpot_payout,
                    'total_jackpot_payout': total_jackpot_payout,
                    'games_with_jackpots': games_with_jackpots,
                    'posted_blind': posted_blind,
                    'convergence_status': convergence_status,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }

                logger.info(
                    f"Computed aggregation for cell {matrix_cell.id}: {total_games} games, "
                    f"equity={equity:.4f}, EV={avg_ev:.2f}, jackpot_freq={jackpot_frequency:.4f}, "
                    f"jackpot_adjusted_EV={jackpot_adjusted_ev:.2f}"
                )
                return result

    def _game_state_matches_cell(self, game_state: GameState, row_idx: int, col_idx: int) -> bool:
        hero_player = next((player for player in game_state.players if player.is_hero), None)
        if hero_player is None:
            return False

        try:
            row, col = hand_coordinates_from_hole_cards(hero_player.hole_cards)
        except Exception:
            return False

        return row == row_idx and col == col_idx

    def _calculate_aggregate_metrics(self, game_states: List[GameState]) -> tuple[float, float]:
        total_games = len(game_states)
        if total_games == 0:
            return 0.0, 0.0

        win_score = 0.0
        ev_sum = 0.0

        for gs in game_states:
            if gs.outcome in ['win', 'jackpot_win']:
                win_score += 1.0
                ev_sum += float(gs.pot_size)
            elif gs.outcome in ['loss', 'jackpot_loss']:
                ev_sum -= float(gs.pot_size)
            elif gs.outcome in ['tie', 'jackpot_tie']:
                win_score += 0.5

        equity = win_score / total_games
        avg_ev = ev_sum / total_games
        return equity, avg_ev

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
                JOIN players p ON p.game_state_id = gs.id
                WHERE p.is_hero = 1
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
                "Consider adding indexes on players.game_state_id and game_states.timestamp for better aggregation performance"
            )

        if analysis['full_table_scans'] > 0:
            analysis['recommendations'].append(
                f"Query performs {analysis['full_table_scans']} table scan(s) - may need optimization"
            )

        return analysis
