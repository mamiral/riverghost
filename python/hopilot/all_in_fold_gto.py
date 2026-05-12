"""
GTO Solver for All-In-or-Fold Poker with Bonus Payouts

This module implements Game Theory Optimal strategy calculation for simplified
all-in-or-fold poker games, accounting for bonus payouts on special hands like
flush straights.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import math
from hopilot.logging_config import get_logger
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.database.persistence import GameStatePersistence
from hopilot.hand_range import HandRange

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None


class AllInFoldGTOSolver:
    """
    GTO solver for all-in-or-fold poker games with bonus payouts.

    In all-in-or-fold, each player either folds or goes all-in preflop.
    The optimal strategy is determined by finding the equity threshold where EV = 0.
    """

    def __init__(self, analyzer: PokerAnalyzer, persistence: Optional[GameStatePersistence] = None):
        self.analyzer = analyzer
        self.persistence = persistence
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
                                equity: float, pot_size: float, bb: float, rake: float, posted_blind: float) -> float:
        """
        Calculate expected value including bonus payouts.

        Args:
            hole_cards: Player's hole cards
            board_cards: Community cards
            equity: Win probability (0-1)
            pot_size: Current pot size
            bb: Big blind amount
            rake: Rake percentage (0-1)
            posted_blind: Amount already posted (for baseline adjustment)

        Returns:
            Expected value relative to folding
        """
        effective_pot = pot_size * (1 - rake)
        # Standard poker EV: weighted by win/loss probabilities
        call_ev = (equity * effective_pot) - ((1.0 - equity) * bb)

        # Add bonus payout EV
        hand_category = self._get_hand_category(hole_cards, board_cards)
        bonus_multiplier = self.bonus_payouts.get(hand_category, 0)

        if bonus_multiplier > 0:
            # Bonus is paid when you win, so multiply equity by bonus
            bonus_ev = equity * (effective_pot * bonus_multiplier)
            total_ev = call_ev + bonus_ev
        else:
            total_ev = call_ev

        # Adjust for posted blind to get EV relative to folding
        return total_ev - posted_blind

    def solve(self, hero_hole: List[str], villain_hole: List[str], board_cards: List[str] = None,
              pot_size: float = 20, bb: float = 10, rake: float = 0.0) -> Dict:
        """
        Solve GTO for a specific hero vs villain all-in scenario.

        Args:
            hero_hole: Hero's hole cards (exactly 2)
            villain_hole: Villain's hole cards (exactly 2)
            board_cards: Community cards (optional)
            pot_size: Current pot size before bet
            bb: Big blind amount
            rake: Rake percentage (0-1)

        Returns:
            Dict with GTO analysis for the matchup
        """
        if board_cards is None:
            board_cards = []

        # Parameter validation
        if not isinstance(hero_hole, list) or len(hero_hole) != 2:
            raise ValueError("hero_hole must be a list of exactly 2 card strings")
        if not isinstance(villain_hole, list) or len(villain_hole) != 2:
            raise ValueError("villain_hole must be a list of exactly 2 card strings")
        if not isinstance(board_cards, list):
            raise ValueError("board_cards must be a list")
        if not isinstance(pot_size, (int, float)) or pot_size <= 0:
            raise ValueError("pot_size must be a positive number")
        if not isinstance(bb, (int, float)) or bb <= 0:
            raise ValueError("bb must be a positive number")
        if not isinstance(rake, (int, float)) or not (0 <= rake <= 1):
            raise ValueError("rake must be a number between 0 and 1")

        # Check for duplicate cards
        all_cards = hero_hole + villain_hole + board_cards
        if len(all_cards) != len(set(all_cards)):
            raise ValueError("Duplicate cards are not allowed")

        # Calculate equity
        equity_result = self.analyzer.calculate_odds(
            hero_hole_cards=hero_hole,
            opponent_hole_cards_list=[villain_hole],
            board_cards=board_cards,
            num_simulations=10000  # Use high simulation count for accuracy
        )

        if not equity_result:
            return {'error': 'Could not calculate equity'}

        hero_equity = equity_result['win_probability']
        hero_ev = self._calculate_ev_with_bonus(hero_hole, board_cards, hero_equity, pot_size + bb, bb, rake, 0.5 * bb)

        # For villain, equity is 1 - hero_equity, and they don't have to call (they're the bettor)
        villain_equity = 1 - hero_equity
        villain_ev = villain_equity * ((pot_size + bb) * (1 - rake)) - (1 - villain_equity) * bb - bb

        # Get hand categories for bonus analysis
        hero_category = self._get_hand_category(hero_hole, board_cards)
        villain_category = self._get_hand_category(villain_hole, board_cards)

        hero_bonus = self.bonus_payouts.get(hero_category, 0)
        villain_bonus = self.bonus_payouts.get(villain_category, 0)

        # Hero strategy: call if EV > 0
        hero_strategy = "CALL" if hero_ev > 0 else "FOLD"
        villain_strategy = "ALL-IN"  # Villain already bet

        return {
            'hero_hole': hero_hole,
            'villain_hole': villain_hole,
            'board_cards': board_cards,
            'hero_equity': hero_equity,
            'villain_equity': villain_equity,
            'hero_ev': hero_ev,
            'villain_ev': villain_ev,
            'hero_strategy': hero_strategy,
            'villain_strategy': villain_strategy,
            'hero_category': hero_category,
            'villain_category': villain_category,
            'hero_bonus_multiplier': hero_bonus,
            'villain_bonus_multiplier': villain_bonus,
            'pot_size': pot_size,
            'bb': bb,
            'rake': rake,
            'total_pot': pot_size + bet_amount
        }

    def _detect_jackpot(self, hole_cards: List[str], board_cards: List[str] = None) -> Optional[Dict]:
        """
        Detect if a hand qualifies for a jackpot payout.

        Args:
            hole_cards: Player's hole cards
            board_cards: Community cards (optional)

        Returns:
            Dict with jackpot info if detected, None otherwise
        """
        if board_cards is None:
            board_cards = []

        all_cards = hole_cards + board_cards

        # Need at least 5 cards to form a hand
        if len(all_cards) < 5:
            return None

        # Convert cards to ranks and suits
        ranks = []
        suits = []
        for card in all_cards:
            if len(card) == 2:
                rank, suit = card[0], card[1]
            else:
                # Handle 10 (like 'Ts', 'Td', etc.)
                rank, suit = card[:1], card[1:]
            
            ranks.append(rank)
            suits.append(suit)

        # Check for royal flush
        royal_ranks = {'A', 'K', 'Q', 'J', 'T'}
        if set(ranks) == royal_ranks and len(set(suits)) == 1:
            return {
                'type': 'royal_flush',
                'payout_multiplier': 500,
                'cards_used': all_cards
            }

        # Check for straight flush (non-royal)
        # This is a simplified check - in practice would need more sophisticated logic
        if len(set(suits)) == 1:  # All same suit
            rank_values = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14}
            numeric_ranks = sorted([rank_values.get(r, 0) for r in ranks], reverse=True)
            
            # Check for consecutive ranks
            for i in range(len(numeric_ranks) - 4):
                if numeric_ranks[i] - numeric_ranks[i+4] == 4:
                    # Not royal flush (already checked above)
                    if not (numeric_ranks[i] == 14 and numeric_ranks[i+4] == 10):
                        return {
                            'type': 'straight_flush',
                            'payout_multiplier': 100,
                            'cards_used': all_cards
                        }

        # Check for four of a kind
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        if 4 in rank_counts.values():
            return {
                'type': 'four_of_a_kind',
                'payout_multiplier': 50,
                'cards_used': all_cards
            }

        # Check for full house
        if 3 in rank_counts.values() and 2 in rank_counts.values():
            return {
                'type': 'full_house',
                'payout_multiplier': 10,
                'cards_used': all_cards
            }

        # Check for flush
        if len(set(suits)) == 1 and len(all_cards) >= 5:
            return {
                'type': 'flush',
                'payout_multiplier': 5,
                'cards_used': all_cards
            }

        # Check for straight
        # Simplified straight detection
        if len(set(ranks)) >= 5:
            numeric_ranks = sorted([rank_values.get(r, 0) for r in set(ranks)], reverse=True)
            for i in range(len(numeric_ranks) - 4):
                if numeric_ranks[i] - numeric_ranks[i+4] == 4:
                    return {
                        'type': 'straight',
                        'payout_multiplier': 4,
                        'cards_used': all_cards
                    }

        # Check for three of a kind
        if 3 in rank_counts.values():
            return {
                'type': 'three_of_a_kind',
                'payout_multiplier': 3,
                'cards_used': all_cards
            }

        # Check for two pair
        pair_count = sum(1 for count in rank_counts.values() if count == 2)
        if pair_count >= 2:
            return {
                'type': 'two_pair',
                'payout_multiplier': 2,
                'cards_used': all_cards
            }

        # Check for one pair
        if 2 in rank_counts.values():
            return {
                'type': 'one_pair',
                'payout_multiplier': 1,
                'cards_used': all_cards
            }

        return None

    def evaluate_hand_key(
        self,
        hand_key: str,
        num_opponents: int,
        pot_size: float,
        bet_amount: float,
        timeout_ms: int | None = None,
        matrix_cell_id: int = 0
    ) -> dict[str, Any]:
        """
        Evaluate a shorthand hand by simulating sampled concrete combos.
        
        This replaces the AoFSolverAdapter functionality by directly using
        AllInFoldGTOSolver with combo expansion.
        """
        if matrix_cell_id and matrix_cell_id > 0:
            raise ValueError(
                "matrix_cell_id-coupled sweep execution is not supported here; use MatrixSweepService"
            )

        if not hand_key:
            return {"status": "MISSING", "reason": "NO_HAND_KEY", "value": None}

        # Expand hand key to concrete card combos
        combos = HandRange.parse_shorthand(hand_key)
        if not combos:
            return {
                "status": "MISSING",
                "reason": "NO_VALID_COMBOS",
                "value": None,
                "combo_results": [],
            }

        combo_results: list[dict[str, Any]] = []
        all_individual_outcomes: list[dict[str, Any]] = []
        
        # Sample combos (limit to reasonable number for performance)
        max_combos = min(len(combos), 10)  # Sample up to 10 combos
        sampled_combos = combos[:max_combos]

        for combo in sampled_combos:
            # Convert tuple to list of card strings
            hole_cards = [combo[0], combo[1]]
            
            result = self._analyze_hand_without_storage(
                hole_cards=hole_cards,
                num_opponents=num_opponents,
                pot_size=pot_size,
                bet_amount=bet_amount,
                num_simulations=500,
                return_individual_outcomes=True,
            )
            
            # Format result for compatibility
            combo_result = {
                "is_valid": True,
                "win_probability": result["equity"],
                "equity": result["equity"],
                "ev": result["ev"],
                "hand_key": hand_key,
                "hole_cards": hole_cards,
                "individual_outcomes": result.get("individual_outcomes", [])
            }
            combo_results.append(combo_result)
            all_individual_outcomes.extend(result.get("individual_outcomes", []))

        if not combo_results:
            return {
                "status": "MISSING",
                "reason": "NO_VALID_COMBOS",
                "value": None,
                "combo_results": combo_results,
                "individual_outcomes": all_individual_outcomes,
            }

        # Average results across combos
        win_prob = sum(float(r["win_probability"]) for r in combo_results) / len(combo_results)
        equity = sum(float(r["equity"]) for r in combo_results) / len(combo_results)
        ev = sum(float(r["ev"]) for r in combo_results) / len(combo_results)

        return {
            "status": "AVAILABLE",
            "win_probability": round(win_prob, 4),
            "equity": round(equity, 4),
            "ev": round(ev, 4),
            "source": "solver",
            "sampled_combos": len(sampled_combos),
            "total_combos": len(combos),
            "combo_results": combo_results,
            "individual_outcomes": all_individual_outcomes,
        }

    def _analyze_hand_without_storage(
        self,
        hole_cards: List[str],
        num_opponents: int,
        pot_size: float,
        bet_amount: float,
        num_simulations: int,
        return_individual_outcomes: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze a hand without storing GameStates in the database.
        
        For preflop all-in analysis, uses equity calculation vs random opponents.
        """
        # For preflop all-in, we can use the equity calculator directly
        # since we're only interested in win probability vs random hands
        equity_result = self.analyzer.calculate_odds_random_opponents(
            hero_hole_cards=hole_cards,
            board_cards=[],  # Preflop
            num_opponents=num_opponents,
            num_simulations=num_simulations,
            return_individual_outcomes=return_individual_outcomes,
        )
        
        if not equity_result:
            return {
                "equity": 0.0,
                "ev": -bet_amount,
                "win_probability": 0.0,
                "simulations_run": 0,
                "individual_outcomes": []
            }
        
        equity = equity_result['win_probability']
        # Calculate EV from total showdown pot net of the hero's risk.
        ev = equity * pot_size - bet_amount
        
        return {
            "equity": equity,
            "ev": ev,
            "win_probability": equity,
            "simulations_run": equity_result.get('valid_simulations', num_simulations),
            "individual_outcomes": equity_result.get('individual_outcomes', [])
        }