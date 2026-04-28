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
from sqlalchemy.orm import Session, selectinload

from hopilot.database import DatabaseConnection
from hopilot.gto.aof_hand_matrix import hand_coordinates_from_hole_cards
from hopilot.models import GameState, Player, MatrixCell, Jackpot, HandMatrix
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
                if matrix_id is not None:
                    matrix = session.query(HandMatrix).filter(HandMatrix.id == matrix_id).first()
                    if matrix is None:
                        logger.warning(f"No HandMatrix found for matrix_id={matrix_id}")
                        return {}
                else:
                    matrix = None

                query = session.query(GameState).options(selectinload(GameState.players).selectinload(Player.jackpots))
                game_states = query.all()

                if matrix is not None:
                    valid_cells = {
                        (cell.row_index, cell.col_index)
                        for cell in session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).all()
                    }
                    game_states = [
                        gs for gs in game_states
                        if self._game_state_matches_matrix(gs, valid_cells)
                    ]

                total_games = len(game_states)
                if total_games < min_samples:
                    logger.warning(f"Insufficient samples: {total_games} < {min_samples}")
                    return {}

                jackpot_aggregates: Dict[str, list[float]] = {}
                for gs in game_states:
                    for player in gs.players:
                        for jackpot in player.jackpots:
                            jackpot_aggregates.setdefault(jackpot.jackpot_type, []).append(float(jackpot.payout_amount))

                jackpot_stats = {}
                for jt, payouts in jackpot_aggregates.items():
                    count = len(payouts)
                    avg_payout = sum(payouts) / count if count else 0
                    frequency = count / total_games if total_games > 0 else 0
                    ev_impact = frequency * avg_payout

                    jackpot_stats[jt] = {
                        'count': count,
                        'frequency': frequency,
                        'avg_payout': avg_payout,
                        'ev_impact': ev_impact,
                        'frequency_percent': frequency * 100
                    }

                total_jackpots = sum(stats['count'] for stats in jackpot_stats.values())
                overall_frequency = total_jackpots / total_games if total_games > 0 else 0
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
                matrix = session.query(HandMatrix).filter(HandMatrix.id == matrix_id).first()
                if matrix is None:
                    logger.warning(f"No HandMatrix found for matrix_id={matrix_id}")
                    return {
                        'matrix_id': matrix_id,
                        'hands_analyzed': 0,
                        'min_samples': min_samples,
                        'hand_analysis': [],
                        'summary': {
                            'total_hands': 0,
                            'total_ev_impact': 0.0,
                            'average_ev_impact': 0.0
                        }
                    }

                game_states = (
                    session.query(GameState)
                    .options(selectinload(GameState.players).selectinload(Player.jackpots))
                    .all()
                )

                cells_by_coord = {
                    (cell.row_index, cell.col_index): cell
                    for cell in session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).all()
                }

                sample_counts: Dict[tuple[int, int], int] = {}
                jackpot_records: Dict[tuple[int, int], list[Jackpot]] = {}

                for gs in game_states:
                    coord = self._derive_game_state_cell_coordinate(gs)
                    if coord is None or coord not in cells_by_coord:
                        continue

                    sample_counts[coord] = sample_counts.get(coord, 0) + 1
                    for player in gs.players:
                        for jackpot in player.jackpots:
                            jackpot_records.setdefault(coord, []).append(jackpot)

                hand_ev_analysis = []
                for coord, sample_count in sample_counts.items():
                    if sample_count < min_samples:
                        continue

                    cell = cells_by_coord.get(coord)
                    cell_jackpots = jackpot_records.get(coord, [])
                    if not cell_jackpots:
                        continue

                    jackpot_count = len(cell_jackpots)
                    frequency = jackpot_count / sample_count
                    total_payout = sum(float(j.payout_amount) for j in cell_jackpots)
                    avg_payout = total_payout / jackpot_count if jackpot_count > 0 else 0
                    ev_impact = frequency * avg_payout

                    jackpot_types: Dict[str, list[float]] = {}
                    for jackpot in cell_jackpots:
                        jackpot_types.setdefault(jackpot.jackpot_type, []).append(float(jackpot.payout_amount))

                    type_stats = {
                        jt: {
                            'count': len(payouts),
                            'avg_payout': sum(payouts) / len(payouts),
                            'frequency': len(payouts) / sample_count,
                            'ev_impact': (len(payouts) / sample_count) * (sum(payouts) / len(payouts))
                        }
                        for jt, payouts in jackpot_types.items()
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

    def _game_state_matches_matrix(self, game_state: GameState, valid_cells: set[tuple[int, int]]) -> bool:
        coord = self._derive_game_state_cell_coordinate(game_state)
        return coord in valid_cells if coord is not None else False

    def _derive_game_state_cell_coordinate(self, game_state: GameState) -> Optional[tuple[int, int]]:
        hero_player = next((player for player in game_state.players if player.is_hero), None)
        if hero_player is None:
            return None

        try:
            return hand_coordinates_from_hole_cards(hero_player.hole_cards)
        except ValueError:
            return None

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
                query = session.query(GameState).options(selectinload(GameState.players).selectinload(Player.jackpots)).order_by(asc(GameState.timestamp))
                game_states = query.all()

                if matrix_id is not None:
                    valid_cells = {
                        (cell.row_index, cell.col_index)
                        for cell in session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).all()
                    }
                    game_states = [
                        gs for gs in game_states
                        if self._game_state_matches_matrix(gs, valid_cells)
                    ]

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
                        for player in gs.players:
                            if player.jackpots:
                                jackpot_count += len(player.jackpots)
                                total_payout += sum(float(j.payout_amount) for j in player.jackpots)

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