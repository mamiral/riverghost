import os
import sqlite3
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from treys import Card, Deck, Evaluator

from hopilot.logging_config import get_logger


@dataclass
class OddsResult:
    """Result of odds calculation."""
    win_probability: float
    tie_probability: float
    loss_probability: float
    total_simulations: int
    cached: bool = False
    valid_simulations: Optional[int] = None


class PokerAnalyzer:
    def __init__(self):
        self.evaluator = Evaluator()
        self.logger = get_logger(__name__)
        self.logger.info("PokerAnalyzer initialized")
        
        # Cache for odds: key -> {'wins': int, 'ties': int, 'sims': int}
        self.odds_cache = {}
        self.cache_db_path = os.path.join(os.path.dirname(__file__), 'odds_cache.db')
        self.cache_db = sqlite3.connect(self.cache_db_path)
        self._init_db()
        self.load_cache()

    def _init_db(self) -> None:
        """Initialize the database table."""
        self.cache_db.execute('''
            CREATE TABLE IF NOT EXISTS odds_cache (
                key TEXT PRIMARY KEY,
                wins INTEGER,
                ties INTEGER,
                sims INTEGER
            )
        ''')
        self.cache_db.commit()

    def _generate_cache_key(self, hero_hole_cards: List[str], board_cards: List[str], num_opponents: int) -> str:
        """Generate a string key for caching."""
        # Normalize card names to canonical format for consistent keys
        def normalize_card(card_name: str) -> str:
            """Convert any card format to canonical 'RS' format (Rank + Suit)."""
            card = self.card_name_to_treys(card_name)
            if card is None:
                return card_name  # Fallback to original if invalid
            # Convert back to string format: e.g., 'As', '10h'
            rank_int = Card.get_rank_int(card)
            suit_int = Card.get_suit_int(card)
            rank_char = Card.STR_RANKS[rank_int]
            suit_char = Card.STR_SUITS[suit_int].lower()
            return f"{rank_char}{suit_char}"

        # Normalize and sort hero and board cards
        hero_normalized = [normalize_card(c) for c in hero_hole_cards]
        board_normalized = [normalize_card(c) for c in board_cards]

        hero_sorted = ','.join(sorted(hero_normalized))
        board_sorted = ','.join(sorted(board_normalized))
        return f"{hero_sorted}#{board_sorted}#{num_opponents}"

    def load_cache(self) -> None:
        """Load cache from database."""
        try:
            cursor = self.cache_db.execute('SELECT key, wins, ties, sims FROM odds_cache')
            self.odds_cache = {row[0]: {'wins': row[1], 'ties': row[2], 'sims': row[3]} for row in cursor}
            self.logger.info(f"Loaded odds cache with {len(self.odds_cache)} entries")
        except Exception as e:
            self.logger.error(f"Failed to load cache: {e}")
            self.odds_cache = {}

    def save_cache(self) -> None:
        """Save cache to database."""
        try:
            data = [(k, v['wins'], v['ties'], v['sims']) for k, v in self.odds_cache.items()]
            self.cache_db.executemany('INSERT OR REPLACE INTO odds_cache (key, wins, ties, sims) VALUES (?, ?, ?, ?)', data)
            self.cache_db.commit()
            self.logger.info(f"Saved odds cache with {len(self.odds_cache)} entries")
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")

    def calculate_odds_cached(
        self, 
        hero_hole_cards: List[str], 
        board_cards: List[str], 
        num_opponents: int = 1, 
        num_simulations: int = 10000, 
        accumulate: bool = True
    ) -> Optional[OddsResult]:
        """
        Cached version of calculate_odds. Simulates against random opponent hands.
        
        Args:
            hero_hole_cards: list of 2 card names.
            board_cards: list of known community cards.
            num_opponents: number of opponents (assumes random hands).
            num_simulations: sims per call.
            accumulate: accumulate results.
        
        Returns:
            OddsResult with probabilities.
        """
        key = self._generate_cache_key(hero_hole_cards, board_cards, num_opponents)
        
        cached = self.odds_cache.get(key, {'wins': 0, 'ties': 0, 'sims': 0})
        
        if not accumulate:
            if cached['sims'] >= num_simulations:
                win_prob = cached['wins'] / cached['sims']
                tie_prob = cached['ties'] / cached['sims']
                loss_prob = 1 - win_prob - tie_prob
                result = OddsResult(
                    win_probability=win_prob,
                    tie_probability=tie_prob,
                    loss_probability=loss_prob,
                    total_simulations=cached['sims'],
                    cached=True
                )
                self.logger.info(f"Used cached odds: {result}")
                return result
            else:
                # Run simulations and save
                new_result = self.calculate_odds_random_opponents(hero_hole_cards, board_cards, num_opponents, num_simulations)
                if new_result is None:
                    return None
                self.odds_cache[key] = {'wins': int(new_result['win_probability'] * num_simulations), 'ties': int(new_result['tie_probability'] * num_simulations), 'sims': num_simulations}
                self.save_cache()
                result = OddsResult(
                    win_probability=new_result['win_probability'],
                    tie_probability=new_result['tie_probability'],
                    loss_probability=new_result['loss_probability'],
                    total_simulations=num_simulations,
                    cached=False
                )
                self.logger.info(f"Saved new odds: {result}")
                return result
        else:
            # Accumulate: always run and add to cache
            new_result = self.calculate_odds_random_opponents(hero_hole_cards, board_cards, num_opponents, num_simulations)
            if new_result is None:
                return None
            
            # Accumulate
            total_wins = cached['wins'] + int(new_result['win_probability'] * num_simulations)
            total_ties = cached['ties'] + int(new_result['tie_probability'] * num_simulations)
            total_sims = cached['sims'] + num_simulations
            
            # Update cache
            self.odds_cache[key] = {'wins': total_wins, 'ties': total_ties, 'sims': total_sims}
            self.save_cache()
            
            # Return final probabilities
            win_prob = total_wins / total_sims
            tie_prob = total_ties / total_sims
            loss_prob = 1 - win_prob - tie_prob
            result = OddsResult(
                win_probability=win_prob,
                tie_probability=tie_prob,
                loss_probability=loss_prob,
                total_simulations=total_sims,
                cached=False
            )
            self.logger.info(f"Updated cached odds: {result}")
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
        
        # Convert hero and board
        hero = [self.card_name_to_treys(c) for c in hero_hole_cards]
        board = [self.card_name_to_treys(c) for c in board_cards]
        
        if any(c is None for c in hero + board):
            self.logger.error("Invalid card names")
            return None
        
        known_cards = set(hero + board)
        
        wins = 0
        ties = 0
        
        for _ in range(num_simulations):
            # Generate random opponent hands
            deck = Deck()
            deck.cards = [c for c in deck.cards if c not in known_cards]
            deck.shuffle()
            
            opponent_holes = []
            for _ in range(num_opponents):
                hole = [deck.draw(1)[0], deck.draw(1)[0]]
                opponent_holes.append(hole)
            
            # Remaining board
            remaining_board = 5 - len(board)
            full_board = board + deck.draw(remaining_board)
            
            try:
                # Evaluate
                hero_score = self.evaluator.evaluate(full_board, hero)
                opp_scores = [self.evaluator.evaluate(full_board, opp) for opp in opponent_holes]
            except KeyError:
                continue
            
            hero_better = all(hero_score < opp for opp in opp_scores)
            hero_ties = all(hero_score == opp for opp in opp_scores)
            
            if hero_better:
                wins += 1
            elif hero_ties:
                ties += 1
        
        win_prob = wins / num_simulations
        tie_prob = ties / num_simulations
        loss_prob = 1 - win_prob - tie_prob
        
        result = {
            'win_probability': win_prob,
            'tie_probability': tie_prob,
            'loss_probability': loss_prob
        }
        
        self.logger.info(f"Odds result: {result}")
        return result

    def build_cache_offline(
        self, 
        scenarios: List[Dict[str, Any]], 
        total_simulations_per_scenario: int = 10000
    ) -> None:
        """
        Offline dry run to build cache for multiple scenarios.
        
        Args:
            scenarios: List of dicts with 'hero', 'board', 'num_opponents' keys.
            total_simulations_per_scenario: Sims per scenario.
        """
        self.logger.info(f"Building cache for {len(scenarios)} scenarios")
        for scenario in scenarios:
            self.calculate_odds_cached(
                scenario['hero'], 
                scenario['board'], 
                scenario['num_opponents'],
                total_simulations_per_scenario, 
                accumulate=True
            )
        self.logger.info("Cache build complete")

    def card_name_to_treys(self, card_name: str) -> Optional[Card]:
        """
        Convert card name like 'AS' or 'ace_of_hearts' to treys format.
        """
        # Handle both formats: 'AS' or 'ace_of_hearts'
        if "_" in card_name:
            # Format: 'ace_of_hearts'
            rank_map = {
                "ace": "A",
                "king": "K",
                "queen": "Q",
                "jack": "J",
                "ten": "T",
                "nine": "9",
                "eight": "8",
                "seven": "7",
                "six": "6",
                "five": "5",
                "four": "4",
                "three": "3",
                "two": "2",
            }
            suit_map = {"hearts": "h", "diamonds": "d", "clubs": "c", "spades": "s"}

            parts = card_name.split("_of_")
            if len(parts) != 2:
                return None
            rank_str, suit_str = parts
            rank = rank_map.get(rank_str.lower())
            suit = suit_map.get(suit_str.lower())
            if not rank or not suit:
                return None
            return Card.new(rank + suit)
        else:
            # Format: 'AS', '2C', '10H', etc.
            rank_map = {
                "A": "A",
                "K": "K",
                "Q": "Q",
                "J": "J",
                "T": "T",
                "9": "9",
                "8": "8",
                "7": "7",
                "6": "6",
                "5": "5",
                "4": "4",
                "3": "3",
                "2": "2",
            }
            suit_map = {"S": "s", "H": "h", "D": "d", "C": "c"}
            if len(card_name) == 2:
                rank_char, suit_char = card_name[0], card_name[1]
            elif len(card_name) == 3 and card_name.startswith("10"):
                rank_char = "T"
                suit_char = card_name[2]
            else:
                return None
            rank = rank_map.get(rank_char.upper())
            suit = suit_map.get(suit_char.upper())
            if not rank or not suit:
                return None
            return Card.new(rank + suit)

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
            card = self.card_name_to_treys(c)
            if card is not None:
                hole.append(card)

        board = []
        for c in board_cards:
            card = self.card_name_to_treys(c)
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

        score = self.evaluator.evaluate(all_cards[:2], all_cards[2:])
        self.logger.debug(f"Hand evaluation score: {score}")
        return score

    def get_hand_class(self, score: Optional[int]) -> str:
        """
        Get hand class from score.
        """
        if score is None:
            return "Unknown"
        hand_class = self.evaluator.get_rank_class(score)
        class_names = [
            "High Card",
            "Pair",
            "Two Pair",
            "Three of a Kind",
            "Straight",
            "Flush",
            "Full House",
            "Four of a Kind",
            "Straight Flush",
        ]
        return class_names[hand_class] if hand_class < len(class_names) else "Unknown"

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
        
        # Convert card names to treys format
        hero_hole = [self.card_name_to_treys(c) for c in hero_hole_cards]
        opponent_holes = [[self.card_name_to_treys(c) for c in opp] for opp in opponent_hole_cards_list]
        board = [self.card_name_to_treys(c) for c in board_cards]
        
        # Check for None values
        if any(c is None for c in hero_hole + [c for opp in opponent_holes for c in opp] + board):
            self.logger.error("Invalid card names provided")
            return None
        
        # All known cards
        known_cards = hero_hole + [c for opp in opponent_holes for c in opp] + board
        if len(set(known_cards)) < len(known_cards):
            self.logger.error("Duplicate cards in input")
            return None
        
        # Create deck and remove known cards
        deck = Deck()
        for card in known_cards:
            if card in deck.cards:
                deck.cards.remove(card)
        
        # Number of cards to draw for board
        cards_needed = 5 - len(board)
        
        wins = 0
        ties = 0
        
        for _ in range(num_simulations):
            # Shuffle remaining deck
            deck.shuffle()
            
            # Draw remaining board cards
            remaining_board = deck.draw(cards_needed)
            full_board = board + remaining_board
            
            # Evaluate hero hand
            hero_score = self.evaluator.evaluate(full_board, hero_hole)
            
            # Evaluate opponent hands
            opp_scores = [self.evaluator.evaluate(full_board, opp_hole) for opp_hole in opponent_holes]
            
            # Determine if hero wins, ties, or loses
            hero_better_than_all = all(hero_score < opp_score for opp_score in opp_scores)
            hero_ties_all = all(hero_score == opp_score for opp_score in opp_scores)
            
            if hero_better_than_all:
                wins += 1
            elif hero_ties_all:
                ties += 1
        
        win_prob = wins / num_simulations
        tie_prob = ties / num_simulations
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

    def calculate_odds_optimized(
        self, 
        hero_hole_cards: List[str], 
        opponent_hole_cards_list: List[List[str]], 
        board_cards: List[str], 
        num_simulations: int = 10000
    ) -> Optional[Dict[str, float]]:
        """
        Optimized Monte Carlo simulation that ignores flush possibilities for speed.
        Uses rank-based deck (13 ranks) and assigns random suits, skipping flush outcomes.
        
        This approximates odds for non-flush hands only—add separate flush analysis if needed.
        
        Args:
            Same as calculate_odds.
        
        Returns:
            Same as calculate_odds, but biased toward non-flush scenarios.
        """
        self.logger.info(f"Calculating optimized odds (non-flush only): hero={hero_hole_cards}, opponents={len(opponent_hole_cards_list)}, board={board_cards}, sims={num_simulations}")
        
        # Convert to ranks only (ignore suits for known cards)
        def card_to_rank(card_name):
            card = self.card_name_to_treys(card_name)
            if card is None:
                return None
            return Card.get_rank_int(card)  # 0-12 for 2-A
        
        hero_ranks = [card_to_rank(c) for c in hero_hole_cards]
        opp_ranks = [[card_to_rank(c) for c in opp] for opp in opponent_hole_cards_list]
        board_ranks = [card_to_rank(c) for c in board_cards]
        
        if any(r is None for r in hero_ranks + [r for opp in opp_ranks for r in opp] + board_ranks):
            self.logger.error("Invalid card names")
            return None
        
        known_ranks = hero_ranks + [r for opp in opp_ranks for r in opp] + board_ranks
        if len(set(known_ranks)) < len(known_ranks):
            self.logger.error("Duplicate ranks in input")
            return None
        
        # Rank deck: 4 copies of each rank (0-12)
        rank_deck = [r for r in range(13) for _ in range(4)]
        for rank in known_ranks:
            if rank in rank_deck:
                rank_deck.remove(rank)
        
        cards_needed = 5 - len(board_cards)
        
        wins = 0
        ties = 0
        valid_sims = 0
        
        for _ in range(num_simulations):
            # Draw ranks
            import random
            random.shuffle(rank_deck)
            drawn_ranks = rank_deck[:cards_needed]
            
            # Assign random suits to drawn ranks (ensure no flush: limit suits)
            suits = ['s', 'h', 'd', 'c']
            assigned_suits = []
            suit_counts = {'s': 0, 'h': 0, 'd': 0, 'c': 0}
            for _ in drawn_ranks:
                suit = random.choice(suits)
                # Prevent >4 of any suit to avoid flushes
                if suit_counts[suit] >= 4:
                    suit = random.choice([s for s in suits if suit_counts[s] < 4])
                assigned_suits.append(suit)
                suit_counts[suit] += 1
            
            # Create treys cards for board
            full_board_ranks = board_ranks + drawn_ranks
            full_board_suits = [self.card_name_to_treys(board_cards[i])[1] for i in range(len(board_cards))] + assigned_suits
            full_board = [Card.new(f"{Card.STR_RANKS[r]}{s}") for r, s in zip(full_board_ranks, full_board_suits)]
            
            # Check for flush (skip if any)
            board_suit_counts = {}
            for card in full_board:
                suit = Card.get_suit_int(card)
                board_suit_counts[suit] = board_suit_counts.get(suit, 0) + 1
            if any(count >= 5 for count in board_suit_counts.values()):
                continue  # Skip flush boards
            
            # Evaluate hands
            hero_score = self.evaluator.evaluate(full_board, [Card.new(f"{Card.STR_RANKS[hero_ranks[0]]}s"), Card.new(f"{Card.STR_RANKS[hero_ranks[1]]}s")])  # Assign dummy suits
            opp_scores = []
            for opp in opp_ranks:
                opp_score = self.evaluator.evaluate(full_board, [Card.new(f"{Card.STR_RANKS[opp[0]]}s"), Card.new(f"{Card.STR_RANKS[opp[1]]}s")])
                opp_scores.append(opp_score)
            
            hero_better = all(hero_score < opp for opp in opp_scores)
            hero_ties = all(hero_score == opp for opp in opp_scores)
            
            if hero_better:
                wins += 1
            elif hero_ties:
                ties += 1
            valid_sims += 1
        
        if valid_sims == 0:
            self.logger.error("No valid non-flush simulations")
            return None
        
        win_prob = wins / valid_sims
        tie_prob = ties / valid_sims
        loss_prob = 1 - win_prob - tie_prob
        
        result = {
            'win_probability': win_prob,
            'tie_probability': tie_prob,
            'loss_probability': loss_prob,
            'valid_simulations': valid_sims
        }
        
        self.logger.info(f"Optimized odds result: {result}")
        return result
