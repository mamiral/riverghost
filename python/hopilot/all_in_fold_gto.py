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
        call_ev = equity * pot_size - bet_amount

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
        
        self.logger.debug(f"Evaluating {len(sampled_hands)} sampled starting hands...")

        progress_bar = None
        if progress_callback is None and tqdm is not None:
            progress_bar = tqdm(
                total=len(sampled_hands),
                desc="GTO hand evaluation",
                unit="hand",
                dynamic_ncols=True,
            )

        # Sort hands by equity (we'll calculate this)
        hand_equities = []

        try:
            for i, hand in enumerate(sampled_hands):
                if cancel_check and cancel_check():
                    self.logger.info("GTO calculation cancelled")
                    return {'cancelled': True}

                if progress_callback:
                    progress = (i + 1) / len(sampled_hands)
                    progress_callback(progress, f"Evaluating hand {i+1}/{len(sampled_hands)}")
                elif progress_bar is not None:
                    progress_bar.update(1)

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
        finally:
            if progress_bar is not None:
                progress_bar.close()

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
                            num_simulations: int = 5000, matrix_cell_id: int = 0) -> Dict:
        """
        Analyze whether a specific hand should be played in all-in-or-fold.

        Args:
            hole_cards: The hand to analyze
            num_opponents: Number of opponents
            pot_size: Current pot size
            bet_amount: All-in bet amount
            num_simulations: Monte Carlo simulations
            matrix_cell_id: ID of the matrix cell this analysis belongs to

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

        # Run Monte Carlo simulations and store genuine game states
        import random
        from datetime import datetime
        
        random.seed(42)  # For reproducible results
        wins = 0
        total_simulations = 0
        
        # Create a simulation ID for this analysis
        simulation_id = hash(f"{hole_cards}_{num_opponents}_{num_simulations}_{datetime.now().isoformat()}")
        
        for sim_num in range(num_simulations):
            total_simulations += 1
            # Determine actual pot from all-in hero bet and opponent calls
            actual_pot_size = bet_amount * (1 + num_opponents) if bet_amount > 0 else 0.0

            # Create game state for this simulation
            timestamp = datetime.now().isoformat()
            game_state_id = self.persistence.store_game_state(
                timestamp=timestamp,
                round_name='preflop',
                pot_size=actual_pot_size,
                board_cards=[],  # No board cards in preflop all-in
                outcome='pending'  # Will update after determining winner
            )
            
            # Store hero player
            hero_hand_class = self.analyzer.get_hand_class_value(hole_cards, [])
            hero_strength = self.analyzer.evaluate_hand(hole_cards, [])
            hero_id = self.persistence.store_player(
                game_state_id=game_state_id,
                position='HERO',
                hole_cards=hole_cards,
                stack_size=100.0,  # Default stack
                is_hero=True,
                hand_class=hero_hand_class,
                final_strength=hero_strength
            )
            
            # Store hero's all-in bet
            if bet_amount > 0.0:
                self.persistence.store_bet(
                    game_state_id=game_state_id,
                    player_id=hero_id,
                    amount=bet_amount,
                    action_type='raise'  # All-in is a raise
                )
            
            # Generate random opponent hands
            available_cards = [r + s for r in '23456789TJQKA' for s in 'shdc' 
                             if r + s not in hole_cards]
            
            opponent_hands = []
            for opp_num in range(num_opponents):
                # Select 2 random cards for opponent
                opp_cards = random.sample(available_cards, 2)
                available_cards = [c for c in available_cards if c not in opp_cards]
                
                # Store opponent player
                opp_hand_class = self.analyzer.get_hand_class_value(opp_cards, [])
                opp_strength = self.analyzer.evaluate_hand(opp_cards, [])
                opp_id = self.persistence.store_player(
                    game_state_id=game_state_id,
                    position=f'OPP{opp_num}',
                    hole_cards=opp_cards,
                    stack_size=100.0,
                    is_hero=False,
                    hand_class=opp_hand_class,
                    final_strength=opp_strength
                )
                
                # Opponents call the hero's all-in
                if bet_amount > 0.0:
                    self.persistence.store_bet(
                        game_state_id=game_state_id,
                        player_id=opp_id,
                        amount=bet_amount,
                        action_type='call'
                    )
                
                opponent_hands.append(opp_cards)
            
            # Determine winner by evaluating all hands
            all_hands = [hole_cards] + opponent_hands
            hand_strengths = []
            
            for hand in all_hands:
                strength = self.analyzer.evaluate_hand(hand, [])
                hand_strengths.append(strength)
            
            # Filter out None strengths (invalid hands) and determine winner
            valid_hands = [(i, strength) for i, strength in enumerate(hand_strengths) if strength is not None]
            
            if not valid_hands:
                # No valid hands - this shouldn't happen, but handle it
                outcome = 'invalid_hands'
                hero_wins = False
            else:
                # Hero wins if they have the best valid hand
                hero_strength = hand_strengths[0]
                if hero_strength is None:
                    # Hero's hand is invalid
                    hero_wins = False
                else:
                    # Compare hero's strength against all other valid hands
                    other_valid_strengths = [s for i, s in valid_hands if i > 0 and s is not None]
                    hero_wins = all(s < hero_strength for s in other_valid_strengths)
            
            if hero_wins:
                wins += 1
                outcome = 'hero_win'
            else:
                outcome = 'hero_loss'
            
            # Update game state with final outcome
            self.persistence.update_game_state_outcome(game_state_id, outcome)
            
            # Check for jackpot if hero won
            if hero_wins:
                jackpot = self._detect_jackpot(hole_cards, [])
                if jackpot:
                    self.persistence.store_jackpot(
                        game_state_id=game_state_id,
                        player_id=hero_id,
                        jackpot_type=jackpot['type'],
                        payout_amount=jackpot['payout_multiplier'] * bet_amount,
                        cards_used=jackpot['cards_used']
                    )
            
            # Update game state with final outcome
            # Note: In a real implementation, we'd update the stored game state
            # For now, we'll just use the outcome for statistics
        
        # Calculate final equity and EV
        equity = wins / total_simulations if total_simulations > 0 else 0.0
        ev = self._calculate_ev_with_bonus(hole_cards, [], equity, pot_size, bet_amount)
        
        # Commit all stored data
        self.persistence.commit_transaction()
        
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
            'num_opponents': num_opponents,
            'simulations_run': total_simulations,
            'genuine_data_stored': True
        }

    def solve(self, hero_hole: List[str], villain_hole: List[str], board_cards: List[str] = None,
              pot_size: float = 20, bet_amount: float = 10) -> Dict:
        """
        Solve GTO for a specific hero vs villain all-in scenario.

        Args:
            hero_hole: Hero's hole cards (exactly 2)
            villain_hole: Villain's hole cards (exactly 2)
            board_cards: Community cards (optional)
            pot_size: Current pot size before bet
            bet_amount: All-in bet amount

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
        if not isinstance(bet_amount, (int, float)) or bet_amount <= 0:
            raise ValueError("bet_amount must be a positive number")

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
        hero_ev = self._calculate_ev_with_bonus(hero_hole, board_cards, hero_equity, pot_size, bet_amount)

        # For villain, equity is 1 - hero_equity, and they don't have to call (they're the bettor)
        villain_equity = 1 - hero_equity
        villain_ev = villain_equity * (pot_size + bet_amount) - (1 - villain_equity) * bet_amount

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
            'bet_amount': bet_amount,
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

        # For evaluation (when matrix_cell_id is 0 or None), don't store GameStates
        # Just run the analysis without persistence
        eval_mode = not matrix_cell_id or matrix_cell_id <= 0
        
        for combo in sampled_combos:
            # Convert tuple to list of card strings
            hole_cards = [combo[0], combo[1]]
            
            if eval_mode:
                # Run analysis without storing GameStates, but still capture individual outcomes
                result = self._analyze_hand_without_storage(
                    hole_cards=hole_cards,
                    num_opponents=num_opponents,
                    pot_size=pot_size,
                    bet_amount=bet_amount,
                    num_simulations=500,
                    return_individual_outcomes=True,
                )
            else:
                # Normal analysis with GameState storage
                result = self.analyze_hand_strategy(
                    hole_cards=hole_cards,
                    num_opponents=num_opponents,
                    pot_size=pot_size,
                    bet_amount=bet_amount,
                    num_simulations=500,
                    matrix_cell_id=matrix_cell_id
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