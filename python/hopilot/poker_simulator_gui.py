import pygame
import sys
from typing import List, Optional, Dict, Any

from hopilot.logging_config import get_logger
from hopilot.poker_analyzer import PokerAnalyzer

from .gui_components.player_seat import PlayerSeat
from .gui_components.board_slot import BoardSlot
from .gui_components.card_picker import CardPicker
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

        # Game state
        self.hero_cards: List[Optional[str]] = [None, None]  # Two hole cards
        self.villain_cards: List[List[Optional[str]]] = []  # List of villain hole cards
        self.board_cards: List[Optional[str]] = [None, None, None, None, None]  # Flop, turn, river

        # GUI components
        self.player_seats: List[PlayerSeat] = []
        self.board_slots: List[BoardSlot] = []
        self.card_picker: Optional[CardPicker] = None
        self.simulation_panel: Optional[SimulationPanel] = None

        # Simulation parameters
        self.num_simulations = 10000
        self.randomize_unset = True

        # Results
        self.simulation_results: Optional[Dict[str, Any]] = None

        self._setup_layout()
        self.logger.info("PokerSimulatorGUI initialization completed")

    def _setup_layout(self):
        """Set up the initial GUI layout."""
        # Hero seat
        hero_seat = PlayerSeat(self.screen, 100, 500, "Hero", self.hero_cards)
        self.player_seats.append(hero_seat)

        # Board slots
        board_positions = [(300, 300), (400, 300), (500, 300), (600, 300), (700, 300)]
        for i, pos in enumerate(board_positions):
            slot = BoardSlot(self.screen, pos[0], pos[1], f"Board {i+1}", self.board_cards[i], self.board_cards, i)
            self.board_slots.append(slot)

        # Simulation panel
        self.simulation_panel = SimulationPanel(self.screen, self.analyzer, 800, 100, self)

        # Add default villain
        self.add_villain()

    def add_villain(self):
        """Add a new villain seat."""
        villain_index = len(self.villain_cards)
        self.villain_cards.append([None, None])
        seat_x = 100 + (villain_index + 1) * 150
        seat_y = 500
        villain_seat = PlayerSeat(self.screen, seat_x, seat_y, f"Villain {villain_index + 1}", self.villain_cards[-1])
        self.player_seats.append(villain_seat)

    def remove_villain(self):
        """Remove the last villain seat."""
        if len(self.villain_cards) > 1:  # Keep at least one villain
            self.villain_cards.pop()
            self.player_seats.pop()

    def get_assigned_cards(self) -> set:
        """Get set of all currently assigned card names."""
        assigned = set()
        # Hero cards
        for card in self.hero_cards:
            if card:
                assigned.add(card)
        # Villain cards
        for villain in self.villain_cards:
            for card in villain:
                if card:
                    assigned.add(card)
        # Board cards
        for card in self.board_cards:
            if card:
                assigned.add(card)
        return assigned

    def run_simulation(self):
        """Run the poker simulation with current setup."""
        # Check if hero range is specified
        hero_range = self.simulation_panel.hero_range.strip()
        if hero_range:
            # Use range-based simulation
            board = [c for c in self.board_cards if c is not None]
            
            # Check for duplicate cards in board
            if len(board) != len(set(board)):
                self.logger.error("Duplicate cards in board")
                self.simulation_results = {"error": "Duplicate cards are not allowed in board"}
                return
            
            try:
                result = self.analyzer.calculate_odds_range(hero_range, board, 1, self.num_simulations)
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
        hero_hole = [c for c in self.hero_cards if c is not None]
        villain_holes = [[c for c in v if c is not None] for v in self.villain_cards if any(c is not None for c in v)]
        board = [c for c in self.board_cards if c is not None]

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