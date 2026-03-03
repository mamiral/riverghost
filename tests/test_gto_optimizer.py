"""
Unit tests for GTOOptimizer - Range vs Range Nash Equilibrium Solver.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
from unittest.mock import Mock, patch
from hopilot.gto.gto_optimizer import GTOOptimizer


class TestGTOOptimizer:
    """Test suite for GTOOptimizer component."""

    @pytest.fixture
    def mock_analyzer(self):
        """Mock PokerAnalyzer for testing."""
        return Mock()

    @pytest.fixture
    def optimizer(self, mock_analyzer):
        """Create GTOOptimizer instance for testing."""
        return GTOOptimizer(mock_analyzer)

    @pytest.fixture
    def sample_hero_range(self):
        """Sample hero range for testing."""
        return ['AA', 'AKs', 'AQs', 'AJs', 'ATs', 'AKo', 'AQo']

    @pytest.fixture
    def sample_villain_range(self):
        """Sample villain range for testing."""
        return ['KK', 'QQ', 'JJ', 'AKs', 'AQs', 'AKo']

    def test_initialization(self, optimizer, mock_analyzer):
        """Test GTOOptimizer initialization."""
        assert optimizer.analyzer is mock_analyzer
        assert hasattr(optimizer, 'find_nash_equilibrium')
        assert hasattr(optimizer, 'calculate_range_vs_range_equity')
        assert hasattr(optimizer, 'find_indifference_points')

    def test_find_nash_equilibrium_basic(self, optimizer, sample_hero_range, sample_villain_range):
        """Test basic Nash equilibrium finding."""
        with patch.object(optimizer, 'calculate_range_vs_range_equity') as mock_equity:
            # Mock equity calculations
            mock_equity.return_value = {
                'hero_equity': 0.55,
                'villain_equity': 0.45,
                'hero_range_size': len(sample_hero_range),
                'villain_range_size': len(sample_villain_range)
            }

            result = optimizer.find_nash_equilibrium(
                hero_range=sample_hero_range,
                villain_range=sample_villain_range,
                pot_size=20,
                bet_amount=10
            )

            assert 'hero_strategy' in result
            assert 'villain_strategy' in result
            assert 'equilibrium_found' in result
            assert 'iterations' in result

    def test_calculate_range_vs_range_equity(self, optimizer, sample_hero_range, sample_villain_range):
        """Test range vs range equity calculation."""
        with patch.object(optimizer.analyzer, 'calculate_odds') as mock_odds:
            # Mock odds calculations for each hand matchup
            mock_odds.return_value = {
                'win_probability': 0.5,
                'tie_probability': 0.05,
                'loss_probability': 0.45
            }

            result = optimizer.calculate_range_vs_range_equity(
                hero_range=sample_hero_range,
                villain_range=sample_villain_range,
                num_simulations=100
            )

            assert 'hero_equity' in result
            assert 'villain_equity' in result
            assert 'hero_range_size' in result
            assert 'villain_range_size' in result
            assert result['hero_equity'] + result['villain_equity'] == pytest.approx(1.0, abs=0.1)  # Should sum to ~1

    def test_find_indifference_points(self, optimizer, sample_hero_range):
        """Test indifference point calculation for optimal shove frequencies."""
        with patch.object(optimizer, 'calculate_range_vs_range_equity') as mock_equity:
            mock_equity.return_value = {'hero_equity': 0.6, 'villain_equity': 0.4}

            result = optimizer.find_indifference_points(
                hero_range=sample_hero_range,
                villain_range=['KK', 'QQ'],
                pot_size=20,
                bet_amount=10
            )

            assert 'indifference_points' in result
            assert 'optimal_frequencies' in result
            assert len(result['optimal_frequencies']) == len(sample_hero_range)

    def test_asymmetric_stacks_support(self, optimizer, sample_hero_range, sample_villain_range):
        """Test support for asymmetric stack sizes."""
        result = optimizer.find_nash_equilibrium(
            hero_range=sample_hero_range,
            villain_range=sample_villain_range,
            pot_size=30,
            bet_amount=15,
            hero_stack=100,
            villain_stack=80
        )

        assert 'hero_strategy' in result
        assert 'villain_strategy' in result
        # Asymmetric stacks should affect the equilibrium

    def test_convergence_checking(self, optimizer, sample_hero_range, sample_villain_range):
        """Test convergence validation for Nash equilibrium."""
        with patch.object(optimizer, 'calculate_range_vs_range_equity') as mock_equity:
            mock_equity.return_value = {'hero_equity': 0.55, 'villain_equity': 0.45}

            result = optimizer.find_nash_equilibrium(
                hero_range=sample_hero_range,
                villain_range=sample_villain_range,
                pot_size=20,
                bet_amount=10,
                max_iterations=10,
                tolerance=0.01
            )

            assert 'converged' in result
            assert 'iterations' in result
            assert result['iterations'] <= 10

    def test_empty_ranges_handling(self, optimizer):
        """Test handling of empty ranges."""
        with pytest.raises(ValueError):
            optimizer.find_nash_equilibrium(
                hero_range=[],
                villain_range=['AA'],
                pot_size=20,
                bet_amount=10
            )

        with pytest.raises(ValueError):
            optimizer.find_nash_equilibrium(
                hero_range=['AA'],
                villain_range=[],
                pot_size=20,
                bet_amount=10
            )

    def test_invalid_parameters(self, optimizer, sample_hero_range, sample_villain_range):
        """Test validation of invalid parameters."""
        with pytest.raises(ValueError):
            optimizer.find_nash_equilibrium(
                hero_range=sample_hero_range,
                villain_range=sample_villain_range,
                pot_size=-5,  # Invalid
                bet_amount=10
            )

        with pytest.raises(ValueError):
            optimizer.find_nash_equilibrium(
                hero_range=sample_hero_range,
                villain_range=sample_villain_range,
                pot_size=20,
                bet_amount=-5  # Invalid
            )

    def test_best_response_validation(self, optimizer, sample_hero_range, sample_villain_range):
        """Test best response validation for equilibrium."""
        with patch.object(optimizer, 'calculate_range_vs_range_equity') as mock_equity:
            mock_equity.return_value = {'hero_equity': 0.55, 'villain_equity': 0.45}

            result = optimizer.find_nash_equilibrium(
                hero_range=sample_hero_range,
                villain_range=sample_villain_range,
                pot_size=20,
                bet_amount=10,
                validate_best_response=True
            )

            assert 'best_response_valid' in result
            assert 'deviation_analysis' in result

    def test_dynamic_programming_convergence(self, optimizer):
        """Test that dynamic programming approach converges to Nash equilibrium."""
        # Create a simple 2x2 game for testing
        hero_range = ['AA', 'KK']
        villain_range = ['QQ', 'JJ']

        with patch.object(optimizer.analyzer, 'calculate_odds') as mock_odds:
            # Set up payoff matrix
            call_count = 0
            def mock_odds_func(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                # Simple payoff matrix where AA beats everything, etc.
                payoffs = {
                    0: {'win_probability': 0.8, 'tie_probability': 0.0, 'loss_probability': 0.2},  # AA vs QQ
                    1: {'win_probability': 0.7, 'tie_probability': 0.0, 'loss_probability': 0.3},  # AA vs JJ
                    2: {'win_probability': 0.6, 'tie_probability': 0.0, 'loss_probability': 0.4},  # KK vs QQ
                    3: {'win_probability': 0.5, 'tie_probability': 0.0, 'loss_probability': 0.5},  # KK vs JJ
                }
                return payoffs.get(call_count - 1, {'win_probability': 0.5, 'tie_probability': 0.0, 'loss_probability': 0.5})

            mock_odds.side_effect = mock_odds_func

            result = optimizer.find_nash_equilibrium(
                hero_range=hero_range,
                villain_range=villain_range,
                pot_size=20,
                bet_amount=10,
                max_iterations=50
            )

            assert result['equilibrium_found'] is True
            assert 'hero_strategy' in result
            assert 'villain_strategy' in result
            assert len(result['hero_strategy']) == len(hero_range)
            assert len(result['villain_strategy']) == len(villain_range)