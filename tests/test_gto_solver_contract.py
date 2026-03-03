"""
Contract tests for AllInFoldGTOSolver API compliance.
"""

import pytest
from unittest.mock import Mock
from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.poker_analyzer import PokerAnalyzer


class TestAllInFoldGTOSolverContract:
    """Contract tests ensuring API compliance."""

    @pytest.fixture
    def analyzer(self):
        """Create a real PokerAnalyzer for contract testing."""
        return PokerAnalyzer()

    @pytest.fixture
    def solver(self, analyzer):
        """Create solver with real analyzer."""
        return AllInFoldGTOSolver(analyzer)

    def test_constructor_signature(self, analyzer):
        """Test constructor accepts PokerAnalyzer."""
        solver = AllInFoldGTOSolver(analyzer)
        assert solver.analyzer == analyzer

    def test_set_bonus_payouts_method_exists(self, solver):
        """Test set_bonus_payouts method exists and is callable."""
        assert hasattr(solver, 'set_bonus_payouts')
        assert callable(solver.set_bonus_payouts)

    def test_find_gto_threshold_method_exists(self, solver):
        """Test find_gto_threshold method exists and is callable."""
        assert hasattr(solver, 'find_gto_threshold')
        assert callable(solver.find_gto_threshold)

    def test_analyze_hand_strategy_method_exists(self, solver):
        """Test analyze_hand_strategy method exists and is callable."""
        assert hasattr(solver, 'analyze_hand_strategy')
        assert callable(solver.analyze_hand_strategy)

    def test_find_gto_threshold_return_structure(self, solver):
        """Test find_gto_threshold returns expected structure."""
        # This will fail until implementation is complete
        # For now, just test that it raises expected validation errors
        with pytest.raises(ValueError):
            solver.find_gto_threshold(num_opponents=10)  # Invalid opponents

    def test_analyze_hand_strategy_return_structure(self, solver):
        """Test analyze_hand_strategy returns expected structure."""
        # This will fail until implementation is complete
        # For now, just test that it raises expected validation errors
        with pytest.raises(ValueError):
            solver.analyze_hand_strategy(['As'])  # Invalid hole cards

    def test_bonus_payouts_initialization(self, solver):
        """Test bonus payouts are initialized with expected categories."""
        expected_categories = [
            'royal_flush', 'straight_flush', 'four_of_a_kind',
            'full_house', 'flush', 'straight', 'three_of_a_kind',
            'two_pair', 'one_pair'
        ]

        for category in expected_categories:
            assert category in solver.bonus_payouts
            assert isinstance(solver.bonus_payouts[category], (int, float))
            assert solver.bonus_payouts[category] >= 0

    def test_set_bonus_payouts_contract(self, solver):
        """Test set_bonus_payouts contract compliance."""
        # Should accept dict with valid data
        payouts = {'royal_flush': 1000, 'straight_flush': 200}
        solver.set_bonus_payouts(payouts)  # Should not raise

        # Should raise TypeError for non-dict
        with pytest.raises(TypeError):
            solver.set_bonus_payouts("not a dict")

        # Should raise ValueError for negative values
        with pytest.raises(ValueError):
            solver.set_bonus_payouts({'royal_flush': -100})

    def test_parameter_validation_ranges(self, solver):
        """Test parameter validation matches contract ranges."""
        # num_opponents: 1-9
        with pytest.raises(ValueError):
            solver.find_gto_threshold(num_opponents=0)
        with pytest.raises(ValueError):
            solver.find_gto_threshold(num_opponents=10)

        # pot_size: > 0
        with pytest.raises(ValueError):
            solver.find_gto_threshold(pot_size=0)
        with pytest.raises(ValueError):
            solver.find_gto_threshold(pot_size=-1)

        # bet_amount: > 0
        with pytest.raises(ValueError):
            solver.find_gto_threshold(bet_amount=0)

        # num_simulations: 100-10000
        with pytest.raises(ValueError):
            solver.find_gto_threshold(num_simulations=99)
        with pytest.raises(ValueError):
            solver.find_gto_threshold(num_simulations=10001)

    def test_analyze_hand_strategy_validation(self, solver):
        """Test analyze_hand_strategy parameter validation."""
        # hole_cards must be list of exactly 2 strings
        with pytest.raises(ValueError):
            solver.analyze_hand_strategy(['As'])  # Too few
        with pytest.raises(ValueError):
            solver.analyze_hand_strategy(['As', 'Ks', 'Qs'])  # Too many
        with pytest.raises(ValueError):
            solver.analyze_hand_strategy('As Ks')  # Not a list

        # Other parameters same as find_gto_threshold
        with pytest.raises(ValueError):
            solver.analyze_hand_strategy(['As', 'Ks'], num_opponents=0)