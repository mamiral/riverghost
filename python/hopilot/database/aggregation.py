"""
Aggregation engine for computing MatrixCells and metrics from GameStates.

This module implements the aggregation logic that computes MatrixCells
and AggregatedMetrics from stored GameStates data, ensuring equity
calculations are based on real simulation outcomes.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from hopilot.logging_config import get_logger
from hopilot.models import GameState, Player, Bet, Jackpot, MatrixCell, AggregatedMetric

logger = get_logger(__name__)


class AggregationEngine:
    """
    Engine for aggregating GameStates into MatrixCells and metrics.

    Computes statistical measures from stored simulation data,
    including equity calculations, jackpot statistics, and convergence
    tracking for genuine GameStates-first architecture.
    """

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self.logger = get_logger(__name__)

    def aggregate_matrix_cell(self, matrix_cell_id: int) -> Optional[AggregatedMetric]:
        """
        Aggregate all GameStates for a matrix cell into metrics.

        Args:
            matrix_cell_id: ID of the matrix cell to aggregate

        Returns:
            AggregatedMetric object with computed statistics, or None if no data
        """
        # Get all game states for this matrix cell
        game_states = self.session.query(GameState).filter(
            GameState.cell_id == matrix_cell_id
        ).all()

        if not game_states:
            self.logger.debug(f"No game states found for matrix cell {matrix_cell_id}")
            return None

        self.logger.info(f"Aggregating {len(game_states)} game states for matrix cell {matrix_cell_id}")

        # Compute aggregated metrics
        metrics = self._compute_aggregated_metrics(game_states)

        # Get or create aggregated metric record
        aggregated_metric = self.session.query(AggregatedMetric).filter(
            AggregatedMetric.cell_id == matrix_cell_id
        ).first()

        if aggregated_metric:
            # Update existing record
            self._update_aggregated_metric(aggregated_metric, metrics)
        else:
            # Create new record
            aggregated_metric = AggregatedMetric(
                cell_id=matrix_cell_id,
                **metrics
            )
            self.session.add(aggregated_metric)

        self.session.commit()
        self.logger.info(f"Updated aggregated metrics for matrix cell {matrix_cell_id}")

        return aggregated_metric

    def _compute_aggregated_metrics(self, game_states: List[GameState]) -> Dict:
        """
        Compute aggregated metrics from game states.

        Args:
            game_states: List of GameState objects

        Returns:
            Dict with computed metric values
        """
        total_games = len(game_states)
        hero_wins = 0
        total_ev = 0.0
        jackpot_events = []
        convergence_samples = []

        for game_state in game_states:
            # Determine if hero won
            hero_player = None
            for player in game_state.players:
                if player.is_hero:
                    hero_player = player
                    break

            if hero_player:
                # Check if hero won based on game outcome
                hero_won = game_state.outcome == 'hero_win'
                if hero_won:
                    hero_wins += 1

                # Calculate EV (simplified - just win/loss for now)
                # In a real implementation, this would factor in bet amounts and pot sizes
                if hero_won:
                    total_ev += 1.0  # Simplified EV calculation
                else:
                    total_ev -= 1.0

                # Track convergence (equity over time)
                current_equity = hero_wins / (len(convergence_samples) + 1)
                convergence_samples.append(current_equity)

            # Collect jackpot events
            for jackpot in game_state.jackpots:
                jackpot_events.append({
                    'payout': float(jackpot.payout_amount),
                    'type': jackpot.jackpot_type
                })

        # Compute final metrics
        equity = hero_wins / total_games if total_games > 0 else 0.0
        avg_ev = total_ev / total_games if total_games > 0 else 0.0

        # Jackpot statistics
        jackpot_frequency = len(jackpot_events) / total_games if total_games > 0 else 0.0
        avg_jackpot_payout = (
            sum(j['payout'] for j in jackpot_events) / len(jackpot_events)
            if jackpot_events else 0.0
        )

        # Jackpot-adjusted EV (simplified)
        jackpot_adjusted_ev = avg_ev + (jackpot_frequency * avg_jackpot_payout)

        # Convergence assessment (simplified - check if equity is stabilizing)
        convergence_status = self._assess_convergence(convergence_samples)

        return {
            'equity': Decimal(str(round(equity, 4))),
            'win_probability': Decimal(str(round(equity, 4))),  # Same as equity for now
            'ev': Decimal(str(round(avg_ev, 4))),
            'jackpot_adjusted_ev': Decimal(str(round(jackpot_adjusted_ev, 4))),
            'jackpot_frequency': Decimal(str(round(jackpot_frequency, 4))),
            'avg_jackpot_payout': Decimal(str(round(avg_jackpot_payout, 2))),
            'convergence_status': convergence_status,
            'last_updated': datetime.now().isoformat()
        }

    def _assess_convergence(self, equity_samples: List[float]) -> str:
        """
        Assess convergence status from equity samples.

        Args:
            equity_samples: List of equity values over time

        Returns:
            Convergence status string
        """
        if len(equity_samples) < 10:
            return 'insufficient_data'
        
        # Calculate standard deviation as a measure of convergence
        import statistics
        try:
            std_dev = statistics.stdev(equity_samples)
            mean = statistics.mean(equity_samples)
            
            # Relative standard deviation (coefficient of variation)
            if mean != 0:
                cv = std_dev / abs(mean)
            else:
                cv = 0.0  # If mean is 0, consider it perfectly stable
            
            # Convergence thresholds based on coefficient of variation
            if cv < 0.05:  # Very low variation - converged
                return 'converged'
            elif cv < 0.15:  # Moderate variation - converging
                return 'converging'
            else:  # High variation - diverging or not converged
                return 'diverging'
                
        except statistics.StatisticsError:
            # Not enough variation for statistical calculations (all same values)
            # This is actually perfect convergence
            return 'converged'

    def _update_aggregated_metric(self, metric: AggregatedMetric, new_values: Dict):
        """
        Update an existing AggregatedMetric with new values.

        Args:
            metric: Existing AggregatedMetric object
            new_values: Dict of new values to update
        """
        for key, value in new_values.items():
            if hasattr(metric, key):
                setattr(metric, key, value)

    def get_matrix_cell_stats(self, matrix_cell_id: int) -> Optional[Dict]:
        """
        Get comprehensive statistics for a matrix cell.

        Args:
            matrix_cell_id: ID of the matrix cell

        Returns:
            Dict with detailed statistics, or None if no data
        """
        # Get aggregated metrics
        aggregated = self.session.query(AggregatedMetric).filter(
            AggregatedMetric.cell_id == matrix_cell_id
        ).first()

        if not aggregated:
            return None

        # Get game state count
        game_state_count = self.session.query(GameState).filter(
            GameState.cell_id == matrix_cell_id
        ).count()

        # Get jackpot count
        jackpot_count = self.session.query(Jackpot).join(GameState).filter(
            GameState.cell_id == matrix_cell_id
        ).count()

        return {
            'matrix_cell_id': matrix_cell_id,
            'game_states_count': game_state_count,
            'jackpots_count': jackpot_count,
            'equity': float(aggregated.equity) if aggregated.equity else None,
            'ev': float(aggregated.ev) if aggregated.ev else None,
            'jackpot_adjusted_ev': float(aggregated.jackpot_adjusted_ev) if aggregated.jackpot_adjusted_ev else None,
            'jackpot_frequency': float(aggregated.jackpot_frequency) if aggregated.jackpot_frequency else None,
            'convergence_status': aggregated.convergence_status,
            'last_updated': aggregated.last_updated
        }