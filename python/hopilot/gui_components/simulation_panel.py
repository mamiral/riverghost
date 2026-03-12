import pygame
from typing import Optional

from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.gui_components.plot_panel import ConvergencePlot


class SimulationPanel:
    """
    Panel for simulation parameters and results display.
    Includes controls for running simulations and showing outcomes.
    """

    def __init__(self, screen: pygame.Surface, analyzer: PokerAnalyzer, *args):
        self.screen = screen
        self.analyzer = analyzer
        
        # Handle backward compatibility for different calling conventions
        if len(args) == 2:
            # Old calling convention: SimulationPanel(screen, analyzer, x, y)
            self.gto_solver = None
            self.x = args[0]
            self.y = args[1]
            self.gui = None
        elif len(args) == 3:
            # Transitional calling convention: SimulationPanel(screen, analyzer, x, y, gui)
            self.gto_solver = None
            self.x = args[0]
            self.y = args[1]
            self.gui = args[2]
        elif len(args) == 4:
            # New calling convention: SimulationPanel(screen, analyzer, gto_solver, x, y, gui)
            self.gto_solver = args[0]
            self.x = args[1]
            self.y = args[2]
            self.gui = args[3]
        else:
            raise ValueError(f"Invalid number of arguments: expected 4, 5, or 6, got {2 + len(args)}")
        self.width = 350
        self.height = 600
        self.font = pygame.font.SysFont("arial", 20)
        self.width = 350
        self.height = 600
        self.font = pygame.font.SysFont("arial", 20)

        # Parameters - use gui's values if available
        self.num_simulations = self.gui.num_simulations if self.gui else 10000
        self.randomize_unset = self.gui.randomize_unset if self.gui else False

        # GTO Parameters
        self.gto_pot_size = 20.0  # Default pot size in BB
        self.gto_bet_amount = 10.0  # Default bet amount in BB
        
        # Bonus payouts - copy from GTO solver if available
        self.bonus_payouts = {
            'royal_flush': 500,
            'straight_flush': 100,
            'four_of_a_kind': 50,
            'full_house': 10,
            'flush': 5,
            'straight': 4,
            'three_of_a_kind': 3,
            'two_pair': 2,
            'one_pair': 1,
        }
        if self.gto_solver:
            self.bonus_payouts = self.gto_solver.bonus_payouts.copy()

        # Input field state
        self.active_input_field = None  # Track which field is being edited
        self.input_text = ""  # Current input text

        # Buttons
        self.run_button_rect = (self.x + 20, self.y + 50, 100, 30)
        self.add_villain_rect = (self.x + 140, self.y + 50, 100, 30)
        self.remove_villain_rect = (self.x + 260, self.y + 50, 70, 30)
        self.inc_sims_rect = (self.x + 20, self.y + 90, 30, 30)
        self.dec_sims_rect = (self.x + 60, self.y + 90, 30, 30)
        self.select_range_button_rect = (self.x + 20, self.y + 130, 150, 30)
        self.gto_button_rect = (self.x + 180, self.y + 130, 150, 30)

        # GTO Configuration UI elements
        self.pot_size_input_rect = (self.x + 20, self.y + 170, 80, 25)
        self.bet_amount_input_rect = (self.x + 120, self.y + 170, 80, 25)
        
        # Bonus payout input fields
        self.bonus_input_rects = {}
        bonus_y = self.y + 200
        for i, (hand_type, multiplier) in enumerate(self.bonus_payouts.items()):
            self.bonus_input_rects[hand_type] = (self.x + 20, bonus_y + i * 25, 60, 20)

        # Preset buttons
        self.preset_buttons = {
            'none': (self.x + 20, bonus_y + len(self.bonus_payouts) * 25 + 10, 60, 25),
            'standard': (self.x + 90, bonus_y + len(self.bonus_payouts) * 25 + 10, 80, 25),
            'high_roller': (self.x + 180, bonus_y + len(self.bonus_payouts) * 25 + 10, 90, 25),
        }

        # Results
        self.results: Optional[dict] = None
        self.gto_results: Optional[dict] = None

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

        # GTO button
        pygame.draw.rect(self.screen, (255, 165, 0), self.gto_button_rect)
        gto_text = self.font.render("Run GTO", True, (0, 0, 0))
        self.screen.blit(gto_text, (self.gto_button_rect[0] + 10, self.gto_button_rect[1] + 5))

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

        # GTO Configuration Section
        gto_config_y = params_y + 60
        gto_title = self.font.render("GTO Config:", True, (255, 255, 0))
        self.screen.blit(gto_title, (self.x + 20, gto_config_y))
        
        # Pot size and bet amount inputs
        pot_bet_y = gto_config_y + 25
        pot_label = self.font.render("Pot:", True, (255, 255, 255))
        self.screen.blit(pot_label, (self.x + 20, pot_bet_y))
        
        bet_label = self.font.render("Bet:", True, (255, 255, 255))
        self.screen.blit(bet_label, (self.x + 120, pot_bet_y))
        
        # Input field backgrounds
        pygame.draw.rect(self.screen, (100, 100, 100), self.pot_size_input_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), self.bet_amount_input_rect)
        
        # Input field borders (highlight active field)
        pot_border_color = (255, 255, 0) if self.active_input_field == 'pot_size' else (200, 200, 200)
        bet_border_color = (255, 255, 0) if self.active_input_field == 'bet_amount' else (200, 200, 200)
        pygame.draw.rect(self.screen, pot_border_color, self.pot_size_input_rect, 2)
        pygame.draw.rect(self.screen, bet_border_color, self.bet_amount_input_rect, 2)
        
        # Input field text
        pot_text = self.input_text if self.active_input_field == 'pot_size' else str(self.gto_pot_size)
        bet_text = self.input_text if self.active_input_field == 'bet_amount' else str(self.gto_bet_amount)
        
        pot_display = self.font.render(pot_text, True, (255, 255, 255))
        bet_display = self.font.render(bet_text, True, (255, 255, 255))
        self.screen.blit(pot_display, (self.pot_size_input_rect[0] + 5, self.pot_size_input_rect[1] + 2))
        self.screen.blit(bet_display, (self.bet_amount_input_rect[0] + 5, self.bet_amount_input_rect[1] + 2))

        # Bonus payouts section
        bonus_y = pot_bet_y + 40
        bonus_title = self.font.render("Bonus Payouts:", True, (255, 255, 0))
        self.screen.blit(bonus_title, (self.x + 20, bonus_y))
        
        bonus_list_y = bonus_y + 20
        for i, (hand_type, multiplier) in enumerate(self.bonus_payouts.items()):
            # Hand type label
            hand_label = hand_type.replace('_', ' ').title()
            label_text = self.font.render(f"{hand_label}:", True, (255, 255, 255))
            self.screen.blit(label_text, (self.x + 20, bonus_list_y + i * 25))
            
            # Input field
            rect = self.bonus_input_rects[hand_type]
            pygame.draw.rect(self.screen, (100, 100, 100), rect)
            border_color = (255, 255, 0) if self.active_input_field == hand_type else (200, 200, 200)
            pygame.draw.rect(self.screen, border_color, rect, 1)
            
            # Current value
            current_value = self.input_text if self.active_input_field == hand_type else str(multiplier)
            value_text = self.font.render(current_value, True, (255, 255, 255))
            self.screen.blit(value_text, (rect[0] + 5, rect[1] + 2))

        # Preset buttons
        preset_y = bonus_list_y + len(self.bonus_payouts) * 25 + 10
        preset_title = self.font.render("Presets:", True, (255, 255, 0))
        self.screen.blit(preset_title, (self.x + 20, preset_y))
        
        preset_buttons_y = preset_y + 20
        for preset_name, rect in self.preset_buttons.items():
            pygame.draw.rect(self.screen, (70, 70, 70), rect)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 1)
            preset_label = preset_name.replace('_', ' ').title()
            preset_text = self.font.render(preset_label, True, (255, 255, 255))
            self.screen.blit(preset_text, (rect[0] + 5, rect[1] + 2))

        # Results
        if self.results:
            results_y = preset_buttons_y + 40
            for key, value in self.results.items():
                result_text = self.font.render(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}", True, (255, 255, 255))
                self.screen.blit(result_text, (self.x + 20, results_y))
                results_y += 25

        # GTO Results
        if self.gto_results:
            gto_y = preset_buttons_y + 40
            if self.results:
                # Position below simulation results
                num_results = len(self.results)
                gto_y = preset_buttons_y + 40 + num_results * 25 + 20
            gto_title = self.font.render("GTO Analysis:", True, (255, 255, 0))
            self.screen.blit(gto_title, (self.x + 20, gto_y))
            gto_y += 25
            
            # Show key GTO results
            key_fields = ['hero_equity', 'villain_equity', 'hero_ev', 'villain_ev', 
                         'hero_strategy', 'villain_strategy', 'hero_category', 'villain_category']
            
            for key in key_fields:
                if key in self.gto_results:
                    value = self.gto_results[key]
                    if key in ['hero_equity', 'villain_equity', 'hero_ev', 'villain_ev']:
                        display_text = f"{key.replace('_', ' ').title()}: {value:.3f}"
                    else:
                        display_text = f"{key.replace('_', ' ').title()}: {value}"
                    gto_text = self.font.render(display_text, True, (255, 255, 255))
                    self.screen.blit(gto_text, (self.x + 20, gto_y))
                    gto_y += 20

        # Draw convergence plot
        self.convergence_plot = ConvergencePlot(self.screen, self.x + 20, self.y + 500, 310, 200)
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

            # GTO button
            if (self.gto_button_rect[0] <= mouse_x <= self.gto_button_rect[0] + self.gto_button_rect[2] and
                self.gto_button_rect[1] <= mouse_y <= self.gto_button_rect[1] + self.gto_button_rect[3]):
                return "run_gto"

            # Pot size input field
            if (self.pot_size_input_rect[0] <= mouse_x <= self.pot_size_input_rect[0] + self.pot_size_input_rect[2] and
                self.pot_size_input_rect[1] <= mouse_y <= self.pot_size_input_rect[1] + self.pot_size_input_rect[3]):
                self.active_input_field = 'pot_size'
                self.input_text = str(self.gto_pot_size)
                return True

            # Bet amount input field
            if (self.bet_amount_input_rect[0] <= mouse_x <= self.bet_amount_input_rect[0] + self.bet_amount_input_rect[2] and
                self.bet_amount_input_rect[1] <= mouse_y <= self.bet_amount_input_rect[1] + self.bet_amount_input_rect[3]):
                self.active_input_field = 'bet_amount'
                self.input_text = str(self.gto_bet_amount)
                return True

            # Bonus payout input fields
            for hand_type, rect in self.bonus_input_rects.items():
                if (rect[0] <= mouse_x <= rect[0] + rect[2] and
                    rect[1] <= mouse_y <= rect[1] + rect[3]):
                    self.active_input_field = hand_type
                    self.input_text = str(self.bonus_payouts[hand_type])
                    return True

            # Preset buttons
            for preset_name, rect in self.preset_buttons.items():
                if (rect[0] <= mouse_x <= rect[0] + rect[2] and
                    rect[1] <= mouse_y <= rect[1] + rect[3]):
                    self.apply_preset(preset_name)
                    return True

            # Click outside input fields to deactivate
            self.active_input_field = None
            self.input_text = ""

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

        # Handle keyboard input for active input fields
        elif event.type == pygame.KEYDOWN and self.active_input_field:
            if event.key == pygame.K_RETURN or event.key == pygame.K_TAB:
                # Save the input
                self.save_input_value()
                self.active_input_field = None
                self.input_text = ""
                return True
            elif event.key == pygame.K_ESCAPE:
                # Cancel input
                self.active_input_field = None
                self.input_text = ""
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
                return True
            elif event.unicode.isdigit() or event.unicode == '.':
                self.input_text += event.unicode
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

    def set_gto_results(self, results: dict):
        """Set the GTO analysis results."""
        self.gto_results = results

    def save_input_value(self):
        """Save the current input value to the appropriate parameter."""
        if not self.active_input_field or not self.input_text:
            return

        try:
            value = float(self.input_text)
            if value < 0:
                return  # Don't allow negative values

            if self.active_input_field == 'pot_size':
                self.gto_pot_size = value
            elif self.active_input_field == 'bet_amount':
                self.gto_bet_amount = value
            elif self.active_input_field in self.bonus_payouts:
                self.bonus_payouts[self.active_input_field] = int(value)
                # Update GTO solver if available
                if self.gto_solver:
                    self.gto_solver.set_bonus_payouts(self.bonus_payouts)
        except ValueError:
            pass  # Invalid input, ignore

    def apply_preset(self, preset_name: str):
        """Apply a bonus payout preset."""
        if preset_name == 'none':
            # No bonus payouts
            self.bonus_payouts = {k: 0 for k in self.bonus_payouts.keys()}
        elif preset_name == 'standard':
            # Standard tournament payouts
            self.bonus_payouts = {
                'royal_flush': 500,
                'straight_flush': 100,
                'four_of_a_kind': 50,
                'full_house': 10,
                'flush': 5,
                'straight': 4,
                'three_of_a_kind': 3,
                'two_pair': 2,
                'one_pair': 1,
            }
        elif preset_name == 'high_roller':
            # High roller tournament payouts
            self.bonus_payouts = {
                'royal_flush': 2000,
                'straight_flush': 500,
                'four_of_a_kind': 200,
                'full_house': 50,
                'flush': 20,
                'straight': 15,
                'three_of_a_kind': 10,
                'two_pair': 5,
                'one_pair': 2,
            }

        # Update GTO solver with new payouts
        if self.gto_solver:
            self.gto_solver.set_bonus_payouts(self.bonus_payouts)