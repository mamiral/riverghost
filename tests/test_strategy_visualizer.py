"""
Unit tests for StrategyVisualizer GUI component.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
import pygame
from unittest.mock import Mock, patch, MagicMock, call
from hopilot.gui_components.strategy_visualizer import StrategyVisualizer


class TestStrategyVisualizer:
    """Test suite for StrategyVisualizer component."""

    @pytest.fixture
    def mock_screen(self):
        """Mock pygame screen for testing."""
        return Mock()

    @pytest.fixture
    def visualizer(self, mock_screen):
        """Create StrategyVisualizer instance for testing."""
        with patch('pygame.font.SysFont') as mock_font:
            mock_title = Mock()
            mock_label = Mock()
            mock_small = Mock()
            mock_font.side_effect = [mock_title, mock_label, mock_small]
            return StrategyVisualizer(mock_screen, x=0, y=0, width=800, height=600)

    @pytest.fixture
    def sample_gto_results(self):
        """Sample GTO results for testing."""
        return {
            'threshold_equity': 0.35,
            'optimal_hands': 169,
            'total_hands': 1326,
            'optimal_range': ['AA', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s'],
            'top_10_hands': [
                {'shorthand': 'AA', 'equity': 0.85, 'ev': 0.45, 'bonus_multiplier': 2.0},
                {'shorthand': 'AKs', 'equity': 0.67, 'ev': 0.32, 'bonus_multiplier': 1.5},
                {'shorthand': 'AQs', 'equity': 0.65, 'ev': 0.30, 'bonus_multiplier': 1.5},
            ],
            'bonus_payouts': True
        }

    def test_initialization(self, visualizer):
        """Test StrategyVisualizer initialization."""
        assert visualizer.screen is not None
        assert visualizer.x == 0
        assert visualizer.y == 0
        assert visualizer.width == 800
        assert visualizer.height == 600
        assert visualizer.gto_results is None
        assert visualizer.selected_hand is None
        assert visualizer.scroll_y == 0

    def test_set_results(self, visualizer, sample_gto_results):
        """Test setting GTO results."""
        visualizer.set_results(sample_gto_results)

        assert visualizer.gto_results == sample_gto_results
        assert visualizer.selected_hand is None
        assert visualizer.scroll_y == 0
        assert visualizer.max_scroll == 0  # Small range, no scroll needed

    def test_draw_empty_state(self, visualizer, mock_screen):
        """Test drawing when no results are set."""
        with patch('pygame.draw.rect'):

            # Mock the font render methods separately
            title_render_mock = Mock()
            title_render_mock.get_width.return_value = 100
            title_render_mock.get_height.return_value = 20
            visualizer.title_font.render = Mock(return_value=title_render_mock)

            no_data_render_mock = Mock()
            no_data_render_mock.get_width.return_value = 150
            no_data_render_mock.get_height.return_value = 16
            visualizer.label_font.render = Mock(return_value=no_data_render_mock)

            instructions_render_mock = Mock()
            instructions_render_mock.get_width.return_value = 200
            instructions_render_mock.get_height.return_value = 12
            visualizer.small_font.render = Mock(return_value=instructions_render_mock)

            visualizer.draw()

            # Verify rendering calls
            visualizer.title_font.render.assert_called_with("GTO Strategy Visualization", True, (255, 255, 255))
            visualizer.label_font.render.assert_called_with("No GTO results to display", True, (150, 150, 150))

    def test_draw_with_results(self, visualizer, mock_screen, sample_gto_results):
        """Test drawing with GTO results."""
        visualizer.set_results(sample_gto_results)

        with patch('pygame.draw.rect'):

            # Mock the font render methods separately
            title_render_mock = Mock()
            title_render_mock.get_width.return_value = 100
            title_render_mock.get_height.return_value = 20
            visualizer.title_font.render = Mock(return_value=title_render_mock)

            label_render_mock = Mock()
            label_render_mock.get_width.return_value = 150
            label_render_mock.get_height.return_value = 16
            visualizer.label_font.render = Mock(return_value=label_render_mock)

            small_render_mock = Mock()
            small_render_mock.get_width.return_value = 20
            small_render_mock.get_height.return_value = 12
            visualizer.small_font.render = Mock(return_value=small_render_mock)

            visualizer.draw()

            # Verify title rendering
            visualizer.title_font.render.assert_called_with("GTO Strategy Visualization", True, (255, 255, 255))

            # Verify stats rendering
            expected_calls = [
                call("Equity Threshold: 0.350", True, (255, 255, 255)),
                call("Optimal Hands: 169/1326", True, (255, 255, 255)),
                call("Bonus Payouts: Active", True, (0, 255, 0))
            ]
            visualizer.label_font.render.assert_has_calls(expected_calls, any_order=True)

    def test_select_hand_from_top_10(self, visualizer, sample_gto_results):
        """Test selecting a hand that exists in top 10 results."""
        visualizer.set_results(sample_gto_results)

        visualizer._select_hand('AA')

        assert visualizer.selected_hand == 'AA'
        assert visualizer.selected_hand_info is not None
        assert visualizer.selected_hand_info['shorthand'] == 'AA'
        assert visualizer.selected_hand_info['equity'] == 0.85
        assert visualizer.selected_hand_info['ev'] == 0.45

    def test_select_hand_not_in_top_10(self, visualizer, sample_gto_results):
        """Test selecting a hand that doesn't exist in top 10 results."""
        visualizer.set_results(sample_gto_results)

        visualizer._select_hand('KK')

        assert visualizer.selected_hand == 'KK'
        assert visualizer.selected_hand_info is not None
        assert visualizer.selected_hand_info['hand'] == 'KK'
        assert visualizer.selected_hand_info['equity'] == 0.0  # Default for unknown
        assert visualizer.selected_hand_info['ev'] == 0.0

    def test_handle_mouse_click_in_grid(self, visualizer, sample_gto_results):
        """Test handling mouse click events in the hand grid."""
        visualizer.set_results(sample_gto_results)

        # Mock mouse event at grid position (0,0) which should be AA
        event = Mock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.pos = (visualizer.grid_x + 10, visualizer.grid_y + 10)  # Click on first cell

        with patch.object(visualizer, '_select_hand') as mock_select:
            result = visualizer.handle_event(event)

            mock_select.assert_called_once_with('AA')
            assert result == 'hand_selected:AA'

    def test_handle_mouse_wheel_scroll(self, visualizer, sample_gto_results):
        """Test handling mouse wheel scroll events."""
        visualizer.set_results(sample_gto_results)
        visualizer.max_scroll = 100

        initial_scroll = visualizer.scroll_y

        # Mock scroll down event
        event = Mock()
        event.type = pygame.MOUSEWHEEL
        event.y = -1  # Scroll down

        visualizer.handle_event(event)
        assert visualizer.scroll_y > initial_scroll

        # Mock scroll up event
        event.y = 1  # Scroll up
        visualizer.handle_event(event)
        assert visualizer.scroll_y <= initial_scroll

    def test_export_results_success(self, visualizer, sample_gto_results, tmp_path):
        """Test successful export of results."""
        visualizer.set_results(sample_gto_results)

        export_file = tmp_path / "test_export.json"
        result = visualizer.export_results(str(export_file))

        assert result is True
        assert export_file.exists()

        # Verify content
        import json
        with open(export_file) as f:
            exported_data = json.load(f)
        assert exported_data == sample_gto_results

    def test_export_results_no_data(self, visualizer, tmp_path):
        """Test export when no results are available."""
        export_file = tmp_path / "test_export.json"
        result = visualizer.export_results(str(export_file))

        assert result is False
        assert not export_file.exists()

    def test_export_results_failure(self, visualizer, sample_gto_results):
        """Test export failure handling."""
        visualizer.set_results(sample_gto_results)

        # Try to export to invalid path
        result = visualizer.export_results("/invalid/path/test.json")

        assert result is False

    def test_draw_hand_details_profitable(self, visualizer, mock_screen, sample_gto_results):
        """Test drawing hand details for a profitable hand."""
        visualizer.set_results(sample_gto_results)
        visualizer._select_hand('AA')  # Profitable hand

        with patch('pygame.draw.rect'):

            # Mock the font render methods
            visualizer.label_font.render = Mock()
            visualizer.label_font.render.return_value = Mock()
            visualizer.label_font.render.return_value.get_width.return_value = 100
            visualizer.label_font.render.return_value.get_height.return_value = 16

            visualizer._draw_hand_details()

            # Verify profitable hand rendering
            expected_calls = [
                call("Hand: AA", True, (255, 255, 255)),
                call("Equity: 0.850", True, (255, 255, 255)),
                call("EV: 0.450", True, (0, 180, 0)),  # Green for positive EV
                call("PLAY (Profitable)", True, (0, 180, 0)),
                call("Bonus: 2.0x", True, (255, 255, 0))
            ]
            visualizer.label_font.render.assert_has_calls(expected_calls, any_order=True)

    def test_draw_hand_details_unprofitable(self, visualizer, mock_screen, sample_gto_results):
        """Test drawing hand details for an unprofitable hand."""
        visualizer.set_results(sample_gto_results)
        visualizer._select_hand('KK')  # Unknown/unprofitable hand

        with patch('pygame.draw.rect'):

            # Mock the font render methods
            visualizer.label_font.render = Mock()
            visualizer.label_font.render.return_value = Mock()
            visualizer.label_font.render.return_value.get_width.return_value = 100
            visualizer.label_font.render.return_value.get_height.return_value = 16

            visualizer._draw_hand_details()

            # Verify unprofitable hand rendering
            expected_calls = [
                call("Hand: KK", True, (255, 255, 255)),
                call("Equity: 0.000", True, (255, 255, 255)),
                call("EV: 0.000", True, (180, 0, 0)),  # Red for zero/negative EV
                call("FOLD (Unprofitable)", True, (180, 0, 0))
            ]
            visualizer.label_font.render.assert_has_calls(expected_calls, any_order=True)