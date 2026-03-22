"""
Simple Averaging Utilities for Poker Metrics.

This module provides utility functions for computing simple averages
of poker-related metrics like equity, EV, and other statistical measures.
These utilities complement the SQL-based aggregation in the AggregationEngine.
"""

from typing import List, Optional, Union, Dict, Any
from decimal import Decimal
import statistics
import logging

logger = logging.getLogger(__name__)


class SimpleAveraging:
    """
    Utility class for computing simple averages of poker metrics.

    Provides mathematical averaging functions that can be used independently
    of database queries, useful for testing, validation, and in-memory calculations.
    """

    @staticmethod
    def calculate_equity(outcomes: List[str]) -> float:
        """
        Calculate equity (win rate) from a list of game outcomes.

        Args:
            outcomes: List of outcome strings ('win', 'loss', 'tie', 'jackpot_win', etc.)

        Returns:
            Equity as a float between 0.0 and 1.0

        Raises:
            ValueError: If outcomes list is empty
        """
        if not outcomes:
            raise ValueError("Cannot calculate equity from empty outcomes list")

        total_games = len(outcomes)
        wins = sum(1.0 for outcome in outcomes if outcome in ['win', 'jackpot_win'])
        ties = sum(0.5 for outcome in outcomes if outcome in ['tie', 'jackpot_tie'])

        equity = (wins + ties) / total_games
        return equity

    @staticmethod
    def calculate_ev(values: List[Union[float, int, Decimal]]) -> float:
        """
        Calculate expected value (EV) as simple average of values.

        Args:
            values: List of numeric values to average

        Returns:
            Average EV as float

        Raises:
            ValueError: If values list is empty
            StatisticsError: If values contain invalid data
        """
        if not values:
            raise ValueError("Cannot calculate EV from empty values list")

        # Convert to float and filter out None values
        numeric_values = []
        for value in values:
            if value is not None:
                try:
                    numeric_values.append(float(value))
                except (ValueError, TypeError):
                    logger.warning(f"Skipping invalid EV value: {value}")

        if not numeric_values:
            return 0.0

        return statistics.mean(numeric_values)

    @staticmethod
    def calculate_jackpot_frequency(outcomes: List[str]) -> float:
        """
        Calculate jackpot frequency from game outcomes.

        Args:
            outcomes: List of outcome strings

        Returns:
            Jackpot frequency as float between 0.0 and 1.0

        Raises:
            ValueError: If outcomes list is empty
        """
        if not outcomes:
            raise ValueError("Cannot calculate jackpot frequency from empty outcomes list")

        total_games = len(outcomes)
        jackpot_games = sum(1 for outcome in outcomes if outcome in ['jackpot_win', 'jackpot_tie'])

        return jackpot_games / total_games

    @staticmethod
    def calculate_jackpot_adjusted_ev(
        base_ev: float,
        jackpot_frequency: float,
        avg_jackpot_payout: float
    ) -> float:
        """
        Calculate jackpot-adjusted expected value.

        Args:
            base_ev: Base expected value without jackpots
            jackpot_frequency: Frequency of jackpot events (0.0-1.0)
            avg_jackpot_payout: Average jackpot payout amount

        Returns:
            Jackpot-adjusted EV
        """
        jackpot_ev = jackpot_frequency * avg_jackpot_payout
        return base_ev + jackpot_ev

    @staticmethod
    def calculate_weighted_average(values: List[float], weights: Optional[List[float]] = None) -> float:
        """
        Calculate weighted average of values.

        Args:
            values: List of values to average
            weights: Optional list of weights (same length as values)

        Returns:
            Weighted average as float

        Raises:
            ValueError: If lists have different lengths or are empty
        """
        if not values:
            raise ValueError("Cannot calculate weighted average from empty values list")

        if weights is None:
            return statistics.mean(values)

        if len(values) != len(weights):
            raise ValueError("Values and weights lists must have the same length")

        weighted_sum = sum(value * weight for value, weight in zip(values, weights))
        total_weight = sum(weights)

        if total_weight == 0:
            raise ValueError("Total weight cannot be zero")

        return weighted_sum / total_weight

    @staticmethod
    def calculate_convergence_status(sample_count: int) -> str:
        """
        Determine convergence status based on sample count.

        Args:
            sample_count: Number of samples/games

        Returns:
            Convergence status string
        """
        if sample_count >= 10000:
            return 'converged'
        elif sample_count >= 1000:
            return 'converging'
        else:
            return 'insufficient_samples'

    @classmethod
    def calculate_aggregated_metrics(
        cls,
        outcomes: List[str],
        ev_values: Optional[List[Union[float, int, Decimal]]] = None,
        jackpot_payouts: Optional[List[Union[float, int, Decimal]]] = None
    ) -> Dict[str, Any]:
        """
        Calculate complete set of aggregated metrics from raw data.

        Args:
            outcomes: List of game outcomes
            ev_values: Optional list of EV values (if not provided, calculated from outcomes)
            jackpot_payouts: Optional list of jackpot payout amounts

        Returns:
            Dictionary with all calculated metrics
        """
        if not outcomes:
            return {
                'total_games': 0,
                'equity': 0.0,
                'ev': 0.0,
                'jackpot_frequency': 0.0,
                'avg_jackpot_payout': 0.0,
                'jackpot_adjusted_ev': 0.0,
                'convergence_status': 'insufficient_samples'
            }

        total_games = len(outcomes)
        equity = cls.calculate_equity(outcomes)
        jackpot_frequency = cls.calculate_jackpot_frequency(outcomes)

        # Calculate EV
        if ev_values:
            ev = cls.calculate_ev(ev_values)
        else:
            # Estimate EV from outcomes (simplified)
            ev = equity * 1000  # Assume $1000 pot size for estimation

        # Calculate average jackpot payout
        if jackpot_payouts:
            avg_jackpot_payout = cls.calculate_ev(jackpot_payouts)
        else:
            # Use default estimate
            avg_jackpot_payout = 5000.0 if jackpot_frequency > 0 else 0.0

        # Calculate jackpot-adjusted EV
        jackpot_adjusted_ev = cls.calculate_jackpot_adjusted_ev(ev, jackpot_frequency, avg_jackpot_payout)

        convergence_status = cls.calculate_convergence_status(total_games)

        return {
            'total_games': total_games,
            'equity': equity,
            'ev': ev,
            'jackpot_frequency': jackpot_frequency,
            'avg_jackpot_payout': avg_jackpot_payout,
            'jackpot_adjusted_ev': jackpot_adjusted_ev,
            'convergence_status': convergence_status
        }


# Convenience functions for direct use
def average_equity(outcomes: List[str]) -> float:
    """Convenience function for equity calculation."""
    return SimpleAveraging.calculate_equity(outcomes)


def average_ev(values: List[Union[float, int, Decimal]]) -> float:
    """Convenience function for EV calculation."""
    return SimpleAveraging.calculate_ev(values)


def average_jackpot_frequency(outcomes: List[str]) -> float:
    """Convenience function for jackpot frequency calculation."""
    return SimpleAveraging.calculate_jackpot_frequency(outcomes)