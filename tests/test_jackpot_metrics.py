"""
Tests for jackpot detection and metrics calculation.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from hopilot.jackpot_detector import JackpotDetector
from hopilot.metrics_calculator import MetricsCalculator, calculate_matrix_equity, calculate_jackpot_analysis
from hopilot.models import GameState, Player, BoardCard, MatrixCell


class TestJackpotDetector:
    """Test jackpot detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = JackpotDetector()

    def test_init(self):
        """Test detector initialization."""
        assert hasattr(self.detector, 'logger')
        assert hasattr(self.detector, 'JACKPOT_RULES')

    def test_detect_jackpots_empty_game(self):
        """Test jackpot detection with empty game state."""
        game_state = Mock()
        game_state.hero_player = None
        game_state.villain_player = None

        jackpots = self.detector.detect_jackpots(game_state)
        assert jackpots == []

    def test_calculate_payout(self):
        """Test payout calculation."""
        payout = self.detector._calculate_payout('royal_flush', Decimal('1000'))
        expected = Decimal('1000') * Decimal('500')  # 500x multiplier
        assert payout == expected

    def test_hole_cards_contribute(self):
        """Test hole cards contribution check."""
        cards_used = ['As', 'Ks', 'Qs']
        hole_cards = ['As', 'Kh']

        contributes = self.detector._hole_cards_contribute(cards_used, hole_cards)
        assert contributes == True

        # Test no contribution
        hole_cards_no_contrib = ['Js', 'Th']
        contributes = self.detector._hole_cards_contribute(cards_used, hole_cards_no_contrib)
        assert contributes == False

    def test_detect_royal_flush(self):
        """Test royal flush detection."""
        # Royal flush: A-K-Q-J-10 same suit
        all_cards = ['As', 'Ks', 'Qs', 'Js', 'Ts', '2h']
        hole_cards = ['As', 'Ks']

        is_royal, cards_used = self.detector._detect_royal_flush(all_cards, hole_cards)
        assert is_royal == True
        assert len(cards_used) == 5
        assert all(card.endswith('s') for card in cards_used)

    def test_detect_four_of_a_kind(self):
        """Test four of a kind detection."""
        all_cards = ['As', 'Ah', 'Ad', 'Ac', 'Ks', 'Qs']
        hole_cards = ['As', 'Ah']

        is_quads, cards_used = self.detector._detect_four_of_a_kind(all_cards, hole_cards)
        assert is_quads == True
        assert len(cards_used) == 4
        assert all(card.startswith('A') for card in cards_used)

    def test_cards_to_values(self):
        """Test card to value conversion."""
        cards = ['2s', 'Ts', 'As', 'Ks']
        values = self.detector._cards_to_values(cards)
        expected = [2, 10, 14, 13]  # Should be sorted
        assert values == sorted(expected)

    def test_has_straight(self):
        """Test straight detection."""
        # Has straight: 5,6,7,8,9
        values = [5, 6, 7, 8, 9, 10]
        assert self.detector._has_straight(values) == True

        # No straight
        values = [2, 4, 6, 8, 10]
        assert self.detector._has_straight(values) == False

        # Ace-low straight: A,2,3,4,5
        values = [14, 2, 3, 4, 5]
        assert self.detector._has_straight(values) == True

    def test_count_ranks(self):
        """Test rank counting."""
        cards = ['As', 'Ah', 'Ks', 'Kh', 'Qs']
        counts = self.detector._count_ranks(cards)

        assert counts['A'] == 2
        assert counts['K'] == 2
        assert counts['Q'] == 1


class TestMetricsCalculator:
    """Test metrics calculation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = MetricsCalculator()

    def test_calculate_cell_equity_no_games(self):
        """Test equity calculation with no game states."""
        cell = Mock()
        cell.game_states = []

        equity = self.calculator.calculate_cell_equity(cell)
        assert equity is None

    @patch.object(MetricsCalculator, '_is_hero_winner')
    def test_calculate_cell_equity_with_games(self, mock_winner):
        """Test equity calculation with game states."""
        # Mock 10 games, hero wins 6
        mock_winner.side_effect = [True] * 6 + [False] * 4

        cell = Mock()
        cell.game_states = [Mock() for _ in range(10)]

        equity = self.calculator.calculate_cell_equity(cell)
        assert equity == Decimal('0.6')

    def test_calculate_jackpot_metrics_no_games(self):
        """Test jackpot metrics with no games."""
        cell = Mock()
        cell.game_states = []

        metrics = self.calculator.calculate_jackpot_metrics(cell)
        assert metrics['frequency'] == Decimal(0)
        assert metrics['avg_payout'] == Decimal(0)

    def test_calculate_jackpot_adjusted_ev(self):
        """Test jackpot-adjusted EV calculation."""
        equity = Decimal('0.5')
        jackpot_metrics = {
            'frequency': Decimal('0.1'),
            'avg_payout': Decimal('1000')
        }

        adjusted_ev = self.calculator.calculate_jackpot_adjusted_ev(equity, jackpot_metrics)
        expected = Decimal('0.5') + Decimal('0.1') * Decimal('1000')
        assert adjusted_ev == expected

    def test_assess_convergence_insufficient_data(self):
        """Test convergence assessment with insufficient data."""
        cell = Mock()
        cell.game_states = [Mock() for _ in range(50)]  # Less than 100

        status = self.calculator.assess_convergence(cell)
        assert status == "insufficient_data"

    @patch.object(MetricsCalculator, '_calculate_equity_from_games')
    def test_assess_convergence_converged(self, mock_equity):
        """Test convergence assessment when converged."""
        mock_equity.side_effect = [Decimal('0.5'), Decimal('0.501')]  # Small difference

        cell = Mock()
        cell.game_states = [Mock() for _ in range(150)]

        status = self.calculator.assess_convergence(cell, threshold=0.01)
        assert status == "converged"


class TestMetricsFunctions:
    """Test standalone metrics functions."""

    @patch('hopilot.database.get_database_connection')
    def test_calculate_matrix_equity(self, mock_conn):
        """Test matrix equity calculation."""
        # Mock database connection and session
        mock_session = Mock()
        mock_conn.return_value.session_scope.return_value.__enter__ = Mock(return_value=mock_session)

        # Mock cells with equity calculations
        mock_cell = Mock()
        mock_cell.row_index = 0
        mock_cell.col_index = 0
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_cell]

        # Mock calculator
        with patch.object(MetricsCalculator, 'calculate_cell_equity', return_value=Decimal('0.6')):
            result = calculate_matrix_equity(1)

        assert result['0,0'] == 0.6

    @patch('hopilot.database.get_database_connection')
    def test_calculate_jackpot_analysis(self, mock_conn):
        """Test jackpot analysis calculation."""
        # Mock database connection and session
        mock_session = Mock()
        mock_conn.return_value.session_scope.return_value.__enter__ = Mock(return_value=mock_session)

        # Mock query results
        mock_result = Mock()
        mock_result.jackpot_type = 'royal_flush'
        mock_result.count = 5
        mock_result.avg_payout = Decimal('10000')
        mock_session.query.return_value.group_by.return_value.all.return_value = [mock_result]

        result = calculate_jackpot_analysis()

        assert len(result) == 1
        assert result[0]['jackpot_type'] == 'royal_flush'
        assert result[0]['frequency'] == 5
        assert result[0]['avg_payout'] == 10000.0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = JackpotDetector()
        self.calculator = MetricsCalculator()

    def test_jackpot_detector_invalid_jackpot_type(self):
        """Test jackpot detector with invalid jackpot type."""
        with pytest.raises(KeyError):
            self.detector._calculate_payout('invalid_type', Decimal('1000'))

    def test_jackpot_detector_empty_cards(self):
        """Test jackpot detection with empty card lists."""
        game_state = Mock()
        game_state.hero_player = Mock()
        game_state.hero_player.hole_cards = []
        game_state.villain_player = Mock()
        game_state.villain_player.hole_cards = []
        game_state.board_cards = Mock()
        game_state.board_cards.cards = []

        jackpots = self.detector.detect_jackpots(game_state)
        assert jackpots == []

    def test_metrics_calculator_empty_cell(self):
        """Test metrics calculation with empty cell."""
        cell = Mock()
        cell.game_states = []

        equity = self.calculator.calculate_cell_equity(cell)
        assert equity is None

    def test_metrics_calculator_single_game(self):
        """Test metrics calculation with single game."""
        cell = Mock()
        game_state = Mock()
        game_state.outcome = 'hero_win'
        cell.game_states = [game_state]

        with patch.object(self.calculator, '_is_hero_winner', return_value=True):
            equity = self.calculator.calculate_cell_equity(cell)
            assert equity == Decimal('1.0')

    def test_jackpot_adjusted_ev_zero_frequency(self):
        """Test jackpot-adjusted EV with zero frequency."""
        equity = Decimal('0.5')
        jackpot_metrics = {
            'frequency': Decimal('0'),
            'avg_payout': Decimal('1000')
        }

        adjusted_ev = self.calculator.calculate_jackpot_adjusted_ev(equity, jackpot_metrics)
        assert adjusted_ev == equity

    def test_convergence_assessment_boundary_cases(self):
        """Test convergence assessment at boundary conditions."""
        cell = Mock()
        
        # Exactly 100 games (minimum for assessment)
        cell.game_states = [Mock() for _ in range(100)]
        status = self.calculator.assess_convergence(cell)
        assert status in ["converged", "not_converged", "insufficient_data", "diverging"]

        # Just below threshold
        cell.game_states = [Mock() for _ in range(99)]
        status = self.calculator.assess_convergence(cell)
        assert status == "insufficient_data"

    def test_invalid_card_formats(self):
        """Test handling of invalid card formats."""
        # Test with malformed cards - should raise KeyError
        cards = ['invalid', 'As', 'Ks']
        with pytest.raises(KeyError):
            self.detector._cards_to_values(cards)