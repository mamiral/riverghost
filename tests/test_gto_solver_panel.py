import pytest
import pygame
from unittest.mock import Mock, patch, MagicMock
from hopilot.gui_components.gto_solver_panel import GTOSolverPanel
from hopilot.gto.gto_optimizer import GTOOptimizer
from hopilot.poker_analyzer import PokerAnalyzer


class TestGTOSolverPanel:
    """Test GTOSolverPanel GUI component functionality."""

    @pytest.fixture
    def mock_analyzer(self):
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
    def mock_optimizer(self, mock_analyzer):
        """Mock GTOOptimizer for testing."""
        optimizer = Mock(spec=GTOOptimizer)
        optimizer.find_nash_equilibrium = Mock(return_value={
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.5, 0.0],
            'villain_strategy': [0.8, 0.6, 0.2],
            'iterations': 5,
            'convergence_tolerance': 0.01
        })
        optimizer.find_indifference_points = Mock(return_value={
            'indifference_points': {},
            'optimal_frequencies': [1.0, 0.5, 0.0],
            'hero_range_size': 3,
            'villain_range_size': 3
        })
        return optimizer

    @pytest.fixture
    def panel(self, mock_analyzer, mock_optimizer):
        """Create GTOSolverPanel instance for testing."""
        with patch('pygame.display.set_mode'), \
             patch('pygame.font.Font'), \
             patch('pygame.time.Clock'):
            panel = GTOSolverPanel(mock_analyzer, mock_optimizer)
            return panel

    def test_initialization(self, panel):
        """Test panel initializes correctly."""
        assert panel.analyzer is not None
        assert panel.optimizer is not None
        assert panel.current_mode == 'threshold'
        assert panel.num_opponents == 8
        assert panel.pot_size == 20.0
        assert panel.bet_amount == 10.0

    def test_mode_switching(self, panel):
        """Test switching between analysis modes."""
        # Test threshold mode
        panel.set_mode('threshold')
        assert panel.current_mode == 'threshold'

        # Test range vs range mode
        panel.set_mode('range_vs_range')
        assert panel.current_mode == 'range_vs_range'

        # Test indifference points mode
        panel.set_mode('indifference')
        assert panel.current_mode == 'indifference'

    def test_parameter_validation(self, panel):
        """Test parameter input validation."""
        # Valid parameters
        assert panel.set_num_opponents(5) == True
        assert panel.num_opponents == 5

        # Invalid opponents (too few)
        assert panel.set_num_opponents(0) == False
        assert panel.num_opponents == 5  # Should remain unchanged

        # Invalid opponents (too many)
        assert panel.set_num_opponents(15) == False
        assert panel.num_opponents == 5

        # Valid pot size
        assert panel.set_pot_size(50.0) == True
        assert panel.pot_size == 50.0

        # Invalid pot size (negative)
        assert panel.set_pot_size(-10.0) == False
        assert panel.pot_size == 50.0

    def test_threshold_calculation(self, panel, mock_optimizer):
        """Test GTO threshold calculation."""
        panel.set_mode('threshold')

        # Mock the threshold calculation
        mock_optimizer.find_gto_threshold = Mock(return_value={
            'threshold_equity': 0.35,
            'optimal_range': ['AA', 'KK', 'QQ', 'AKs'],
            'ev_breakdown': {'AA': 2.5, 'KK': 1.8}
        })

        result = panel.calculate_threshold()

        assert result['threshold_equity'] == 0.35
        assert len(result['optimal_range']) == 4
        mock_optimizer.find_gto_threshold.assert_called_once()

    def test_range_vs_range_analysis(self, panel, mock_optimizer):
        """Test range vs range Nash equilibrium analysis."""
        panel.set_mode('range_vs_range')
        panel.hero_range = ['AA', 'AKs', 'AQs']
        panel.villain_range = ['KK', 'QQ', 'JJ']

        result = panel.calculate_range_vs_range()

        assert result['equilibrium_found'] == True
        assert len(result['hero_strategy']) == 3
        assert len(result['villain_strategy']) == 3
        mock_optimizer.find_nash_equilibrium.assert_called_once()

    def test_indifference_points_calculation(self, panel, mock_optimizer):
        """Test indifference points calculation."""
        panel.set_mode('indifference')
        panel.hero_range = ['AA', 'AKs', 'AQs']
        panel.villain_range = ['KK', 'QQ', 'JJ']

        result = panel.calculate_indifference_points()

        assert 'optimal_frequencies' in result
        assert len(result['optimal_frequencies']) == 3
        mock_optimizer.find_indifference_points.assert_called_once()

    def test_range_file_loading(self, panel):
        """Test loading ranges from YAML files."""
        # Mock file content
        mock_range_data = {
            'name': 'Premium Range',
            'hands': ['AA', 'KK', 'QQ', 'AKs', 'AQs'],
            'description': 'High value hands'
        }

        with patch('builtins.open', create=True) as mock_open, \
             patch('yaml.safe_load', return_value=mock_range_data):

            success = panel.load_hero_range('test_range.yaml')

            assert success == True
            assert panel.hero_range == mock_range_data['hands']
            mock_open.assert_called_once()

    def test_invalid_range_file_handling(self, panel):
        """Test handling of invalid range files."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            success = panel.load_hero_range('nonexistent.yaml')
            assert success == False

        with patch('yaml.safe_load', side_effect=Exception("Invalid YAML")):
            with patch('builtins.open', create=True):
                success = panel.load_hero_range('invalid.yaml')
                assert success == False

    def test_result_display_formatting(self, panel):
        """Test result display formatting."""
        # Test threshold results
        threshold_result = {
            'threshold_equity': 0.35,
            'optimal_range': ['AA', 'KK', 'QQ'],
            'ev_breakdown': {'AA': 2.5, 'KK': 1.8, 'QQ': 0.5}
        }

        formatted = panel.format_threshold_results(threshold_result)
        assert 'Threshold Equity' in formatted
        assert 'Optimal Range' in formatted
        assert 'EV Breakdown' in formatted

        # Test range vs range results
        range_result = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.8, 0.0],
            'villain_strategy': [0.9, 0.7, 0.1]
        }

        formatted = panel.format_range_vs_range_results(range_result)
        assert 'Nash Equilibrium Found' in formatted
        assert 'Hero Strategy' in formatted
        assert 'Villain Strategy' in formatted

    def test_progress_indicator(self, panel):
        """Test progress indicator functionality."""
        # Start calculation
        panel.start_calculation()

        # Check progress state
        assert panel.is_calculating == True
        assert panel.progress == 0.0

        # Update progress
        panel.update_progress(0.5)
        assert panel.progress == 0.5

        # Complete calculation
        panel.complete_calculation()
        assert panel.is_calculating == False
        assert panel.progress == 1.0

    def test_error_handling(self, panel, mock_optimizer):
        """Test error handling during calculations."""
        mock_optimizer.find_nash_equilibrium.side_effect = Exception("Calculation failed")

        panel.set_mode('range_vs_range')
        # Load dummy ranges to avoid range validation error
        panel.hero_range = ['AA', 'KK']
        panel.villain_range = ['QQ', 'JJ']
        result = panel.calculate_current_mode()

        assert result is None
        assert panel.last_error is not None
        assert "Calculation failed" in panel.last_error

    def test_gui_event_handling(self, panel):
        """Test GUI event handling."""
        # Mock pygame events
        calculate_event = Mock()
        calculate_event.type = pygame.MOUSEBUTTONDOWN
        calculate_event.pos = panel.calculate_button_rect.center

        mode_event = Mock()
        mode_event.type = pygame.MOUSEBUTTONDOWN
        mode_event.pos = panel.mode_buttons_rects['threshold'][0].center

        # Test calculate button click
        with patch.object(panel, 'calculate_current_mode') as mock_calc:
            panel.handle_event(calculate_event)
            mock_calc.assert_called_once()

        # Test mode button click
        panel.handle_event(mode_event)
        assert panel.current_mode == 'threshold'