"""
GTO Optimizer - Range vs Range Nash Equilibrium Solver

Implements push-fold Nash equilibrium algorithms for poker tournament scenarios.
Uses dynamic programming to find optimal shoving frequencies against opponent ranges.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from hopilot.logging_config import get_logger
from hopilot.poker_analyzer import PokerAnalyzer

logger = get_logger(__name__)


class GTOOptimizer:
    """
    Game Theory Optimal (GTO) optimizer for push-fold scenarios.

    Finds Nash equilibrium solutions for shove/fold matchups between two ranges.
    Uses dynamic programming and indifference point calculations.
    """

    def __init__(self, analyzer: PokerAnalyzer):
        """
        Initialize GTO optimizer.

        Args:
            analyzer: PokerAnalyzer instance for equity calculations
        """
        self.analyzer = analyzer
        logger.info("GTOOptimizer initialized")

    def find_nash_equilibrium(self, hero_range: List[str], villain_range: List[str],
                            pot_size: float, bet_amount: float,
                            hero_stack: Optional[float] = None,
                            villain_stack: Optional[float] = None,
                            num_simulations: int = 1000,
                            max_iterations: int = 100,
                            tolerance: float = 0.001,
                            validate_best_response: bool = False) -> Dict[str, Any]:
        """
        Find Nash equilibrium for push-fold scenario.

        Uses dynamic programming to iteratively find optimal shove frequencies
        for both players until convergence.

        Args:
            hero_range: List of hero's hand shorthands
            villain_range: List of villain's hand shorthands
            pot_size: Current pot size
            bet_amount: All-in bet amount
            hero_stack: Hero's remaining stack (optional)
            villain_stack: Villain's remaining stack (optional)
            num_simulations: Monte Carlo simulations per equity calculation
            max_iterations: Maximum iterations for convergence
            tolerance: Convergence tolerance
            validate_best_response: Whether to validate equilibrium with best response

        Returns:
            Dict with equilibrium strategies and analysis
        """
        if not hero_range or not villain_range:
            raise ValueError("Both hero and villain ranges must be non-empty")

        if pot_size <= 0 or bet_amount <= 0:
            raise ValueError("Pot size and bet amount must be positive")

        logger.info(f"Finding Nash equilibrium: hero_range={len(hero_range)} hands, "
                   f"villain_range={len(villain_range)} hands")

        # Initialize strategies (uniform random)
        hero_strategy = np.random.uniform(0.1, 0.9, len(hero_range))
        villain_strategy = np.random.uniform(0.1, 0.9, len(villain_range))

        prev_hero_strategy = hero_strategy.copy()
        prev_villain_strategy = villain_strategy.copy()

        converged = False
        iterations = 0

        for iteration in range(max_iterations):
            iterations = iteration + 1

            # Hero's best response to villain's current strategy
            hero_strategy = self._find_best_response(
                hero_range, villain_range, villain_strategy,
                pot_size, bet_amount, hero_stack, villain_stack, num_simulations
            )

            # Villain's best response to hero's current strategy
            villain_strategy = self._find_best_response(
                villain_range, hero_range, hero_strategy,
                pot_size, bet_amount, villain_stack, hero_stack, num_simulations
            )

            # Check convergence
            hero_diff = np.max(np.abs(hero_strategy - prev_hero_strategy))
            villain_diff = np.max(np.abs(villain_strategy - prev_villain_strategy))

            max_diff = max(hero_diff, villain_diff)

            if max_diff < tolerance:
                converged = True
                logger.info(f"Nash equilibrium found after {iterations} iterations")
                break

            prev_hero_strategy = hero_strategy.copy()
            prev_villain_strategy = villain_strategy.copy()

        result = {
            'hero_strategy': hero_strategy.tolist(),
            'villain_strategy': villain_strategy.tolist(),
            'equilibrium_found': converged,
            'iterations': iterations,
            'converged': converged,
            'tolerance': tolerance,
            'hero_range_size': len(hero_range),
            'villain_range_size': len(villain_range)
        }

        # Validate best response if requested
        if validate_best_response:
            validation = self._validate_best_response(
                hero_range, villain_range, hero_strategy, villain_strategy,
                pot_size, bet_amount, num_simulations
            )
            result.update(validation)

        return result

    def calculate_range_vs_range_equity(self, hero_range: List[str], villain_range: List[str],
                                       num_simulations: int = 1000) -> Dict[str, float]:
        """
        Calculate equity of hero's range vs villain's range.

        Args:
            hero_range: Hero's hand range
            villain_range: Villain's hand range
            num_simulations: Number of Monte Carlo simulations

        Returns:
            Dict with equity calculations
        """
        logger.info(f"Calculating range vs range equity: {len(hero_range)} vs {len(villain_range)} hands")

        total_hero_wins = 0
        total_villain_wins = 0
        total_ties = 0
        total_simulations = 0

        # Calculate equity for each hero hand vs each villain hand
        for hero_hand in hero_range:
            for villain_hand in villain_range:
                try:
                    # Convert shorthands to card format
                    hero_cards = self._shorthand_to_cards(hero_hand)
                    villain_cards = self._shorthand_to_cards(villain_hand)
                    
                    # Skip if hands share cards (can't occur in same game)
                    hero_card_set = set(hero_cards)
                    villain_card_set = set(villain_cards)
                    if hero_card_set & villain_card_set:  # Intersection not empty
                        logger.debug(f"Skipping {hero_hand} vs {villain_hand}: shared cards {hero_card_set & villain_card_set}")
                        continue

                    # Calculate odds
                    odds_result = self.analyzer.calculate_odds(
                        hero_hole_cards=hero_cards,
                        opponent_hole_cards_list=[villain_cards],
                        board_cards=[],
                        num_simulations=num_simulations
                    )

                    total_hero_wins += odds_result['wins']
                    total_villain_wins += odds_result['valid_simulations'] - odds_result['wins'] - odds_result['ties']  # From hero's perspective
                    total_ties += odds_result['ties']
                    total_simulations += odds_result['valid_simulations']

                except Exception as e:
                    logger.warning(f"Failed to calculate equity for {hero_hand} vs {villain_hand}: {e}")
                    continue

        if total_simulations == 0:
            return {
                'hero_equity': 0.5,
                'villain_equity': 0.5,
                'hero_range_size': len(hero_range),
                'villain_range_size': len(villain_range)
            }

        hero_equity = (total_hero_wins + total_ties * 0.5) / total_simulations
        villain_equity = 1.0 - hero_equity

        return {
            'hero_equity': hero_equity,
            'villain_equity': villain_equity,
            'hero_range_size': len(hero_range),
            'villain_range_size': len(villain_range)
        }

    def find_indifference_points(self, hero_range: List[str], villain_range: List[str],
                               pot_size: float, bet_amount: float) -> Dict[str, Any]:
        """
        Find indifference points for optimal shove frequencies.

        For each hand, finds the frequency at which the expected value is zero
        when facing the opponent's calling range.

        Args:
            hero_range: Hero's hand range
            villain_range: Villain's hand range
            pot_size: Current pot size
            bet_amount: All-in bet amount

        Returns:
            Dict with indifference points and optimal frequencies
        """
        logger.info(f"Finding indifference points for {len(hero_range)} hands")

        indifference_points = {}
        optimal_frequencies = []

        # Calculate equity of each hero hand vs villain's calling range
        calling_range_equity = {}

        for hero_hand in hero_range:
            # Equity when called (villain calls with entire range)
            equity_vs_calling = self.calculate_range_vs_range_equity(
                [hero_hand], villain_range, num_simulations=500
            )['hero_equity']

            calling_range_equity[hero_hand] = equity_vs_calling

            # Indifference point: shove if equity > threshold, fold otherwise
            # Threshold = bet / (pot + 2*bet)
            threshold = bet_amount / (pot_size + 2 * bet_amount)
            
            if equity_vs_calling > threshold:
                indifference_freq = 1.0  # Always shove
            else:
                indifference_freq = 0.0  # Never shove

            indifference_points[hero_hand] = {
                'equity_vs_calling': equity_vs_calling,
                'indifference_frequency': indifference_freq
            }
            optimal_frequencies.append(indifference_freq)

        return {
            'indifference_points': indifference_points,
            'optimal_frequencies': optimal_frequencies,
            'hero_range_size': len(hero_range),
            'villain_range_size': len(villain_range)
        }

    def _find_best_response(self, player_range: List[str], opponent_range: List[str],
                          opponent_strategy: np.ndarray, pot_size: float, bet_amount: float,
                          player_stack: Optional[float] = None,
                          opponent_stack: Optional[float] = None,
                          num_simulations: int = 1000) -> np.ndarray:
        """
        Find best response strategy for one player against opponent's mixed strategy.

        Args:
            player_range: Player's hand range
            opponent_range: Opponent's hand range
            opponent_strategy: Opponent's mixed strategy (frequencies)
            pot_size: Current pot size
            bet_amount: All-in bet amount
            player_stack: Player's stack size
            opponent_stack: Opponent's stack size
            num_simulations: Monte Carlo simulations

        Returns:
            Best response frequencies for player's range
        """
        best_response = np.zeros(len(player_range))

        for i, hand in enumerate(player_range):
            # Calculate equity vs opponent's calling range
            calling_range = [opp_hand for opp_hand, freq in zip(opponent_range, opponent_strategy) if freq > 0.01]
            if not calling_range:
                calling_range = opponent_range  # Fallback if no hands are being played

            equity_vs_calling = self.calculate_range_vs_range_equity(
                [hand], calling_range, num_simulations
            )['hero_equity']

            # Calculate fold equity (effective stack consideration)
            fold_equity = self._calculate_fold_equity(player_stack, opponent_stack, pot_size, bet_amount)

            # Best response: shove if equity vs calling range > fold equity
            if equity_vs_calling > fold_equity:
                best_response[i] = 1.0
            else:
                best_response[i] = 0.0

        return best_response

    def _calculate_fold_equity(self, player_stack: Optional[float],
                             opponent_stack: Optional[float],
                             pot_size: float, bet_amount: float) -> float:
        """
        Calculate fold equity considering stack sizes and ICM.

        Args:
            player_stack: Player's remaining stack
            opponent_stack: Opponent's remaining stack
            pot_size: Current pot size
            bet_amount: All-in bet amount

        Returns:
            Effective fold equity (0-1)
        """
        if player_stack is None or opponent_stack is None:
            # No ICM consideration - fold equity is 0
            return 0.0

        # Simple ICM approximation: fold equity based on stack ratio
        total_stacks = player_stack + opponent_stack
        if total_stacks == 0:
            return 0.0

        stack_ratio = player_stack / total_stacks

        # Higher fold equity if player has more chips
        fold_equity = min(0.3, stack_ratio * 0.5)  # Cap at 30%

        return fold_equity

    def _validate_best_response(self, hero_range: List[str], villain_range: List[str],
                              hero_strategy: np.ndarray, villain_strategy: np.ndarray,
                              pot_size: float, bet_amount: float,
                              num_simulations: int = 500) -> Dict[str, Any]:
        """
        Validate that strategies are best responses to each other.

        Args:
            hero_range: Hero's hand range
            villain_range: Villain's hand range
            hero_strategy: Hero's strategy
            villain_strategy: Villain's strategy
            pot_size: Pot size
            bet_amount: Bet amount
            num_simulations: Simulations for validation

        Returns:
            Validation results
        """
        # Check hero's strategy against villain's
        hero_best_response = self._find_best_response(
            hero_range, villain_range, villain_strategy,
            pot_size, bet_amount, num_simulations=num_simulations
        )

        # Check villain's strategy against hero's
        villain_best_response = self._find_best_response(
            villain_range, hero_range, hero_strategy,
            pot_size, bet_amount, num_simulations=num_simulations
        )

        # Calculate deviations
        hero_deviation = np.max(np.abs(hero_strategy - hero_best_response))
        villain_deviation = np.max(np.abs(villain_strategy - villain_best_response))

        max_deviation = max(hero_deviation, villain_deviation)
        is_valid = bool(max_deviation < 0.1)  # Allow small deviations

        return {
            'best_response_valid': is_valid,
            'max_deviation': max_deviation,
            'hero_deviation': hero_deviation,
            'villain_deviation': villain_deviation,
            'deviation_analysis': {
                'hero_best_response': hero_best_response.tolist(),
                'villain_best_response': villain_best_response.tolist()
            }
        }

    def _shorthand_to_cards(self, shorthand: str) -> List[str]:
        """
        Convert poker shorthand to card list.

        Args:
            shorthand: Hand shorthand (e.g., 'AKs', '22')

        Returns:
            List of two cards
        """
        if len(shorthand) == 2:
            # Pocket pair
            rank1, rank2 = shorthand[0], shorthand[1]
            if rank1 == rank2:
                # Different suits for pair
                return [f"{rank1}h", f"{rank2}d"]
        elif len(shorthand) == 3:
            # Suited or offsuit
            rank1, rank2, suit_type = shorthand[0], shorthand[1], shorthand[2]
            if suit_type.lower() == 's':
                return [f"{rank1}h", f"{rank2}h"]  # Same suit
            else:
                return [f"{rank1}h", f"{rank2}d"]  # Different suits

        # Default fallback
        return ["Ah", "Kd"]