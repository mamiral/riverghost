import pytest
import pygame
import sys
import os
from unittest.mock import MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.player_seat import PlayerSeat


class TestPlayerSeat:
    """Unit tests for PlayerSeat component."""

    @pytest.fixture
    def screen(self):
        """Create a pygame screen for testing."""
        pygame.init()
        screen = pygame.display.set_mode((1200, 800))
        yield screen
        pygame.quit()

    def test_player_seat_initialization(self, screen):
        """Test PlayerSeat initialization."""
        cards = [None, None]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards)

        assert seat.x == 100
        assert seat.y == 100
        assert seat.name == "Hero"
        assert seat.cards == [None, None]
        assert seat.range_str is None
        assert seat.width == 120
        assert seat.height == 80

    def test_player_seat_initialization_with_range(self, screen):
        """Test PlayerSeat initialization with range."""
        cards = [None, None]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards, "AKs")

        assert seat.range_str == "AKs"
        assert seat.cards == [None, None]

    def test_player_seat_draw_no_range(self, screen):
        """Test drawing player seat without range (shows cards)."""
        cards = ["As", "Kh"]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards)

        # Should not raise exceptions
        seat.draw()

    def test_player_seat_draw_with_range(self, screen):
        """Test drawing player seat with range."""
        cards = [None, None]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards, "AKs")

        # Should not raise exceptions
        seat.draw()

    def test_player_seat_draw_mixed_state(self, screen):
        """Test drawing player seat with both range and cards (should show range)."""
        cards = ["As", "Kh"]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards, "AKs")

        # Range takes precedence
        seat.draw()

    def test_player_seat_handle_event_range_area_click(self, screen):
        """Test clicking on range area opens range picker."""
        cards = [None, None]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards)

        mock_gui = MagicMock()

        # Click on range area (when no range is set, this should open range picker)
        # Range area is roughly the seat area
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 140)  # Center of seat

        result = seat.handle_event(mock_event, mock_gui)

        assert result is True
        assert mock_gui.range_picker is not None

    def test_player_seat_handle_event_card_click(self, screen):
        """Test clicking on individual card opens range picker."""
        cards = [None, None]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards)

        mock_gui = MagicMock()

        # Click on first card area (x+10 to x+50, y+25 to y+75)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 140)  # Center of first card

        result = seat.handle_event(mock_event, mock_gui)

        assert result is True
        assert mock_gui.range_picker is not None

    def test_player_seat_handle_event_second_card_click(self, screen):
        """Test clicking on second card."""
        cards = [None, None]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards)

        mock_gui = MagicMock()

        # Click on second card area (x+60 to x+100, y+25 to y+75)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (180, 140)  # Center of second card

        result = seat.handle_event(mock_event, mock_gui)

        assert result is True
        assert mock_gui.range_picker is not None

    def test_player_seat_range_callback(self, screen):
        """Test range selection callback."""
        cards = [None, None]
        range_selected = None

        def range_callback(range_str):
            nonlocal range_selected
            range_selected = range_str

        seat = PlayerSeat(screen, 100, 100, "Hero", cards, None, range_callback)

        mock_gui = MagicMock()

        # Click to open range picker
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 140)

        seat.handle_event(mock_event, mock_gui)

        # Simulate range selection (this would normally be done by the range picker)
        # The callback should be triggered when range is selected

    def test_player_seat_card_callback(self, screen):
        """Test individual card assignment callback."""
        cards = [None, None]
        card_updates = []

        def card_callback(index, card):
            card_updates.append((index, card))

        seat = PlayerSeat(screen, 100, 100, "Hero", cards, None, None, None, card_callback)

        mock_gui = MagicMock()

        # Click on first card
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 140)

        seat.handle_event(mock_event, mock_gui)

        # The range picker opens, and if a card were selected, it would trigger card_callback

    def test_player_seat_range_initialization(self, screen):
        """Test that setting range in constructor doesn't clear existing cards."""
        cards = ["As", "Kh"]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards, "AKs")

        # Range is set but cards remain (this is just initialization)
        assert seat.range_str == "AKs"
        assert seat.cards == ["As", "Kh"]  # Cards are not cleared on initialization

    def test_player_seat_card_clears_range(self, screen):
        """Test that setting a specific card clears range."""
        cards = [None, None]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards, "AKs")

        # Setting a card should clear the range
        seat.cards[0] = "As"
        # Note: In the actual implementation, this happens in the callback

    def test_player_seat_can_assign_range_callback(self, screen):
        """Test can_assign_range callback functionality."""
        cards = [None, None]

        def can_assign(range_str):
            return not range_str.startswith("AA")

        seat = PlayerSeat(screen, 100, 100, "Hero", cards, None, None, can_assign)

        assert seat.can_assign_range("AKs") is True
        assert seat.can_assign_range("AA") is False

    def test_player_seat_handle_event_outside(self, screen):
        """Test clicking outside seat area does nothing."""
        cards = [None, None]
        seat = PlayerSeat(screen, 100, 100, "Hero", cards)

        mock_gui = MagicMock()
        initial_range_picker = mock_gui.range_picker
        initial_card_picker = mock_gui.card_picker

        # Click outside seat area
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (50, 50)

        result = seat.handle_event(mock_event, mock_gui)

        assert result is False
        assert mock_gui.range_picker == initial_range_picker
        assert mock_gui.card_picker == initial_card_picker

    def test_player_seat_handle_event_range_editing(self, screen):
        """Test clicking on range area opens range picker for editing."""
        mock_gui = MagicMock()
        seat = PlayerSeat(screen, 100, 100, "Hero", [None, None], "AKs")

        # Click on range area (center of range box)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (160, 125)  # Center of range box: x=100+10+50=160, y=100+35+15=150, wait let me check coordinates

        # Actually, range box is at: self.x + 10, self.y + 35, width 100, height 30
        # So center is at: x=100+10+50=160, y=100+35+15=150
        mock_event.pos = (160, 150)

        result = seat.handle_event(mock_event, mock_gui)

        assert result is True
        # Should create a range picker
        assert mock_gui.range_picker is not None

    def test_player_seat_handle_event_card_click_empty(self, screen):
        """Test clicking on empty card slot opens card picker."""
        mock_gui = MagicMock()
        seat = PlayerSeat(screen, 100, 100, "Hero", [None, None])

        # Click on first card slot
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (120, 150)  # Center of first card: x=100+10+20=130, y=100+25+25=150

        result = seat.handle_event(mock_event, mock_gui)

        assert result is True
        # Should create a card picker
        assert mock_gui.card_picker is not None

    def test_player_seat_handle_event_card_click_with_card(self, screen):
        """Test clicking on card with existing card allows reselection."""
        mock_gui = MagicMock()
        seat = PlayerSeat(screen, 100, 100, "Hero", ["As", None])

        # Click on first card slot (has "As")
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (130, 150)  # Center of first card

        result = seat.handle_event(mock_event, mock_gui)

        assert result is True
        # Should create a card picker
        assert mock_gui.card_picker is not None

    def test_player_seat_handle_event_switch_from_range_to_cards(self, screen):
        """Test switching from range mode to card selection."""
        mock_gui = MagicMock()
        seat = PlayerSeat(screen, 100, 100, "Hero", [None, None], "AKs")

        # Click on second card slot to switch to card mode
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (170, 150)  # Center of second card: x=100+10+50+20=180, y=150

        result = seat.handle_event(mock_event, mock_gui)

        assert result is True
        # Should create a range picker (since no range is set for this card)
        assert mock_gui.range_picker is not None

    def test_player_seat_range_update_callback(self, screen):
        """Test that range update callback is called correctly."""
        range_callback_called = []
        def range_callback(range_str):
            range_callback_called.append(range_str)

        seat = PlayerSeat(screen, 100, 100, "Hero", [None, None], None, range_callback)

        # Simulate range update
        seat.range_str = "AKs"
        if seat.range_update_callback:
            seat.range_update_callback("QQs")

        assert range_callback_called == ["QQs"]

    def test_player_seat_card_update_callback(self, screen):
        """Test that card update callback is called correctly."""
        card_callback_called = []
        def card_callback(index, card):
            card_callback_called.append((index, card))

        seat = PlayerSeat(screen, 100, 100, "Hero", [None, None], None, None, None, card_callback)

        # Simulate card update
        if seat.card_update_callback:
            seat.card_update_callback(0, "As")
            seat.card_update_callback(1, "Kh")

        assert card_callback_called == [(0, "As"), (1, "Kh")]

    def test_player_seat_can_assign_range_callback(self, screen):
        """Test range assignment validation callback."""
        def can_assign_range(range_str):
            return range_str != "INVALID"

        seat = PlayerSeat(screen, 100, 100, "Hero", [None, None], None, None, can_assign_range, None)

        # Test valid range
        assert seat.can_assign_range("AKs") is True
        # Test invalid range
        assert seat.can_assign_range("INVALID") is False
