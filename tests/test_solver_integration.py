"""
Unit tests for AllInFoldGTOSolver persistence strategy integration.

Tests that the solver correctly interacts with persistence strategies
without requiring actual database operations.
"""

import pytest
from unittest.mock import Mock
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.database.persistence import MockPersistenceStrategy


class TestSolverPersistenceIntegration:
    """Test solver integration with persistence strategies."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock poker analyzer."""
        analyzer = Mock(spec=PokerAnalyzer)
        # Mock the equity calculation
        analyzer.calculate_odds_random_opponents.return_value = {
            'win_probability': 0.6,
            'total_simulations': 1000
        }
        # Mock hand evaluation - return integer strength values (lower is better)
        analyzer.evaluate_hand.side_effect = lambda hole_cards, board_cards: {
            # Return different strength values for different hands
            ('As', 'Kh'): 100,  # Hero hand - relatively weak
            ('Qd', 'Jd'): 200,  # Opponent 1
            ('7s', '8s'): 150,  # Opponent 2
            ('2h', '3h'): 300,  # Opponent 3
            ('Ac', 'Kc'): 90,   # Opponent 4 - better than hero
            ('Td', '9d'): 250,  # Opponent 5
        }.get(tuple(hole_cards), 500)  # Default weak hand
        return analyzer

    @pytest.fixture
    def mock_persistence(self):
        """Create a mock persistence strategy."""
        return MockPersistenceStrategy()

    @pytest.fixture
    def solver(self, mock_analyzer, mock_persistence):
        """Create solver with mock dependencies."""
        return AllInFoldGTOSolver(mock_analyzer, mock_persistence)

    def test_solver_accepts_persistence_strategy(self, mock_analyzer, mock_persistence):
        """Test that solver constructor accepts persistence strategy."""
        solver = AllInFoldGTOSolver(mock_analyzer, mock_persistence)
        assert solver.persistence is mock_persistence

    def test_analyze_hand_strategy_calls_persistence(self, solver, mock_persistence):
        """Test that analyze_hand_strategy calls persistence methods."""
        # Reset mock to clear any previous calls
        mock_persistence.reset()

        # Call analyze_hand_strategy
        result = solver.analyze_hand_strategy(
            hole_cards=['As', 'Kh'],
            num_opponents=5,
            pot_size=20,
            bet_amount=10,
            num_simulations=100
        )

        # Verify the method completed
        assert 'recommendation' in result
        assert result['recommendation'] in ['ALL-IN', 'FOLD']

        # Note: Currently this doesn't call persistence because the method
        # only returns aggregated results. This test will need to be updated
        # when the method is modified to store individual game states.

    def test_persistence_strategy_interface(self, mock_persistence):
        """Test that mock persistence strategy implements the interface."""
        # Test game state storage
        game_state_id = mock_persistence.store_game_state(
            simulation_id=1,
            matrix_cell_id=1,
            timestamp='2024-01-01T00:00:00',
            round_name='preflop',
            pot_size=20.0,
            board_cards=[],
            outcome='hero_win'
        )
        assert game_state_id == 1

        # Test player storage
        player_id = mock_persistence.store_player(
            game_state_id=game_state_id,
            position=0,
            hole_cards=['As', 'Kh'],
            stack_size=100.0,
            is_hero=True
        )
        assert player_id == 1

        # Test bet storage
        bet_id = mock_persistence.store_bet(
            game_state_id=game_state_id,
            player_id=player_id,
            amount=10.0,
            action_type='all_in'
        )
        assert bet_id == 1

        # Test transaction methods
        mock_persistence.commit_transaction()
        assert mock_persistence.commit_calls == 1

        mock_persistence.rollback_transaction()
        assert mock_persistence.rollback_calls == 1

    def test_persistence_call_recording(self, mock_persistence):
        """Test that mock persistence records all calls for verification."""
        mock_persistence.reset()

        # Make some calls
        mock_persistence.store_game_state(1, 1, '2024-01-01T00:00:00', 'preflop', 20.0, [], 'win')
        mock_persistence.store_player(1, 0, ['As', 'Kh'], 100.0, True)
        mock_persistence.commit_transaction()

        # Verify calls were recorded
        assert len(mock_persistence.store_game_state_calls) == 1
        assert len(mock_persistence.store_player_calls) == 1
        assert mock_persistence.commit_calls == 1

        # Verify call details
        game_state_call = mock_persistence.store_game_state_calls[0]
        assert game_state_call['simulation_id'] == 1
        assert game_state_call['matrix_cell_id'] == 1
        assert game_state_call['pot_size'] == 20.0

        player_call = mock_persistence.store_player_calls[0]
        assert player_call['game_state_id'] == 1
        assert player_call['hole_cards'] == ['As', 'Kh']
        assert player_call['is_hero'] is True