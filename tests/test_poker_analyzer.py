import pytest
import os
import tempfile
import shutil
import sys
from unittest.mock import patch, MagicMock
from pokerkit.hands import StandardHighHand

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from hopilot.poker_analyzer import PokerAnalyzer


class TestPokerAnalyzer:
    """Comprehensive test suite for PokerAnalyzer."""

    @pytest.mark.parametrize("hero, villain, expected_min, expected_max, description", [
        # Texas Hold'em Preflop: Common hand match-up probabilities
        # Pair against two higher cards ("coin flip"): 46% (4♦4♠ vs. J♥T♥) up to 57% (Q♠Q♣ vs. A♥K♦)
        (["4d", "4s"], ["Jh", "Th"], 0.44, 0.48, "Pair vs. two higher cards (low pair)"),
        (["Qh", "Qd"], ["As", "Kd"], 0.55, 0.58, "Pair vs. two higher cards (high pair)"),
        # Pair against higher and lower card: 68% (6♥6♦ vs. 7♠5♠) up to 73% (Q♥Q♦ vs. K♣2♠)
        (["6h", "6d"], ["7s", "5s"], 0.64, 0.68, "Pair vs. higher and lower card (low pair)"),
        (["Qh", "Qd"], ["Kc", "2s"], 0.71, 0.74, "Pair vs. higher and lower card (high pair)"),
        # Pair against two lower cards: 77% (K♠K♥ vs. 8♦7♦) up to 89% (K♠K♥ vs. 7♠2♥)
        (["Ks", "Kh"], ["8d", "7d"], 0.76, 0.79, "Pair vs. two lower cards (mid)"),
        (["Ks", "Kh"], ["7s", "2h"], 0.87, 0.90, "Pair vs. two lower cards (extreme)"),
        # Pair against higher and equal rank: 60% (4♥4♠ vs. 5♣4♣) up to 70% (8♥8♦ vs. K♠8♣)
        (["4h", "4s"], ["5c", "4c"], 0.57, 0.61, "Pair vs. higher and equal rank (low)"),
        (["8h", "8d"], ["Ks", "8c"], 0.68, 0.71, "Pair vs. higher and equal rank (high)"),
        # Pair against equal and lower rank: 81% (5♥5♠ vs. 5♣4♣) up to 95% (K♠K♣ vs. K♥2♦)
        (["5h", "5s"], ["5c", "4c"], 0.78, 0.82, "Pair vs. equal and lower rank (low)"),
        (["Ks", "Kc"], ["Kh", "2d"], 0.93, 0.96, "Pair vs. equal and lower rank (high)"),
        # Two higher against two lower cards: 58% (K♣8♠ vs. 5♦4♦) up to 71% (J♠T♠ vs. 7♥2♦)
        (["Kc", "8s"], ["5d", "4d"], 0.56, 0.60, "Two higher vs. two lower cards (mid)"),
        (["Js", "Ts"], ["7h", "2d"], 0.69, 0.72, "Two higher vs. two lower cards (high)"),
        # High and low card against two inbetween: 58% (K♠2♥ vs. 8♦7♦) up to 63% (A♠2♠ vs. 8♣3♥)
        (["Ks", "2h"], ["8d", "7d"], 0.49, 0.55, "High and low vs. two inbetween (mid)"),
        (["As", "2s"], ["8c", "3h"], 0.61, 0.64, "High and low vs. two inbetween (high)"),
        # Same high card, different kicker: 53% (A♥3♥ vs. A♣2♣) up to 76% (K♥Q♥ vs. K♦2♣)
        (["Ah", "3h"], ["Ac", "2c"], 0.30, 0.35, "Same high card, different kicker (low)"),
        (["Kh", "Qh"], ["Kd", "2c"], 0.72, 0.76, "Same high card, different kicker (high)"),
        # Interlocked cards: 56% (K♣8♠ vs. 9♥7♥) up to 66% (A♥9♥ vs. T♠4♣)
        (["Kc", "8s"], ["9h", "7h"], 0.54, 0.58, "Interlocked cards (mid)"),
        (["Ah", "9h"], ["Ts", "4c"], 0.64, 0.67, "Interlocked cards (high)"),
    ])
    def test_preflop_matchup_probabilities(self, analyzer, hero, villain, expected_min, expected_max, description):
        """
        Test preflop all-in probabilities for common Texas Hold'em hand matchups.
        Simulates hero vs. villain, no board cards, 10,000+ simulations.
        Asserts hero's win probability is within expected range.
        """
        # Use a high number of simulations for stability
        num_simulations = 15000
        # Simulate hero vs. villain (1 opponent)
        result = analyzer.calculate_odds(hero, [villain], [], num_simulations)
        assert result is not None, f"Simulation failed for {description}"
        win_prob = result['win_probability']
        assert expected_min <= win_prob <= expected_max, (
            f"{description}: Win probability {win_prob:.3f} not in expected range [{expected_min:.3f}, {expected_max:.3f}] for {hero} vs {villain}"
        )
        # Optionally print for documentation
        print(f"{description}: {hero} vs {villain} => win probability: {win_prob:.3f}")

    @pytest.fixture
    def analyzer(self):
        """Create a fresh PokerAnalyzer instance for each test."""
        return PokerAnalyzer()

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_cache.db')
        yield db_path
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    # ===== CARD NAME CONVERSION TESTS =====

    @pytest.mark.parametrize("input_card,expected", [
        # Short format
        ("AS", "As"),
        ("KH", "Kh"),
        ("QC", "Qc"),
        ("JD", "Jd"),
        ("10H", "Th"),
        ("2S", "2s"),
        # Long format
        ("ace_of_spades", "As"),
        ("king_of_hearts", "Kh"),
        ("queen_of_clubs", "Qc"),
        ("jack_of_diamonds", "Jd"),
        ("ten_of_hearts", "Th"),
        ("two_of_spades", "2s"),
    ])
    def test_card_name_normalization(self, analyzer, input_card, expected):
        """Test that card names are normalized consistently."""
        card = analyzer.card_name_to_pokerkit(input_card)
        assert card is not None

        # Convert back to string to check normalization
        normalized = repr(card)
        assert normalized == expected

    def test_invalid_card_names(self, analyzer):
        """Test handling of invalid card names."""
        invalid_cards = ["XX", "1Z", "ace_of_mars", "", "A", "11H"]
        for card_name in invalid_cards:
            result = analyzer.card_name_to_pokerkit(card_name)
            assert result is None

    # ===== HAND EVALUATION TESTS =====

    def test_hand_strength_ordering(self, analyzer):
        """Test that stronger hands have lower (better) scores."""
        # Royal flush (best possible hand)
        royal_flush = analyzer.evaluate_hand(["AS", "KS"], ["QS", "JS", "10S"])
        assert royal_flush is not None
        assert royal_flush < 100  # Very strong hand

        # High card (weak hand)
        high_card = analyzer.evaluate_hand(["AS", "2H"], ["3C", "4D", "7S"])
        assert high_card is not None
        assert high_card > royal_flush  # Weaker hand has higher score

    def test_best_standard_high_hand_entry_matches_pokerkit(self, analyzer):
        """Regression test: direct lookup entry must match StandardHighHand.from_game."""
        hero_cards = [analyzer.card_name_to_pokerkit(c) for c in ["AS", "KH"]]
        board_cards = [analyzer.card_name_to_pokerkit(c) for c in ["QS", "JS", "10S", "2D", "3C"]]

        assert all(card is not None for card in hero_cards + board_cards)

        lookup_entry = analyzer._best_standard_high_hand_entry(hero_cards, board_cards)
        expected_entry = StandardHighHand.from_game(hero_cards, board_cards).entry

        assert lookup_entry.index == expected_entry.index
        assert lookup_entry.label == expected_entry.label

    def test_hand_class_mapping(self, analyzer):
        """Test that hand classes are mapped correctly."""
        test_cases = [
            (["AS", "KS"], ["QS", "JS", "10S"], "Straight Flush"),  # Royal flush
            (["AS", "AD"], ["AC", "AH", "2S"], "Four of a Kind"),  # Quads
            (["AS", "KS"], ["QS", "JS", "10H"], "Straight"),  # Straight
            (["AS", "AH"], ["2S", "3D", "4C"], "One Pair"),  # Pair
            (["AS", "7H"], ["3D", "4C", "5S"], "High Card"),  # High card
        ]

        for hole_cards, board_cards, expected_class in test_cases:
            hand_class = analyzer.get_hand_class(hole_cards, board_cards)
            assert hand_class == expected_class

    def test_invalid_hand_evaluation(self, analyzer):
        """Test error handling in hand evaluation."""
        # Duplicate cards
        result = analyzer.evaluate_hand(["AS", "AS"], ["KH"])
        assert result is None

        # Insufficient cards
        result = analyzer.evaluate_hand(["AS"], [])
        assert result is None

        # Invalid card names
        result = analyzer.evaluate_hand(["XX", "AS"], ["KH"])
        assert result is None

    # ===== ODDS CALCULATION TESTS =====

    def test_odds_mathematical_properties(self, analyzer):
        """Test that calculated odds have correct mathematical properties."""
        # Simple scenario: hero has pocket aces vs one opponent on flop
        result = analyzer.calculate_odds(["AS", "AH"], [["KC", "QD"]], ["2S", "3D", "4C"], 1000)

        assert result is not None
        assert 0 <= result['win_probability'] <= 1
        assert 0 <= result['tie_probability'] <= 1
        assert 0 <= result['loss_probability'] <= 1

        # Probabilities should sum to approximately 1.0
        total_prob = (result['win_probability'] +
                     result['tie_probability'] +
                     result['loss_probability'])
        assert abs(total_prob - 1.0) < 0.01  # Allow small floating point errors

    def test_odds_with_known_outcome(self, analyzer):
        """Test odds calculation with a scenario where outcome is known."""
        # Hero has royal flush, opponent has high card
        # Hero should win almost 100% of the time
        result = analyzer.calculate_odds(
            ["AS", "KS"],  # Hero: royal flush
            [["2H", "3C"]],  # Opponent: weak hand
            ["QS", "JS", "10S", "9H", "8D"],  # Board: 5 cards, royal flush for hero
            1000
        )

        assert result is not None
        assert result['win_probability'] > 0.99  # Should win almost always
        assert result['loss_probability'] < 0.01

    # ===== POT ODDS AND EV TESTS =====

    def test_pot_odds_calculation(self, analyzer):
        """Test pot odds calculation."""
        result = analyzer.calculate_pot_odds(pot_size=100, bet_amount=50)

        assert result is not None
        assert abs(result['odds_decimal'] - 0.3333333333333333) < 1e-10  # 50 / (100 + 50) = 50/150 = 1/3
        assert abs(result['odds_percentage'] - 33.33333333333333) < 1e-10  # 33.33...
        assert '1:2' in result['odds_ratio']  # 50:100 simplifies to 1:2

    def test_ev_calculation(self, analyzer):
        """Test expected value calculation."""
        # Hero has 60% win probability, pot is 100, bet is 50
        result = analyzer.calculate_ev_index(0.6, 100, 50)

        assert result is not None
        assert result['ev_index'] == "+EV"  # Positive expected value
        assert result['ev_amount'] == 40.0  # (0.6 * 150) - 50 = 90 - 50 = 40
        assert abs(result['break_even_percentage'] - 33.33333333333333) < 1e-10  # 50/150 ≈ 33.33%

    def test_negative_ev(self, analyzer):
        """Test negative expected value scenario."""
        # Hero has 20% win probability, pot is 50, bet is 100
        result = analyzer.calculate_ev_index(0.2, 50, 100)

        assert result['ev_index'] == "-EV"
        assert result['ev_amount'] == -70.0  # (0.2 * 150) - 100 = 30 - 100 = -70

    # ===== ERROR HANDLING TESTS =====

    def test_calculate_odds_error_handling(self, analyzer):
        """Test error handling in odds calculations."""
        # Invalid card names
        result = analyzer.calculate_odds(["XX", "AS"], [["KH", "QC"]], [], 100)
        assert result is None

        # Duplicate cards
        result = analyzer.calculate_odds(["AS", "AS"], [["KH", "QC"]], [], 100)
        assert result is None

    # ===== PERFORMANCE TESTS =====

    def test_calculation_performance(self, analyzer):
        """Test that calculations complete within reasonable time."""
        import time

        start_time = time.time()
        result = analyzer.calculate_odds_random_opponents(["AS", "KH"], ["QC", "JD"], 3, 1000)
        end_time = time.time()

        # Should complete in less than 3 seconds for 1000 simulations (accounting for test overhead)
        assert end_time - start_time < 3.0
        assert result is not None

    # ===== EDGE CASE TESTS =====

    def test_edge_cases(self, analyzer):
        """Test various edge cases."""
        # Empty board
        result = analyzer.calculate_odds_random_opponents(["AS", "KH"], [], 1, 100)
        assert result is not None

        # Full board (river)
        result = analyzer.calculate_odds_random_opponents(["AS", "KH"], ["QC", "JD", "10H", "2S", "3C"], 1, 100)
        assert result is not None

        # Zero opponents (shouldn't happen in practice but test robustness)
        result = analyzer.calculate_odds_random_opponents(["AS", "KH"], ["QC"], 0, 100)
        assert result is not None

    # ===== INTEGRATION TESTS =====

    def test_full_workflow(self, analyzer):
        """Test the complete analysis workflow."""
        # Simulate a poker hand analysis
        hole_cards = ["AS", "KH"]
        board_cards = ["QC", "JD", "10H"]

        # Evaluate hand
        score = analyzer.evaluate_hand(hole_cards, board_cards)
        assert score is not None

        hand_class = analyzer.get_hand_class(hole_cards, board_cards)
        assert isinstance(hand_class, str)

        # Calculate odds
        odds = analyzer.calculate_odds_random_opponents(hole_cards, board_cards, 2, 500)
        assert isinstance(odds, dict)
        assert 'win_probability' in odds
        assert 'tie_probability' in odds
        assert 'loss_probability' in odds
        assert 0 <= odds['win_probability'] <= 1
        assert 0 <= odds['tie_probability'] <= 1
        assert 0 <= odds['loss_probability'] <= 1

        # Verify probabilities sum to ~1
        total = odds['win_probability'] + odds['tie_probability'] + odds['loss_probability']
        assert abs(total - 1.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__])