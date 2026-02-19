import pygame
from typing import Optional

from hopilot.poker_analyzer import PokerAnalyzer


class SimulationPanel:
    """
    Panel for simulation parameters and results display.
    Includes controls for running simulations and showing outcomes.
    """

    def __init__(self, screen: pygame.Surface, analyzer: PokerAnalyzer, x: int = 800, y: int = 100, gui: Optional['PokerSimulatorGUI'] = None):
        self.screen = screen
        self.analyzer = analyzer
        self.x = x
        self.y = y
        self.gui = gui
        self.width = 350
        self.height = 600
        self.font = pygame.font.SysFont("arial", 20)

        # Parameters - use gui's values if available
        self.num_simulations = gui.num_simulations if gui else 10000
        self.randomize_unset = gui.randomize_unset if gui else True

        # Buttons
        self.run_button_rect = (self.x + 20, self.y + 50, 100, 30)
        self.add_villain_rect = (self.x + 140, self.y + 50, 100, 30)
        self.remove_villain_rect = (self.x + 260, self.y + 50, 70, 30)
        self.inc_sims_rect = (self.x + 20, self.y + 90, 30, 30)
        self.dec_sims_rect = (self.x + 60, self.y + 90, 30, 30)

        # Results
        self.results: Optional[dict] = None

    def draw(self):
        """Draw the simulation panel."""
        # Panel background
        pygame.draw.rect(self.screen, (50, 50, 50), (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, (255, 255, 255), (self.x, self.y, self.width, self.height), 2)

        # Title
        title = self.font.render("Simulation Panel", True, (255, 255, 255))
        self.screen.blit(title, (self.x + 20, self.y + 20))

        # Run button
        pygame.draw.rect(self.screen, (0, 255, 0), self.run_button_rect)
        run_text = self.font.render("Run Sim", True, (0, 0, 0))
        self.screen.blit(run_text, (self.run_button_rect[0] + 10, self.run_button_rect[1] + 5))

        # Add villain button
        pygame.draw.rect(self.screen, (0, 0, 255), self.add_villain_rect)
        add_text = self.font.render("Add Villain", True, (255, 255, 255))
        self.screen.blit(add_text, (self.add_villain_rect[0] + 5, self.add_villain_rect[1] + 5))

        # Remove villain button
        pygame.draw.rect(self.screen, (255, 0, 0), self.remove_villain_rect)
        remove_text = self.font.render("Remove", True, (255, 255, 255))
        self.screen.blit(remove_text, (self.remove_villain_rect[0] + 5, self.remove_villain_rect[1] + 5))

        # Parameters
        params_y = self.y + 100
        num_sims_text = self.font.render(f"Simulations: {self.num_simulations}", True, (255, 255, 255))
        self.screen.blit(num_sims_text, (self.x + 100, params_y - 10))

        # Inc/dec buttons
        pygame.draw.rect(self.screen, (0, 255, 0), self.inc_sims_rect)
        inc_text = self.font.render("+", True, (0, 0, 0))
        self.screen.blit(inc_text, (self.inc_sims_rect[0] + 10, self.inc_sims_rect[1] + 5))

        pygame.draw.rect(self.screen, (255, 0, 0), self.dec_sims_rect)
        dec_text = self.font.render("-", True, (255, 255, 255))
        self.screen.blit(dec_text, (self.dec_sims_rect[0] + 10, self.dec_sims_rect[1] + 5))

        randomize_text = self.font.render(f"Randomize Unset: {self.randomize_unset}", True, (255, 255, 255))
        self.screen.blit(randomize_text, (self.x + 20, params_y + 30))

        # Results
        if self.results:
            results_y = params_y + 80
            for key, value in self.results.items():
                result_text = self.font.render(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}", True, (255, 255, 255))
                self.screen.blit(result_text, (self.x + 20, results_y))
                results_y += 25

    def handle_event(self, event) -> bool:
        """Handle events in the panel."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos

            # Run simulation button
            if (self.run_button_rect[0] <= mouse_x <= self.run_button_rect[0] + self.run_button_rect[2] and
                self.run_button_rect[1] <= mouse_y <= self.run_button_rect[1] + self.run_button_rect[3]):
                # Trigger simulation - this will be handled by the main GUI
                return "run_simulation"

            # Add villain button
            if (self.add_villain_rect[0] <= mouse_x <= self.add_villain_rect[0] + self.add_villain_rect[2] and
                self.add_villain_rect[1] <= mouse_y <= self.add_villain_rect[1] + self.add_villain_rect[3]):
                return "add_villain"

            # Remove villain button
            if (self.remove_villain_rect[0] <= mouse_x <= self.remove_villain_rect[0] + self.remove_villain_rect[2] and
                self.remove_villain_rect[1] <= mouse_y <= self.remove_villain_rect[1] + self.remove_villain_rect[3]):
                return "remove_villain"

            # Inc simulations
            if (self.inc_sims_rect[0] <= mouse_x <= self.inc_sims_rect[0] + self.inc_sims_rect[2] and
                self.inc_sims_rect[1] <= mouse_y <= self.inc_sims_rect[1] + self.inc_sims_rect[3]):
                self.num_simulations = min(self.num_simulations * 2, 100000)  # Double, max 100k
                if self.gui:
                    self.gui.num_simulations = self.num_simulations
                return True

            # Dec simulations
            if (self.dec_sims_rect[0] <= mouse_x <= self.dec_sims_rect[0] + self.dec_sims_rect[2] and
                self.dec_sims_rect[1] <= mouse_y <= self.dec_sims_rect[1] + self.dec_sims_rect[3]):
                self.num_simulations = max(self.num_simulations // 2, 1000)  # Half, min 1k
                if self.gui:
                    self.gui.num_simulations = self.num_simulations
                return True

        return False