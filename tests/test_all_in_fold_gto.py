"""
Unit tests for AllInFoldGTOSolver GTO threshold calculations.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.poker_analyzer import PokerAnalyzer


class TestAllInFoldGTOSolver:
    """Test cases for GTO threshold calculation."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock PokerAnalyzer."""
        analyzer = Mock(spec=PokerAnalyzer)
        return analyzer

    @pytest.fixture
    def solver(self, mock_analyzer):
        """Create a GTO solver with mock analyzer."""
        return AllInFoldGTOSolver(mock_analyzer)

    def test_init(self, mock_analyzer):
        """Test solver initialization."""
        solver = AllInFoldGTOSolver(mock_analyzer)
        assert solver.analyzer == mock_analyzer
        assert 'royal_flush' in solver.bonus_payouts
        assert solver.bonus_payouts['royal_flush'] == 500

    def test_set_bonus_payouts_valid(self, solver):
        """Test setting valid bonus payouts."""
        payouts = {'royal_flush': 1000, 'straight_flush': 200}
        solver.set_bonus_payouts(payouts)
        assert solver.bonus_payouts['royal_flush'] == 1000
        assert solver.bonus_payouts['straight_flush'] == 200

    def test_set_bonus_payouts_invalid_type(self, solver):
        """Test setting bonus payouts with invalid type."""
        with pytest.raises(TypeError):
            solver.set_bonus_payouts("not a dict")

    def test_set_bonus_payouts_negative_value(self, solver):
        """Test setting bonus payouts with negative value."""
        payouts = {'royal_flush': -100}
        with pytest.raises(ValueError, match="cannot be negative"):
            solver.set_bonus_payouts(payouts)

    def test_find_gto_threshold_parameter_validation(self, solver):
        """Test parameter validation for find_gto_threshold."""
        # Valid parameters should not raise
        # Note: This will fail until we implement the method with validation
        with pytest.raises(ValueError, match="num_opponents must be an integer between 1 and 9"):
            solver.find_gto_threshold(num_opponents=10)

        with pytest.raises(ValueError, match="pot_size must be a positive number"):
            solver.find_gto_threshold(pot_size=-1)

        with pytest.raises(ValueError, match="bet_amount must be a positive number"):
            solver.find_gto_threshold(bet_amount=0)

        with pytest.raises(ValueError, match="num_simulations must be an integer between 100 and 10000"):
            solver.find_gto_threshold(num_simulations=50)

    def test_analyze_hand_strategy_parameter_validation(self, solver):
        """Test parameter validation for analyze_hand_strategy."""
        # Note: This will fail until we implement the method with validation
        with pytest.raises(ValueError, match="hole_cards must be a list of exactly 2 card strings"):
            solver.analyze_hand_strategy(['As'])  # Only 1 card

        with pytest.raises(ValueError, match="hole_cards must be a list of exactly 2 card strings"):
            solver.analyze_hand_strategy(['As', 'Ks', 'Qs'])  # 3 cards

        with pytest.raises(ValueError, match="num_opponents must be an integer between 1 and 9"):
            solver.analyze_hand_strategy(['As', 'Ks'], num_opponents=0)

        with pytest.raises(ValueError, match="pot_size must be a positive number"):
            solver.analyze_hand_strategy(['As', 'Ks'], pot_size=0)

        with pytest.raises(ValueError, match="bet_amount must be a positive number"):
            solver.analyze_hand_strategy(['As', 'Ks'], bet_amount=-1)

        with pytest.raises(ValueError, match="num_simulations must be an integer between 100 and 10000"):
            solver.analyze_hand_strategy(['As', 'Ks'], num_simulations=100000)

    @patch('hopilot.all_in_fold_gto.AllInFoldGTOSolver._calculate_ev_with_bonus')
    def test_find_gto_threshold_basic_functionality(self, mock_ev_calc, solver, mock_analyzer):
        """Test basic GTO threshold calculation functionality."""
        # Mock the analyzer's equity calculation
        mock_analyzer.calculate_odds_random_opponents.return_value = {
            'win_probability': 0.5
        }

        # Mock EV calculation to return positive for strong hands, negative for weak
        def mock_ev_func(hole_cards, board_cards, equity, pot_size, bet_amount):
            # Simple heuristic: hands with A or K get positive EV
            hand_str = ''.join(hole_cards)
            if 'A' in hand_str or 'K' in hand_str:
                return 1.0  # Positive EV
            else:
                return -1.0  # Negative EV

        mock_ev_calc.side_effect = mock_ev_func

        # This test will fail until the full implementation is done
        # For now, we're just setting up the test structure
        result = solver.find_gto_threshold(num_opponents=8, pot_size=20, bet_amount=10, num_simulations=100)

        # Basic structure checks
        assert isinstance(result, dict)
        assert 'threshold_equity' in result
        assert 'optimal_hands' in result
        assert 'total_hands' in result
        assert 'optimal_range' in result
        assert 'bonus_payouts' in result

        # Equity should be between 0 and 1
        assert 0.0 <= result['threshold_equity'] <= 1.0

    def test_get_hand_category(self, mock_analyzer):
        """Test hand category detection for bonus payouts."""
        # Set up mock analyzer
        mock_analyzer.get_hand_class.side_effect = lambda hole, board: {
            (('As', 'Ks'), ('Qs', 'Js', 'Ts')): 'Straight Flush',  # Royal flush case
            (('9s', '8s'), ('Ts', '7s', '6s')): 'Straight Flush',  # Straight flush case
            (('As', 'Ah'), ('Ad', 'Ac', 'Ks')): 'Four of a Kind',  # Quads case
            (('As', '2h'), ('3c', '5d', '7s')): 'High Card',  # High card case
        }.get((tuple(hole), tuple(board)), 'High Card')
        
        solver = AllInFoldGTOSolver(mock_analyzer)
        
        # Royal flush
        category = solver._get_hand_category(['As', 'Ks'], ['Qs', 'Js', 'Ts'])
        assert category == 'royal_flush'

        # Straight flush
        category = solver._get_hand_category(['9s', '8s'], ['Ts', '7s', '6s'])
        assert category == 'straight_flush'

        # Four of a kind
        category = solver._get_hand_category(['As', 'Ah'], ['Ad', 'Ac', 'Ks'])
        assert category == 'four_of_a_kind'

        # High card
        category = solver._get_hand_category(['As', '2h'], ['3c', '5d', '7s'])
        assert category == 'high_card'

    def test_calculate_ev_with_bonus(self, solver):
        """Test EV calculation with bonus payouts."""
        # Mock the analyzer for hand evaluation
        mock_result = Mock()
        mock_result.get_hand_class.return_value = "Flush"
        solver.analyzer.get_hand_class = mock_result.get_hand_class

        # Test with flush (5x multiplier) - use cards that don't form royal flush
        ev = solver._calculate_ev_with_bonus(
            hole_cards=['As', '2s'],  # Different cards to avoid royal flush
            board_cards=['3s', '5s', '7s'],
            equity=0.6,
            pot_size=20,
            bet_amount=10
        )

        # Standard EV: 0.6 * 20 - 0.4 * 10 = 12 - 4 = 8
        # Bonus EV: 0.6 * (20 * 5) = 60
        # Total EV: 8 + 60 = 68
        assert ev == 68.0

    def test_calculate_ev_without_bonus(self, solver):
        """Test EV calculation for hands without bonus."""
        # Mock the analyzer for hand evaluation
        mock_result = Mock()
        mock_result.get_hand_class.return_value = "High Card"
        solver.analyzer.get_hand_class = mock_result.get_hand_class

        # Test with high card (no bonus)
        ev = solver._calculate_ev_with_bonus(
            hole_cards=['As', '2h'],
            board_cards=['3c', '5d', '7s'],
            equity=0.4,
            pot_size=20,
            bet_amount=10
        )

        # Standard EV only: 0.4 * 20 - 0.6 * 10 = 8 - 6 = 2
        assert ev == 2.0