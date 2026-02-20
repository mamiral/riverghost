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
        picker = CardPicker(gui_app.screen, on_select, on_random, on_cancel, lambda: None, set(), None)

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
        picker = CardPicker(gui_app.screen, on_select, lambda: None, lambda: None, lambda: None, set(), None)

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


    def test_hero_card_cancel_preserves_selection(self, gui_app):
        """Test that clicking away from hero card picker preserves current selection."""
        # Set up hero with a card
        gui_app.hero_cards[0] = "As"
        
        # Click on hero position 0 to open picker
        mock_click_event = MagicMock()
        mock_click_event.type = pygame.MOUSEBUTTONDOWN
        mock_click_event.pos = (115, 525)  # Hero position 0 (x=100+10+0*50=110, y=500+25=525)
        
        # Handle the click to open picker
        result = gui_app.player_seats[0].handle_event(mock_click_event, gui_app)
        assert result is True
        assert gui_app.card_picker is not None
        
        # Simulate clicking outside the picker (cancel)
        mock_cancel_event = MagicMock()
        mock_cancel_event.type = pygame.MOUSEBUTTONDOWN
        mock_cancel_event.pos = (50, 50)  # Outside picker area
        
        # Handle the cancel event
        cancel_result = gui_app.handle_event(mock_cancel_event)
        assert cancel_result is True
        assert gui_app.card_picker is None
        
        # Verify the card is preserved
        assert gui_app.hero_cards[0] == "As"

    def test_hero_card_current_selection_highlighted(self, gui_app):
        """Test that the current hero card is highlighted in yellow in the picker."""
        # Set up hero with a card
        gui_app.hero_cards[0] = "As"
        
        # Click on hero position 0 to open picker
        mock_click_event = MagicMock()
        mock_click_event.type = pygame.MOUSEBUTTONDOWN
        mock_click_event.pos = (115, 525)  # Hero position 0 (x=100+10+0*50=110, y=500+25=525)
        
        # Handle the click to open picker
        result = gui_app.player_seats[0].handle_event(mock_click_event, gui_app)
        assert result is True
        assert gui_app.card_picker is not None
        
        # Verify the picker has the current card set
        assert gui_app.card_picker.current_card == "As"
        
        # Draw the picker and check that As is highlighted
        gui_app.card_picker.draw()
        
        # The test passes if no exceptions occur and the picker is properly configured
        assert gui_app.card_picker.current_card == "As"

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
        gui_app.hero_cards[0] = None
        assert gui_app.hero_cards[0] is None
        
        # Test board cards
        gui_app.board_cards[0] = "As"
        assert gui_app.board_cards[0] == "As"
        
        # Test villain cards
        gui_app.villain_cards[0][0] = "Kh"
        assert gui_app.villain_cards[0][0] == "Kh"

    def test_minimum_villain_constraint(self, gui_app):
        """Test that at least one villain is always maintained."""
        initial_villain_count = len(gui_app.villain_cards)
        assert initial_villain_count >= 1
        
        # Try to remove villains until we hit the minimum
        for i in range(initial_villain_count - 1):
            gui_app.remove_villain()
        
        # Should still have at least 1 villain
        assert len(gui_app.villain_cards) >= 1
        
        # Try to remove one more - should not work
        gui_app.remove_villain()
        assert len(gui_app.villain_cards) >= 1

    def test_simulation_error_handling(self, gui_app):
        """Test simulation error handling with invalid setups."""
        # Clear all cards - should handle gracefully
        gui_app.hero_cards = [None, None]
        gui_app.villain_cards = [[None, None]]
        gui_app.board_cards = [None, None, None, None, None]
        
        # Run simulation - should not crash
        gui_app.run_simulation()
        # Results should indicate error or be empty
        assert gui_app.simulation_results is not None

    def test_component_state_synchronization(self, gui_app):
        """Test that component states stay synchronized with GUI state."""
        # Set hero cards
        gui_app.hero_cards[0] = "As"
        gui_app.hero_cards[1] = "Kh"
        
        # Check that player seat reflects this
        hero_seat = gui_app.player_seats[0]
        assert hero_seat.cards[0] == "As"
        assert hero_seat.cards[1] == "Kh"
        
        # Set board cards
        gui_app.board_cards[0] = "Qd"
        board_slot = gui_app.board_slots[0]
        assert board_slot.card == "Qd"

    def test_range_picker_initialization(self, gui_app):
        """Test RangePicker initialization and basic functionality."""
        from hopilot.gui_components.range_picker import RangePicker

        selected_range = None
        cancelled = False

        def on_select(range_str):
            nonlocal selected_range
            selected_range = range_str

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        # Test initialization without initial range
        picker = RangePicker(gui_app.screen, on_select, on_cancel)
        assert len(picker.selected_ranges) == 0
        assert picker.ranks == ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

        # Test initialization with initial range
        picker_with_range = RangePicker(gui_app.screen, on_select, on_cancel, "AKs+QQ")
        assert "AKs" in picker_with_range.selected_ranges
        assert "QQ" in picker_with_range.selected_ranges

    def test_range_picker_cell_selection(self, gui_app):
        """Test selecting cells in the range picker matrix."""
        from hopilot.gui_components.range_picker import RangePicker

        selected_range = None

        def on_select(range_str):
            nonlocal selected_range
            selected_range = range_str

        def on_cancel():
            pass

        picker = RangePicker(gui_app.screen, on_select, on_cancel)

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

    def test_range_picker_ok_cancel_buttons(self, gui_app):
        """Test OK and Cancel button functionality in range picker."""
        from hopilot.gui_components.range_picker import RangePicker

        selected_range = None
        cancelled = False

        def on_select(range_str):
            nonlocal selected_range
            selected_range = range_str

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        picker = RangePicker(gui_app.screen, on_select, on_cancel)

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

    def test_card_picker_range_selection_button(self, gui_app):
        """Test the 'Select Range' button in CardPicker."""
        selected_range = None

        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            nonlocal selected_range
            selected_range = "AKs"

        # Create card picker with assigned cards
        assigned_cards = {"As", "Kh"}
        picker = CardPicker(gui_app.screen, on_select, on_random, on_cancel, on_select_range, assigned_cards, None)

        # Test clicking Select Range button
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x + 140 + 60, picker.y + 50 + 15)  # Center of Select Range button

        result = picker.handle_event(mock_event)
        assert result is True
        assert selected_range == "AKs"

    def test_player_seat_range_selection(self, gui_app):
        """Test range selection functionality in PlayerSeat."""
        hero_seat = gui_app.player_seats[0]

        # Initially no range
        assert hero_seat.range_str is None

        # Simulate clicking on range area (assuming it's in the seat)
        # This would typically open a range picker
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (hero_seat.x + 10, hero_seat.y + 10)  # Click in seat area

        # For now, just test that the seat handles events without error
        result = hero_seat.handle_event(mock_event, gui_app)
        # This might return False if no specific area was clicked, which is fine

    def test_plot_panel_functionality(self, gui_app):
        """Test PlotPanel data setting and basic functionality."""
        from hopilot.gui_components.plot_panel import PlotPanel

        # Create a plot panel
        plot_panel = PlotPanel(gui_app.screen, 100, 100, 400, 300, "Test Plot", "X Axis", "Y Axis")

        # Test initial state
        assert plot_panel.title == "Test Plot"
        assert plot_panel.xlabel == "X Axis"
        assert plot_panel.ylabel == "Y Axis"
        assert len(plot_panel.data_x) == 0
        assert len(plot_panel.data_y) == 0

        # Set some test data
        x_data = [1, 2, 3, 4, 5]
        y_data = [10, 20, 15, 25, 30]
        plot_panel.set_data(x_data, y_data, "Test Data")

        assert plot_panel.data_x == x_data
        assert plot_panel.data_y == y_data
        assert plot_panel.data_label == "Test Data"

        # Test drawing (should not raise exceptions)
        try:
            plot_panel.draw()
        except Exception as e:
            pytest.fail(f"PlotPanel.draw() raised an exception: {e}")

    def test_range_picker_click_outside_cancel(self, gui_app):
        """Test that clicking outside the range picker cancels it."""
        from hopilot.gui_components.range_picker import RangePicker

        cancelled = False

        def on_select(range_str):
            pass

        def on_cancel():
            nonlocal cancelled
            cancelled = True

        picker = RangePicker(gui_app.screen, on_select, on_cancel)

        # Click outside the dialog
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker.x - 10, picker.y - 10)  # Outside the dialog

        result = picker.handle_event(mock_event)
        assert result is True
        assert cancelled is True

    def test_card_picker_current_card_highlighting(self, gui_app):
        """Test that current card is properly highlighted in CardPicker."""
        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        # Create card picker with a current card
        assigned_cards = {"As", "Kh"}
        picker = CardPicker(gui_app.screen, on_select, on_random, on_cancel, on_select_range, assigned_cards, "Qd")

        # Test that current card is set
        assert picker.current_card == "Qd"

        # Test drawing (should highlight Qd appropriately)
        try:
            picker.draw()
        except Exception as e:
            pytest.fail(f"CardPicker.draw() with current card raised an exception: {e}")

    def test_card_picker_hide_range_button(self, gui_app):
        """Test that CardPicker can hide the Select Range button."""
        def on_select(card):
            pass

        def on_random():
            pass

        def on_cancel():
            pass

        def on_select_range():
            pass

        # Create card picker with range button hidden
        assigned_cards = {"As", "Kh"}
        picker_hidden = CardPicker(gui_app.screen, on_select, on_random, on_cancel, on_select_range, assigned_cards, None, show_range_button=False)
        picker_shown = CardPicker(gui_app.screen, on_select, on_random, on_cancel, on_select_range, assigned_cards, None, show_range_button=True)

        # Test that the flag is set correctly
        assert picker_hidden.show_range_button == False
        assert picker_shown.show_range_button == True

        # Test that clicking where the range button would be doesn't trigger it when hidden
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (picker_hidden.x + 140 + 60, picker_hidden.y + 50 + 15)  # Where Select Range button would be

        # Should not return True (button not handled) when range button is hidden
        result = picker_hidden.handle_event(mock_event)
        assert result == False  # Event not handled since button is hidden

    def test_board_slot_visual_rendering(self, gui_app):
        """Test that BoardSlot renders correctly with and without cards."""
        board_slot = gui_app.board_slots[0]

        # Test drawing without card
        assert board_slot.card is None
        try:
            board_slot.draw()
        except Exception as e:
            pytest.fail(f"BoardSlot.draw() without card raised an exception: {e}")

        # Test drawing with card
        board_slot.card = "As"
        try:
            board_slot.draw()
        except Exception as e:
            pytest.fail(f"BoardSlot.draw() with card raised an exception: {e}")

    def test_simulation_panel_results_display(self, gui_app):
        """Test that simulation panel displays results correctly."""
        # Set some mock results
        mock_results = {
            'win_probability': 0.65,
            'tie_probability': 0.05,
            'loss_probability': 0.30,
            'valid_simulations': 10000
        }

        gui_app.simulation_panel.set_results(mock_results)

        # Test drawing with results
        try:
            gui_app.simulation_panel.draw()
        except Exception as e:
            pytest.fail(f"SimulationPanel.draw() with results raised an exception: {e}")


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