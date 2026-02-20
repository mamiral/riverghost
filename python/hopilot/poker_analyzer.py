import os
from typing import List, Dict, Optional, Any

from pokerkit.hands import StandardHighHand
from pokerkit.utilities import Card as PokerkitCard, Deck as PokerkitDeck

from hopilot.logging_config import get_logger


class PokerAnalyzer:
    def __init__(self):
        self.evaluator = StandardHighHand
        self.logger = get_logger(__name__)
        self.logger.info("PokerAnalyzer initialized")
        
        # Using PokerKit library for robust poker hand evaluation

    def safe_evaluate(self, board: List[int], hand: List[int]) -> int:
        """
        Safe evaluation using PokerKit.
        """
        return self.evaluator.evaluate(board, hand)

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
        
        known_cards = set(hero + board)
        
        wins = 0
        ties = 0
        valid_simulations = 0
        
        for _ in range(num_simulations):
            # Generate random opponent hands
            deck_cards = list(PokerkitDeck.STANDARD)
            # Remove known cards
            deck_cards = [c for c in deck_cards if c not in known_cards]
            # Shuffle
            import random
            random.shuffle(deck_cards)
            
            # Check deck size
            needed = 2 * num_opponents + (5 - len(board))
            if len(deck_cards) < needed:
                self.logger.error(f"Insufficient cards in deck: {len(deck_cards)}, needed: {needed}")
                continue
            
            opponent_holes = []
            for _ in range(num_opponents):
                if len(deck_cards) < 2:
                    self.logger.warning("Insufficient cards for opponent hole")
                    opponent_holes = None
                    break
                hole = [deck_cards.pop(), deck_cards.pop()]
                hole.reverse()  # First card dealt is first in hand
                opponent_holes.append(hole)
            
            if opponent_holes is not None:
                # Remaining board
                remaining_board = 5 - len(board)
                if len(deck_cards) < remaining_board:
                    self.logger.warning("Insufficient cards for board")
                    continue
                full_board = board + [deck_cards.pop() for _ in range(remaining_board)]
                
                try:
                    # Evaluate
                    hero_hand = StandardHighHand.from_game(hero, full_board)
                    opp_hands = [StandardHighHand.from_game(opp, full_board) for opp in opponent_holes]
                    hero_score = -hero_hand.entry.index  # Negative so higher index = stronger = lower score
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
                    self.logger.warning(f"Random opponents simulation iteration failed: {type(e).__name__}: {e} (hero: {hero}, board: {full_board}, opponents: {opponent_holes})")
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
        
        self.logger.info(f"Odds result: {result}")
        return result

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

        advice = ""
        if phase == "pre-flop":
            if score and score < 1000:  # Strong hand
                advice = f"Strong starting hand ({hand_class}). Consider raising."
            else:
                advice = f"Weak starting hand ({hand_class}). Play cautiously."
        elif phase in ["flop", "turn", "river"]:
            if score and score < 500:  # Very strong
                advice = (
                    f"Very strong hand ({hand_class}). Aggressive play recommended."
                )
            elif score and score < 2000:
                advice = f"Good hand ({hand_class}). Continue betting."
            else:
                advice = f"Weak hand ({hand_class}). Consider folding."
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
        
        # Create deck and remove known cards
        available_cards = [c for c in PokerkitDeck.STANDARD if c not in known_cards]
        import random
        random.shuffle(available_cards)
        
        # Number of cards to draw for board
        cards_needed = 5 - len(board)
        
        wins = 0
        ties = 0
        valid_simulations = 0
        
        for _ in range(num_simulations):
            # Create fresh deck for each simulation
            deck_cards = [c for c in PokerkitDeck.STANDARD if c not in known_cards]
            import random
            random.shuffle(deck_cards)
            
            # Draw remaining board cards
            if len(deck_cards) < cards_needed:
                self.logger.warning("Insufficient cards for board")
                continue
            remaining_board = [deck_cards.pop() for _ in range(cards_needed)]
            full_board = board + remaining_board
            
            try:
                # Evaluate hero hand
                hero_hand = StandardHighHand.from_game(hero_hole, full_board)
                opp_hands = [StandardHighHand.from_game(opp_hole, full_board) for opp_hole in opponent_holes]
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
                self.logger.warning(f"Simulation iteration failed: {type(e).__name__}: {e} (hero: {hero_hole}, opponents: {opponent_holes}, board: {full_board})")
                # Continue with next simulation
                continue
        
        # Calculate probabilities
        if valid_simulations == 0:
            self.logger.error("No valid simulation results obtained")
            return None
            
        win_prob = wins / valid_simulations
        tie_prob = ties / valid_simulations
        loss_prob = 1 - win_prob - tie_prob
        
        result = {
            'win_probability': win_prob,
            'tie_probability': tie_prob,
            'loss_probability': loss_prob
        }
        
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
