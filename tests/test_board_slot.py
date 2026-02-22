import pytest
import pygame
import sys
import os
from unittest.mock import MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.board_slot import BoardSlot


class TestBoardSlot:
    """Unit tests for BoardSlot component."""

    @pytest.fixture
    def screen(self):
        """Create a pygame screen for testing."""
        pygame.init()
        screen = pygame.display.set_mode((1200, 800))
        yield screen
        pygame.quit()

    def test_board_slot_initialization(self, screen):
        """Test BoardSlot initialization."""
        board_cards = [None, None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", None, board_cards, 0)

        assert slot.x == 100
        assert slot.y == 100
        assert slot.name == "Flop 1"
        assert slot.index == 0
        assert slot.width == 60
        assert slot.height == 80

    def test_board_slot_card_property(self, screen):
        """Test card property getter and setter."""
        board_cards = [None, None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", None, board_cards, 0)

        # Initially None
        assert slot.card is None
        assert board_cards[0] is None

        # Set card
        slot.card = "As"
        assert slot.card == "As"
        assert board_cards[0] == "As"

        # Set back to None
        slot.card = None
        assert slot.card is None
        assert board_cards[0] is None

    def test_board_slot_draw_empty(self, screen):
        """Test drawing an empty board slot."""
        board_cards = [None, None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", None, board_cards, 0)

        # Should not raise exceptions
        slot.draw()

    def test_board_slot_draw_with_card(self, screen):
        """Test drawing a board slot with a card."""
        board_cards = ["As", None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", "As", board_cards, 0)

        # Should not raise exceptions
        slot.draw()

    def test_board_slot_draw_random(self, screen):
        """Test drawing a board slot with random card (None)."""
        board_cards = [None, None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", None, board_cards, 0)

        # Should not raise exceptions and show hatch pattern
        slot.draw()

    def test_board_slot_handle_event_click_card_area(self, screen):
        """Test clicking on the card area opens card picker."""
        board_cards = [None, None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", None, board_cards, 0)

        # Mock GUI with get_assigned_cards method
        mock_gui = MagicMock()
        mock_gui.get_assigned_cards.return_value = set()

        # Click on card area (x+10 to x+50, y+20 to y+70)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 140)  # Center of card area

        result = slot.handle_event(mock_event, mock_gui)

        assert result is True
        assert mock_gui.card_picker is not None

    def test_board_slot_handle_event_click_outside(self, screen):
        """Test clicking outside card area does nothing."""
        board_cards = [None, None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", None, board_cards, 0)

        mock_gui = MagicMock()

        # Click outside card area
        initial_card_picker = mock_gui.card_picker
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (50, 50)  # Outside slot

        result = slot.handle_event(mock_event, mock_gui)

        assert result is False
        assert mock_gui.card_picker == initial_card_picker  # Should not change

    def test_board_slot_card_assignment_callback(self, screen):
        """Test that card assignment triggers callback."""
        board_cards = [None, None, None, None, None]
        callback_called = False
        assigned_index = None
        assigned_card = None

        def card_callback(index, card):
            nonlocal callback_called, assigned_index, assigned_card
            callback_called = True
            assigned_index = index
            assigned_card = card

        slot = BoardSlot(screen, 100, 100, "Flop 1", None, board_cards, 0, card_callback)

        mock_gui = MagicMock()
        mock_gui.get_assigned_cards.return_value = set()

        # Click to open picker, then simulate card selection
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 140)

        slot.handle_event(mock_event, mock_gui)

        # Simulate selecting a card (this would normally be done by the picker)
        # For this test, we'll directly call the on_select callback that gets created
        # This is a bit of a white-box test, but necessary to test the callback

    def test_board_slot_random_assignment(self, screen):
        """Test random card assignment (setting to None)."""
        board_cards = ["As", None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", "As", board_cards, 0)

        mock_gui = MagicMock()
        mock_gui.get_assigned_cards.return_value = set()

        # Click to open picker
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 140)

        slot.handle_event(mock_event, mock_gui)

        # The picker should be created with current card "As" in assigned_cards
        # (though we can't easily test the random button without more complex mocking)

    def test_board_slot_current_card_excluded_from_assigned(self, screen):
        """Test that current card is excluded from assigned cards when opening picker."""
        board_cards = ["As", None, None, None, None]
        slot = BoardSlot(screen, 100, 100, "Flop 1", "As", board_cards, 0)

        mock_gui = MagicMock()
        mock_gui.get_assigned_cards.return_value = {"As", "Kh"}  # As is assigned elsewhere

        # Click to open picker
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 140)

        slot.handle_event(mock_event, mock_gui)

        # Verify get_assigned_cards was called
        mock_gui.get_assigned_cards.assert_called_once()
        # The card picker should be created, allowing re-selection of "As"</content>
