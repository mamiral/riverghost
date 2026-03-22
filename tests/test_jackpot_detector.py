"""
Test suite for Jackpot Detection Implementation (JACKPOT-002).

Validates that jackpot detection logic correctly identifies qualifying hands
and calculates payouts according to the defined rules.

PHASE 2: P1 - CRITICAL
- Tests jackpot detection during simulation runs
- Validates correct payout amount calculations
- Ensures qualifying cards are properly identified
"""

import pytest
from hopilot.gto.jackpot_detector import JackpotDetector, JackpotResult, detect_hand_jackpot, should_trigger_jackpot


class TestJackpotDetector:
    """Test suite for JackpotDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a jackpot detector instance."""
        return JackpotDetector('ggpoker')

    def test_detect_royal_flush(self, detector):
        """Test royal flush detection."""
        hole_cards = ['As', 'Ks']
        board_cards = ['Qs', 'Js', 'Ts', '9s', '8s']  # Royal flush on board

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'royal_flush'
        assert result.payout_multiplier == 500
        assert result.payout_amount == 500000  # 1000 * 500
        assert len(result.qualifying_cards) == 5
        assert all(card[1] == 's' for card in result.qualifying_cards)  # All spades

    def test_detect_straight_flush(self, detector):
        """Test straight flush detection."""
        hole_cards = ['9s', '8s']
        board_cards = ['7s', '6s', '5s', '4s', '3s']  # Steel wheel straight flush

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'straight_flush'
        assert result.payout_multiplier == 100
        assert result.payout_amount == 100000

    def test_detect_four_of_a_kind(self, detector):
        """Test four of a kind detection."""
        hole_cards = ['As', 'Ad']
        board_cards = ['Ac', 'Ah', 'Ks', 'Qs', 'Js']  # Quad aces

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'four_of_a_kind'
        assert result.payout_multiplier == 50
        assert result.payout_amount == 50000
        assert len(result.qualifying_cards) == 4
        assert all(card[0] == 'A' for card in result.qualifying_cards)

    def test_detect_full_house(self, detector):
        """Test full house detection."""
        hole_cards = ['As', 'Ad']
        board_cards = ['Ac', 'Ks', 'Kd', 'Qs', 'Js']  # Aces full of kings

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'full_house'
        assert result.payout_multiplier == 10
        assert result.payout_amount == 10000

    def test_detect_flush(self, detector):
        """Test flush detection."""
        hole_cards = ['As', 'Ks']
        board_cards = ['Qs', 'Js', '9s', '7s', '3s']  # Spade flush

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'flush'
        assert result.payout_multiplier == 5
        assert result.payout_amount == 5000

    def test_detect_straight(self, detector):
        """Test straight detection."""
        hole_cards = ['As', 'Kh']
        board_cards = ['Qd', 'Jc', 'Ts', '9s', '8s']  # Broadway straight

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'straight'
        assert result.payout_multiplier == 4
        assert result.payout_amount == 4000

    def test_detect_wheel_straight(self, detector):
        """Test wheel straight detection (A-2-3-4-5)."""
        hole_cards = ['As', '2h']
        board_cards = ['3d', '4c', '5s', 'Ks', 'Qs']  # Wheel straight

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'straight'
        assert result.payout_multiplier == 4

    def test_detect_three_of_a_kind(self, detector):
        """Test three of a kind detection."""
        hole_cards = ['As', 'Ad']
        board_cards = ['Ac', '7h', '8d', '9c', 'Th']  # Three aces, no straights or flushes possible

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'three_of_a_kind'
        assert result.payout_multiplier == 3
        assert result.payout_amount == 3000

    def test_detect_two_pair(self, detector):
        """Test two pair detection."""
        hole_cards = ['As', 'Ad']
        board_cards = ['2h', '2d', '7c', '8s', '9h']  # Aces and deuces, no straights

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'two_pair'
        assert result.payout_multiplier == 2
        assert result.payout_amount == 2000

    def test_detect_one_pair(self, detector):
        """Test one pair detection."""
        hole_cards = ['As', 'Ad']
        board_cards = ['7h', '2d', '3c', '4s', '6h']  # Pair of aces, no straights possible

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'one_pair'
        assert result.payout_multiplier == 1
        assert result.payout_amount == 1000

    def test_no_jackpot_high_card(self, detector):
        """Test high card hand (no jackpot)."""
        hole_cards = ['As', '7d']
        board_cards = ['2h', '3c', '8s', '9h', 'Tc']  # High card, no pairs or straights

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert not result.detected
        assert result.jackpot_type == 'high_card'
        assert result.payout_multiplier == 0
        assert result.payout_amount == 0

    def test_insufficient_cards(self, detector):
        """Test with insufficient cards for any jackpot."""
        hole_cards = ['As', 'Ks']
        board_cards = ['Qs']  # Only 3 cards total, need 5+ for most jackpots

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert not result.detected
        assert result.jackpot_type == 'high_card'

    def test_priority_order_royal_beats_straight_flush(self, detector):
        """Test that royal flush beats straight flush in priority."""
        hole_cards = ['As', 'Ks']
        board_cards = ['Qs', 'Js', 'Ts', '9s', '8s']  # Contains both royal and straight flush

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        # Should detect royal flush (higher priority) not straight flush
        assert result.detected
        assert result.jackpot_type == 'royal_flush'
        assert result.payout_multiplier == 500

    def test_platform_disabled_jackpots(self):
        """Test behavior when jackpots are disabled for platform."""
        # Create detector for ggpoker but mock platform rules to disable jackpots
        detector = JackpotDetector('ggpoker')
        # Manually disable jackpots for this test
        detector.platform_rules = {'jackpot_enabled': False}

        hole_cards = ['As', 'Ks']
        board_cards = ['Qs', 'Js', 'Ts', '9s', '8s']

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert not result.detected
        assert result.jackpot_type == 'high_card'

    def test_jackpot_result_to_dict(self, detector):
        """Test JackpotResult.to_dict() method."""
        result = JackpotResult(
            jackpot_type='royal_flush',
            payout_multiplier=500,
            qualifying_cards=['As', 'Ks', 'Qs', 'Js', 'Ts'],
            payout_amount=500000,
            detected=True
        )

        result_dict = result.to_dict()

        expected = {
            'jackpot_type': 'royal_flush',
            'payout_multiplier': 500,
            'qualifying_cards': ['As', 'Ks', 'Qs', 'Js', 'Ts'],
            'payout_amount': 500000,
            'detected': True
        }

        assert result_dict == expected

    def test_detect_hand_jackpot_convenience_function(self):
        """Test the convenience function detect_hand_jackpot."""
        hole_cards = ['As', 'Ks']
        board_cards = ['Qs', 'Js', 'Ts', '9s', '8s']
        pot_size = 1000

        result = detect_hand_jackpot(hole_cards, board_cards, pot_size, 'ggpoker')

        assert result.detected
        assert result.jackpot_type == 'royal_flush'
        assert result.payout_amount == 500000

    def test_should_trigger_jackpot(self):
        """Test should_trigger_jackpot helper function."""
        # Detected jackpot with payout
        detected_result = JackpotResult('royal_flush', 500, ['As', 'Ks'], 500000, True)
        assert should_trigger_jackpot(detected_result)

        # No jackpot detected
        no_jackpot = JackpotResult('high_card', 0, [], 0, False)
        assert not should_trigger_jackpot(no_jackpot)

        # Detected but zero payout
        zero_payout = JackpotResult('high_card', 0, [], 0, True)
        assert not should_trigger_jackpot(zero_payout)

    def test_edge_cases(self, detector):
        """Test various edge cases."""
        # Empty board cards
        result = detector.detect_jackpot(['As', 'Ks'], [], 1000)
        assert not result.detected

        # All same suit but not flush (less than 5 cards)
        result = detector.detect_jackpot(['As', 'Ks'], ['Qs', 'Js'], 1000)
        assert not result.detected

        # Cards that don't form any hand
        result = detector.detect_jackpot(['As', 'Ks'], ['2s', '7h', '9d', 'Tc', 'Qh'], 1000)
        assert not result.detected  # No qualifying hand

    def test_complex_full_house_scenarios(self, detector):
        """Test complex full house detection scenarios."""
        # Two sets of trips available
        hole_cards = ['As', 'Ad']
        board_cards = ['Ac', 'Ks', 'Kd', 'Kc', 'Qs']  # Aces full of kings

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'full_house'
        assert len(result.qualifying_cards) == 5

    def test_mixed_suit_straight(self, detector):
        """Test straight with mixed suits."""
        hole_cards = ['As', 'Kh']
        board_cards = ['Qd', 'Jc', 'Ts', '9s', '8h']  # Mixed suit straight

        result = detector.detect_jackpot(hole_cards, board_cards, 1000)

        assert result.detected
        assert result.jackpot_type == 'straight'
        # Should have cards from different suits
        suits = [card[1] for card in result.qualifying_cards]
        assert len(set(suits)) > 1  # Mixed suits