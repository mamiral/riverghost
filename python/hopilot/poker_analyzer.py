import logging
from treys import Evaluator, Card

class PokerAnalyzer:
    def __init__(self):
        self.evaluator = Evaluator()
        self.logger = logging.getLogger(__name__)
        self.logger.info("PokerAnalyzer initialized")

    def card_name_to_treys(self, card_name):
        """
        Convert card name like 'AS' or 'ace_of_hearts' to treys format.
        """
        # Handle both formats: 'AS' or 'ace_of_hearts'
        if '_' in card_name:
            # Format: 'ace_of_hearts'
            rank_map = {
                'ace': 'A',
                'king': 'K',
                'queen': 'Q',
                'jack': 'J',
                'ten': 'T',
                'nine': '9',
                'eight': '8',
                'seven': '7',
                'six': '6',
                'five': '5',
                'four': '4',
                'three': '3',
                'two': '2'
            }
            suit_map = {
                'hearts': 'h',
                'diamonds': 'd',
                'clubs': 'c',
                'spades': 's'
            }

            parts = card_name.split('_of_')
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
            rank_map = {'A': 'A', 'K': 'K', 'Q': 'Q', 'J': 'J', 'T': 'T', '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'}
            suit_map = {'S': 's', 'H': 'h', 'D': 'd', 'C': 'c'}
            if len(card_name) == 2:
                rank_char, suit_char = card_name[0], card_name[1]
            elif len(card_name) == 3 and card_name.startswith('10'):
                rank_char = 'T'
                suit_char = card_name[2]
            else:
                return None
            rank = rank_map.get(rank_char.upper())
            suit = suit_map.get(suit_char.upper())
            if not rank or not suit:
                return None
            return Card.new(rank + suit)

    def evaluate_hand(self, hole_cards, board_cards):
        """
        Evaluate hand strength.
        hole_cards: list of 2 card names
        board_cards: list of up to 5 card names
        Returns hand strength score (lower is better)
        """
        self.logger.debug(f"Evaluating hand: hole_cards={hole_cards}, board_cards={board_cards}")

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
            self.logger.debug(f"Insufficient cards for evaluation: {len(all_cards)} (need at least 5)")
            return None  # Need at least 5 cards for evaluation

        score = self.evaluator.evaluate(all_cards[:2], all_cards[2:])
        self.logger.debug(f"Hand evaluation score: {score}")
        return score

    def get_hand_class(self, score):
        """
        Get hand class from score.
        """
        if score is None:
            return "Unknown"
        hand_class = self.evaluator.get_rank_class(score)
        class_names = [
            "High Card", "Pair", "Two Pair", "Three of a Kind",
            "Straight", "Flush", "Full House", "Four of a Kind",
            "Straight Flush"
        ]
        return class_names[hand_class] if hand_class < len(class_names) else "Unknown"

    def get_advice(self, hole_cards, board_cards, phase):
        """
        Provide basic advice based on phase.
        """
        self.logger.debug(f"Getting advice for phase: {phase}, hole_cards: {hole_cards}, board_cards: {board_cards}")

        score = self.evaluate_hand(hole_cards, board_cards)
        hand_class = self.get_hand_class(score)

        advice = ""
        if phase == 'pre-flop':
            if score and score < 1000:  # Strong hand
                advice = f"Strong starting hand ({hand_class}). Consider raising."
            else:
                advice = f"Weak starting hand ({hand_class}). Play cautiously."
        elif phase in ['flop', 'turn', 'river']:
            if score and score < 500:  # Very strong
                advice = f"Very strong hand ({hand_class}). Aggressive play recommended."
            elif score and score < 2000:
                advice = f"Good hand ({hand_class}). Continue betting."
            else:
                advice = f"Weak hand ({hand_class}). Consider folding."
        else:
            advice = "Insufficient information for advice."

        self.logger.info(f"Generated advice: {advice}")
        return advice