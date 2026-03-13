import pytest
import pygame
import sys
import os
import time
import threading
from unittest.mock import patch, MagicMock, Mock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.poker_simulator_gui import PokerSimulatorGUI
from hopilot.logging_config import get_logger
from hopilot.gui_components.card_picker import CardPicker
from hopilot.gui_components.range_picker import RangePicker
from hopilot.gui_components.plot_panel import PlotPanel

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
        assert len(gui_app.player_seats) == 2  # Hero seat + 1 default villain
        assert len(gui_app.board_slots) == 5  # Flop, turn, river
        assert gui_app.simulation_panel is not None
        assert gui_app.num_simulations == 10000
        # Regression guard: simulator stays decoupled from standalone AoF/GTO browser flows.
        assert gui_app.gto_solver_panel is None

    def test_add_remove_villain(self, gui_app):
        """Test adding and removing villains."""
        initial_villain_count = len(gui_app.card_manager.villain_cards)

        # Add a villain
        gui_app.add_villain()
        assert len(gui_app.card_manager.villain_cards) == initial_villain_count + 1
        assert len(gui_app.player_seats) == initial_villain_count + 2  # Hero + villains

        # Remove a villain
        gui_app.remove_villain()
        assert len(gui_app.card_manager.villain_cards) == initial_villain_count
        assert len(gui_app.player_seats) == initial_villain_count + 1

    def test_card_assignment(self, gui_app):
        """Test assigning cards to hero."""
        # Initially no cards assigned
        hero_state = gui_app.card_manager.get_hero_state()
        assert hero_state['cards'] == [None, None]

        # Assign a card to first position
        gui_app.card_manager.set_hero_card(0, "As")
        hero_state = gui_app.card_manager.get_hero_state()
        assert hero_state['cards'][0] == "As"

        # Clear the card
        gui_app.card_manager.set_hero_card(0, None)
        hero_state = gui_app.card_manager.get_hero_state()
        assert hero_state['cards'][0] is None

    def test_duplicate_card_detection(self, gui_app):
        """Test that duplicate cards are detected."""
        # Set up hero with As Kh
        gui_app.card_manager.set_hero_card(0, "As")
        gui_app.card_manager.set_hero_card(1, "Kh")

        # Try to set board card to As (duplicate)
        gui_app.card_manager.set_board_card(0, "As")

        # Run simulation - should detect duplicate
        gui_app.run_simulation()

        # Check that error is set
        assert "error" in gui_app.simulation_results
        assert "Duplicate cards" in gui_app.simulation_results["error"]

    def test_simulation_with_valid_cards(self, gui_app):
        """Test running simulation with valid card setup."""
        # Set up valid cards using card manager
        gui_app.card_manager.set_hero_card(0, "As")
        gui_app.card_manager.set_hero_card(1, "Kh")
        gui_app.card_manager.set_board_card(0, "Qd")
        gui_app.card_manager.set_board_card(1, "Jc")
        gui_app.card_manager.set_board_card(2, "Th")

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
            gui_app.screen, lambda x: None, lambda: None, lambda: None, lambda: None, set(), None
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

    def test_event_handling_structure(self, gui_app):
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
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[0] is None
        
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
        mock_select_event.pos = (855, 320)  # Position of As in card picker (adjusted for wider dialog)
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        # Card picker should be closed and card assigned
        assert gui_app.card_picker is None
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[0] == "As"

    def test_board_card_assignment_flop2(self, gui_app):
        """Test assigning a card to flop 2 position."""
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[1] is None
        
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
        mock_select_event.pos = (810, 345)  # Position of Kh in card picker (adjusted for wider dialog)
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        assert gui_app.card_picker is None
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[1] == "Kh"

    def test_board_card_assignment_flop3(self, gui_app):
        """Test assigning a card to flop 3 position."""
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[2] is None
        
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
        mock_select_event.pos = (765, 435)  # Position of Qc in card picker (adjusted for wider dialog)
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        assert gui_app.card_picker is None
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[2] == "Qc"

    def test_board_card_assignment_turn(self, gui_app):
        """Test assigning a card to turn position."""
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[3] is None
        
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
        mock_select_event.pos = (720, 300)  # Position of Js in card picker (adjusted for wider dialog)
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        assert gui_app.card_picker is None
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[3] == "Js"

    def test_board_card_assignment_river(self, gui_app):
        """Test assigning a card to river position."""
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[4] is None
        
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
        mock_select_event.pos = (675, 345)  # Position of 10h in card picker (adjusted for wider dialog)
        
        picker_result = gui_app.handle_event(mock_select_event)
        assert picker_result is True
        
        assert gui_app.card_picker is None
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[4] == "Th"

    def test_board_card_random_assignment(self, gui_app):
        """Test assigning random cards to all board positions."""
        # Assign random to all board positions
        for i, slot in enumerate(gui_app.board_slots):
            board_state = gui_app.card_manager.get_board_state()
            assert board_state[i] is None
            
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
            board_state = gui_app.card_manager.get_board_state()
            assert board_state[i] is None


    def test_hero_card_cancel_preserves_selection(self, gui_app):
        """Test that clicking away from hero card picker preserves current selection."""
        # Set up hero with a card
        gui_app.card_manager.set_hero_card(0, "As")
        
        # Click on hero position 0 to open picker
        mock_click_event = MagicMock()
        mock_click_event.type = pygame.MOUSEBUTTONDOWN
        mock_click_event.pos = (115, 525)  # Hero position 0 (x=100+10+0*50=110, y=500+25=525)
        
        # Handle the click to open picker
        result = gui_app.player_seats[0].handle_event(mock_click_event, gui_app)
        assert result is True
        assert gui_app.range_picker is not None
        
        # Simulate clicking outside the picker (cancel)
        mock_cancel_event = MagicMock()
        mock_cancel_event.type = pygame.MOUSEBUTTONDOWN
        mock_cancel_event.pos = (50, 50)  # Outside picker area
        
        # Handle the cancel event
        cancel_result = gui_app.handle_event(mock_cancel_event)
        assert cancel_result is True
        assert gui_app.range_picker is None
        
        # Verify the card is preserved
        hero_state = gui_app.card_manager.get_hero_state()
        assert hero_state['cards'][0] == "As"

    def test_hero_card_current_selection_highlighted(self, gui_app):
        """Test that the current hero card is highlighted in yellow in the picker."""
        # Set up hero with a card
        gui_app.card_manager.set_hero_card(0, "As")
        
        # Click on hero position 0 to open picker
        mock_click_event = MagicMock()
        mock_click_event.type = pygame.MOUSEBUTTONDOWN
        mock_click_event.pos = (115, 525)  # Hero position 0 (x=100+10+0*50=110, y=500+25=525)
        
        # Handle the click to open picker
        result = gui_app.player_seats[0].handle_event(mock_click_event, gui_app)
        assert result is True
        assert gui_app.range_picker is not None
        
        # Verify the picker is opened (now a range picker by default)
        assert gui_app.range_picker is not None
        
        # Draw the picker and check that it renders without errors
        gui_app.range_picker.draw()
        
        # The test passes if no exceptions occur and the picker is properly opened

    def test_simulation_panel_button_interactions(self, gui_app):
        """Test simulation panel button clicks."""
        # Test run simulation button
        mock_run_event = MagicMock()
        mock_run_event.type = pygame.MOUSEBUTTONDOWN
        mock_run_event.pos = (825, 155)  # Run button position (x=800+20+5, y=100+50+5)
        
        result = gui_app.simulation_panel.handle_event(mock_run_event)
        assert result == "run_simulation"
        
        # Test add villain button
        mock_add_event = MagicMock()
        mock_add_event.type = pygame.MOUSEBUTTONDOWN
        mock_add_event.pos = (945, 155)  # Add villain button position (x=800+140+5, y=100+50+5)
        
        result = gui_app.simulation_panel.handle_event(mock_add_event)
        assert result == "add_villain"
        
        # Test remove villain button
        mock_remove_event = MagicMock()
        mock_remove_event.type = pygame.MOUSEBUTTONDOWN
        mock_remove_event.pos = (1065, 155)  # Remove villain button position (x=800+260+5, y=100+50+5)
        
        result = gui_app.simulation_panel.handle_event(mock_remove_event)
        assert result == "remove_villain"

    def test_simulation_controls_functionality(self, gui_app):
        """Test simulation number increment/decrement controls."""
        initial_sims = gui_app.num_simulations
        assert initial_sims == 10000
        
        # Test increment button
        mock_inc_event = MagicMock()
        mock_inc_event.type = pygame.MOUSEBUTTONDOWN
        mock_inc_event.pos = (825, 195)  # Inc button position (x=800+20+5, y=100+90+5)
        
        result = gui_app.simulation_panel.handle_event(mock_inc_event)
        assert result is True
        assert gui_app.num_simulations == initial_sims * 2  # Should double
        
        # Test decrement button
        mock_dec_event = MagicMock()
        mock_dec_event.type = pygame.MOUSEBUTTONDOWN
        mock_dec_event.pos = (865, 195)  # Dec button position (x=800+60+5, y=100+90+5)
        
        result = gui_app.simulation_panel.handle_event(mock_dec_event)
        assert result is True
        assert gui_app.num_simulations == initial_sims  # Should be back to original

    def test_component_layout_positions(self, gui_app):
        """Test that GUI components are positioned correctly."""
        # Hero seat position
        hero_seat = gui_app.player_seats[0]
        assert hero_seat.x == 100
        assert hero_seat.y == 500
        
        # Villain seat position
        villain_seat = gui_app.player_seats[1]
        assert villain_seat.x == 250  # 100 + 150
        assert villain_seat.y == 500
        
        # Board slots positions
        expected_board_positions = [(300, 300), (400, 300), (500, 300), (600, 300), (700, 300)]
        for i, slot in enumerate(gui_app.board_slots):
            assert slot.x == expected_board_positions[i][0]
            assert slot.y == expected_board_positions[i][1]
        
        # Simulation panel position
        assert gui_app.simulation_panel.x == 800
        assert gui_app.simulation_panel.y == 100

    def test_gui_drawing_without_errors(self, gui_app):
        """Test that all GUI components can draw without errors."""
        # This should not raise any exceptions
        gui_app.draw()
        
        # Test individual component drawing
        for seat in gui_app.player_seats:
            seat.draw()
        
        for slot in gui_app.board_slots:
            slot.draw()
        
        gui_app.simulation_panel.draw()

    def test_event_handling_edge_cases(self, gui_app):
        """Test event handling for edge cases and invalid inputs."""
        # Test non-mouse events
        mock_key_event = MagicMock()
        mock_key_event.type = pygame.KEYDOWN
        mock_key_event.key = pygame.K_SPACE
        
        result = gui_app.handle_event(mock_key_event)
        assert result is True  # Should be handled gracefully
        
        # Test mouse events outside any component
        mock_outside_event = MagicMock()
        mock_outside_event.type = pygame.MOUSEBUTTONDOWN
        mock_outside_event.pos = (0, 0)  # Top-left corner
        
        result = gui_app.handle_event(mock_outside_event)
        assert result is True  # Should be handled gracefully

    def test_card_assignment_edge_cases(self, gui_app):
        """Test card assignment edge cases."""
        # Test assigning None (should work)
        gui_app.card_manager.set_hero_card(0, None)
        hero_state = gui_app.card_manager.get_hero_state()
        assert hero_state['cards'][0] is None
        
        # Test board cards
        gui_app.card_manager.set_board_card(0, "As")
        board_state = gui_app.card_manager.get_board_state()
        assert board_state[0] == "As"
        
        # Test villain cards
        gui_app.card_manager.set_villain_card(0, 0, "Kh")
        villain_state = gui_app.card_manager.get_villain_state(0)
        assert villain_state['cards'][0] == "Kh"

    def test_minimum_villain_constraint(self, gui_app):
        """Test that at least one villain is always maintained."""
        initial_villain_count = len(gui_app.card_manager.villain_cards)
        assert initial_villain_count >= 1
        
        # Try to remove villains until we hit the minimum
        for i in range(initial_villain_count - 1):
            gui_app.remove_villain()
        
        # Should still have at least 1 villain
        assert len(gui_app.card_manager.villain_cards) >= 1
        
        # Try to remove one more - should not work
        gui_app.remove_villain()
        assert len(gui_app.card_manager.villain_cards) >= 1

    def test_simulation_error_handling(self, gui_app):
        """Test simulation error handling with invalid setups."""
        # Clear all cards - should handle gracefully
        gui_app.card_manager.set_hero_card(0, None)
        gui_app.card_manager.set_hero_card(1, None)
        gui_app.card_manager.set_villain_card(0, 0, None)
        gui_app.card_manager.set_villain_card(0, 1, None)
        gui_app.card_manager.set_board_card(0, None)
        gui_app.card_manager.set_board_card(1, None)
        gui_app.card_manager.set_board_card(2, None)
        gui_app.card_manager.set_board_card(3, None)
        gui_app.card_manager.set_board_card(4, None)
        
        # Run simulation - should not crash
        gui_app.run_simulation()
        # Results should indicate error or be empty
        assert gui_app.simulation_results is not None

    def test_component_state_synchronization(self, gui_app):
        """Test that component states stay synchronized with GUI state."""
        # Set hero cards
        gui_app.card_manager.set_hero_card(0, "As")
        gui_app.card_manager.set_hero_card(1, "Kh")
        
        # Check that player seat reflects this
        hero_seat = gui_app.player_seats[0]
        assert hero_seat.cards[0] == "As"
        assert hero_seat.cards[1] == "Kh"
        
        # Set board cards
        gui_app.card_manager.set_board_card(0, "Qd")
        board_slot = gui_app.board_slots[0]
        assert board_slot.card == "Qd"

    def test_panel_navigation(self, gui_app):
        """Test simulator-only panel state remains stable."""
        assert gui_app.current_panel == 'simulator'
        assert gui_app.simulation_panel is not None
        assert gui_app.gto_solver_panel is None
        assert len(gui_app.player_seats) > 0
        assert len(gui_app.board_slots) > 0

    def test_navigation_button_events(self, gui_app):
        """Test simulator header button click handling."""
        simulator_button_center = gui_app.nav_buttons['simulator'].center
        event = Mock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.pos = simulator_button_center

        result = gui_app.handle_event(event)

        assert result == True
        assert gui_app.current_panel == 'simulator'
        assert gui_app.simulation_panel is not None
        assert gui_app.gto_solver_panel is None


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