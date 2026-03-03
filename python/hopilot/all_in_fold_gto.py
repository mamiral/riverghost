"""
GTO Solver for All-In-or-Fold Poker with Bonus Payouts

This module implements Game Theory Optimal strategy calculation for simplified
all-in-or-fold poker games, accounting for bonus payouts on special hands like
flush straights.
"""

from typing import Dict, List, Optional, Tuple, Set
import math
from hopilot.logging_config import get_logger
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.hand_range import HandRange

logger = get_logger(__name__)


class AllInFoldGTOSolver:
    """
    GTO solver for all-in-or-fold poker games with bonus payouts.

    In all-in-or-fold, each player either folds or goes all-in preflop.
    The optimal strategy is determined by finding the equity threshold where EV = 0.
    """

    def __init__(self, analyzer: PokerAnalyzer):
        self.analyzer = analyzer
        self.logger = get_logger(__name__)

        # Default bonus payouts (can be customized)
        self.bonus_payouts = {
            'royal_flush': 500,      # Royal flush
            'straight_flush': 100,   # Straight flush (non-royal)
            'four_of_a_kind': 50,    # Quads
            'full_house': 10,        # Full house
            'flush': 5,              # Flush
            'straight': 4,           # Straight
            'three_of_a_kind': 3,    # Trips
            'two_pair': 2,           # Two pair
            'one_pair': 1,           # One pair
        }

        # Result caching for performance
        self._cache = {}

    def set_bonus_payouts(self, payouts: Dict[str, float]):
        """Set custom bonus payout multipliers."""
        if not isinstance(payouts, dict):
            raise TypeError("payouts must be a dictionary")
        
        for key, value in payouts.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Bonus payout for {key} must be a number")
            if value < 0:
                raise ValueError(f"Bonus payout for {key} cannot be negative")
        
        self.bonus_payouts = payouts.copy()
        self._cache.clear()  # Clear cache when payouts change

    def _get_hand_category(self, hole_cards: List[str], board_cards: List[str]) -> str:
        """Get the hand category for bonus payout calculation."""
        try:
            # For preflop analysis, we can't determine the final hand
            if not board_cards:
                return 'high_card'
            
            hand = self.analyzer.get_hand_class(hole_cards, board_cards)
            hand_lower = hand.lower()

            # Special case: Check for royal flush (straight flush with royal cards)
            all_cards = hole_cards + board_cards
            suits = [card[1] for card in all_cards]
            ranks = [card[0] for card in all_cards]
            
            # Check if all cards are same suit
            if len(set(suits)) == 1:
                suit = suits[0]
                # Check for royal flush ranks
                royal_ranks = {'A', 'K', 'Q', 'J', 'T'}
                if royal_ranks.issubset(set(ranks)):
                    return 'royal_flush'

            # Map hand classes to bonus categories
            if 'straight flush' in hand_lower:
                return 'straight_flush'
            elif 'four of a kind' in hand_lower or 'quads' in hand_lower:
                return 'four_of_a_kind'
            elif 'full house' in hand_lower:
                return 'full_house'
            elif 'flush' in hand_lower:
                return 'flush'
            elif 'straight' in hand_lower:
                return 'straight'
            elif 'three of a kind' in hand_lower or 'trips' in hand_lower:
                return 'three_of_a_kind'
            elif 'two pair' in hand_lower:
                return 'two_pair'
            elif 'pair' in hand_lower or 'one pair' in hand_lower:
                return 'one_pair'
            else:
                return 'high_card'
        except:
            return 'high_card'

    def _calculate_ev_with_bonus(self, hole_cards: List[str], board_cards: List[str],
                                equity: float, pot_size: float, bet_amount: float) -> float:
        """
        Calculate expected value including bonus payouts.

        Args:
            hole_cards: Player's hole cards
            board_cards: Community cards
            equity: Win probability (0-1)
            pot_size: Current pot size
            bet_amount: All-in bet amount

        Returns:
            Expected value of the hand
        """
        # Standard poker EV
        call_ev = equity * pot_size - (1 - equity) * bet_amount

        # Add bonus payout EV
        hand_category = self._get_hand_category(hole_cards, board_cards)
        bonus_multiplier = self.bonus_payouts.get(hand_category, 0)

        if bonus_multiplier > 0:
            # Bonus is paid when you win, so multiply equity by bonus
            bonus_ev = equity * (pot_size * bonus_multiplier)
            total_ev = call_ev + bonus_ev
        else:
            total_ev = call_ev

        return total_ev

    def find_gto_threshold(self, num_opponents: int = 8, pot_size: float = 20,
                          bet_amount: float = 10, num_simulations: int = 5000,
                          progress_callback=None, cancel_check=None) -> Dict:
        """
        Find the GTO equity threshold for all-in-or-fold.

        Returns the minimum equity required to profitably call all-in.

        Args:
            num_opponents: Number of opponents
            pot_size: Current pot size before bet
            bet_amount: All-in bet amount
            num_simulations: Monte Carlo simulations per hand
            progress_callback: Optional callback for progress updates (progress: float, message: str)
            cancel_check: Optional function that returns True if calculation should be cancelled

        Returns:
            Dict with threshold equity and analysis data
        """
        # Parameter validation
        if not isinstance(num_opponents, int) or not (1 <= num_opponents <= 9):
            raise ValueError("num_opponents must be an integer between 1 and 9")
        if not isinstance(pot_size, (int, float)) or pot_size <= 0:
            raise ValueError("pot_size must be a positive number")
        if not isinstance(bet_amount, (int, float)) or bet_amount <= 0:
            raise ValueError("bet_amount must be a positive number")
        if not isinstance(num_simulations, int) or not (100 <= num_simulations <= 10000):
            raise ValueError("num_simulations must be an integer between 100 and 10000")

        # Check cache first
        cache_key = (num_opponents, pot_size, bet_amount, num_simulations, tuple(sorted(self.bonus_payouts.items())))
        if cache_key in self._cache:
            self.logger.info("Returning cached GTO result")
            return self._cache[cache_key]

        self.logger.info(f"Calculating GTO threshold: opponents={num_opponents}, "
                        f"pot={pot_size}, bet={bet_amount}")

        # Get all possible starting hands (1326 total)
        # For testing/development, sample a subset to speed up calculations
        import random
        random.seed(42)  # For reproducible results
        
        all_hands = []
        for rank1 in 'AKQJT98765432':
            for rank2 in 'AKQJT98765432':
                for suit1 in 'shcd':
                    for suit2 in 'shcd':
                        if rank1 + suit1 != rank2 + suit2:  # No duplicate cards
                            hand = [rank1 + suit1, rank2 + suit2]
                            all_hands.append(hand)
        
        # Sample a subset for faster testing (adjust as needed)
        sample_size = min(500, len(all_hands))  # Sample 500 hands for testing
        sampled_hands = random.sample(all_hands, sample_size)
        
        self.logger.info(f"Evaluating {len(sampled_hands)} sampled starting hands...")

        # Sort hands by equity (we'll calculate this)
        hand_equities = []

        for i, hand in enumerate(sampled_hands):
            if cancel_check and cancel_check():
                self.logger.info("GTO calculation cancelled")
                return {'cancelled': True}

            if progress_callback:
                progress = (i + 1) / len(sampled_hands)
                progress_callback(progress, f"Evaluating hand {i+1}/{len(sampled_hands)}")

            if i % 50 == 0:  # Log less frequently
                self.logger.debug(f"Evaluated {i}/{len(sampled_hands)} hands")

            # Calculate equity vs random opponents
            equity_result = self.analyzer.calculate_odds_random_opponents(
                hero_hole_cards=hand,
                board_cards=[],  # Preflop
                num_opponents=num_opponents,
                num_simulations=num_simulations
            )

            if equity_result:
                equity = equity_result['win_probability']
                ev = self._calculate_ev_with_bonus(hand, [], equity, pot_size, bet_amount)
                hand_equities.append({
                    'hand': hand,
                    'shorthand': HandRange.shorthand_from_cards(hand),
                    'equity': equity,
                    'ev': ev
                })

        # Sort by EV (descending)
        hand_equities.sort(key=lambda x: x['ev'], reverse=True)

        # Find the threshold where EV becomes positive
        # Hands with positive EV should be played, negative should fold
        positive_ev_hands = [h for h in hand_equities if h['ev'] > 0]
        negative_ev_hands = [h for h in hand_equities if h['ev'] <= 0]

        if not positive_ev_hands:
            threshold_equity = 1.0  # No hands are profitable
        elif not negative_ev_hands:
            threshold_equity = 0.0  # All hands are profitable
        else:
            # Threshold is the equity of the worst positive EV hand
            threshold_equity = min(h['equity'] for h in positive_ev_hands)

        # Calculate optimal range
        optimal_range = [h['shorthand'] for h in positive_ev_hands]

        result = {
            'threshold_equity': threshold_equity,
            'optimal_hands': len(positive_ev_hands),
            'total_hands': len(hand_equities),
            'sampled_hands': len(sampled_hands),
            'optimal_range': optimal_range,
            'top_10_hands': hand_equities[:10],
            'bottom_10_hands': hand_equities[-10:],
            'bonus_payouts': self.bonus_payouts.copy()
        }

        # Cache the result
        self._cache[cache_key] = result

        self.logger.info(f"GTO threshold found: {threshold_equity:.3f} equity "
                        f"({len(positive_ev_hands)}/{len(hand_equities)} hands profitable)")

        return result

    def analyze_hand_strategy(self, hole_cards: List[str], num_opponents: int = 8,
                            pot_size: float = 20, bet_amount: float = 10,
                            num_simulations: int = 5000) -> Dict:
        """
        Analyze whether a specific hand should be played in all-in-or-fold.

        Args:
            hole_cards: The hand to analyze
            num_opponents: Number of opponents
            pot_size: Current pot size
            bet_amount: All-in bet amount
            num_simulations: Monte Carlo simulations

        Returns:
            Dict with strategy recommendation and EV analysis
        """
        # Parameter validation
        if not isinstance(hole_cards, list) or len(hole_cards) != 2:
            raise ValueError("hole_cards must be a list of exactly 2 card strings")
        if not isinstance(num_opponents, int) or not (1 <= num_opponents <= 9):
            raise ValueError("num_opponents must be an integer between 1 and 9")
        if not isinstance(pot_size, (int, float)) or pot_size <= 0:
            raise ValueError("pot_size must be a positive number")
        if not isinstance(bet_amount, (int, float)) or bet_amount <= 0:
            raise ValueError("bet_amount must be a positive number")
        if not isinstance(num_simulations, int) or not (100 <= num_simulations <= 10000):
            raise ValueError("num_simulations must be an integer between 100 and 10000")

        # Calculate equity
        equity_result = self.analyzer.calculate_odds_random_opponents(
            hero_hole_cards=hole_cards,
            board_cards=[],
            num_opponents=num_opponents,
            num_simulations=num_simulations
        )

        if not equity_result:
            return {'error': 'Could not calculate equity'}

        equity = equity_result['win_probability']
        ev = self._calculate_ev_with_bonus(hole_cards, [], equity, pot_size, bet_amount)

        hand_category = self._get_hand_category(hole_cards, [])
        bonus_multiplier = self.bonus_payouts.get(hand_category, 0)

        recommendation = "ALL-IN" if ev > 0 else "FOLD"

        return {
            'hand': hole_cards,
            'shorthand': HandRange.shorthand_from_cards(hole_cards),
            'equity': equity,
            'ev': ev,
            'hand_category': hand_category,
            'bonus_multiplier': bonus_multiplier,
            'recommendation': recommendation,
            'pot_size': pot_size,
            'bet_amount': bet_amount,
            'num_opponents': num_opponents
        }