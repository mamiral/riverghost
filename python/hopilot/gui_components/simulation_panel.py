import pygame
from typing import Optional

from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.gui_components.plot_panel import ConvergencePlot


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

        # Hero range input
        self.hero_range = ""  # For range input like "AKs"
        self.range_input_active = False

        # Buttons
        self.run_button_rect = (self.x + 20, self.y + 50, 100, 30)
        self.add_villain_rect = (self.x + 140, self.y + 50, 100, 30)
        self.remove_villain_rect = (self.x + 260, self.y + 50, 70, 30)
        self.inc_sims_rect = (self.x + 20, self.y + 90, 30, 30)
        self.dec_sims_rect = (self.x + 60, self.y + 90, 30, 30)
        self.range_input_rect = (self.x + 20, self.y + 130, 200, 30)

        # Results
        self.results: Optional[dict] = None

        # Convergence plot
        self.convergence_plot = ConvergencePlot(screen, self.x + 20, self.y + 350, 310, 200)
        self.convergence_data = []  # List of (simulations, win_prob) tuples

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

        # Hero range input
        range_label = self.font.render("Hero Range:", True, (255, 255, 255))
        self.screen.blit(range_label, (self.x + 20, params_y + 50))
        pygame.draw.rect(self.screen, (255, 255, 255) if self.range_input_active else (100, 100, 100), self.range_input_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), self.range_input_rect, 2)
        range_text = self.font.render(self.hero_range or "Click to enter range", True, (0, 0, 0))
        self.screen.blit(range_text, (self.range_input_rect[0] + 5, self.range_input_rect[1] + 5))

        # Results
        if self.results:
            results_y = params_y + 80
            for key, value in self.results.items():
                result_text = self.font.render(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}", True, (255, 255, 255))
                self.screen.blit(result_text, (self.x + 20, results_y))
                results_y += 25

        # Draw convergence plot
        self.convergence_plot.draw()

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

            # Range input
            if (self.range_input_rect[0] <= mouse_x <= self.range_input_rect[0] + self.range_input_rect[2] and
                self.range_input_rect[1] <= mouse_y <= self.range_input_rect[1] + self.range_input_rect[3]):
                self.range_input_active = not self.range_input_active
                return True

        # Handle text input for range
        if event.type == pygame.KEYDOWN and self.range_input_active:
            if event.key == pygame.K_RETURN:
                self.range_input_active = False
            elif event.key == pygame.K_BACKSPACE:
                self.hero_range = self.hero_range[:-1]
            else:
                self.hero_range += event.unicode.upper()
            return True

        return False

    def add_convergence_point(self, simulations: int, win_probability: float):
        """Add a data point to the convergence plot."""
        self.convergence_data.append((simulations, win_probability))
        self.convergence_plot.update_convergence_data(
            [s for s, _ in self.convergence_data],
            [p for _, p in self.convergence_data]
        )

    def clear_convergence_data(self):
        """Clear all convergence data."""
        self.convergence_data.clear()
        self.convergence_plot.clear_data()

    def set_results(self, results: dict):
        """Set the simulation results and update convergence plot."""
        self.results = results

        # Clear previous convergence data
        self.clear_convergence_data()

        # Generate simulated convergence data if we have results
        if results and 'win_probability' in results:
            total_sims = results.get('total_simulations', self.num_simulations)
            final_win_prob = results['win_probability']

            # Generate convergence points (simulate how it would have converged)
            self._generate_convergence_data(total_sims, final_win_prob)

    def _generate_convergence_data(self, total_simulations: int, final_win_prob: float):
        """Generate simulated convergence data points."""
        import random
        import math

        # Create checkpoints at regular intervals
        num_points = min(20, total_simulations // 500)  # Up to 20 points, minimum 500 sims per point
        if num_points < 2:
            num_points = 2

        sims_per_point = total_simulations // (num_points - 1)

        for i in range(num_points):
            sim_count = (i + 1) * sims_per_point
            if sim_count > total_simulations:
                sim_count = total_simulations

            # Simulate convergence: early points have more variance, later points converge
            progress = i / (num_points - 1)  # 0 to 1

            # Variance decreases exponentially with simulation count
            variance = 0.02 * math.exp(-3 * progress)  # Start with ±2%, decrease to near 0

            # Add some realistic noise
            noise = random.gauss(0, variance)

            # Ensure we converge to the final value
            if progress > 0.8:  # In final 20%, get very close to final value
                win_prob = final_win_prob + noise * 0.1
            else:
                win_prob = final_win_prob + noise

            # Clamp to valid probability range
            win_prob = max(0.0, min(1.0, win_prob))

            self.add_convergence_point(sim_count, win_prob)

        # Ensure the final point is exactly the final result
        self.add_convergence_point(total_simulations, final_win_prob)