#!/usr/bin/env python3
"""
Convergence Analysis Queries.

This module implements time-series queries for equity progression analysis,
tracking how poker hand equity converges as more simulation samples are added.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy import text, func, and_, or_, asc, desc, case, cast, Integer
from sqlalchemy.orm import Session, selectinload

from hopilot.database import DatabaseConnection
from hopilot.gto.aof_hand_matrix import hand_coordinates_from_hole_cards
from hopilot.models import GameState, MatrixCell, AggregatedMetric, HandMatrix
from hopilot.performance_monitor import PerformanceMonitor
from hopilot.gto.query_cache import cached_query

logger = logging.getLogger(__name__)


class ConvergenceAnalysisQueries:
    """
    Engine for analyzing equity convergence over time.

    This class provides time-series analysis of how poker hand equity
    converges as more simulation samples are accumulated.
    """

    def __init__(self, database_url: str):
        """
        Initialize the convergence analysis queries engine.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.performance_monitor = PerformanceMonitor()

    @cached_query(ttl=600)  # Cache for 10 minutes
    def get_equity_convergence_series(
        self,
        matrix_id: int,
        row_idx: int,
        col_idx: int,
        sample_intervals: Optional[List[int]] = None,
        min_samples: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get equity convergence time series for a specific matrix cell.

        Args:
            matrix_id: Hand matrix ID
            row_idx: Row index in the matrix
            col_idx: Column index in the matrix
            sample_intervals: List of sample counts to analyze (e.g., [100, 500, 1000, 5000])

        Returns:
            Time series data with equity values at different sample sizes
        """
        if sample_intervals is None:
            sample_intervals = [100, 250, 500, 1000, 2500, 5000, 10000]

        with self.performance_monitor.track_operation("equity_convergence_series"):
            with self.db_connection.session_scope() as session:
                # Find the MatrixCell
                matrix_cell = session.query(MatrixCell).filter(
                    and_(
                        MatrixCell.matrix_id == matrix_id,
                        MatrixCell.row_index == row_idx,
                        MatrixCell.col_index == col_idx
                    )
                ).first()

                if not matrix_cell:
                    logger.warning(f"No MatrixCell found for matrix_id={matrix_id}, row={row_idx}, col={col_idx}")
                    return None

                # Get all raw GameStates ordered by timestamp and derive cell membership from hero hole cards.
                game_states = (
                    session.query(GameState)
                    .options(selectinload(GameState.players))
                    .order_by(asc(GameState.timestamp))
                    .all()
                )

                game_states = [
                    gs for gs in game_states
                    if self._game_state_matches_cell(gs, matrix_cell.row_index, matrix_cell.col_index)
                ]

                if min_samples is not None and len(game_states) < min_samples:
                    logger.warning(f"Insufficient samples for minimum requirement: {len(game_states)} < {min_samples}")
                    return None

                if len(game_states) < min(sample_intervals):
                    logger.warning(f"Insufficient samples: {len(game_states)} < {min(sample_intervals)}")
                    return None

                # Calculate equity at each sample interval
                convergence_points = []

                for interval in sample_intervals:
                    if interval > len(game_states):
                        break

                    # Take the first 'interval' number of game states
                    subset = game_states[:interval]

                    # Calculate equity for this subset
                    equity = self._calculate_equity_for_subset(subset)

                    convergence_points.append({
                        'sample_count': interval,
                        'equity': equity,
                        'timestamp': subset[-1].timestamp.isoformat() if subset[-1].timestamp else None
                    })

                return {
                    'matrix_id': matrix_id,
                    'row_idx': row_idx,
                    'col_idx': col_idx,
                    'hand_combination': matrix_cell.hand_combination,
                    'total_samples': len(game_states),
                    'convergence_series': convergence_points,
                    'final_equity': convergence_points[-1]['equity'] if convergence_points else None
                }

    def _game_state_matches_cell(self, game_state: GameState, row_idx: int, col_idx: int) -> bool:
        hero_player = next((player for player in game_state.players if player.is_hero), None)
        if hero_player is None:
            return False

        try:
            row, col = hand_coordinates_from_hole_cards(hero_player.hole_cards)
        except ValueError:
            return False

        return row == row_idx and col == col_idx

    @cached_query(ttl=600)  # Cache for 10 minutes
    def get_convergence_statistics(
        self,
        matrix_id: int,
        min_samples: int = 1000
    ) -> Dict[str, Any]:
        """
        Get convergence statistics for all cells in a matrix.

        Args:
            matrix_id: Hand matrix ID
            min_samples: Minimum samples required for analysis

        Returns:
            Statistics about convergence across the matrix
        """
        with self.performance_monitor.track_operation("convergence_statistics"):
            with self.db_connection.session_scope() as session:
                cells = session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).all()

                convergence_stats = []

                for cell in cells:
                    series = self.get_equity_convergence_series(
                        matrix_id,
                        cell.row_index,
                        cell.col_index,
                        sample_intervals=[100, 500, 1000, min_samples],
                        min_samples=min_samples,
                    )
                    if not series:
                        continue

                    points = series['convergence_series']
                    if len(points) < 2:
                        continue

                    initial_equity = points[0]['equity']
                    final_equity = points[-1]['equity']
                    sample_count = series['total_samples']
                    equity_change = abs(final_equity - initial_equity)
                    convergence_rate = equity_change / len(points) if len(points) > 1 else 0

                    convergence_stats.append({
                        'row_idx': cell.row_index,
                        'col_idx': cell.col_index,
                        'hand_combination': cell.hand_combination,
                        'sample_count': sample_count,
                        'initial_equity': initial_equity,
                        'final_equity': final_equity,
                        'equity_change': equity_change,
                        'convergence_rate': convergence_rate,
                        'convergence_status': self._assess_convergence_status(
                            equity_change, sample_count
                        )
                    })

                return {
                    'matrix_id': matrix_id,
                    'cells_analyzed': len(convergence_stats),
                    'min_samples': min_samples,
                    'convergence_data': convergence_stats,
                    'summary': self._calculate_convergence_summary(convergence_stats)
                }

    def analyze_convergence_stability(
        self,
        matrix_id: int,
        row_idx: int,
        col_idx: int,
        window_size: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze how stable equity values are as more samples are added.

        Args:
            matrix_id: Hand matrix ID
            row_idx: Row index
            col_idx: Column index
            window_size: Size of rolling window for stability analysis

        Returns:
            Stability analysis with variance metrics
        """
        with self.performance_monitor.track_operation("convergence_stability"):
            with self.db_connection.session_scope() as session:
                matrix_cell = session.query(MatrixCell).filter(
                    and_(
                        MatrixCell.matrix_id == matrix_id,
                        MatrixCell.row_index == row_idx,
                        MatrixCell.col_index == col_idx
                    )
                ).first()

                if not matrix_cell:
                    return None

                all_game_states = (
                    session.query(GameState)
                    .options(selectinload(GameState.players))
                    .order_by(asc(GameState.timestamp))
                    .all()
                )

                game_states = [
                    gs for gs in all_game_states
                    if self._game_state_matches_cell(gs, row_idx, col_idx)
                ]

                if len(game_states) < window_size * 2:
                    return None

                # Calculate rolling equity values
                stability_points = []

                for i in range(window_size, len(game_states) + 1, max(1, window_size // 2)):
                    subset = game_states[:i]
                    equity = self._calculate_equity_for_subset(subset)

                    stability_points.append({
                        'sample_count': i,
                        'equity': equity,
                        'variance_window': self._calculate_equity_variance(
                            game_states[max(0, i-window_size):i]
                        )
                    })

                return {
                    'matrix_id': matrix_id,
                    'row_idx': row_idx,
                    'col_idx': col_idx,
                    'window_size': window_size,
                    'total_samples': len(game_states),
                    'stability_series': stability_points
                }

    def _calculate_equity_for_subset(self, game_states: List[GameState]) -> float:
        """
        Calculate equity for a subset of game states.

        Args:
            game_states: List of GameState objects

        Returns:
            Equity value (0.0 to 1.0)
        """
        if not game_states:
            return 0.0

        wins = sum(1 for gs in game_states if gs.outcome in ['win', 'jackpot_win'])
        ties = sum(0.5 for gs in game_states if gs.outcome in ['tie', 'jackpot_tie'])

        return (wins + ties) / len(game_states)

    def _calculate_equity_variance(self, game_states: List[GameState]) -> float:
        """
        Calculate variance in equity for a subset of recent game states.

        Args:
            game_states: List of GameState objects

        Returns:
            Variance measure (lower is more stable)
        """
        if len(game_states) < 2:
            return 0.0

        equities = []
        cumulative_wins = 0
        cumulative_ties = 0

        for i, gs in enumerate(game_states):
            if gs.outcome in ['win', 'jackpot_win']:
                cumulative_wins += 1
            elif gs.outcome in ['tie', 'jackpot_tie']:
                cumulative_ties += 0.5

            current_equity = (cumulative_wins + cumulative_ties) / (i + 1)
            equities.append(current_equity)

        # Calculate simple variance
        if not equities:
            return 0.0

        mean_equity = sum(equities) / len(equities)
        variance = sum((eq - mean_equity) ** 2 for eq in equities) / len(equities)

        return variance

    def _assess_convergence_status(self, equity_change: float, sample_count: int) -> str:
        """
        Assess convergence status based on equity change and sample count.

        Args:
            equity_change: Absolute change in equity from start to end
            sample_count: Total number of samples

        Returns:
            Convergence status string
        """
        if sample_count >= 10000 and equity_change < 0.01:
            return 'converged'
        elif sample_count >= 5000 and equity_change < 0.02:
            return 'well_converged'
        elif sample_count >= 1000 and equity_change < 0.05:
            return 'converging'
        elif sample_count >= 500 and equity_change < 0.10:
            return 'slowly_converging'
        else:
            return 'insufficient_samples'

    def _calculate_convergence_summary(self, convergence_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary statistics for convergence analysis.

        Args:
            convergence_stats: List of individual cell convergence data

        Returns:
            Summary statistics
        """
        if not convergence_stats:
            return {}

        equity_changes = [stat['equity_change'] for stat in convergence_stats]
        convergence_rates = [stat['convergence_rate'] for stat in convergence_stats]

        status_counts = {}
        for stat in convergence_stats:
            status = stat['convergence_status']
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            'total_cells': len(convergence_stats),
            'avg_equity_change': sum(equity_changes) / len(equity_changes),
            'max_equity_change': max(equity_changes),
            'min_equity_change': min(equity_changes),
            'avg_convergence_rate': sum(convergence_rates) / len(convergence_rates),
            'status_distribution': status_counts,
            'most_stable_cell': min(convergence_stats, key=lambda x: x['equity_change']),
            'least_stable_cell': max(convergence_stats, key=lambda x: x['equity_change'])
        }