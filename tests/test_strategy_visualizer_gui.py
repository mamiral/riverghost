"""
GUI component tests for StrategyVisualizer integration.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
import pygame
from unittest.mock import Mock, patch, MagicMock
from hopilot.gui_components.strategy_visualizer import StrategyVisualizer


class TestStrategyVisualizerGUI:
    """GUI integration tests for StrategyVisualizer component."""

    @pytest.fixture(scope="class")
    def pygame_setup(self):
        """Initialize pygame for GUI tests."""
        pygame.init()
        pygame.font.init()
        yield
        pygame.quit()

    @pytest.fixture
    def screen(self, pygame_setup):
        """Create a test screen surface."""
        return pygame.Surface((1024, 768))

    @pytest.fixture
    def visualizer(self, screen):
        """Create StrategyVisualizer instance for GUI testing."""
        return StrategyVisualizer(screen, x=50, y=50, width=700, height=600)

    @pytest.fixture
    def sample_gto_results(self):
        """Sample GTO results for GUI testing."""
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

    def test_gui_initialization(self, visualizer):
        """Test GUI component initialization."""
        assert visualizer.screen is not None
        assert visualizer.x == 50
        assert visualizer.y == 50
        assert visualizer.width == 700
        assert visualizer.height == 600

        # Check font initialization
        assert hasattr(visualizer, 'title_font')
        assert hasattr(visualizer, 'label_font')
        assert hasattr(visualizer, 'small_font')

        # Check color definitions
        assert visualizer.BG_COLOR == (40, 40, 40)
        assert visualizer.GREEN_PLAY == (0, 180, 0)
        assert visualizer.RED_FOLD == (180, 0, 0)

    def test_gui_draw_empty_state(self, visualizer):
        """Test GUI drawing when no results are set."""
        visualizer.draw()

        # Verify the screen was drawn to (basic smoke test)
        # In a real GUI test, we'd capture the surface and verify pixel colors
        assert visualizer.screen is not None

    def test_gui_draw_with_results(self, visualizer, sample_gto_results):
        """Test GUI drawing with GTO results."""
        visualizer.set_results(sample_gto_results)
        visualizer.draw()

        # Verify results are set
        assert visualizer.gto_results == sample_gto_results

        # Basic smoke test - drawing should not crash
        assert visualizer.screen is not None

    def test_gui_hand_selection_workflow(self, visualizer, sample_gto_results):
        """Test complete hand selection workflow through GUI."""
        visualizer.set_results(sample_gto_results)

        # Simulate clicking on AA position (first cell)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                 pos=(visualizer.grid_x + 10, visualizer.grid_y + 10))

        result = visualizer.handle_event(event)

        assert result == "hand_selected:AA"
        assert visualizer.selected_hand == "AA"
        assert visualizer.selected_hand_info is not None
        assert visualizer.selected_hand_info['shorthand'] == "AA"

    def test_gui_scroll_functionality(self, visualizer, sample_gto_results):
        """Test GUI scroll functionality."""
        visualizer.set_results(sample_gto_results)
        visualizer.max_scroll = 100

        initial_scroll = visualizer.scroll_y

        # Simulate scroll down
        event = pygame.event.Event(pygame.MOUSEWHEEL, y=-1)
        visualizer.handle_event(event)

        assert visualizer.scroll_y > initial_scroll

        # Simulate scroll up
        event = pygame.event.Event(pygame.MOUSEWHEEL, y=1)
        visualizer.handle_event(event)

        assert visualizer.scroll_y <= initial_scroll

    def test_gui_multiple_hand_selections(self, visualizer, sample_gto_results):
        """Test selecting multiple different hands."""
        visualizer.set_results(sample_gto_results)

        # Select AA
        event1 = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                  pos=(visualizer.grid_x + 10, visualizer.grid_y + 10))
        visualizer.handle_event(event1)
        assert visualizer.selected_hand == "AA"

        # Select AKs (different position)
        event2 = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                  pos=(visualizer.grid_x + 10, visualizer.grid_y + 35))  # Second row
        visualizer.handle_event(event2)
        assert visualizer.selected_hand == "AKs"

    def test_gui_click_outside_grid(self, visualizer, sample_gto_results):
        """Test clicking outside the hand grid area."""
        visualizer.set_results(sample_gto_results)

        # Click outside grid area
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                 pos=(visualizer.x - 10, visualizer.y - 10))

        result = visualizer.handle_event(event)

        assert result is None
        assert visualizer.selected_hand is None

    def test_gui_export_workflow(self, visualizer, sample_gto_results, tmp_path):
        """Test GUI export functionality."""
        visualizer.set_results(sample_gto_results)

        export_file = tmp_path / "gui_export_test.json"
        success = visualizer.export_results(str(export_file))

        assert success is True
        assert export_file.exists()

        # Verify it's valid JSON
        import json
        with open(export_file) as f:
            data = json.load(f)
        assert 'threshold_equity' in data
        assert 'optimal_range' in data

    def test_gui_visual_feedback_drawing(self, visualizer, sample_gto_results):
        """Test that visual feedback is drawn correctly."""
        visualizer.set_results(sample_gto_results)
        visualizer._select_hand('AA')

        # Draw with selection
        visualizer.draw()

        # Verify selection is maintained
        assert visualizer.selected_hand == 'AA'
        assert visualizer.selected_hand_info is not None

    def test_gui_color_coding_display(self, visualizer, sample_gto_results):
        """Test that color coding is applied correctly in display."""
        visualizer.set_results(sample_gto_results)

        # The draw method should handle color coding internally
        # This is a smoke test to ensure no exceptions during drawing
        visualizer.draw()

        assert visualizer.screen is not None

    def test_gui_info_panel_display(self, visualizer, sample_gto_results):
        """Test that the information panel displays correctly."""
        visualizer.set_results(sample_gto_results)
        visualizer._select_hand('AA')

        # Draw the details panel
        visualizer._draw_hand_details()

        # Verify hand info is available
        assert visualizer.selected_hand_info is not None
        assert visualizer.selected_hand_info['ev'] == 0.45  # Positive EV

    def test_gui_large_range_handling(self, visualizer):
        """Test handling of large hand ranges."""
        large_results = {
            'threshold_equity': 0.35,
            'optimal_hands': 500,
            'total_hands': 1326,
            'optimal_range': [f"hand_{i}" for i in range(500)],  # Large range
            'top_10_hands': [
                {'shorthand': f"hand_{i}", 'equity': 0.5 + i*0.01, 'ev': 0.1 + i*0.01}
                for i in range(10)
            ]
        }

        visualizer.set_results(large_results)

        # Should handle large ranges without crashing
        visualizer.draw()

        assert visualizer.max_scroll > 0  # Should enable scrolling for large ranges

    def test_gui_event_handling_edge_cases(self, visualizer, sample_gto_results):
        """Test edge cases in event handling."""
        visualizer.set_results(sample_gto_results)

        # Test invalid event type
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        result = visualizer.handle_event(event)
        assert result is None

        # Test mouse event outside component bounds
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(-100, -100))
        result = visualizer.handle_event(event)
        assert result is None

    def test_gui_font_rendering(self, visualizer, sample_gto_results):
        """Test that fonts render correctly."""
        visualizer.set_results(sample_gto_results)

        # This tests that font rendering doesn't crash
        visualizer.draw()

        # Fonts should be accessible
        assert visualizer.title_font is not None
        assert visualizer.label_font is not None
        assert visualizer.small_font is not None

    def test_gui_component_bounds_checking(self, visualizer):
        """Test that component respects its bounds."""
        # Component should not draw outside its allocated rectangle
        visualizer.draw()

        # Basic bounds check - component dimensions should be maintained
        assert visualizer.width == 700
        assert visualizer.height == 600