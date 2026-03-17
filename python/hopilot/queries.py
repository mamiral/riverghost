"""
Query service for complex analytical queries on poker simulation data.

Provides high-level query functions for equity analysis, jackpot statistics,
game replay, and other analytical operations on the normalized database schema.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from sqlalchemy import func, desc, and_, or_, text
from sqlalchemy.orm import Session

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger
from hopilot.models import (
    Simulation, HandMatrix, MatrixCell, GameState,
    Player, Bet, BoardCard, Jackpot, AggregatedMetric
)

logger = get_logger(__name__)


class QueryService:
    """
    Service for complex analytical queries on poker simulation data.

    Provides methods for equity analysis, jackpot statistics, game replay,
    and other analytical operations that require complex joins and aggregations.
    """

    def __init__(self, database_connection: DatabaseConnection):
        """
        Initialize query service with database connection.

        Args:
            database_connection: Database connection instance
        """
        self.db = database_connection

    def get_game_states_for_cell(self, cell_id: int, limit: int = 1000) -> List[GameState]:
        """
        Retrieve game states for a specific matrix cell.

        Args:
            cell_id: Matrix cell ID to query
            limit: Maximum number of game states to return

        Returns:
            List of GameState objects ordered by timestamp
        """
        with self.db.session_scope() as session:
            game_states = (
                session.query(GameState)
                .filter(GameState.cell_id == cell_id)
                .order_by(desc(GameState.timestamp))
                .limit(limit)
                .all()
            )
            return game_states

    def get_matrix_equity(self, matrix_id: int) -> Dict[str, Any]:
        """
        Calculate equity overview for an entire hand matrix.

        Args:
            matrix_id: Hand matrix ID to analyze

        Returns:
            Dictionary with equity statistics and cell data
        """
        with self.db.session_scope() as session:
            # Get matrix info
            matrix = session.query(HandMatrix).filter(HandMatrix.id == matrix_id).first()
            if not matrix:
                return {}

            # Get all cells with their aggregated metrics
            cells = (
                session.query(MatrixCell, AggregatedMetric)
                .outerjoin(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
                .filter(MatrixCell.matrix_id == matrix_id)
                .all()
            )

            # Calculate matrix statistics
            equities = []
            total_games = 0
            cells_with_data = 0

            for cell, metric in cells:
                if metric and metric.equity is not None:
                    equities.append(float(metric.equity))
                    total_games += metric.total_games or 0
                    cells_with_data += 1

            result = {
                'matrix_id': matrix_id,
                'matrix_name': matrix.name,
                'total_cells': len(cells),
                'cells_with_data': cells_with_data,
                'avg_equity': sum(equities) / len(equities) if equities else 0,
                'min_equity': min(equities) if equities else 0,
                'max_equity': max(equities) if equities else 0,
                'total_games': total_games,
                'cell_data': []
            }

            # Add individual cell data
            for cell, metric in cells:
                cell_info = {
                    'cell_id': cell.id,
                    'row_index': cell.row_index,
                    'col_index': cell.col_index,
                    'hero_hand': cell.hero_hand,
                    'villain_hand': cell.villain_hand,
                    'equity': float(metric.equity) if metric and metric.equity else None,
                    'total_games': metric.total_games if metric else 0,
                    'jackpot_adjusted_ev': (
                        float(metric.jackpot_adjusted_ev) 
                        if metric and metric.jackpot_adjusted_ev else None
                    )
                }
                result['cell_data'].append(cell_info)

            return result

    def get_jackpot_analysis(self) -> Dict[str, Any]:
        """
        Aggregate jackpot frequency and payout data across all simulations.

        Returns:
            Dictionary with jackpot statistics by type and overall metrics
        """
        with self.db.session_scope() as session:
            # Get jackpot statistics by type
            jackpot_stats = (
                session.query(
                    Jackpot.jackpot_type,
                    func.count(Jackpot.id).label('count'),
                    func.avg(Jackpot.payout_amount).label('avg_payout'),
                    func.sum(Jackpot.payout_amount).label('total_payout'),
                    func.min(Jackpot.payout_amount).label('min_payout'),
                    func.max(Jackpot.payout_amount).label('max_payout')
                )
                .group_by(Jackpot.jackpot_type)
                .all()
            )

            # Get overall jackpot frequency
            total_games = session.query(func.count(GameState.id)).scalar() or 0
            total_jackpots = session.query(func.count(Jackpot.id)).scalar() or 0

            result = {
                'total_games': total_games,
                'total_jackpots': total_jackpots,
                'jackpot_frequency': total_jackpots / total_games if total_games > 0 else 0,
                'by_type': {}
            }

            for stat in jackpot_stats:
                result['by_type'][stat.jackpot_type] = {
                    'count': stat.count,
                    'frequency': stat.count / total_games if total_games > 0 else 0,
                    'avg_payout': float(stat.avg_payout or 0),
                    'total_payout': float(stat.total_payout or 0),
                    'min_payout': float(stat.min_payout or 0),
                    'max_payout': float(stat.max_payout or 0)
                }

            return result

    def replay_game(self, cell_id: int, hand_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Reconstruct game sequence for replay purposes.

        Args:
            cell_id: Matrix cell ID to replay
            hand_filter: Optional filter for specific hands (e.g., "Ac Kd")

        Returns:
            List of game replay data with chronological events
        """
        with self.db.session_scope() as session:
            # Get a recent game state for this cell
            game_state = (
                session.query(GameState)
                .filter(GameState.cell_id == cell_id)
                .order_by(desc(GameState.timestamp))
                .first()
            )

            if not game_state:
                return []

            # Build replay sequence
            replay_data = []

            # Add preflop action
            replay_data.append({
                'phase': 'preflop',
                'timestamp': game_state.timestamp.isoformat(),
                'pot_size': float(game_state.pot_size),
                'board_cards': [],
                'players': [],
                'bets': [],
                'jackpots': []
            })

            # Add players
            for player in game_state.players:
                player_data = {
                    'seat': player.seat,
                    'hole_cards': player.hole_cards,
                    'is_hero': player.is_hero,
                    'stack_size': float(player.stack_size)
                }
                replay_data[-1]['players'].append(player_data)

            # Add bets
            for bet in game_state.bets:
                bet_data = {
                    'player_seat': bet.player_seat,
                    'amount': float(bet.amount),
                    'action_type': bet.action_type,
                    'timestamp': bet.timestamp.isoformat()
                }
                replay_data[-1]['bets'].append(bet_data)

            # Add board cards if any
            if game_state.board_cards:
                for card in game_state.board_cards.cards:
                    replay_data[-1]['board_cards'].append(card)

            # Add jackpots
            for jackpot in game_state.jackpots:
                jackpot_data = {
                    'type': jackpot.jackpot_type,
                    'payout': float(jackpot.payout_amount),
                    'cards_used': jackpot.cards_used
                }
                replay_data[-1]['jackpots'].append(jackpot_data)

            return replay_data

    def get_convergence_data(self, cell_id: int, max_points: int = 50) -> List[Dict[str, Any]]:
        """
        Get timestamped equity data for convergence analysis.

        Args:
            cell_id: Matrix cell ID to analyze
            max_points: Maximum number of data points to return

        Returns:
            List of convergence data points with timestamps and equity values
        """
        with self.db.session_scope() as session:
            # Get aggregated metrics updates for this cell
            convergence_points = (
                session.query(AggregatedMetric)
                .filter(AggregatedMetric.cell_id == cell_id)
                .order_by(AggregatedMetric.last_updated)
                .limit(max_points)
                .all()
            )

            result = []
            for point in convergence_points:
                result.append({
                    'timestamp': point.last_updated.isoformat(),
                    'equity': float(point.equity) if point.equity else None,
                    'total_games': point.total_games,
                    'jackpot_adjusted_ev': float(point.jackpot_adjusted_ev) if point.jackpot_adjusted_ev else None,
                    'confidence_interval': float(point.confidence_interval) if point.confidence_interval else None
                })

            return result

    def get_query_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for common queries.

        Returns:
            Dictionary with query performance metrics
        """
        with self.db.session_scope() as session:
            stats = {
                'table_counts': {},
                'index_info': {},
                'query_timings': {}
            }
            
            # Get table row counts
            if self.db.database_url.startswith("sqlite"):
                tables = ['simulations', 'hand_matrices', 'matrix_cells', 
                         'game_states', 'players', 'bets', 'board_cards', 
                         'jackpots', 'aggregated_metrics']
                
                for table in tables:
                    try:
                        result = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                        stats['table_counts'][table] = result
                    except:
                        stats['table_counts'][table] = 0
            
            return stats

    def optimize_query(self, query_type: str, **params) -> Any:
        """
        Execute optimized version of common queries.

        Args:
            query_type: Type of query to optimize
            **params: Query parameters

        Returns:
            Query results with optimization applied
        """
        if query_type == "matrix_equity_batch":
            return self._get_matrix_equity_batch(**params)
        elif query_type == "jackpot_summary":
            return self._get_jackpot_summary_optimized(**params)
        elif query_type == "convergence_fast":
            return self._get_convergence_fast(**params)
        else:
            raise ValueError(f"Unknown query type: {query_type}")

    def _get_matrix_equity_batch(self, matrix_ids: List[int]) -> Dict[int, Dict]:
        """
        Optimized batch query for multiple matrix equities.
        """
        results = {}
        with self.db.session_scope() as session:
            for matrix_id in matrix_ids:
                # Use single query with aggregation
                equity_data = (
                    session.query(
                        func.avg(AggregatedMetric.equity).label('avg_equity'),
                        func.count(AggregatedMetric.id).label('cell_count'),
                        func.sum(AggregatedMetric.total_games).label('total_games')
                    )
                    .join(MatrixCell, AggregatedMetric.cell_id == MatrixCell.id)
                    .filter(MatrixCell.matrix_id == matrix_id)
                    .first()
                )
                
                results[matrix_id] = {
                    'avg_equity': float(equity_data.avg_equity or 0),
                    'cell_count': equity_data.cell_count or 0,
                    'total_games': equity_data.total_games or 0
                }
        
        return results

    def _get_jackpot_summary_optimized(self, simulation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Optimized jackpot summary query.
        """
        with self.db.session_scope() as session:
            query = session.query(
                Jackpot.jackpot_type,
                func.count(Jackpot.id),
                func.sum(Jackpot.payout_amount),
                func.avg(Jackpot.payout_amount)
            )
            
            if simulation_id:
                query = query.join(GameState, Jackpot.game_state_id == GameState.id)\
                           .filter(GameState.simulation_id == simulation_id)
            
            results = query.group_by(Jackpot.jackpot_type).all()
            
            return {
                'by_type': {
                    row[0]: {
                        'count': row[1],
                        'total_payout': float(row[2] or 0),
                        'avg_payout': float(row[3] or 0)
                    } for row in results
                }
            }

    def _get_convergence_fast(self, cell_id: int, sample_size: int = 10) -> List[Dict]:
        """
        Fast convergence query using sampling.
        """
        with self.db.session_scope() as session:
            # Get total count
            total_count = session.query(func.count(AggregatedMetric.id))\
                               .filter(AggregatedMetric.cell_id == cell_id)\
                               .scalar()
            
            if total_count == 0:
                return []
            
            # Sample evenly across the timeline
            step = max(1, total_count // sample_size)
            
            results = (
                session.query(AggregatedMetric)
                .filter(AggregatedMetric.cell_id == cell_id)
                .order_by(AggregatedMetric.last_updated)
                .all()
            )[::step][:sample_size]
            
            return [{
                'timestamp': r.last_updated.isoformat(),
                'equity': float(r.equity) if r.equity else None,
                'total_games': r.total_games
            } for r in results]