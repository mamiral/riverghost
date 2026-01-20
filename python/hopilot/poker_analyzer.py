from treys import Evaluator, Card

class PokerAnalyzer:
    def __init__(self):
        self.evaluator = Evaluator()

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
            # Format: 'AS', '2C', etc.
            if len(card_name) != 2:
                return None
            rank_char, suit_char = card_name[0], card_name[1]
            rank_map = {'A': 'A', 'K': 'K', 'Q': 'Q', 'J': 'J', 'T': 'T', '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'}
            suit_map = {'S': 's', 'H': 'h', 'D': 'd', 'C': 'c'}
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
        hole = [self.card_name_to_treys(c) for c in hole_cards if c]
        board = [self.card_name_to_treys(c) for c in board_cards if c]

        if len(hole) != 2:
            return None

        all_cards = hole + board
        if len(all_cards) < 5:
            return None  # Need at least 5 cards for evaluation

        score = self.evaluator.evaluate(all_cards[:2], all_cards[2:])
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
        score = self.evaluate_hand(hole_cards, board_cards)
        hand_class = self.get_hand_class(score)

        if phase == 'pre-flop':
            if score and score < 1000:  # Strong hand
                return f"Strong starting hand ({hand_class}). Consider raising."
            else:
                return f"Weak starting hand ({hand_class}). Play cautiously."
        elif phase in ['flop', 'turn', 'river']:
            if score and score < 500:  # Very strong
                return f"Very strong hand ({hand_class}). Aggressive play recommended."
            elif score and score < 2000:
                return f"Good hand ({hand_class}). Continue betting."
            else:
                return f"Weak hand ({hand_class}). Consider folding."
        return "Insufficient information for advice."