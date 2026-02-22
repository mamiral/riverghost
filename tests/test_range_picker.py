import pytest
import pygame
import sys
import os
from unittest.mock import MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.range_picker import RangePicker


class TestRangePicker:
    """Unit tests for RangePicker component."""

    @pytest.fixture
    def screen(self):
        """Create a pygame screen for testing."""
        pygame.init()
        screen = pygame.display.set_mode((1200, 800))
        yield screen
        pygame.quit()

    def test_range_picker_initialization(self, screen):
        """Test RangePicker initialization and basic functionality."""
        selected_range = None
        cancelled = False

        def on_select(range_str):
            nonlocal selected_range
            selected_range = range_str

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        # Test initialization without initial range
        picker = RangePicker(screen, on_select, on_cancel)
        assert len(picker.selected_ranges) == 0
        assert picker.ranks == ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        assert picker.can_assign_range is not None

        # Test initialization with initial range
        picker_with_range = RangePicker(screen, on_select, on_cancel, "AKs+QQ")
        assert "AKs" in picker_with_range.selected_ranges
        assert "QQ" in picker_with_range.selected_ranges

    def test_range_picker_with_can_assign_range(self, screen):
        """Test RangePicker with custom can_assign_range function."""
        def can_assign(range_str):
            return range_str != "AA"  # Block AA

        def on_select(range_str):
            pass

        def on_cancel():
            pass

        picker = RangePicker(screen, on_select, on_cancel, can_assign_range=can_assign)
        assert picker.can_assign_range == can_assign

    def test_range_picker_cell_selection(self, screen):
        """Test selecting cells in the range picker matrix."""
        selected_range = None

        def on_select(range_str):
            nonlocal selected_range
            selected_range = range_str

        def on_cancel():
            pass

        picker = RangePicker(screen, on_select, on_cancel)

        # Simulate clicking on AA (pocket pair)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 30 + 35//2, picker.y + 85 + 35//2)  # Center of AA cell

        result = picker.handle_event(mock_event)
        assert result is True
        assert "AA" in picker.selected_ranges

        # Click again to deselect
        result = picker.handle_event(mock_event)
        assert result is True
        assert "AA" not in picker.selected_ranges

    def test_range_picker_suited_combinations(self, screen):
        """Test selecting suited combinations."""
        def on_select(range_str):
            pass

        def on_cancel():
            pass

        picker = RangePicker(screen, on_select, on_cancel)

        # Click on AKs (A row=0, K col=1, suited upper triangle)
        # cell_x = 30 + 1 * 37 = 67, cell_y = 85 + 0 * 37 = 85
        # center = (67 + 17.5, 85 + 17.5) = (84.5, 102.5)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 84, picker.y + 102)  # AKs position

        result = picker.handle_event(mock_event)
        assert result is True
        assert "AKs" in picker.selected_ranges

    def test_range_picker_offsuit_combinations(self, screen):
        """Test selecting offsuit combinations."""
        def on_select(range_str):
            pass

        def on_cancel():
            pass

        picker = RangePicker(screen, on_select, on_cancel)

        # Click on AKo (K row=1, A col=0, offsuit lower triangle)
        # cell_x = 30 + 0 * 37 = 30, cell_y = 85 + 1 * 37 = 122
        # center = (30 + 17.5, 122 + 17.5) = (47.5, 139.5)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 47, picker.y + 139)  # AKo position

        result = picker.handle_event(mock_event)
        assert result is True
        assert "AKo" in picker.selected_ranges

    def test_range_picker_ok_cancel_buttons(self, screen):
        """Test OK and Cancel button functionality in range picker."""
        selected_range = None
        cancelled = False

        def on_select(range_str):
            nonlocal selected_range
            selected_range = range_str

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        picker = RangePicker(screen, on_select, on_cancel)

        # Select a range first
        picker.selected_ranges.add("AKs")
        picker.selected_ranges.add("QQ")

        # Test OK button
        mock_ok_event = MagicMock()
        mock_ok_event.type = pygame.MOUSEBUTTONDOWN
        mock_ok_event.pos = (picker.x + picker.width - 180 + 40, picker.y + picker.height - 50 + 15)  # Center of OK button

        result = picker.handle_event(mock_ok_event)
        assert result is True
        assert selected_range == "AKs+QQ"

        # Reset for no selection test
        selected_range = None
        cancelled = False

        # Clear all selections and test OK button (should call on_select with empty string)
        picker.selected_ranges.clear()
        mock_ok_event2 = MagicMock()
        mock_ok_event2.type = pygame.MOUSEBUTTONDOWN
        mock_ok_event2.pos = (picker.x + picker.width - 180 + 40, picker.y + picker.height - 50 + 15)  # Center of OK button

        result = picker.handle_event(mock_ok_event2)
        assert result is True
        assert selected_range == ""  # Should call on_select with empty string for no selection
        assert cancelled is False  # Should not call on_cancel

        # Reset for cancel test
        selected_range = None
        cancelled = False

        # Test Cancel button
        mock_cancel_event = MagicMock()
        mock_cancel_event.type = pygame.MOUSEBUTTONDOWN
        mock_cancel_event.pos = (picker.x + picker.width - 90 + 40, picker.y + picker.height - 50 + 15)  # Center of Cancel button

        result = picker.handle_event(mock_cancel_event)
        assert result is True
        assert cancelled is True

    def test_range_picker_click_outside_cancel(self, screen):
        """Test that clicking outside the range picker cancels it."""
        cancelled = False

        def on_select(range_str):
            pass

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        picker = RangePicker(screen, on_select, on_cancel)

        # Click outside the dialog
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x - 10, picker.y - 10)  # Outside the dialog

        result = picker.handle_event(mock_event)
        assert result is True
        assert cancelled is True

    def test_range_picker_can_assign_range_blocking(self, screen):
        """Test that can_assign_range function blocks invalid ranges."""
        def can_assign(range_str):
            return not range_str.startswith("AA")  # Block any range starting with AA

        def on_select(range_str):
            pass

        def on_cancel():
            pass

        picker = RangePicker(screen, on_select, on_cancel, can_assign_range=can_assign)

        # Try to select AA (should be blocked)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 30 + 35//2, picker.y + 85 + 35//2)  # Center of AA cell

        result = picker.handle_event(mock_event)
        assert result is True
        assert "AA" not in picker.selected_ranges  # Should not be selected due to can_assign_range

    def test_range_picker_drawing(self, screen):
        """Test that RangePicker draws without errors."""
        def on_select(range_str):
            pass

        def on_cancel():
            pass

        picker = RangePicker(screen, on_select, on_cancel)

        # Test drawing
        try:
            picker.draw()
        except Exception as e:
            pytest.fail(f"RangePicker.draw() raised an exception: {e}")

    def test_range_picker_range_parsing(self, screen):
        """Test that initial range parsing works correctly."""
        def on_select(range_str):
            pass

        def on_cancel():
            pass

        # Test various range formats
        test_ranges = [
            "AA",
            "AKs+QQ",
            "22+",
            "AKo+AQo",
            "TT-77"
        ]

        for range_str in test_ranges:
            picker = RangePicker(screen, on_select, on_cancel, range_str)
            # Should not raise exceptions
            assert picker.selected_ranges is not None
