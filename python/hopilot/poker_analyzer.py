import os
import random
from datetime import datetime, timezone
from itertools import combinations
from typing import List, Dict, Optional, Any

from pokerkit.hands import StandardHighHand
from pokerkit.utilities import Card as PokerkitCard, Deck as PokerkitDeck, Rank as PokerkitRank

from hopilot.logging_config import get_logger
from hopilot.hand_range import expand_range_to_hands, HandRange


class PokerAnalyzer:
    def __init__(self):
        self.evaluator = StandardHighHand
        self.logger = get_logger(__name__)
        self.logger.info("PokerAnalyzer initialized")
        
        # Using PokerKit library for robust poker hand evaluation

    def _lookup_key(self, cards: List[PokerkitCard]) -> tuple[int, bool]:
        return StandardHighHand.lookup._get_key(cards)

    def _best_standard_high_hand_entry(self, hole_cards: List[PokerkitCard], board_cards: List[PokerkitCard]):
        cards = tuple(hole_cards) + tuple(board_cards)
        best_entry = None
        entry_table = StandardHighHand.lookup._Lookup__entries

        for combo in combinations(cards, 5):
            entry = entry_table.get(self._lookup_key(list(combo)))
            if entry is None:
                continue
            if best_entry is None or entry.index > best_entry.index:
                best_entry = entry

        if best_entry is None:
            raise ValueError("No valid high hand entry found")

        return best_entry

    def _map_entry_label_to_hand_class(self, entry_label) -> str:
        label = str(entry_label).lower()

        if "royal flush" in label:
            return "royal_flush"
        if "straight flush" in label:
            return "straight_flush"
        if "four of a kind" in label:
            return "four_of_a_kind"
        if "full house" in label:
            return "full_house"
        if "flush" in label:
            return "flush"
        if "straight" in label:
            return "straight"
        if "three of a kind" in label:
            return "three_of_a_kind"
        if "two pair" in label:
            return "two_pair"
        if "pair" in label:
            return "pair"
        return "high_card"

    def safe_evaluate(self, board: List[PokerkitCard], hand: List[PokerkitCard]) -> int:
        """
        Safe evaluation using PokerKit.
        """
        full_hand = StandardHighHand.from_game(hand, board)
        return -full_hand.entry.index  # Negative so higher index = stronger = lower score

    def _map_hand_class(self, hand: StandardHighHand) -> str:
        """Map PokerKit hand label to persisted hand class enum value."""
        label = str(hand.entry.label).lower()

        if "royal flush" in label:
            return "royal_flush"
        if "straight flush" in label:
            return "straight_flush"
        if "four of a kind" in label:
            return "four_of_a_kind"
        if "full house" in label:
            return "full_house"
        if "flush" in label:
            return "flush"
        if "straight" in label:
            return "straight"
        if "three of a kind" in label:
            return "three_of_a_kind"
        if "two pair" in label:
            return "two_pair"
        if "pair" in label:
            return "pair"
        return "high_card"

    def _run_monte_carlo_simulation(
        self,
        hero_hole: List[PokerkitCard],
        board: List[PokerkitCard],
        num_simulations: int,
        opponent_holes: Optional[List[List[PokerkitCard]]] = None,
        num_random_opponents: int = 0,
        persistence=None,
        return_individual_outcomes: bool = False,
        pot_size: float = 0.0,
        bet_amount: float = 0.0,
        cancel_check=None,
    ) -> Optional[Dict[str, float]]:
        """
        Core Monte Carlo simulation method.
        
        Args:
            hero_hole: Hero's hole cards (PokerKit format)
            board: Known board cards (PokerKit format)
            num_simulations: Number of simulations to run
            opponent_holes: Fixed opponent hands (if None, generate random)
            num_random_opponents: Number of random opponents to generate (if opponent_holes is None)
        
        Returns:
            dict with win/tie/loss probabilities
        """
        # Determine known cards
        known_cards = set(hero_hole + board)
        if opponent_holes:
            known_cards.update(c for opp in opponent_holes for c in opp)

        base_deck = [c for c in PokerkitDeck.STANDARD if c not in known_cards]
        opponent_card_count = num_random_opponents * 2
        remaining_board_needed = 5 - len(board)

        wins = 0
        ties = 0
        valid_simulations = 0
        individual_outcomes: list[Dict[str, Any]] = []

        for _ in range(num_simulations):
            if cancel_check is not None and cancel_check():
                break
            # Copy a pre-filtered deck each simulation, then shuffle
            deck_cards = base_deck.copy()
            random.shuffle(deck_cards)

            # Generate opponents if needed
            current_opponent_holes = opponent_holes
            if opponent_holes is None:
                # Generate random opponents
                if len(deck_cards) < opponent_card_count:
                    continue  # Not enough cards

                current_opponent_holes = []
                for _ in range(num_random_opponents):
                    hole = [deck_cards.pop(), deck_cards.pop()]
                    current_opponent_holes.append(hole)

            # Deal remaining board cards
            if len(deck_cards) < remaining_board_needed:
                continue  # Not enough cards for board

            remaining_board = [deck_cards.pop() for _ in range(remaining_board_needed)]
            full_board = board + remaining_board
            
            try:
                # Evaluate all hands with a direct lookup path.
                hero_entry = self._best_standard_high_hand_entry(hero_hole, full_board)
                opp_entries = [
                    self._best_standard_high_hand_entry(opp_hole, full_board)
                    for opp_hole in current_opponent_holes
                ]
                hero_score = hero_entry.index
                opp_scores = [entry.index for entry in opp_entries]
                valid_simulations += 1

                # Determine if hero wins, ties, or loses
                hero_better_than_all = all(hero_score > opp_score for opp_score in opp_scores)
                hero_ties_all = all(hero_score == opp_score for opp_score in opp_scores)

                if hero_better_than_all:
                    wins += 1
                elif hero_ties_all:
                    ties += 1

                if return_individual_outcomes:
                    actual_pot_size = bet_amount * (1 + len(current_opponent_holes)) if bet_amount > 0 else 0.0
                    hero_equity = 1.0 if hero_better_than_all else (0.5 if hero_ties_all else 0.0)
                    if bet_amount > 0.0:
                        if hero_better_than_all:
                            ev_chips = actual_pot_size
                        elif hero_ties_all:
                            ev_chips = actual_pot_size / 2.0 - bet_amount / 2.0
                        else:
                            ev_chips = -bet_amount
                    else:
                        ev_chips = hero_equity

                    villain_hands = []
                    if current_opponent_holes:
                        villain_hands = [
                            ''.join(self.pokerkit_to_card_name(c) for c in opp_hole)
                            for opp_hole in current_opponent_holes
                        ]

                    individual_outcomes.append({
                        'hero_hand': ''.join(self.pokerkit_to_card_name(c) for c in hero_hole),
                        'villain_hand': villain_hands[0] if villain_hands else 'NONE',
                        'villain_hands': villain_hands,
                        'outcome': 'WIN' if hero_better_than_all else ('TIE' if hero_ties_all else 'LOSS'),
                        'hero_equity': hero_equity,
                        'ev_chips': ev_chips,
                        'board_cards': ','.join(self.pokerkit_to_card_name(c) for c in full_board)
                    })

                if persistence is not None:
                    iteration_outcome = 'WIN' if hero_better_than_all else ('TIE' if hero_ties_all else 'LOSS')
                    board_str = [self.pokerkit_to_card_name(c) for c in full_board]
                    stored_pot_size = bet_amount * (1 + len(current_opponent_holes)) if bet_amount > 0.0 else 0.0
                    gs_id = persistence.store_game_state(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        round_name='preflop',
                        pot_size=stored_pot_size,
                        board_cards=board_str,
                        outcome=iteration_outcome
                    )
                    hero_cards_str = [self.pokerkit_to_card_name(c) for c in hero_hole]
                    hero_hand_class = self._map_entry_label_to_hand_class(hero_entry.label)
                    hero_id = persistence.store_player(
                        gs_id, 'hero', hero_cards_str, 100.0, is_hero=True,
                        hand_class=hero_hand_class,
                        final_strength=hero_score
                    )
                    if bet_amount > 0.0:
                        persistence.store_bet(
                            game_state_id=gs_id,
                            player_id=hero_id,
                            amount=bet_amount,
                            action_type='raise',
                            round_name='preflop'
                        )
                    for i, (opp_h, opp_entry, opp_score) in enumerate(zip(current_opponent_holes, opp_entries, opp_scores)):
                        opp_str = [self.pokerkit_to_card_name(c) for c in opp_h]
                        opp_hand_class = self._map_entry_label_to_hand_class(opp_entry.label)
                        opp_id = persistence.store_player(
                            game_state_id=gs_id,
                            position=f'opp_{i}',
                            hole_cards=opp_str,
                            stack_size=100.0,
                            is_hero=False,
                            hand_class=opp_hand_class,
                            final_strength=opp_score
                        )
                        if bet_amount > 0.0:
                            persistence.store_bet(
                                game_state_id=gs_id,
                                player_id=opp_id,
                                amount=bet_amount,
                                action_type='call',
                                round_name='preflop'
                            )
                    persistence.commit_transaction()

            except Exception as e:
                self.logger.warning(f"Simulation iteration failed: {type(e).__name__}: {e}")
                continue
        
        if valid_simulations == 0:
            self.logger.error("No valid simulations completed")
            return None
        
        win_prob = wins / valid_simulations
        tie_prob = ties / valid_simulations
        loss_prob = 1 - win_prob - tie_prob
        
        result = {
            'win_probability': win_prob,
            'tie_probability': tie_prob,
            'loss_probability': loss_prob,
            'valid_simulations': valid_simulations,
            'wins': wins,
            'ties': ties,
            'individual_outcomes': individual_outcomes if return_individual_outcomes else []
        }
        
        return result

    def calculate_odds_random_opponents(
        self,
        hero_hole_cards: List[str],
        board_cards: List[str],
        num_opponents: int,
        num_simulations: int = 10000,
        persistence=None,
        return_individual_outcomes: bool = False,
        pot_size: float = 0.0,
        bet_amount: float = 0.0,
        cancel_check=None,
    ) -> Optional[Dict[str, float]]:
        """
        Calculate odds against random opponent hands.
        
        Args:
            hero_hole_cards: list of 2 card names.
            board_cards: list of community cards.
            num_opponents: number of opponents.
            num_simulations: number of sims.
        
        Returns:
            dict with win/tie/loss probabilities.
        """
        self.logger.debug(f"Calculating odds with random opponents: hero={hero_hole_cards}, board={board_cards}, opponents={num_opponents}, sims={num_simulations}")
        
        # Check for duplicates in input
        all_input_cards = hero_hole_cards + board_cards
        if len(set(all_input_cards)) < len(all_input_cards):
            self.logger.error("Duplicate cards in input")
            return None
        
        # Convert hero and board
        hero = [self.card_name_to_pokerkit(c) for c in hero_hole_cards]
        board = [self.card_name_to_pokerkit(c) for c in board_cards]
        
        if any(c is None for c in hero + board):
            self.logger.error("Invalid card names")
            return None
        
        if len(board) > 5:
            self.logger.error(f"Board cannot have more than 5 cards, got {len(board)}")
            return None
        
        # Use common simulation method
        result = self._run_monte_carlo_simulation(
            hero_hole=hero,
            board=board,
            num_simulations=num_simulations,
            opponent_holes=None,
            num_random_opponents=num_opponents,
            persistence=persistence,
            return_individual_outcomes=return_individual_outcomes,
            pot_size=pot_size,
            bet_amount=bet_amount,
            cancel_check=cancel_check,
        )
        
        if result:
            self.logger.debug(f"Odds result: {result}")
        return result

    def calculate_odds_range(
        self, 
        hero_range: str, 
        board_cards: List[str], 
        num_opponents: int, 
        num_simulations: int = 10000
    ) -> Optional[Dict[str, float]]:
        """
        Calculate odds for a hero hand range against random opponent hands.
        
        Args:
            hero_range: shorthand range string like "AKs", "QJo", "22", etc.
            board_cards: list of community cards.
            num_opponents: number of opponents.
            num_simulations: number of sims.
        
        Returns:
            dict with win/tie/loss probabilities averaged over the range.
        """
        self.logger.debug(f"Calculating odds for range: {hero_range}, board={board_cards}, opponents={num_opponents}, sims={num_simulations}")
        
        # Expand range to all possible hands
        hero_hands = expand_range_to_hands(hero_range)
        if not hero_hands:
            self.logger.error(f"Invalid hero range: {hero_range}")
            return None
        
        # Check for duplicates in board
        if len(set(board_cards)) < len(board_cards):
            self.logger.error("Duplicate cards in board")
            return None
        
        # Convert board
        board = [self.card_name_to_pokerkit(c) for c in board_cards]
        if any(c is None for c in board):
            self.logger.error("Invalid board card names")
            return None
        
        if len(board) > 5:
            self.logger.error(f"Board cannot have more than 5 cards, got {len(board)}")
            return None
        
        known_cards = set(board)
        
        total_wins = 0
        total_ties = 0
        total_valid_simulations = 0
        
        # For each hand in the range, run simulations and accumulate results
        for hero_hole_cards in hero_hands:
            # Check for duplicates with board
            if set(hero_hole_cards) & set(board_cards):
                continue  # Skip this hand
            
            hero = [self.card_name_to_pokerkit(c) for c in hero_hole_cards]
            if any(c is None for c in hero):
                continue
            
            # Use common simulation method for this hand
            hand_result = self._run_monte_carlo_simulation(
                hero_hole=hero,
                board=board,
                num_simulations=num_simulations,
                opponent_holes=None,
                num_random_opponents=num_opponents
            )
            
            if hand_result:
                total_wins += hand_result['wins']
                total_ties += hand_result['ties']
                total_valid_simulations += hand_result['valid_simulations']
        
        if total_valid_simulations == 0:
            self.logger.error("No valid simulations completed")
            return None
        
        win_prob = total_wins / total_valid_simulations
        tie_prob = total_ties / total_valid_simulations
        loss_prob = 1 - win_prob - tie_prob
        
        result = {
            'win_probability': win_prob,
            'tie_probability': tie_prob,
            'loss_probability': loss_prob,
            'valid_simulations': total_valid_simulations,
            'wins': total_wins,
            'ties': total_ties,
            'range_size': len(hero_hands)
        }
        
        self.logger.debug(f"Range odds result: {result}")
        return result

    def simulate_individual_outcomes(
        self,
        hero_hole_cards: List[str],
        board_cards: List[str],
        num_opponents: int,
        num_simulations: int = 10000
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Run Monte Carlo simulations and return individual outcomes for each simulation.

        Args:
            hero_hole_cards: Hero's hole cards (2 cards)
            board_cards: Community cards (0-5 cards)
            num_opponents: Number of random opponents
            num_simulations: Number of simulations to run

        Returns:
            List of individual simulation outcomes, each containing:
            - hero_hand: Hero's hand in shorthand format
            - villain_hand: Villain's hand in shorthand format
            - outcome: 'WIN', 'LOSS', or 'TIE'
            - hero_equity: 1.0 for win, 0.0 for loss, 0.5 for tie
            - ev_chips: EV in chips (pot_size for win, -bet_amount for loss, 0 for tie)
            - board_cards: Final board cards used in simulation
        """
        self.logger.debug(f"Simulating individual outcomes: hero={hero_hole_cards}, board={board_cards}, opponents={num_opponents}, sims={num_simulations}")

        # Check for duplicates in input
        all_input_cards = hero_hole_cards + board_cards
        if len(set(all_input_cards)) < len(all_input_cards):
            self.logger.error("Duplicate cards in input")
            return None

        # Convert hero and board
        hero = [self.card_name_to_pokerkit(c) for c in hero_hole_cards]
        board = [self.card_name_to_pokerkit(c) for c in board_cards]

        if any(c is None for c in hero + board):
            self.logger.error("Invalid card names")
            return None

        if len(board) > 5:
            self.logger.error(f"Board cannot have more than 5 cards, got {len(board)}")
            return None

        # Get hero hand shorthand for output
        hero_shorthand = HandRange.shorthand_from_cards(hero_hole_cards)

        # Determine known cards
        known_cards = set(hero + board)

        outcomes = []

        for sim_idx in range(num_simulations):
            # Create fresh deck for each simulation
            deck_cards = [c for c in PokerkitDeck.STANDARD if c not in known_cards]
            import random
            random.shuffle(deck_cards)

            # Generate random opponents
            if len(deck_cards) < num_opponents * 2:
                continue  # Not enough cards

            opponent_holes = []
            for _ in range(num_opponents):
                hole = [deck_cards.pop(), deck_cards.pop()]
                opponent_holes.append(hole)

            # Deal remaining board cards
            remaining_board_needed = 5 - len(board)
            if len(deck_cards) < remaining_board_needed:
                continue  # Not enough cards for board

            remaining_board = [deck_cards.pop() for _ in range(remaining_board_needed)]
            full_board = board + remaining_board

            try:
                # Evaluate all hands
                hero_hand = StandardHighHand.from_game(hero, full_board)
                opp_hands = [StandardHighHand.from_game(opp_hole, full_board) for opp_hole in opponent_holes]
                hero_score = -hero_hand.entry.index
                opp_scores = [-h.entry.index for h in opp_hands]

                # Determine if hero wins, ties, or loses
                hero_better_than_all = all(hero_score < opp_score for opp_score in opp_scores)
                hero_ties_all = all(hero_score == opp_score for opp_score in opp_scores)

                # Collect all sampled villain hands for multi-opponent scenarios
                villain_hands = []
                for opp_hole in opponent_holes:
                    villain_cards = [self.pokerkit_to_card_name(c) for c in opp_hole]
                    villain_hands.append(HandRange.shorthand_from_cards(villain_cards))
                villain_shorthand = villain_hands[0] if villain_hands else 'NONE'

                # Convert board cards to string format
                board_card_names = [self.pokerkit_to_card_name(c) for c in full_board]
                board_string = ','.join(board_card_names)

                if hero_better_than_all:
                    outcome = 'WIN'
                    hero_equity = 1.0
                    ev_chips = 20.0  # Assuming standard pot size
                elif hero_ties_all:
                    outcome = 'TIE'
                    hero_equity = 0.5
                    ev_chips = 0.0
                else:
                    outcome = 'LOSS'
                    hero_equity = 0.0
                    ev_chips = -10.0  # Assuming standard bet amount

                outcomes.append({
                    'hero_hand': hero_shorthand,
                    'villain_hand': villain_shorthand,
                    'villain_hands': [villain_shorthand],
                    'outcome': outcome,
                    'hero_equity': hero_equity,
                    'ev_chips': ev_chips,
                    'board_cards': board_string
                })

            except Exception as e:
                self.logger.warning(f"Simulation {sim_idx} failed: {type(e).__name__}: {e}")
                continue

        if not outcomes:
            self.logger.error("No valid simulations completed")
            return None

        self.logger.debug(f"Generated {len(outcomes)} individual simulation outcomes")
        return outcomes

    def evaluate_hand(self, hole_cards: List[str], board_cards: List[str]) -> Optional[int]:
        """
        Evaluate hand strength.
        hole_cards: list of 2 card names
        board_cards: list of up to 5 card names
        Returns hand strength score (lower is better)
        """
        self.logger.debug(
            f"Evaluating hand: hole_cards={hole_cards}, board_cards={board_cards}"
        )

        hole = []
        for c in hole_cards:
            card = self.card_name_to_pokerkit(c)
            if card is not None:
                hole.append(card)

        board = []
        for c in board_cards:
            card = self.card_name_to_pokerkit(c)
            if card is not None:
                board.append(card)

        if len(hole) != 2:
            self.logger.warning(f"Invalid hole cards count: {len(hole)} (expected 2)")
            return None

        all_cards = hole + board
        if len(set(all_cards)) < len(all_cards):
            self.logger.warning("Duplicate cards detected in hand evaluation")
            return None  # Duplicates not allowed
        if len(all_cards) < 5:
            self.logger.debug(
                f"Insufficient cards for evaluation: {len(all_cards)} (need at least 5)"
            )
            return None  # Need at least 5 cards for evaluation

        try:
            return self.safe_evaluate(board, hole)
        except Exception as e:
            self.logger.error(f"Failed to evaluate hand: {e}")
            return None

    def get_hand_class(self, hole_cards: List[str], board_cards: List[str]) -> str:
        """
        Get hand class from cards.
        """
        try:
            hand = StandardHighHand.from_game(
                [self.card_name_to_pokerkit(c) for c in hole_cards],
                [self.card_name_to_pokerkit(c) for c in board_cards]
            )
            label = str(hand.entry.label)
            # Capitalize first letter of each word, but keep 'of' lowercase and 'a' lowercase after 'of'
            words = label.split()
            capitalized = []
            for i, word in enumerate(words):
                if word.lower() == 'of':
                    capitalized.append('of')
                elif word.lower() == 'a' and i > 0 and words[i-1].lower() == 'of':
                    capitalized.append('a')
                else:
                    capitalized.append(word.capitalize())
            return ' '.join(capitalized)
        except:
            return "Unknown"

    def get_hand_class_value(self, hole_cards: List[str], board_cards: List[str]) -> Optional[str]:
        """Get normalized hand class value for persistence."""
        try:
            hand = StandardHighHand.from_game(
                [self.card_name_to_pokerkit(c) for c in hole_cards],
                [self.card_name_to_pokerkit(c) for c in board_cards]
            )
            return self._map_hand_class(hand)
        except Exception:
            return None

    def get_advice(self, hole_cards: List[str], board_cards: List[str], phase: str) -> str:
        """
        Provide basic advice based on phase.
        """
        self.logger.debug(
            f"Getting advice for phase: {phase}, hole_cards: {hole_cards}, board_cards: {board_cards}"
        )

        score = self.evaluate_hand(hole_cards, board_cards)
        hand_class = self.get_hand_class(hole_cards, board_cards)
        
        # Get shorthand notation for the hand
        shorthand = HandRange.shorthand_from_cards(hole_cards)

        advice = ""
        if phase == "pre-flop":
            if score and score < 1000:  # Strong hand
                advice = f"Strong starting hand {shorthand} ({hand_class}). Consider raising."
            else:
                advice = f"Weak starting hand {shorthand} ({hand_class}). Play cautiously."
        elif phase in ["flop", "turn", "river"]:
            if score and score < 500:  # Very strong
                advice = (
                    f"Very strong hand {shorthand} ({hand_class}). Aggressive play recommended."
                )
            elif score and score < 2000:
                advice = f"Good hand {shorthand} ({hand_class}). Continue betting."
            else:
                advice = f"Weak hand {shorthand} ({hand_class}). Consider folding."
        else:
            advice = "Insufficient information for advice."

        self.logger.debug(f"Generated advice: {advice}")
        return advice

    def calculate_odds(
        self, 
        hero_hole_cards: List[str], 
        opponent_hole_cards_list: List[List[str]], 
        board_cards: List[str], 
        num_simulations: int = 10000
    ) -> Optional[Dict[str, float]]:
        """
        Calculate win/tie probabilities for hero against opponents using Monte Carlo simulation.
        
        Args:
            hero_hole_cards: list of 2 card names (e.g., ['AS', 'KH'])
            opponent_hole_cards_list: list of lists, each with 2 card names for each opponent
            board_cards: list of known community cards (0-5 cards)
            num_simulations: number of simulations to run
        
        Returns:
            dict with 'win_probability', 'tie_probability', 'loss_probability'
        """
        self.logger.debug(f"Calculating odds: hero={hero_hole_cards}, opponents={len(opponent_hole_cards_list)}, board={board_cards}, sims={num_simulations}")
        
        # Check for duplicates in input
        all_input_cards = hero_hole_cards + [c for opp in opponent_hole_cards_list for c in opp] + board_cards
        if len(set(all_input_cards)) < len(all_input_cards):
            self.logger.error("Duplicate cards in input")
            return None
        
        # Convert card names to PokerKit format
        hero_hole = [self.card_name_to_pokerkit(c) for c in hero_hole_cards]
        opponent_holes = [[self.card_name_to_pokerkit(c) for c in opp] for opp in opponent_hole_cards_list]
        board = [self.card_name_to_pokerkit(c) for c in board_cards]
        
        # Check for None values
        if any(c is None for c in hero_hole + [c for opp in opponent_holes for c in opp] + board):
            self.logger.error("Invalid card names provided")
            return None
        
        # Validate input lengths
        if len(hero_hole) != 2:
            self.logger.error(f"Hero must have exactly 2 hole cards, got {len(hero_hole)}")
            return None
        if any(len(opp) != 2 for opp in opponent_holes):
            self.logger.error("All opponents must have exactly 2 hole cards")
            return None
        
        # All known cards
        known_cards = set(hero_hole + [c for opp in opponent_holes for c in opp] + board)
        if len(set(known_cards)) < len(known_cards):
            self.logger.error("Duplicate cards in input")
            return None
        
        # Use common simulation method
        result = self._run_monte_carlo_simulation(
            hero_hole=hero_hole,
            board=board,
            num_simulations=num_simulations,
            opponent_holes=opponent_holes,
            num_random_opponents=0
        )
        
        if result:
            self.logger.debug(f"Odds calculation result: {result}")
        return result

    def calculate_pot_odds(
        self, 
        pot_size: float, 
        bet_amount: float
    ) -> Optional[Dict[str, float]]:
        """
        Calculate pot odds as a decimal (e.g., 0.25 for 1:3 odds).
        
        Args:
            pot_size (float): Current size of the pot.
            bet_amount (float): Amount you need to call.
        
        Returns:
            dict: Contains 'odds_decimal', 'odds_ratio', and 'odds_percentage'.
        """
        if pot_size <= 0 or bet_amount <= 0:
            self.logger.error("Pot size and bet amount must be positive")
            return None
        
        total_pot = pot_size + bet_amount
        odds_decimal = bet_amount / total_pot
        odds_percentage = odds_decimal * 100
        
        # Calculate ratio (e.g., 1:3)
        bet_to_pot_ratio = bet_amount / pot_size
        # Simplify ratio if possible
        import math
        gcd = math.gcd(int(bet_amount * 100), int(pot_size * 100)) / 100
        simplified_bet = bet_amount / gcd
        simplified_pot = pot_size / gcd
        odds_ratio = f"{int(simplified_bet)}:{int(simplified_pot)}"
        
        result = {
            'odds_decimal': odds_decimal,
            'odds_ratio': odds_ratio,
            'odds_percentage': odds_percentage
        }
        
        self.logger.debug(f"Pot odds: {result}")
        return result

    def calculate_ev_index(
        self, 
        win_probability: float, 
        pot_size: float, 
        bet_amount: float
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate Expected Value (EV) for a call decision.
        
        Args:
            win_probability (float): Probability of winning the hand (from calculate_odds).
            pot_size (float): Current size of the pot.
            bet_amount (float): Amount you need to call.
        
        Returns:
            dict: Contains 'ev_amount', 'ev_index' (+EV or -EV), and 'break_even_percentage'.
        """
        if not (0 <= win_probability <= 1):
            self.logger.error("Win probability must be between 0 and 1")
            return None
        if pot_size <= 0 or bet_amount <= 0:
            self.logger.error("Pot size and bet amount must be positive")
            return None
        
        # EV = p * (pot + bet) - bet
        ev = win_probability * (pot_size + bet_amount) - bet_amount
        
        # Alternatively: EV = p * pot - (1-p) * bet
        # ev = win_probability * pot_size - (1 - win_probability) * bet_amount
        
        ev_index = "+EV" if ev > 0 else "-EV" if ev < 0 else "Break-even"
        
        # Break-even percentage: the win prob needed for EV=0
        # 0 = p * (pot + bet) - bet => p = bet / (pot + bet)
        break_even_percentage = (bet_amount / (pot_size + bet_amount)) * 100
        
        result = {
            'ev_amount': ev,
            'ev_index': ev_index,
            'break_even_percentage': break_even_percentage
        }
        
        self.logger.debug(f"EV calculation: {result}")
        return result

    def card_name_to_pokerkit(self, card_name: str) -> Optional[PokerkitCard]:
        """
        Convert card name to pokerkit Card object.
        Supports formats: 'AS', 'A S', 'ace of spades', etc.
        Returns None if invalid.
        """
        if not card_name:
            return None
        
        card_name = card_name.strip().lower()
        
        # Handle long format: "ace of spades" or "ace_of_spades"
        if ' of ' in card_name or '_of_' in card_name:
            separator = ' of ' if ' of ' in card_name else '_of_'
            parts = card_name.split(separator)
            if len(parts) != 2:
                return None
            rank_str, suit_str = parts
        else:
            # Handle short format: "AS" or "A S"
            card_name = card_name.replace(' ', '')
            if len(card_name) < 2:
                return None
            rank_str = card_name[:-1]
            suit_str = card_name[-1]
        
        # Map rank
        rank_map = {
            'a': 'A', 'ace': 'A',
            'k': 'K', 'king': 'K',
            'q': 'Q', 'queen': 'Q',
            'j': 'J', 'jack': 'J',
            't': 'T', '10': 'T', 'ten': 'T',
            '9': '9', 'nine': '9',
            '8': '8', 'eight': '8',
            '7': '7', 'seven': '7',
            '6': '6', 'six': '6',
            '5': '5', 'five': '5',
            '4': '4', 'four': '4',
            '3': '3', 'three': '3',
            '2': '2', 'two': '2',
        }
        rank = rank_map.get(rank_str)
        if rank is None:
            return None
        
        # Map suit
        suit_map = {
            's': 's', 'spades': 's',
            'h': 'h', 'hearts': 'h',
            'd': 'd', 'diamonds': 'd',
            'c': 'c', 'clubs': 'c',
        }
        suit = suit_map.get(suit_str)
        if suit is None:
            return None
        
        try:
            return PokerkitCard(rank, suit)
        except:
            return None

    def pokerkit_to_card_name(self, card: PokerkitCard) -> str:
        """
        Convert pokerkit Card object to card name string.
        Returns format like 'AS', 'KH', etc.
        """
        if card is None:
            return ""
        
        # Extract rank and suit from the card
        # PokerkitCard has rank and suit attributes
        rank = card.rank
        suit = card.suit
        
        # Convert back to short format
        return f"{rank}{suit}"
