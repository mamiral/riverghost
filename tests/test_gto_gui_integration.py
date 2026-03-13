import pytest
import pygame
import yaml
import time
from unittest.mock import Mock, patch, MagicMock, mock_open, mock_open
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.gto.gto_optimizer import GTOOptimizer
from hopilot.aof_gto_browser_gui import AoFGTOBrowserGUI


@pytest.fixture
def mock_pygame_setup():
    """Mock pygame setup for GUI testing."""
    with patch('pygame.init'), \
         patch('pygame.display.set_mode'), \
         patch('pygame.display.set_caption'), \
         patch('pygame.font.Font'), \
         patch('pygame.time.Clock'), \
         patch('pygame.display.flip'), \
         patch('pygame.event.get', return_value=[]):
        yield


@pytest.fixture
def mock_analyzer():
    """Mock PokerAnalyzer for testing."""
    analyzer = Mock(spec=PokerAnalyzer)
    analyzer.calculate_odds = Mock(return_value={
        'win_probability': 0.5,
        'tie_probability': 0.0,
        'loss_probability': 0.5,
        'valid_simulations': 100,
        'wins': 50,
        'ties': 0
    })
    return analyzer


@pytest.fixture
def mock_optimizer(mock_analyzer):
    """Mock GTOOptimizer for testing."""
    optimizer = Mock(spec=GTOOptimizer)
    optimizer.find_nash_equilibrium = Mock(return_value={
        'equilibrium_found': True,
        'hero_strategy': [1.0, 0.8, 0.6],
        'villain_strategy': [0.9, 0.7, 0.4],
        'iterations': 8,
        'convergence_tolerance': 0.01,
        'best_response_valid': True
    })
    optimizer.find_indifference_points = Mock(return_value={
        'indifference_points': {
            'AA': {'equity_vs_calling': 0.85, 'indifference_frequency': 1.0},
            'AKs': {'equity_vs_calling': 0.62, 'indifference_frequency': 1.0},
            'AQs': {'equity_vs_calling': 0.45, 'indifference_frequency': 0.0}
        },
        'optimal_frequencies': [1.0, 1.0, 0.0],
        'hero_range_size': 3,
        'villain_range_size': 3
    })
    optimizer.find_gto_threshold = Mock(return_value={
        'threshold_equity': 0.35,
        'optimal_range': ['AA', 'KK', 'QQ', 'AKs', 'AQs', 'AJs'],
        'ev_breakdown': {
            'AA': 3.2, 'KK': 2.8, 'QQ': 2.1,
            'AKs': 1.8, 'AQs': 1.2, 'AJs': 0.8
        },
        'bonus_adjusted_threshold': 0.38
    })
    return optimizer


class TestGTOGUIIntegration:
    """End-to-end GUI workflow tests for GTO solver integration."""

    def test_full_threshold_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test complete threshold analysis workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Step 1: Set threshold mode
        panel.set_mode('threshold')
        assert panel.current_mode == 'threshold'

        # Step 2: Configure parameters
        assert panel.set_num_opponents(6)
        assert panel.set_pot_size(30.0)
        assert panel.set_bet_amount(15.0)

        # Step 3: Execute calculation
        result = panel.calculate_threshold()

        # Step 4: Verify results
        assert result is not None
        assert 'threshold_equity' in result
        assert 'optimal_range' in result
        assert result['threshold_equity'] == 0.35
        assert len(result['optimal_range']) == 6

        # Step 5: Verify display formatting
        formatted = panel.format_threshold_results(result)
        assert 'Threshold Equity' in formatted
        assert 'Optimal Range' in formatted

    def test_full_range_vs_range_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test complete range vs range analysis workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        # Setup mock return value
        mock_optimizer.find_nash_equilibrium.return_value = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.8, 0.6],
            'villain_strategy': [0.9, 0.7, 0.4],
            'iterations': 8,
            'convergence_tolerance': 0.01,
            'best_response_valid': True
        }

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Step 1: Set range vs range mode
        panel.set_mode('range_vs_range')
        assert panel.current_mode == 'range_vs_range'

        # Step 2: Load ranges
        hero_range_data = {
            'name': 'Hero Range',
            'hands': ['AA', 'AKs', 'AQs'],
            'description': 'Premium tournament range'
        }

        villain_range_data = {
            'name': 'Villain Range',
            'hands': ['KK', 'QQ', 'JJ'],
            'description': 'Medium strength range'
        }

        with patch('builtins.open', create=True), \
             patch('yaml.safe_load', side_effect=[hero_range_data, villain_range_data]):

            assert panel.load_hero_range('hero.yaml')
            assert panel.load_villain_range('villain.yaml')

        assert panel.hero_range == hero_range_data['hands']
        assert panel.villain_range == villain_range_data['hands']

        # Step 3: Configure parameters
        assert panel.set_pot_size(40.0)
        assert panel.set_bet_amount(20.0)

        # Step 4: Execute calculation
        result = panel.calculate_range_vs_range()

        # Step 5: Verify results
        assert result is not None
        assert result['equilibrium_found'] == True
        assert len(result['hero_strategy']) == 3
        assert len(result['villain_strategy']) == 3
        assert result['best_response_valid'] == True

        # Step 6: Verify display formatting
        formatted = panel.format_range_vs_range_results(result)
        assert 'Nash Equilibrium Found' in formatted
        assert 'Hero Strategy' in formatted
        assert 'Villain Strategy' in formatted

    def test_full_indifference_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test complete indifference points workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Step 1: Set indifference mode
        panel.set_mode('indifference')
        assert panel.current_mode == 'indifference'

        # Step 2: Load ranges
        hero_range_data = {
            'name': 'Test Hero',
            'hands': ['AA', 'AKs', 'AQs']
        }

        villain_range_data = {
            'name': 'Test Villain',
            'hands': ['KK', 'QQ', 'JJ']
        }

        with patch('builtins.open', create=True), \
             patch('yaml.safe_load', side_effect=[hero_range_data, villain_range_data]):

            assert panel.load_hero_range('hero.yaml')
            assert panel.load_villain_range('villain.yaml')

        # Step 3: Configure parameters
        assert panel.set_pot_size(25.0)
        assert panel.set_bet_amount(12.5)

        # Step 4: Execute calculation
        result = panel.calculate_indifference_points()

        # Step 5: Verify results
        assert result is not None
        assert 'optimal_frequencies' in result
        assert len(result['optimal_frequencies']) == 3
        assert result['optimal_frequencies'] == [1.0, 1.0, 0.0]  # AA and AKs shove, AQs folds

        # Step 6: Verify display formatting
        formatted = panel.format_indifference_results(result)
        assert 'Optimal Shove Frequencies' in formatted
        assert 'AA' in formatted
        assert 'AKs' in formatted
        assert 'AQs' in formatted

    def test_parameter_persistence_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test that parameters persist across mode switches."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Set initial parameters
        panel.set_num_opponents(7)
        panel.set_pot_size(35.0)
        panel.set_bet_amount(17.5)

        # Switch modes
        panel.set_mode('range_vs_range')
        panel.set_mode('indifference')
        panel.set_mode('threshold')

        # Verify parameters persisted
        assert panel.num_opponents == 7
        assert panel.pot_size == 35.0
        assert panel.bet_amount == 17.5


class TestAoFBrowserIntegration:
    @pytest.fixture
    def aof_app(self):
        pygame.init()
        app = AoFGTOBrowserGUI(width=1000, height=760)
        yield app
        pygame.quit()

    def test_position_switch_updates_matrix(self, aof_app):
        before = [c["value"] for c in aof_app.panel.payload["cells"]]
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.card_rects["BB"].center,
        )
        aof_app.panel.handle_event(event)
        after = [c["value"] for c in aof_app.panel.payload["cells"]]

        assert aof_app.panel.state.selected_position == "BB"
        assert before != after

    def test_action_switch_updates_matrix(self, aof_app):
        before = [c["value"] for c in aof_app.panel.payload["cells"]]
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.rects[("UTG", "ALL_IN")].center,
        )
        aof_app.panel.handle_event(event)
        after = [c["value"] for c in aof_app.panel.payload["cells"]]

        assert aof_app.panel.state.get_position_action("UTG") == "ALL_IN"
        assert before != after

    def test_metric_switch_updates_matrix(self, aof_app):
        before = [c["display"] for c in aof_app.panel.payload["cells"]]
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.metric_dropdown.rect.center,
        )
        aof_app.panel.handle_event(event)
        after = [c["display"] for c in aof_app.panel.payload["cells"]]

        assert aof_app.panel.state.selected_metric != "WIN_LOSE_PROBABILITY"
        assert before != after

    def test_position_switch_latency_under_1s(self, aof_app):
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.card_rects["SB"].center,
        )
        start = time.perf_counter()
        aof_app.panel.handle_event(event)
        elapsed = time.perf_counter() - start
        assert elapsed <= 1.0

    def test_action_switch_latency_under_1s(self, aof_app):
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.rects[("UTG", "ALL_IN")].center,
        )
        start = time.perf_counter()
        aof_app.panel.handle_event(event)
        elapsed = time.perf_counter() - start
        assert elapsed <= 1.0

    def test_metric_switch_latency_under_1s(self, aof_app):
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.metric_dropdown.rect.center,
        )
        start = time.perf_counter()
        aof_app.panel.handle_event(event)
        elapsed = time.perf_counter() - start
        assert elapsed <= 1.0

    def test_error_recovery_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test error handling and recovery in GUI workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Set up a failing calculation
        mock_optimizer.find_nash_equilibrium.side_effect = Exception("Simulation timeout")

        panel.set_mode('range_vs_range')
        panel.hero_range = ['AA', 'KK']
        panel.villain_range = ['QQ', 'JJ']

        # Execute failing calculation
        result = panel.calculate_current_mode()
        assert result is None
        assert panel.last_error is not None

        # Reset error state
        panel.clear_error()

        # Fix the mock and retry
        mock_optimizer.find_nash_equilibrium.side_effect = None
        mock_optimizer.find_nash_equilibrium.return_value = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.8],
            'villain_strategy': [0.9, 0.6],
            'iterations': 6,
            'best_response_valid': True
        }

        # Retry calculation
        result = panel.calculate_range_vs_range()
        assert result is not None
        assert result['equilibrium_found'] == True
        assert panel.last_error is None

    def test_progress_tracking_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test progress tracking during long calculations."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        # Setup mock return value
        mock_optimizer.find_nash_equilibrium.return_value = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.7],
            'villain_strategy': [0.8, 0.5],
            'iterations': 10,
            'best_response_valid': True
        }

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        mock_optimizer.find_nash_equilibrium.return_value = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.7],
            'villain_strategy': [0.8, 0.5],
            'iterations': 10,
            'best_response_valid': True
        }

        panel.set_mode('range_vs_range')
        panel.hero_range = ['AA', 'AKs']
        panel.villain_range = ['KK', 'QQ']

        # Start calculation
        panel.start_calculation()
        assert panel.is_calculating == True
        assert panel.progress == 0.0

        # Execute calculation (progress updates happen inside)
        result = panel.calculate_range_vs_range()

        # Complete the calculation
        panel.complete_calculation()

        # Verify progress completed
        assert panel.progress == 1.0
        assert panel.is_calculating == False
        assert result is not None

    def test_range_validation_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test range validation in GUI workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Test invalid range file
        with patch('builtins.open', side_effect=FileNotFoundError):
            success = panel.load_hero_range('nonexistent.yaml')
            assert success == False
            assert panel.last_error is not None

        # Test valid range file
        valid_range = {
            'name': 'Valid Range',
            'hands': ['AA', 'KK', 'QQ']
        }

        panel.clear_error()  # Clear previous error

        with patch('builtins.open', mock_open()), \
             patch('yaml.safe_load', return_value=valid_range):
            success = panel.load_hero_range('valid.yaml')
            assert success == True
            assert panel.hero_range == ['AA', 'KK', 'QQ']
            assert panel.last_error is None

    def test_mode_specific_validation(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test mode-specific validation requirements."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Threshold mode doesn't need ranges
        panel.set_mode('threshold')
        can_calculate = panel.can_calculate_current_mode()
        assert can_calculate == True

        # Range vs range mode needs both ranges
        panel.set_mode('range_vs_range')
        can_calculate = panel.can_calculate_current_mode()
        assert can_calculate == False  # No ranges loaded

        # Load ranges
        panel.hero_range = ['AA', 'KK']
        panel.villain_range = ['QQ', 'JJ']
        can_calculate = panel.can_calculate_current_mode()
        assert can_calculate == True

        # Indifference mode needs both ranges
        panel.set_mode('indifference')
        can_calculate = panel.can_calculate_current_mode()
        assert can_calculate == True  # Ranges already loaded

    def test_result_export_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test result export functionality."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        # Setup mock to return a result
        mock_optimizer.find_gto_threshold.return_value = {
            'threshold_equity': 0.35,
            'optimal_range': ['AA', 'KK']
        }

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Perform a calculation
        panel.set_mode('threshold')
        result = panel.calculate_current_mode()

        # Verify calculation worked
        assert panel.last_result is not None

        # Export results
        with patch('builtins.open', create=True) as mock_file, \
             patch('yaml.dump') as mock_yaml:
            success = panel.export_results('results.yaml')

            assert success == True
            mock_file.assert_called_once()
            mock_yaml.assert_called_once()

        # Test export failure
        with patch('builtins.open', side_effect=PermissionError):
            success = panel.export_results('readonly.yaml')
            assert success == False