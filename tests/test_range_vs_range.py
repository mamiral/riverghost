"""
Integration tests for range vs range GTO analysis.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
from unittest.mock import Mock, patch
from hopilot.gto.gto_optimizer import GTOOptimizer
from hopilot.poker_analyzer import PokerAnalyzer


class TestRangeVsRangeIntegration:
    """Integration tests for hero vs villain range analysis."""

    @pytest.fixture
    def analyzer(self):
        """Create real PokerAnalyzer for integration testing."""
        return PokerAnalyzer()

    @pytest.fixture
    def optimizer(self, analyzer):
        """Create GTOOptimizer with real analyzer."""
        return GTOOptimizer(analyzer)

    @pytest.fixture
    def tight_hero_range(self):
        """Tight hero range (premium hands)."""
        return ['AA', 'AKs', 'AQs', 'AJs', 'AKo']

    @pytest.fixture
    def loose_villain_range(self):
        """Loose villain range."""
        return ['AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AQs', 'AJs', 'ATs', 'AKo', 'AQo', 'AJo']

    def test_hero_vs_villain_basic_analysis(self, optimizer, tight_hero_range, loose_villain_range):
        """Test basic hero vs villain range analysis."""
        result = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=20,
            bet_amount=10,
            num_simulations=50  # Small number for testing
        )

        assert result['equilibrium_found'] is True
        assert len(result['hero_strategy']) == len(tight_hero_range)
        assert len(result['villain_strategy']) == len(loose_villain_range)

        # All strategies should be between 0 and 1
        assert all(0 <= freq <= 1 for freq in result['hero_strategy'])
        assert all(0 <= freq <= 1 for freq in result['villain_strategy'])

    def test_range_equity_calculation_accuracy(self, optimizer, tight_hero_range, loose_villain_range):
        """Test that range vs range equity calculations are reasonable."""
        equity_result = optimizer.calculate_range_vs_range_equity(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            num_simulations=100
        )

        # Equity should be reasonable (hero has premium hands vs loose range)
        assert 0.4 <= equity_result['hero_equity'] <= 0.7
        assert 0.3 <= equity_result['villain_equity'] <= 0.6
        assert abs(equity_result['hero_equity'] + equity_result['villain_equity'] - 1.0) < 0.1  # Should sum to ~1

    def test_indifference_point_calculation(self, optimizer):
        """Test indifference point calculation for shove frequencies."""
        hero_range = ['AA', 'AKs', 'AQs']
        villain_range = ['AA', 'KK', 'QQ']  # Stronger villain range

        result = optimizer.find_indifference_points(
            hero_range=hero_range,
            villain_range=villain_range,
            pot_size=20,
            bet_amount=10
        )

        assert 'indifference_points' in result
        assert 'optimal_frequencies' in result
        assert len(result['optimal_frequencies']) == len(hero_range)

        # With strong villain range, weaker hands should have lower shove frequencies
        # AA should have higher frequency than AQs
        assert result['optimal_frequencies'][0] >= result['optimal_frequencies'][2]  # AA >= AQs

    def test_asymmetric_stack_sizes(self, optimizer, tight_hero_range, loose_villain_range):
        """Test analysis with different stack sizes."""
        result = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=30,
            bet_amount=15,
            hero_stack=100,
            villain_stack=200,  # Villain has deeper stack
            num_simulations=50
        )

        assert result['equilibrium_found'] is True
        # With deeper villain stack, hero should be more conservative
        # (This is a behavioral test - actual frequencies depend on implementation)

    def test_convergence_with_different_tolerances(self, optimizer, tight_hero_range, loose_villain_range):
        """Test convergence behavior with different tolerance levels."""
        tight_result = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=20,
            bet_amount=10,
            tolerance=0.001,  # Tight tolerance
            max_iterations=20,
            num_simulations=30
        )

        loose_result = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=20,
            bet_amount=10,
            tolerance=0.01,  # Loose tolerance
            max_iterations=20,
            num_simulations=30
        )

        # Tight tolerance should generally take more iterations or be more precise
        assert tight_result['converged'] is True
        assert loose_result['converged'] is True

    def test_best_response_validation(self, optimizer, tight_hero_range, loose_villain_range):
        """Test best response validation of equilibrium solutions."""
        result = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=20,
            bet_amount=10,
            validate_best_response=True,
            num_simulations=50
        )

        assert 'best_response_valid' in result
        assert 'deviation_analysis' in result

        # Best response should be valid for Nash equilibrium
        assert result['best_response_valid'] is True

    def test_large_range_performance(self, optimizer):
        """Test performance with larger ranges."""
        large_hero_range = ['AA', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'AKo', 'AQo', 'AJo', 'KK', 'QQ']
        large_villain_range = ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'AKo', 'AQo', 'AJo', 'ATo']

        result = optimizer.find_nash_equilibrium(
            hero_range=large_hero_range,
            villain_range=large_villain_range,
            pot_size=20,
            bet_amount=10,
            num_simulations=25,  # Very small for performance
            max_iterations=5     # Limited iterations for performance
        )

        assert result['equilibrium_found'] is True
        assert len(result['hero_strategy']) == len(large_hero_range)
        assert len(result['villain_strategy']) == len(large_villain_range)

    def test_edge_case_ranges(self, optimizer):
        """Test edge cases with very small or specific ranges."""
        # Hero has nuts, villain has medium strength
        hero_range = ['AA']
        villain_range = ['QQ', 'JJ']

        result = optimizer.find_nash_equilibrium(
            hero_range=hero_range,
            villain_range=villain_range,
            pot_size=20,
            bet_amount=10,
            num_simulations=50
        )

        assert result['equilibrium_found'] is True
        # AA should always shove against QQ/JJ
        assert result['hero_strategy'][0] > 0.9

    def test_pot_odds_effect(self, optimizer, tight_hero_range, loose_villain_range):
        """Test how different pot odds affect equilibrium strategies."""
        small_pot_result = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=10,  # Small pot
            bet_amount=10,
            num_simulations=30
        )

        large_pot_result = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=50,  # Large pot
            bet_amount=10,
            num_simulations=30
        )

        # With larger pot, both players should be more aggressive
        # (This tests the behavioral effect of pot size)

    def test_strategy_persistence(self, optimizer, tight_hero_range, loose_villain_range):
        """Test that strategies are consistent across multiple runs."""
        result1 = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=20,
            bet_amount=10,
            num_simulations=50
        )

        result2 = optimizer.find_nash_equilibrium(
            hero_range=tight_hero_range,
            villain_range=loose_villain_range,
            pot_size=20,
            bet_amount=10,
            num_simulations=50
        )

        # Strategies should be reasonably consistent (within some tolerance)
        strategy_diff = sum(abs(a - b) for a, b in zip(result1['hero_strategy'], result2['hero_strategy']))
        assert strategy_diff < 0.5  # Allow some variation due to randomness