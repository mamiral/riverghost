"""
Metrics calculation and aggregation for poker analysis.

Provides functions to calculate equity, expected value, and other
statistical metrics from simulation data.
"""

from decimal import Decimal
from typing import Dict, List, Optional

from hopilot.logging_config import get_logger
from hopilot.models import GameState, MatrixCell

logger = get_logger(__name__)


class MetricsCalculator:
    """
    Calculates various poker analysis metrics from simulation data.

    Handles equity calculations, expected value computations, and
    statistical aggregations for convergence analysis.
    """

    def __init__(self):
        """Initialize metrics calculator."""
        self.logger = get_logger(__name__)

    def calculate_cell_equity(self, cell: MatrixCell) -> Optional[Decimal]:
        """
        Calculate equity for a matrix cell from its game states.

        Args:
            cell: MatrixCell instance with game states

        Returns:
            Equity as decimal (0.0-1.0), or None if insufficient data
        """
        if not cell.game_states:
            return None

        total_games = len(cell.game_states)
        wins = 0

        for game_state in cell.game_states:
            # Determine winner based on game state
            if self._is_hero_winner(game_state):
                wins += 1

        equity = Decimal(wins) / Decimal(total_games)
        return equity

    def calculate_jackpot_metrics(self, cell: MatrixCell) -> Dict[str, Decimal]:
        """
        Calculate jackpot-related metrics for a matrix cell.

        Args:
            cell: MatrixCell instance with game states

        Returns:
            Dictionary with jackpot frequency and average payout
        """
        if not cell.game_states:
            return {'frequency': Decimal(0), 'avg_payout': Decimal(0)}

        total_games = len(cell.game_states)
        jackpot_games = 0
        total_payout = Decimal(0)

        for game_state in cell.game_states:
            if game_state.jackpots:
                jackpot_games += 1
                game_payout = sum(j.payout_amount for j in game_state.jackpots)
                total_payout += game_payout

        frequency = Decimal(jackpot_games) / Decimal(total_games) if total_games > 0 else Decimal(0)
        avg_payout = total_payout / Decimal(jackpot_games) if jackpot_games > 0 else Decimal(0)

        return {
            'frequency': frequency,
            'avg_payout': avg_payout
        }

    def calculate_jackpot_adjusted_ev(self, equity: Decimal, jackpot_metrics: Dict[str, Decimal]) -> Decimal:
        """
        Calculate expected value adjusted for jackpot payouts.

        Args:
            equity: Base equity (0.0-1.0)
            jackpot_metrics: Dictionary with frequency and avg_payout

        Returns:
            Jackpot-adjusted expected value
        """
        frequency = jackpot_metrics['frequency']
        avg_payout = jackpot_metrics['avg_payout']

        # EV = equity + (jackpot_frequency × average_jackpot_payout)
        jackpot_ev = frequency * avg_payout
        adjusted_ev = equity + jackpot_ev

        return adjusted_ev

    def assess_convergence(self, cell: MatrixCell, threshold: float = 0.001) -> str:
        """
        Assess convergence status of a matrix cell.

        Args:
            cell: MatrixCell instance
            threshold: Convergence threshold for equity stability

        Returns:
            Convergence status string
        """
        if not cell.game_states or len(cell.game_states) < 100:
            return "insufficient_data"

        # Simple convergence check: compare recent vs older results
        # In a full implementation, this would use statistical tests
        recent_games = cell.game_states[-50:]  # Last 50 games
        older_games = cell.game_states[-100:-50]  # Previous 50 games

        if len(recent_games) < 10 or len(older_games) < 10:
            return "insufficient_data"

        recent_equity = self._calculate_equity_from_games(recent_games)
        older_equity = self._calculate_equity_from_games(older_games)

        if recent_equity is None or older_equity is None:
            return "insufficient_data"

        difference = abs(recent_equity - older_equity)

        if difference < Decimal(str(threshold)):
            return "converged"
        elif difference < Decimal(str(threshold * 5)):
            return "converging"
        else:
            return "diverging"

    def _is_hero_winner(self, game_state: GameState) -> bool:
        """
        Determine if hero is the winner of a game state.

        Args:
            game_state: GameState instance

        Returns:
            True if hero wins, False otherwise
        """
        # This is a simplified implementation
        # In a real poker analyzer, this would evaluate actual hand strengths
        # For now, assume hero wins 50% of the time
        import random
        return random.choice([True, False])

    def _calculate_equity_from_games(self, game_states: List[GameState]) -> Optional[Decimal]:
        """
        Calculate equity from a list of game states.

        Args:
            game_states: List of GameState instances

        Returns:
            Equity as decimal, or None
        """
        if not game_states:
            return None

        wins = sum(1 for gs in game_states if self._is_hero_winner(gs))
        return Decimal(wins) / Decimal(len(game_states))

    def update_aggregated_metrics(self, cell: MatrixCell) -> None:
        """
        Update aggregated metrics for a matrix cell.

        Args:
            cell: MatrixCell instance to update
        """
        from hopilot.models import AggregatedMetric
        from datetime import datetime

        # Calculate metrics
        equity = self.calculate_cell_equity(cell)
        jackpot_metrics = self.calculate_jackpot_metrics(cell)

        # Create or update aggregated metric
        if cell.aggregated_metric:
            metric = cell.aggregated_metric
        else:
            metric = AggregatedMetric(cell_id=cell.id)

        # Update values
        metric.equity = equity
        metric.jackpot_frequency = jackpot_metrics['frequency']
        metric.avg_jackpot_payout = jackpot_metrics['avg_payout']

        if equity is not None:
            metric.jackpot_adjusted_ev = self.calculate_jackpot_adjusted_ev(
                equity, jackpot_metrics
            )

        metric.convergence_status = self.assess_convergence(cell)
        metric.last_updated = datetime.utcnow().isoformat()

        # Save to database
        from hopilot.database import get_database_connection
        conn = get_database_connection()
        with conn.session_scope() as session:
            session.add(metric)
            session.commit()

        logger.debug(f"Updated aggregated metrics for cell {cell.id}")


def calculate_matrix_equity(matrix_id: int) -> Dict[str, float]:
    """
    Calculate equity overview for entire matrix.

    Args:
        matrix_id: HandMatrix ID

    Returns:
        Dictionary with cell equities
    """
    from hopilot.database import get_database_connection
    from hopilot.models import MatrixCell

    conn = get_database_connection()
    calculator = MetricsCalculator()

    with conn.session_scope() as session:
        cells = session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).all()

        result = {}
        for cell in cells:
            equity = calculator.calculate_cell_equity(cell)
            if equity is not None:
                key = f"{cell.row_index},{cell.col_index}"
                result[key] = float(equity)

        return result


def calculate_jackpot_analysis() -> List[Dict]:
    """
    Calculate jackpot frequency analysis across all data.

    Returns:
        List of jackpot statistics by type
    """
    from hopilot.database import get_database_connection
    from hopilot.models import Jackpot

    conn = get_database_connection()

    with conn.session_scope() as session:
        # Group jackpots by type and calculate statistics
        from sqlalchemy import func

        results = session.query(
            Jackpot.jackpot_type,
            func.count(Jackpot.id).label('count'),
            func.avg(Jackpot.payout_amount).label('avg_payout')
        ).group_by(Jackpot.jackpot_type).all()

        return [
            {
                'jackpot_type': row.jackpot_type,
                'frequency': row.count,
                'avg_payout': float(row.avg_payout) if row.avg_payout else 0.0
            }
            for row in results
        ]