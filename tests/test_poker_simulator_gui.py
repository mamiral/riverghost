import pytest
import pygame
import sys
import os
import time
import threading
from unittest.mock import patch, MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.poker_simulator_gui import PokerSimulatorGUI
from hopilot.logging_config import get_logger
from hopilot.gui_components.card_picker import CardPicker

logger = get_logger(__name__)


class TestPokerSimulatorGUI:
    """Automated GUI tests for PokerSimulatorGUI using PyAutoGUI and pytest-pygame."""

    @pytest.fixture
    def gui_app(self):
        """Create a PokerSimulatorGUI instance for testing."""
        # Initialize pygame for testing
        pygame.init()
        pygame.display.set_mode((1200, 800))

        gui = PokerSimulatorGUI()
        yield gui

        # Cleanup
        pygame.quit()

    def test_gui_initialization(self, gui_app):
        """Test that the GUI initializes correctly."""
        assert gui_app.width == 1200
        assert gui_app.height == 800
        assert len(gui_app.player_seats) == 1  # Hero seat
        assert len(gui_app.board_slots) == 5  # Flop, turn, river
        assert gui_app.simulation_panel is not None
        assert gui_app.num_simulations == 10000

    def test_add_remove_villain(self, gui_app):
        """Test adding and removing villains."""
        initial_villain_count = len(gui_app.villain_cards)

        # Add a villain
        gui_app.add_villain()
        assert len(gui_app.villain_cards) == initial_villain_count + 1
        assert len(gui_app.player_seats) == initial_villain_count + 2  # Hero + villains

        # Remove a villain
        gui_app.remove_villain()
        assert len(gui_app.villain_cards) == initial_villain_count
        assert len(gui_app.player_seats) == initial_villain_count + 1

    def test_card_assignment(self, gui_app):
        """Test assigning cards to hero."""
        # Initially no cards assigned
        assert gui_app.hero_cards == [None, None]

        # Assign a card to first position
        gui_app.hero_cards[0] = "As"
        assert gui_app.hero_cards[0] == "As"

        # Clear the card
        gui_app.hero_cards[0] = None
        assert gui_app.hero_cards[0] is None

    def test_duplicate_card_detection(self, gui_app):
        """Test that duplicate cards are detected."""
        # Set up hero with As Kh
        gui_app.hero_cards = ["As", "Kh"]

        # Try to set board card to As (duplicate)
        gui_app.board_cards[0] = "As"

        # Run simulation - should detect duplicate
        gui_app.run_simulation()

        # Check that error is set
        assert "error" in gui_app.simulation_results
        assert "Duplicate cards" in gui_app.simulation_results["error"]

    def test_simulation_with_valid_cards(self, gui_app):
        """Test running simulation with valid card setup."""
        # Set up valid cards
        gui_app.hero_cards = ["As", "Kh"]
        gui_app.board_cards = ["Qd", "Jc", "Th"]

        # Run simulation
        gui_app.run_simulation()

        # Check that results are generated
        assert gui_app.simulation_results is not None
        assert "error" not in gui_app.simulation_results
        assert "win_probability" in gui_app.simulation_results
        assert "tie_probability" in gui_app.simulation_results
        assert "loss_probability" in gui_app.simulation_results

    def test_modal_overlay_event_priority(self, gui_app):
        """Test that card picker events take priority over underlying components."""
        # Open card picker on hero card
        gui_app.card_picker = CardPicker(
            gui_app.screen, lambda x: None, lambda: None, lambda: None, set()
        )

        # Create a click event that would hit both picker and board slot
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (350, 325)  # Position that overlaps board slot

        # Handle event - card picker should consume it
        result = gui_app.handle_event(mock_event)

        # Event should be handled (return True)
        assert result is True

        # Card picker should be closed after selecting a card
        assert gui_app.card_picker is None

    def test_card_picker_selection(self, gui_app):
        """Test card picker selection logic."""
        selected_card = None
        random_called = False
        cancel_called = False

        def on_select(card):
            nonlocal selected_card
            selected_card = card

        def on_random():
            nonlocal random_called
            random_called = True

        def on_cancel():
            nonlocal cancel_called
            cancel_called = True

        # Create card picker
        picker = CardPicker(gui_app.screen, on_select, on_random, on_cancel, set())

        # Test random selection
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (370, 265)  # Random button center position

        result = picker.handle_event(mock_event)
        assert result is True
        assert random_called is True
        assert selected_card is None

    def test_card_picker_card_selection(self, gui_app):
        """Test selecting a specific card from picker."""
        selected_card = None

        def on_select(card):
            nonlocal selected_card
            selected_card = card

        # Create card picker
        picker = CardPicker(gui_app.screen, on_select, lambda: None, lambda: None, set())

        # Test card selection (first spade - 2s)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (325, 305)  # First card position (2s) - centered in card

        result = picker.handle_event(mock_event)
        assert result is True
        assert selected_card == "2s"

    def test_event_handling_structure(self, gui_app):
        """Test the event handling structure without actual events."""
        # Create a mock event
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (100, 500)  # Click on hero seat

        # Test that handle_event doesn't crash
        result = gui_app.handle_event(mock_event)
        assert isinstance(result, bool)

    def test_draw_method(self, gui_app):
        """Test that draw method runs without errors."""
        # This should not raise any exceptions
        gui_app.draw()

    def test_board_card_assignment_flop1(self, gui_app):
        """Test assigning a card to flop 1 position."""
        # Initially no board cards assigned
        assert gui_app.board_cards[0] is None
        
        # Simulate clicking on flop 1 slot
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (315, 325)  # Approximate position of flop 1 slot (within clickable area)
        
        # Handle the event
        result = gui_app.board_slots[0].handle_event(mock_event, gui_app)
        assert result is True
        
        # Card picker should be opened
        assert gui_app.card_picker is not None
        
        # Simulate selecting a card (As)
        mock_select_event = MagicMock()
        mock_select_event.type = pygame.MOUSEBUTTONDOWN
        mock_select_event.pos = (880, 320)  # Position of As in card picker
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        # Card picker should be closed and card assigned
        assert gui_app.card_picker is None
        assert gui_app.board_cards[0] == "As"

    def test_board_card_assignment_flop2(self, gui_app):
        """Test assigning a card to flop 2 position."""
        assert gui_app.board_cards[1] is None
        
        # Click on flop 2
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (415, 325)  # Flop 2 position
        
        result = gui_app.board_slots[1].handle_event(mock_event, gui_app)
        assert result is True
        assert gui_app.card_picker is not None
        
        # Select Kh
        mock_select_event = MagicMock()
        mock_select_event.type = pygame.MOUSEBUTTONDOWN
        mock_select_event.pos = (815, 345)  # Position of Kh in card picker
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        assert gui_app.card_picker is None
        assert gui_app.board_cards[1] == "Kh"

    def test_board_card_assignment_flop3(self, gui_app):
        """Test assigning a card to flop 3 position."""
        assert gui_app.board_cards[2] is None
        
        # Click on flop 3
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (515, 325)  # Flop 3 position
        
        result = gui_app.board_slots[2].handle_event(mock_event, gui_app)
        assert result is True
        assert gui_app.card_picker is not None
        
        # Select Qc
        mock_select_event = MagicMock()
        mock_select_event.type = pygame.MOUSEBUTTONDOWN
        mock_select_event.pos = (770, 435)  # Position of Qc in card picker
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        assert gui_app.card_picker is None
        assert gui_app.board_cards[2] == "Qc"

    def test_board_card_assignment_turn(self, gui_app):
        """Test assigning a card to turn position."""
        assert gui_app.board_cards[3] is None
        
        # Click on turn
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (615, 325)  # Turn position
        
        result = gui_app.board_slots[3].handle_event(mock_event, gui_app)
        assert result is True
        assert gui_app.card_picker is not None
        
        # Select Js
        mock_select_event = MagicMock()
        mock_select_event.type = pygame.MOUSEBUTTONDOWN
        mock_select_event.pos = (725, 300)  # Position of Js in card picker
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        assert gui_app.card_picker is None
        assert gui_app.board_cards[3] == "Js"

    def test_board_card_assignment_river(self, gui_app):
        """Test assigning a card to river position."""
        assert gui_app.board_cards[4] is None
        
        # Click on river
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (715, 325)  # River position
        
        result = gui_app.board_slots[4].handle_event(mock_event, gui_app)
        assert result is True
        assert gui_app.card_picker is not None
        
        # Select 10h
        mock_select_event = MagicMock()
        mock_select_event.type = pygame.MOUSEBUTTONDOWN
        mock_select_event.pos = (680, 345)  # Position of 10h in card picker
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        assert gui_app.card_picker is None
        assert gui_app.board_cards[4] == "Th"

    def test_board_card_random_assignment(self, gui_app):
        """Test assigning random cards to all board positions."""
        # Assign random to all board positions
        for i, slot in enumerate(gui_app.board_slots):
            assert gui_app.board_cards[i] is None
            
            mock_event = MagicMock()
            mock_event.type = pygame.MOUSEBUTTONDOWN
            # Click on each board slot (approximate positions)
            positions = [(315, 325), (415, 325), (515, 325), (615, 325), (715, 325)]
            mock_event.pos = positions[i]
            
            result = slot.handle_event(mock_event, gui_app)
            assert result is True
            assert gui_app.card_picker is not None
            
            # Select random
            mock_random_event = MagicMock()
            mock_random_event.type = pygame.MOUSEBUTTONDOWN
            mock_random_event.pos = (330, 55)  # Random button position
            
            picker_result = gui_app.handle_event(mock_random_event)
            assert picker_result is True
            
            # Card should be assigned to None (random)
            assert gui_app.card_picker is None
            assert gui_app.board_cards[i] is None


# PyAutoGUI-based integration tests (run separately)
def run_pyautogui_tests():
    """
    Run PyAutoGUI-based tests that require a running GUI.
    These should be run manually or in a separate test session.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = True

        # Example test structure
        def test_modal_overlay():
            """Test modal overlay event handling with PyAutoGUI."""
            # Launch GUI in separate thread
            def run_gui():
                gui = PokerSimulatorGUI()
                gui.run()

            gui_thread = threading.Thread(target=run_gui, daemon=True)
            gui_thread.start()
            time.sleep(2)  # Wait for GUI to start

            # Find GUI window
            window = pyautogui.getWindowsWithTitle("Poker Simulator")[0]
            window.activate()

            # Simulate clicking on hero card to open picker
            hero_card_pos = (150, 525)  # Approximate position
            pyautogui.click(hero_card_pos)
            time.sleep(0.5)

            # Click on overlapping position (should only affect picker)
            overlap_pos = (350, 325)  # Overlaps board slot
            pyautogui.click(overlap_pos)

            # Verify behavior (would need more complex verification)
            print("Modal overlay test completed")

        # Run the test
        test_modal_overlay()

    except ImportError:
        print("PyAutoGUI not available - skipping integration tests")
        print(f"PyAutoGUI test failed: {e}")


if __name__ == "__main__":
    # Run PyAutoGUI tests manually
    run_pyautogui_tests()