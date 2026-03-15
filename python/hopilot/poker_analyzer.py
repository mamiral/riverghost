import os
from typing import List, Dict, Optional, Any

from pokerkit.hands import StandardHighHand
from pokerkit.utilities import Card as PokerkitCard, Deck as PokerkitDeck

from hopilot.logging_config import get_logger
from hopilot.hand_range import expand_range_to_hands, HandRange


class PokerAnalyzer:
    def __init__(self):
        self.evaluator = StandardHighHand
        self.logger = get_logger(__name__)
        self.logger.info("PokerAnalyzer initialized")
        
        # Using PokerKit library for robust poker hand evaluation

    def safe_evaluate(self, board: List[PokerkitCard], hand: List[PokerkitCard]) -> int:
        """
        Safe evaluation using PokerKit.
        """
        full_hand = StandardHighHand.from_game(hand, board)
        return -full_hand.entry.index  # Negative so higher index = stronger = lower score

    def evaluate_hand(self, hole_cards: List[str], board_cards: List[str]) -> Optional[int]:
        """
        Evaluate hand strength using PokerKit.
        
        Args:
            hole_cards: list of hole card names (2 cards).
            board_cards: list of board card names.
        
        Returns:
            Hand strength as integer (lower is better), or None if invalid.
        """
        # Convert string cards to PokerKit cards
        hero = [self.card_name_to_pokerkit(c) for c in hole_cards]
        board = [self.card_name_to_pokerkit(c) for c in board_cards]
        
        # Filter out None values (invalid cards)
        hero = [c for c in hero if c is not None]
        board = [c for c in board if c is not None]
        
        if len(hero) != 2:
            self.logger.warning(f"Invalid hole cards: {hole_cards}")
            return None
        
        try:
            return self.safe_evaluate(board, hero)
        except Exception as e:
            self.logger.error(f"Failed to evaluate hand: {e}")
            return None

    def _run_monte_carlo_simulation(
        self,
        hero_hole: List[PokerkitCard],
        board: List[PokerkitCard],
        num_simulations: int,
        opponent_holes: Optional[List[List[PokerkitCard]]] = None,
        num_random_opponents: int = 0
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
        
        wins = 0
        ties = 0
        valid_simulations = 0
        
        for _ in range(num_simulations):
            # Create fresh deck for each simulation
            deck_cards = [c for c in PokerkitDeck.STANDARD if c not in known_cards]
            import random
            random.shuffle(deck_cards)
            
            # Generate opponents if needed
            current_opponent_holes = opponent_holes
            if opponent_holes is None:
                # Generate random opponents
                if len(deck_cards) < num_random_opponents * 2:
                    continue  # Not enough cards
                
                current_opponent_holes = []
                for _ in range(num_random_opponents):
                    hole = [deck_cards.pop(), deck_cards.pop()]
                    current_opponent_holes.append(hole)
            
            # Deal remaining board cards
            remaining_board_needed = 5 - len(board)
            if len(deck_cards) < remaining_board_needed:
                continue  # Not enough cards for board
            
            remaining_board = [deck_cards.pop() for _ in range(remaining_board_needed)]
            full_board = board + remaining_board
            
            try:
                # Evaluate all hands
                hero_hand = StandardHighHand.from_game(hero_hole, full_board)
                opp_hands = [StandardHighHand.from_game(opp_hole, full_board) for opp_hole in current_opponent_holes]
                hero_score = -hero_hand.entry.index
                opp_scores = [-h.entry.index for h in opp_hands]
                valid_simulations += 1
                
                # Determine if hero wins, ties, or loses
                hero_better_than_all = all(hero_score < opp_score for opp_score in opp_scores)
                hero_ties_all = all(hero_score == opp_score for opp_score in opp_scores)
                
                if hero_better_than_all:
                    wins += 1
                elif hero_ties_all:
                    ties += 1
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
            'ties': ties
        }
        
        return result

    def calculate_odds_random_opponents(
        self, 
        hero_hole_cards: List[str], 
        board_cards: List[str], 
        num_opponents: int, 
        num_simulations: int = 10000
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
        self.logger.info(f"Calculating odds with random opponents: hero={hero_hole_cards}, board={board_cards}, opponents={num_opponents}, sims={num_simulations}")
        
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
            num_random_opponents=num_opponents
        )
        
        if result:
            self.logger.info(f"Odds result: {result}")
        return result

    def calculate_odds(
        self, 
        hero_hole_cards: List[str], 
        villain_hole_cards: List[List[str]], 
        board_cards: List[str], 
        num_simulations: int = 10000
    ) -> Optional[Dict[str, float]]:
        """
        Calculate odds against specific opponent hands.
        
        Args:
            hero_hole_cards: list of 2 hero card names.
            villain_hole_cards: list of villain hole card lists (each with 2 cards).
            board_cards: list of community cards.
            num_simulations: number of sims.
        
        Returns:
            dict with win/tie/loss probabilities.
        """
        self.logger.info(f"Calculating odds against specific opponents: hero={hero_hole_cards}, villains={villain_hole_cards}, board={board_cards}, sims={num_simulations}")
        
        # Check for duplicates in input
        all_input_cards = hero_hole_cards + board_cards
        for villain_hole in villain_hole_cards:
            all_input_cards.extend(villain_hole)
        if len(set(all_input_cards)) < len(all_input_cards):
            self.logger.error("Duplicate cards in input")
            return None
        
        # Convert hero and board
        hero = [self.card_name_to_pokerkit(c) for c in hero_hole_cards]
        board = [self.card_name_to_pokerkit(c) for c in board_cards]
        
        # Convert villain hands
        villain_holes = []
        for villain_hole in villain_hole_cards:
            villain = [self.card_name_to_pokerkit(c) for c in villain_hole]
            if any(c is None for c in villain):
                self.logger.error("Invalid villain card names")
                return None
            villain_holes.append(villain)
        
        if any(c is None for c in hero + board):
            self.logger.error("Invalid hero or board card names")
            return None
        
        if len(board) > 5:
            self.logger.error(f"Board cannot have more than 5 cards, got {len(board)}")
            return None
        
        # Use common simulation method
        result = self._run_monte_carlo_simulation(
            hero_hole=hero,
            board=board,
            num_simulations=num_simulations,
            opponent_holes=villain_holes,
            num_random_opponents=0
        )
        
        if result:
            self.logger.info(f"Specific odds result: {result}")
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
        self.logger.info(f"Calculating odds for range: {hero_range}, board={board_cards}, opponents={num_opponents}, sims={num_simulations}")
        
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
        
        self.logger.info(f"Range odds result: {result}")
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
        self.logger.info(f"Simulating individual outcomes: hero={hero_hole_cards}, board={board_cards}, opponents={num_opponents}, sims={num_simulations}")

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

                # Get a representative villain hand (first opponent) for shorthand
                villain_cards = [self.pokerkit_to_card_name(c) for c in opponent_holes[0]]
                villain_shorthand = HandRange.shorthand_from_cards(villain_cards)

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

        self.logger.info(f"Generated {len(outcomes)} individual simulation outcomes")
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

        score = -StandardHighHand(all_cards).entry.index
        self.logger.debug(f"Hand evaluation score: {score}")
        return score

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

    def get_advice(self, hole_cards: List[str], board_cards: List[str], phase: str) -> str:
        """
        Provide basic advice based on phase.
        """
        self.logger.debug(
            f"Getting advice for phase: {phase}, hole_cards: {hole_cards}, board_cards: {board_cards}"
        )

        score = self.evaluate_hand(hole_cards, board_cards)
        hand_class = self.get_hand_class(score)
        
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
        self.logger.info(f"Calculating odds: hero={hero_hole_cards}, opponents={len(opponent_hole_cards_list)}, board={board_cards}, sims={num_simulations}")
        
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
            self.logger.info(f"Odds calculation result: {result}")
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
        
        self.logger.info(f"Pot odds: {result}")
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
        
        self.logger.info(f"EV calculation: {result}")
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
