import pytest
import pygame
import sys
import os
from unittest.mock import MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.card_picker import CardPicker


class TestCardPicker:
    """Unit tests for CardPicker component."""

    @pytest.fixture
    def screen(self):
        """Create a pygame screen for testing."""
        pygame.init()
        screen = pygame.display.set_mode((1200, 800))
        yield screen
        pygame.quit()

    def test_card_picker_initialization(self, screen):
        """Test CardPicker initialization."""
        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards)

        assert picker.screen == screen
        assert picker.assigned_cards == assigned_cards
        assert picker.current_card is None
        assert picker.show_range_button is True

    def test_card_picker_with_current_card(self, screen):
        """Test CardPicker with a current card."""
        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards, "Qd")

        assert picker.current_card == "Qd"

    def test_card_picker_card_selection(self, screen):
        """Test selecting a card in CardPicker."""
        selected_card = None

        def on_select(card):
            nonlocal selected_card
            selected_card = card

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards)

        # Simulate clicking on Qd (diamonds, row 2, col 10)
        # card_x = 20 + 10 * 45 = 470, card_y = 100 + 2 * 45 = 190
        # center = (470 + 20, 190 + 20) = (490, 210)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 490, picker.y + 210)  # Center of Qd card

        result = picker.handle_event(mock_event)
        assert result is True
        assert selected_card == "Qd"

    def test_card_picker_card_deselection(self, screen):
        """Test deselecting a card in CardPicker."""
        selected_card = None

        def on_select(card):
            nonlocal selected_card
            selected_card = card

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards, "Qd")

        # Click on Qd again to deselect (diamonds, row 2, col 10)
        # center = (490, 210)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 490, picker.y + 210)  # Center of Qd card

        result = picker.handle_event(mock_event)
        assert result is True
        assert selected_card is None  # Should deselect

    def test_card_picker_random_button(self, screen):
        """Test the Random button in CardPicker."""
        random_called = False

        def on_select(card):
            pass

        def on_random():
            nonlocal random_called
            random_called = True

        def on_cancel():
            pass

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards)

        # Click Random button (center at x+70, y+65)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 70, picker.y + 65)  # Center of Random button

        result = picker.handle_event(mock_event)
        assert result is True
        assert random_called is True

    def test_card_picker_cancel_button(self, screen):
        """Test the Cancel button in CardPicker."""
        cancel_called = False

        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            nonlocal cancel_called
            cancel_called = True

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards)

        # Click outside dialog to cancel
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x - 10, picker.y - 10)  # Outside the dialog

        result = picker.handle_event(mock_event)
        assert result is True
        assert cancel_called is True

    def test_card_picker_range_selection_button(self, screen):
        """Test the 'Select Range' button in CardPicker."""
        range_selected = False

        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            nonlocal range_selected
            range_selected = True

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards)

        # Click Select Range button (center at x+200, y+65)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 200, picker.y + 65)  # Center of Select Range button

        result = picker.handle_event(mock_event)
        assert result is True
        assert range_selected is True

    def test_card_picker_assigned_cards_blocking(self, screen):
        """Test that assigned cards are blocked from selection."""
        selected_card = None

        def on_select(card):
            nonlocal selected_card
            selected_card = card

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards)

        # Try to select an assigned card (As - spades A, row 0, col 12)
        # center = (20 + 12*45 + 20, 100 + 0*45 + 20) = (580, 120)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 580, picker.y + 120)  # Center of As card

        result = picker.handle_event(mock_event)
        assert result is True
        assert selected_card is None  # Should not select assigned card

    def test_card_picker_current_card_highlighting(self, screen):
        """Test that current card is properly highlighted in CardPicker."""
        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards, "Qd")

        assert picker.current_card == "Qd"

        # Test drawing (should highlight Qd appropriately)
        try:
            picker.draw()
        except Exception as e:
            pytest.fail(f"CardPicker.draw() with current card raised an exception: {e}")

    def test_card_picker_hide_range_button(self, screen):
        """Test CardPicker with range button hidden."""
        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        assigned_cards = {"As", "Kh"}
        picker = CardPicker(screen, on_select, on_random, on_cancel, on_select_range, assigned_cards, show_range_button=False)

        assert picker.show_range_button is False
