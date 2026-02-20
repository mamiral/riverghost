import pygame
import sys
from typing import List, Optional, Dict, Any

from hopilot.logging_config import get_logger
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.card_assignment_manager import CardAssignmentManager

from .gui_components.player_seat import PlayerSeat
from .gui_components.board_slot import BoardSlot
from .gui_components.card_picker import CardPicker
from .gui_components.range_picker import RangePicker
from .gui_components.simulation_panel import SimulationPanel


class PokerSimulatorGUI:
    """
    Main GUI application for poker simulation.
    Allows interactive setup of poker hands and running Monte Carlo simulations.
    """

    def __init__(self, width: int = 1200, height: int = 800):
        self.logger = get_logger(__name__)
        self.logger.info(f"Initializing PokerSimulatorGUI with dimensions {width}x{height}")

        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Poker Simulator")
        self.font = pygame.font.SysFont("arial", 24)
        self.clock = pygame.time.Clock()

        # Initialize PokerAnalyzer
        self.analyzer = PokerAnalyzer()

        # Initialize Card Assignment Manager
        self.card_manager = CardAssignmentManager()
        self.card_manager.add_observer(self._on_assignments_changed)

        # GUI components
        self.player_seats: List[PlayerSeat] = []
        self.board_slots: List[BoardSlot] = []
        self.card_picker: Optional[CardPicker] = None
        self.range_picker: Optional[RangePicker] = None
        self.simulation_panel: Optional[SimulationPanel] = None

        # Simulation parameters
        self.num_simulations = 10000
        self.randomize_unset = True

        # Results
        self.simulation_results: Optional[Dict[str, Any]] = None

        self._setup_layout()
        self.logger.info("PokerSimulatorGUI initialization completed")

    def _on_assignments_changed(self):
        """Called when card assignments change. Update GUI components."""
        # Update player seats with current state
        hero_state = self.card_manager.get_hero_state()
        if self.player_seats:
            self.player_seats[0].cards = hero_state['cards']
            self.player_seats[0].range_str = hero_state['range']

        for i in range(len(self.card_manager.villain_cards)):
            if i + 1 < len(self.player_seats):
                villain_state = self.card_manager.get_villain_state(i)
                self.player_seats[i + 1].cards = villain_state['cards']
                self.player_seats[i + 1].range_str = villain_state['range']

        # Update board slots
        board_state = self.card_manager.get_board_state()
        for i, slot in enumerate(self.board_slots):
            slot.card = board_state[i]

    def _setup_layout(self):
        """Set up the initial GUI layout."""
        # Hero seat
        hero_state = self.card_manager.get_hero_state()
        def update_hero_range(range_str):
            self.card_manager.set_hero_range(range_str)
        def update_hero_card(index, card):
            self.card_manager.set_hero_card(index, card)
        hero_seat = PlayerSeat(self.screen, 100, 500, "Hero", hero_state['cards'], hero_state['range'], update_hero_range, self.card_manager.can_assign_range, update_hero_card)
        self.player_seats.append(hero_seat)

        # Board slots
        board_positions = [(300, 300), (400, 300), (500, 300), (600, 300), (700, 300)]
        board_state = self.card_manager.get_board_state()
        for i, pos in enumerate(board_positions):
            slot = BoardSlot(self.screen, pos[0], pos[1], f"Board {i+1}", board_state[i], board_state, i, self.card_manager.set_board_card)
            self.board_slots.append(slot)

        # Simulation panel
        self.simulation_panel = SimulationPanel(self.screen, self.analyzer, 800, 100, self)

        # Add default villain
        self.add_villain()

    def add_villain(self):
        """Add a new villain seat."""
        villain_index = len(self.card_manager.villain_cards)
        self.card_manager.set_villain_cards(villain_index, [None, None])  # Ensure villain exists
        seat_x = 100 + (villain_index + 1) * 150
        seat_y = 500
        villain_state = self.card_manager.get_villain_state(villain_index)
        def update_villain_range(range_str):
            self.card_manager.set_villain_range(villain_index, range_str)
        def update_villain_card(card_index, card):
            self.card_manager.set_villain_card(villain_index, card_index, card)
        villain_seat = PlayerSeat(self.screen, seat_x, seat_y, f"Villain {villain_index + 1}", villain_state['cards'], villain_state['range'], update_villain_range, self.card_manager.can_assign_range, update_villain_card)
        self.player_seats.append(villain_seat)

    def remove_villain(self):
        """Remove the last villain seat."""
        if len(self.card_manager.villain_cards) > 1:  # Keep at least one villain
            # Remove from card manager
            self.card_manager.villain_cards.pop()
            self.card_manager.villain_ranges.pop()
            self.player_seats.pop()

    def get_assigned_cards(self) -> set:
        """Get set of all currently assigned card names."""
        return self.card_manager.get_blocked_cards()

    def run_simulation(self):
        """Run the poker simulation with current setup."""
        hero_state = self.card_manager.get_hero_state()
        
        # Check if hero has a range
        if hero_state['range']:
            # Use range-based simulation for hero
            board_state = self.card_manager.get_board_state()
            board = [c for c in board_state if c is not None]
            
            # Check for duplicate cards in board
            if len(board) != len(set(board)):
                self.logger.error("Duplicate cards in board")
                self.simulation_results = {"error": "Duplicate cards are not allowed in board"}
                return
            
            try:
                # Count opponents (villains with cards or ranges)
                num_opponents = 0
                for i in range(len(self.card_manager.villain_cards)):
                    villain_state = self.card_manager.get_villain_state(i)
                    if any(villain_state['cards']) or villain_state['range']:
                        num_opponents += 1
                if num_opponents == 0:
                    num_opponents = 1  # Default to 1 opponent
                
                result = self.analyzer.calculate_odds_range(hero_state['range'], board, num_opponents, self.num_simulations)
                self.simulation_results = result
                self.simulation_panel.set_results(result)
                self.logger.info(f"Range simulation completed: {result}")
            except Exception as e:
                self.logger.error(f"Range simulation failed: {e}")
                self.simulation_results = {"error": f"Range simulation failed: {str(e)}"}
                self.simulation_panel.set_results({"error": f"Range simulation failed: {str(e)}"})
            return

        # Original card-based simulation
        # Collect assigned cards
        hero_state = self.card_manager.get_hero_state()
        hero_hole = [c for c in hero_state['cards'] if c is not None]
        villain_holes = []
        for i in range(len(self.card_manager.villain_cards)):
            villain_state = self.card_manager.get_villain_state(i)
            villain_cards = [c for c in villain_state['cards'] if c is not None]
            if villain_cards:
                villain_holes.append(villain_cards)
        
        board_state = self.card_manager.get_board_state()
        board = [c for c in board_state if c is not None]

        if len(hero_hole) != 2:
            self.logger.error("Hero must have exactly 2 hole cards")
            self.simulation_results = {"error": "Hero must have exactly 2 hole cards"}
            return

        # Check for duplicate cards
        all_cards = hero_hole + [c for vh in villain_holes for c in vh] + board
        if len(all_cards) != len(set(all_cards)):
            self.logger.error("Duplicate cards detected")
            self.simulation_results = {"error": "Duplicate cards are not allowed"}
            return

        # Run simulation
        try:
            if villain_holes:
                # Multi-opponent simulation
                result = self.analyzer.calculate_odds(hero_hole, villain_holes, board, self.num_simulations)
            else:
                # Single opponent simulation (random)
                result = self.analyzer.calculate_odds_random_opponents(hero_hole, board, 1, self.num_simulations)

            self.simulation_results = result
            self.simulation_panel.set_results(result)  # Update panel results and convergence plot
            self.logger.info(f"Simulation completed: {result}")
        except Exception as e:
            self.logger.error(f"Simulation failed: {e}")
            self.simulation_results = {"error": f"Simulation failed: {str(e)}"}
            self.simulation_panel.set_results({"error": f"Simulation failed: {str(e)}"})

    def draw(self):
        """Draw the GUI."""
        self.screen.fill((34, 139, 34))  # Green table color

        # Draw components
        for seat in self.player_seats:
            seat.draw()
        for slot in self.board_slots:
            slot.draw()
        if self.simulation_panel:
            self.simulation_panel.draw()

        # Draw card picker if active
        if self.card_picker:
            self.card_picker.draw()

        # Draw range picker if active
        if self.range_picker:
            self.range_picker.draw()

        # Draw error messages if available
        if self.simulation_results and "error" in self.simulation_results:
            self._draw_results()

        pygame.display.flip()

    def _draw_results(self):
        """Draw simulation results."""
        y = 600
        if "error" in self.simulation_results:
            text = self.font.render(self.simulation_results["error"], True, (255, 0, 0))
            self.screen.blit(text, (50, y))
        else:
            for key, value in self.simulation_results.items():
                text = self.font.render(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}", True, (255, 255, 255))
                self.screen.blit(text, (50, y))
                y += 30

    def handle_event(self, event):
        """Handle pygame events."""
        if event.type == pygame.QUIT:
            return False

        # Handle card picker if active (check first for modal priority)
        if self.card_picker:
            if self.card_picker.handle_event(event):
                self.card_picker = None
                return True

        # Handle range picker if active (check first for modal priority)
        if self.range_picker:
            if self.range_picker.handle_event(event):
                return True

        # Handle component events
        for seat in self.player_seats:
            if seat.handle_event(event, self):
                return True
        for slot in self.board_slots:
            if slot.handle_event(event, self):
                return True
        
        # Handle simulation panel events
        if self.simulation_panel:
            panel_result = self.simulation_panel.handle_event(event)
            if panel_result == "run_simulation":
                self.run_simulation()
                return True
            elif panel_result == "add_villain":
                self.add_villain()
                return True
            elif panel_result == "remove_villain":
                self.remove_villain()
                return True
            elif panel_result:
                return True

        return True

    def run(self):
        """Main application loop."""
        running = True
        while running:
            for event in pygame.event.get():
                running = self.handle_event(event)

            self.draw()
            self.clock.tick(30)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    gui = PokerSimulatorGUI()
    gui.run()