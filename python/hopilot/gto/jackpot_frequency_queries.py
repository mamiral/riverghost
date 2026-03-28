#!/usr/bin/env python3
"""
Jackpot Frequency Analysis Queries.

This module implements analytical queries for jackpot frequency analysis
and expected value (EV) impact calculations.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy import text, func, and_, or_, asc, desc, case, cast, Integer, Float
from sqlalchemy.orm import Session

from hopilot.database import DatabaseConnection
from hopilot.models import GameState, MatrixCell, Jackpot, HandMatrix
from hopilot.performance_monitor import PerformanceMonitor
from hopilot.gto.query_cache import cached_query

logger = logging.getLogger(__name__)


class JackpotFrequencyQueries:
    """
    Engine for analyzing jackpot frequency and EV impact.

    This class provides analytical queries for understanding jackpot
    frequency patterns and their impact on expected value.
    """

    def __init__(self, database_url: str):
        """
        Initialize the jackpot frequency queries engine.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.performance_monitor = PerformanceMonitor()

    def get_jackpot_frequency_analysis(
        self,
        matrix_id: Optional[int] = None,
        min_samples: int = 1000
    ) -> Dict[str, Any]:
        """
        Analyze jackpot frequency across all hands or a specific matrix.

        Args:
            matrix_id: Optional hand matrix ID to filter analysis
            min_samples: Minimum samples required for analysis

        Returns:
            Frequency analysis with jackpot types, rates, and EV impact
        """
        with self.performance_monitor.track_operation("jackpot_frequency_analysis"):
            with self.db_connection.session_scope() as session:
                # Base query for jackpot events
                base_query = session.query(Jackpot)

                if matrix_id is not None:
                    # Join through GameState to filter by matrix
                    base_query = base_query.join(GameState).join(MatrixCell).filter(
                        MatrixCell.matrix_id == matrix_id
                    )

                # Get total game states for denominator
                total_games_query = session.query(func.count(GameState.id))

                if matrix_id is not None:
                    total_games_query = total_games_query.join(MatrixCell).filter(
                        MatrixCell.matrix_id == matrix_id
                    )

                total_games = total_games_query.scalar()

                if total_games < min_samples:
                    logger.warning(f"Insufficient samples: {total_games} < {min_samples}")
                    return {}

                # Analyze jackpot frequency by type using a single aggregated query
                jackpot_aggregates = session.query(
                    Jackpot.jackpot_type,
                    func.count(Jackpot.id).label('count'),
                    func.avg(Jackpot.payout_amount).label('avg_payout')
                )

                if matrix_id is not None:
                    jackpot_aggregates = jackpot_aggregates.join(GameState).join(MatrixCell).filter(
                        MatrixCell.matrix_id == matrix_id
                    )

                jackpot_aggregates = jackpot_aggregates.group_by(Jackpot.jackpot_type).all()

                jackpot_stats = {}
                for jt, count, avg_payout in jackpot_aggregates:
                    frequency = count / total_games if total_games > 0 else 0
                    ev_impact = frequency * float(avg_payout or 0)

                    jackpot_stats[jt] = {
                        'count': count,
                        'frequency': frequency,
                        'avg_payout': float(avg_payout or 0),
                        'ev_impact': ev_impact,
                        'frequency_percent': frequency * 100
                    }

                # Calculate overall jackpot statistics
                total_jackpots = sum(stats['count'] for stats in jackpot_stats.values())
                overall_frequency = total_jackpots / total_games if total_games > 0 else 0

                # Calculate total EV impact from all jackpots
                total_ev_impact = sum(stats['ev_impact'] for stats in jackpot_stats.values())

                return {
                    'matrix_id': matrix_id,
                    'total_games': total_games,
                    'total_jackpots': total_jackpots,
                    'overall_frequency': overall_frequency,
                    'overall_frequency_percent': overall_frequency * 100,
                    'total_ev_impact': total_ev_impact,
                    'jackpot_types': jackpot_stats,
                    'analysis_timestamp': datetime.now().isoformat()
                }

    def get_jackpot_ev_impact_by_hand(
        self,
        matrix_id: int,
        min_samples: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze EV impact of jackpots for each hand combination in a matrix.

        Args:
            matrix_id: Hand matrix ID
            min_samples: Minimum samples per hand required for analysis

        Returns:
            EV impact analysis per hand combination
        """
        with self.performance_monitor.track_operation("jackpot_ev_by_hand"):
            with self.db_connection.session_scope() as session:
                # Get all matrix cells with sufficient samples and their jackpots in one query
                cells_query = session.query(
                    MatrixCell,
                    func.count(GameState.id).label('sample_count')
                ).outerjoin(GameState, MatrixCell.id == GameState.cell_id).filter(
                    MatrixCell.matrix_id == matrix_id
                ).group_by(MatrixCell.id).having(
                    func.count(GameState.id) >= min_samples
                ).subquery()

                # Get all jackpots for cells in this matrix with a single query
                jackpots_query = session.query(
                    Jackpot,
                    GameState.cell_id
                ).join(GameState, Jackpot.game_state_id == GameState.id).join(
                    MatrixCell, GameState.cell_id == MatrixCell.id
                ).filter(MatrixCell.matrix_id == matrix_id).all()

                # Group jackpots by cell_id
                jackpots_by_cell = {}
                for jackpot, cell_id in jackpots_query:
                    if cell_id not in jackpots_by_cell:
                        jackpots_by_cell[cell_id] = []
                    jackpots_by_cell[cell_id].append(jackpot)

                # Get cells data
                cells_data = session.query(
                    MatrixCell,
                    func.count(GameState.id).label('sample_count')
                ).join(GameState).filter(
                    MatrixCell.matrix_id == matrix_id
                ).group_by(MatrixCell.id).having(
                    func.count(GameState.id) >= min_samples
                ).all()

                hand_ev_analysis = []

                for cell, sample_count in cells_data:
                    cell_jackpots = jackpots_by_cell.get(cell.id, [])

                    if cell_jackpots:
                        # Calculate jackpot frequency for this hand
                        jackpot_count = len(cell_jackpots)
                        frequency = jackpot_count / sample_count

                        # Calculate average payout
                        total_payout = sum(float(j.payout_amount) for j in cell_jackpots)
                        avg_payout = total_payout / jackpot_count if jackpot_count > 0 else 0

                        # Calculate EV impact
                        ev_impact = frequency * avg_payout

                        # Group by jackpot type
                        jackpot_types = {}
                        for jackpot in cell_jackpots:
                            jt = jackpot.jackpot_type
                            if jt not in jackpot_types:
                                jackpot_types[jt] = []
                            jackpot_types[jt].append(float(jackpot.payout_amount))

                        type_stats = {}
                        for jt, payouts in jackpot_types.items():
                            type_stats[jt] = {
                                'count': len(payouts),
                                'avg_payout': sum(payouts) / len(payouts),
                                'frequency': len(payouts) / sample_count,
                                'ev_impact': (len(payouts) / sample_count) * (sum(payouts) / len(payouts))
                            }

                        hand_ev_analysis.append({
                            'row_idx': cell.row_index,
                            'col_idx': cell.col_index,
                            'hand_combination': cell.hand_combination,
                            'sample_count': sample_count,
                            'total_jackpots': jackpot_count,
                            'jackpot_frequency': frequency,
                            'avg_jackpot_payout': avg_payout,
                            'jackpot_ev_impact': ev_impact,
                            'jackpot_types': type_stats
                        })

                # Sort by EV impact (descending)
                hand_ev_analysis.sort(key=lambda x: x['jackpot_ev_impact'], reverse=True)

                return {
                    'matrix_id': matrix_id,
                    'hands_analyzed': len(hand_ev_analysis),
                    'min_samples': min_samples,
                    'hand_analysis': hand_ev_analysis,
                    'summary': self._calculate_jackpot_ev_summary(hand_ev_analysis)
                }

    @cached_query(ttl=600)  # Cache for 10 minutes
    def get_jackpot_temporal_analysis(
        self,
        matrix_id: Optional[int] = None,
        time_intervals: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Analyze jackpot frequency over time intervals.

        Args:
            matrix_id: Optional hand matrix ID to filter analysis
            time_intervals: List of sample count intervals to analyze

        Returns:
            Temporal analysis of jackpot frequency
        """
        if time_intervals is None:
            time_intervals = [1000, 5000, 10000, 25000, 50000]

        with self.performance_monitor.track_operation("jackpot_temporal_analysis"):
            with self.db_connection.session_scope() as session:
                # Get all game states ordered by timestamp
                query = session.query(GameState).order_by(asc(GameState.timestamp))

                if matrix_id is not None:
                    query = query.join(MatrixCell).filter(MatrixCell.matrix_id == matrix_id)

                game_states = query.all()

                if len(game_states) < min(time_intervals):
                    return {}

                temporal_data = []

                for interval in time_intervals:
                    if interval > len(game_states):
                        break

                    # Take the first 'interval' number of game states
                    subset = game_states[:interval]

                    # Count jackpots in this subset
                    jackpot_count = 0
                    total_payout = 0.0

                    for gs in subset:
                        if gs.jackpots:
                            jackpot_count += len(gs.jackpots)
                            total_payout += sum(float(j.payout_amount) for j in gs.jackpots)

                    frequency = jackpot_count / interval if interval > 0 else 0
                    avg_payout = total_payout / jackpot_count if jackpot_count > 0 else 0.0

                    temporal_data.append({
                        'sample_count': interval,
                        'jackpot_count': jackpot_count,
                        'frequency': frequency,
                        'frequency_percent': frequency * 100,
                        'avg_payout': avg_payout,
                        'total_payout': total_payout,
                        'timestamp': subset[-1].timestamp.isoformat() if subset[-1].timestamp else None
                    })

                return {
                    'matrix_id': matrix_id,
                    'total_samples': len(game_states),
                    'temporal_analysis': temporal_data,
                    'analysis_timestamp': datetime.now().isoformat()
                }

    def _calculate_jackpot_ev_summary(self, hand_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary statistics for jackpot EV analysis.

        Args:
            hand_analysis: List of hand analysis results

        Returns:
            Summary statistics
        """
        if not hand_analysis:
            return {}

        ev_impacts = [h['jackpot_ev_impact'] for h in hand_analysis]
        frequencies = [h['jackpot_frequency'] for h in hand_analysis]

        return {
            'total_hands': len(hand_analysis),
            'avg_jackpot_ev_impact': sum(ev_impacts) / len(ev_impacts),
            'max_jackpot_ev_impact': max(ev_impacts),
            'min_jackpot_ev_impact': min(ev_impacts),
            'avg_jackpot_frequency': sum(frequencies) / len(frequencies),
            'hands_with_jackpots': sum(1 for h in hand_analysis if h['total_jackpots'] > 0),
            'highest_ev_hand': max(hand_analysis, key=lambda x: x['jackpot_ev_impact']),
            'lowest_ev_hand': min(hand_analysis, key=lambda x: x['jackpot_ev_impact'])
        }