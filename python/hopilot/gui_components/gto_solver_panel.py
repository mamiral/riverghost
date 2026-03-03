import pygame
from typing import Optional, Dict, Any, List
import yaml
import os
from hopilot.logging_config import get_logger
from hopilot.gto.gto_optimizer import GTOOptimizer
from hopilot.poker_analyzer import PokerAnalyzer


class GTOSolverPanel:
    """
    GUI panel for GTO solver functionality using basic pygame.

    Provides interface for:
    - GTO threshold analysis
    - Range vs range Nash equilibrium
    - Indifference point calculations
    """

    def __init__(self, analyzer: PokerAnalyzer, optimizer: GTOOptimizer,
                 width: int = 800, height: int = 600):
        """
        Initialize the GTO solver panel.

        Args:
            analyzer: PokerAnalyzer instance
            optimizer: GTOOptimizer instance
            width: Panel width
            height: Panel height
        """
        self.logger = get_logger(__name__)
        self.analyzer = analyzer
        self.optimizer = optimizer

        self.width = width
        self.height = height

        # Analysis parameters
        self.current_mode = 'threshold'  # 'threshold', 'range_vs_range', 'indifference'
        self.num_opponents = 8
        self.pot_size = 20.0
        self.bet_amount = 10.0

        # Range data
        self.hero_range: List[str] = []
        self.villain_range: List[str] = []

        # Calculation state
        self.is_calculating = False
        self.progress = 0.0
        self.last_result: Optional[Dict[str, Any]] = None
        self.last_error: Optional[str] = None

        # Initialize pygame if not already done
        if not pygame.get_init():
            pygame.init()

        # Initialize fonts
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 16)
        self.title_font = pygame.font.SysFont('Arial', 20, bold=True)

        # Colors
        self.BG_COLOR = (240, 240, 240)
        self.TEXT_COLOR = (0, 0, 0)
        self.BUTTON_COLOR = (200, 200, 200)
        self.BUTTON_HOVER_COLOR = (180, 180, 180)
        self.BORDER_COLOR = (150, 150, 150)
        self.ERROR_COLOR = (255, 0, 0)
        self.SUCCESS_COLOR = (0, 150, 0)

        # Create surface
        self.surface = pygame.Surface((width, height))

        # UI element rectangles
        self._create_ui_rects()

        self.logger.info("GTOSolverPanel initialized")

    def _create_ui_rects(self):
        """Create rectangles for UI elements."""
        # Mode buttons
        self.mode_buttons_rects = {}
        modes = [
            ('threshold', 'GTO Threshold'),
            ('range_vs_range', 'Range vs Range'),
            ('indifference', 'Indifference Points')
        ]

        for i, (mode_key, mode_label) in enumerate(modes):
            rect = pygame.Rect(10 + i * 120, 10, 110, 30)
            self.mode_buttons_rects[mode_key] = (rect, mode_label)

        # Calculate button
        self.calculate_button_rect = pygame.Rect(10, 200, 150, 40)

        # Parameter inputs
        self.opponents_rect = pygame.Rect(120, 50, 50, 25)
        self.pot_rect = pygame.Rect(120, 80, 50, 25)
        self.bet_rect = pygame.Rect(120, 110, 50, 25)

        # Range inputs
        self.hero_range_rect = pygame.Rect(290, 50, 150, 25)
        self.villain_range_rect = pygame.Rect(290, 80, 150, 25)

        # Browse buttons
        self.hero_browse_rect = pygame.Rect(450, 50, 80, 25)
        self.villain_browse_rect = pygame.Rect(450, 80, 80, 25)

        # Results area
        self.results_rect = pygame.Rect(10, 250, self.width - 20, self.height - 260)

        # Input field values
        self.opponents_text = str(self.num_opponents)
        self.pot_text = str(self.pot_size)
        self.bet_text = str(self.bet_amount)
        self.hero_range_text = ""
        self.villain_range_text = ""

        # Active input field
        self.active_input = None

    def set_mode(self, mode: str):
        """Set the current analysis mode."""
        if mode in ['threshold', 'range_vs_range', 'indifference']:
            self.current_mode = mode
            self.logger.info(f"Switched to mode: {mode}")

    def set_num_opponents(self, num: int) -> bool:
        """Set number of opponents with validation."""
        if 1 <= num <= 9:
            self.num_opponents = num
            self.opponents_text = str(num)
            return True
        return False

    def set_pot_size(self, pot: float) -> bool:
        """Set pot size with validation."""
        if pot > 0:
            self.pot_size = pot
            self.pot_text = str(pot)
            return True
        return False

    def set_bet_amount(self, bet: float) -> bool:
        """Set bet amount with validation."""
        if bet > 0:
            self.bet_amount = bet
            self.bet_text = str(bet)
            return True
        return False

    def load_hero_range(self, filepath: str) -> bool:
        """Load hero range from YAML file."""
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                if 'hands' in data:
                    self.hero_range = data['hands']
                    self.hero_range_text = filepath
                    self.logger.info(f"Loaded hero range with {len(self.hero_range)} hands")
                    return True
        except Exception as e:
            self.logger.error(f"Failed to load hero range: {e}")
            self.last_error = f"Failed to load hero range: {e}"
        return False

    def load_villain_range(self, filepath: str) -> bool:
        """Load villain range from YAML file."""
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                if 'hands' in data:
                    self.villain_range = data['hands']
                    self.villain_range_text = filepath
                    self.logger.info(f"Loaded villain range with {len(self.villain_range)} hands")
                    return True
        except Exception as e:
            self.logger.error(f"Failed to load villain range: {e}")
            self.last_error = f"Failed to load villain range: {e}"
        return False

    def calculate_current_mode(self):
        """Calculate results for the current mode."""
        self.start_calculation()

        try:
            if self.current_mode == 'threshold':
                result = self.calculate_threshold()
            elif self.current_mode == 'range_vs_range':
                result = self.calculate_range_vs_range()
            elif self.current_mode == 'indifference':
                result = self.calculate_indifference_points()
            else:
                raise ValueError(f"Unknown mode: {self.current_mode}")

            self.last_result = result
            self.display_results(result)

        except Exception as e:
            self.logger.error(f"Calculation failed: {e}")
            self.last_error = str(e)
            self.display_error(str(e))

        finally:
            self.complete_calculation()

    def calculate_threshold(self) -> Optional[Dict[str, Any]]:
        """Calculate GTO threshold."""
        self.update_progress(0.1)

        result = self.optimizer.find_gto_threshold(
            num_opponents=self.num_opponents,
            pot_size=self.pot_size,
            bet_amount=self.bet_amount,
            num_simulations=1000
        )

        self.update_progress(1.0)
        return result

    def calculate_range_vs_range(self) -> Optional[Dict[str, Any]]:
        """Calculate range vs range Nash equilibrium."""
        if not self.hero_range or not self.villain_range:
            raise ValueError("Both hero and villain ranges must be loaded")

        self.update_progress(0.1)

        result = self.optimizer.find_nash_equilibrium(
            hero_range=self.hero_range,
            villain_range=self.villain_range,
            pot_size=self.pot_size,
            bet_amount=self.bet_amount,
            num_simulations=500
        )

        self.update_progress(1.0)
        return result

    def calculate_indifference_points(self) -> Optional[Dict[str, Any]]:
        """Calculate indifference points."""
        if not self.hero_range or not self.villain_range:
            raise ValueError("Both hero and villain ranges must be loaded")

        self.update_progress(0.1)

        result = self.optimizer.find_indifference_points(
            hero_range=self.hero_range,
            villain_range=self.villain_range,
            pot_size=self.pot_size,
            bet_amount=self.bet_amount
        )

        self.update_progress(1.0)
        return result

    def start_calculation(self):
        """Start calculation process."""
        self.is_calculating = True
        self.progress = 0.0

    def update_progress(self, progress: float):
        """Update calculation progress."""
        self.progress = max(0.0, min(1.0, progress))

    def complete_calculation(self):
        """Complete calculation process."""
        self.is_calculating = False
        self.progress = 1.0

    def display_results(self, result: Dict[str, Any]):
        """Display calculation results."""
        if self.current_mode == 'threshold':
            self.results_text = self.format_threshold_results(result)
        elif self.current_mode == 'range_vs_range':
            self.results_text = self.format_range_vs_range_results(result)
        elif self.current_mode == 'indifference':
            self.results_text = self.format_indifference_results(result)
        else:
            self.results_text = f"Unknown mode: {self.current_mode}"

    def display_error(self, error: str):
        """Display error message."""
        self.results_text = f"Error: {error}"

    def format_threshold_results(self, result: Dict[str, Any]) -> str:
        """Format threshold calculation results for display."""
        text = "GTO Threshold Results\n\n"
        threshold_equity = result.get('threshold_equity', 'N/A')
        if isinstance(threshold_equity, (int, float)):
            text += f"Threshold Equity: {threshold_equity:.3f}\n"
        else:
            text += f"Threshold Equity: {threshold_equity}\n"

        bonus_adjusted = result.get('bonus_adjusted_threshold', 'N/A')
        if isinstance(bonus_adjusted, (int, float)):
            text += f"Bonus Adjusted Threshold: {bonus_adjusted:.3f}\n\n"
        else:
            text += f"Bonus Adjusted Threshold: {bonus_adjusted}\n\n"

        optimal_range = result.get('optimal_range', [])
        if optimal_range:
            text += f"Optimal Range ({len(optimal_range)} hands):\n"
            text += ", ".join(optimal_range[:10])  # Show first 10
            if len(optimal_range) > 10:
                text += f"... (+{len(optimal_range) - 10} more)"
            text += "\n\n"

        ev_breakdown = result.get('ev_breakdown', {})
        if ev_breakdown:
            text += "EV Breakdown (top 5):\n"
            sorted_ev = sorted(ev_breakdown.items(), key=lambda x: x[1], reverse=True)
            for hand, ev in sorted_ev[:5]:
                text += f"{hand}: {ev:.2f}\n"

        return text

    def format_range_vs_range_results(self, result: Dict[str, Any]) -> str:
        """Format range vs range results for display."""
        text = "Range vs Range Results\n\n"

        if result.get('equilibrium_found'):
            text += "Nash Equilibrium Found\n"
        else:
            text += "Equilibrium Not Found\n"

        text += f"Iterations: {result.get('iterations', 'N/A')}\n"
        text += f"Convergence Tolerance: {result.get('convergence_tolerance', 'N/A')}\n\n"

        hero_strategy = result.get('hero_strategy', [])
        if hero_strategy:
            text += f"Hero Strategy ({len(hero_strategy)} hands):\n"
            for i, freq in enumerate(hero_strategy[:10]):
                hand = self.hero_range[i] if i < len(self.hero_range) else f'Hand {i}'
                text += f"{hand}: {freq:.2f}\n"

        villain_strategy = result.get('villain_strategy', [])
        if villain_strategy:
            text += f"\nVillain Strategy ({len(villain_strategy)} hands):\n"
            for i, freq in enumerate(villain_strategy[:10]):
                hand = self.villain_range[i] if i < len(self.villain_range) else f'Hand {i}'
                text += f"{hand}: {freq:.2f}\n"

        return text

    def format_indifference_results(self, result: Dict[str, Any]) -> str:
        """Format indifference point results for display."""
        text = "Indifference Points Results\n\n"

        optimal_frequencies = result.get('optimal_frequencies', [])
        if optimal_frequencies:
            text += "Optimal Shove Frequencies:\n"
            for i, freq in enumerate(optimal_frequencies):
                hand = self.hero_range[i] if i < len(self.hero_range) else f'Hand {i}'
                status = "SHOVE" if freq > 0.5 else "FOLD" if freq < 0.1 else "MIXED"
                text += f"{hand}: {freq:.2f} ({status})\n"

        indifference_points = result.get('indifference_points', {})
        if indifference_points:
            text += "\nIndifference Details:\n"
            for hand, data in list(indifference_points.items())[:5]:
                equity = data.get('equity_vs_calling', 0)
                freq = data.get('indifference_frequency', 0)
                text += f"{hand}: Equity={equity:.3f}, Frequency={freq:.2f}\n"

        return text

    def can_calculate_current_mode(self) -> bool:
        """Check if current mode can be calculated."""
        if self.current_mode == 'threshold':
            return True
        elif self.current_mode in ['range_vs_range', 'indifference']:
            return bool(self.hero_range and self.villain_range)
        return False

    def clear_error(self):
        """Clear last error."""
        self.last_error = None

    def export_results(self, filepath: str) -> bool:
        """Export results to YAML file."""
        if not self.last_result:
            return False

        try:
            export_data = {
                'mode': self.current_mode,
                'parameters': {
                    'num_opponents': self.num_opponents,
                    'pot_size': self.pot_size,
                    'bet_amount': self.bet_amount,
                    'hero_range_size': len(self.hero_range),
                    'villain_range_size': len(self.villain_range)
                },
                'results': self.last_result
            }

            with open(filepath, 'w') as f:
                yaml.dump(export_data, f, default_flow_style=False)

            self.logger.info(f"Results exported to {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export results: {e}")
            self.last_error = f"Export failed: {e}"
            return False

    def handle_event(self, event) -> Optional[str]:
        """Handle pygame events."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos

            # Check mode buttons
            for mode_key, (rect, _) in self.mode_buttons_rects.items():
                if rect.collidepoint(mouse_pos):
                    self.set_mode(mode_key)
                    return f'mode_{mode_key}'

            # Check calculate button
            if self.calculate_button_rect.collidepoint(mouse_pos):
                if self.can_calculate_current_mode():
                    self.calculate_current_mode()
                else:
                    self.display_error("Cannot calculate: missing required ranges")
                return 'calculate'

            # Check browse buttons
            if self.hero_browse_rect.collidepoint(mouse_pos):
                self.logger.info("Hero range browse clicked")
                return 'browse_hero'

            if self.villain_browse_rect.collidepoint(mouse_pos):
                self.logger.info("Villain range browse clicked")
                return 'browse_villain'

            # Check input fields
            if self.opponents_rect.collidepoint(mouse_pos):
                self.active_input = 'opponents'
            elif self.pot_rect.collidepoint(mouse_pos):
                self.active_input = 'pot'
            elif self.bet_rect.collidepoint(mouse_pos):
                self.active_input = 'bet'
            elif self.hero_range_rect.collidepoint(mouse_pos):
                self.active_input = 'hero_range'
            elif self.villain_range_rect.collidepoint(mouse_pos):
                self.active_input = 'villain_range'
            else:
                self.active_input = None

        elif event.type == pygame.KEYDOWN and self.active_input:
            if event.key == pygame.K_RETURN:
                self._apply_input_value()
                self.active_input = None
            elif event.key == pygame.K_BACKSPACE:
                self._backspace_input()
            else:
                self._add_input_char(event.unicode)

        return None

    def _apply_input_value(self):
        """Apply the current input value."""
        if self.active_input == 'opponents':
            try:
                val = int(self.opponents_text)
                if not self.set_num_opponents(val):
                    self.opponents_text = str(self.num_opponents)
            except ValueError:
                self.opponents_text = str(self.num_opponents)
        elif self.active_input == 'pot':
            try:
                val = float(self.pot_text)
                if not self.set_pot_size(val):
                    self.pot_text = str(self.pot_size)
            except ValueError:
                self.pot_text = str(self.pot_size)
        elif self.active_input == 'bet':
            try:
                val = float(self.bet_text)
                if not self.set_bet_amount(val):
                    self.bet_text = str(self.bet_amount)
            except ValueError:
                self.bet_text = str(self.bet_amount)

    def _backspace_input(self):
        """Handle backspace in input field."""
        if self.active_input == 'opponents':
            self.opponents_text = self.opponents_text[:-1]
        elif self.active_input == 'pot':
            self.pot_text = self.pot_text[:-1]
        elif self.active_input == 'bet':
            self.bet_text = self.bet_text[:-1]
        elif self.active_input == 'hero_range':
            self.hero_range_text = self.hero_range_text[:-1]
        elif self.active_input == 'villain_range':
            self.villain_range_text = self.villain_range_text[:-1]

    def _add_input_char(self, char: str):
        """Add character to input field."""
        if self.active_input == 'opponents':
            if char.isdigit():
                self.opponents_text += char
        elif self.active_input in ['pot', 'bet']:
            if char.isdigit() or char == '.':
                current = self.pot_text if self.active_input == 'pot' else self.bet_text
                if char != '.' or '.' not in current:
                    if self.active_input == 'pot':
                        self.pot_text += char
                    else:
                        self.bet_text += char
        elif self.active_input in ['hero_range', 'villain_range']:
            self.hero_range_text += char if self.active_input == 'hero_range' else char
            if self.active_input == 'villain_range':
                self.villain_range_text += char

    def update(self, time_delta: float):
        """Update UI elements."""
        pass  # No animation needed for basic pygame

    def draw(self, surface: pygame.Surface):
        """Draw the panel."""
        # Clear surface
        self.surface.fill(self.BG_COLOR)

        # Draw title
        title = self.title_font.render("GTO Solver", True, self.TEXT_COLOR)
        self.surface.blit(title, (10, 10))

        # Draw mode buttons
        mouse_pos = pygame.mouse.get_pos()
        for mode_key, (rect, label) in self.mode_buttons_rects.items():
            color = self.BUTTON_HOVER_COLOR if rect.collidepoint(mouse_pos) else self.BUTTON_COLOR
            if self.current_mode == mode_key:
                color = self.SUCCESS_COLOR
            pygame.draw.rect(self.surface, color, rect)
            pygame.draw.rect(self.surface, self.BORDER_COLOR, rect, 1)
            text = self.font.render(label, True, self.TEXT_COLOR)
            text_rect = text.get_rect(center=rect.center)
            self.surface.blit(text, text_rect)

        # Draw parameter labels and inputs
        self._draw_parameters()

        # Draw range inputs
        self._draw_ranges()

        # Draw calculate button
        calc_color = self.BUTTON_HOVER_COLOR if self.calculate_button_rect.collidepoint(mouse_pos) else self.BUTTON_COLOR
        if not self.can_calculate_current_mode():
            calc_color = self.BORDER_COLOR
        pygame.draw.rect(self.surface, calc_color, self.calculate_button_rect)
        pygame.draw.rect(self.surface, self.BORDER_COLOR, self.calculate_button_rect, 1)
        calc_text = self.font.render("Calculate", True, self.TEXT_COLOR)
        calc_text_rect = calc_text.get_rect(center=self.calculate_button_rect.center)
        self.surface.blit(calc_text, calc_text_rect)

        # Draw progress bar if calculating
        if self.is_calculating:
            progress_rect = pygame.Rect(170, 200, 300, 40)
            pygame.draw.rect(self.surface, self.BORDER_COLOR, progress_rect, 1)
            fill_rect = pygame.Rect(170, 200, int(300 * self.progress), 40)
            pygame.draw.rect(self.surface, self.SUCCESS_COLOR, fill_rect)

        # Draw results
        self._draw_results()

        # Blit to target surface
        surface.blit(self.surface, (0, 0))

    def _draw_parameters(self):
        """Draw parameter inputs."""
        # Labels
        labels = ["Opponents:", "Pot Size:", "Bet Amount:"]
        for i, label in enumerate(labels):
            text = self.font.render(label, True, self.TEXT_COLOR)
            self.surface.blit(text, (10, 50 + i * 30))

        # Input boxes
        inputs = [
            (self.opponents_rect, self.opponents_text),
            (self.pot_rect, self.pot_text),
            (self.bet_rect, self.bet_text)
        ]

        for rect, text in inputs:
            pygame.draw.rect(self.surface, (255, 255, 255), rect)
            pygame.draw.rect(self.surface, self.BORDER_COLOR, rect, 1)
            input_text = self.font.render(text, True, self.TEXT_COLOR)
            self.surface.blit(input_text, (rect.x + 5, rect.y + 5))

    def _draw_ranges(self):
        """Draw range inputs."""
        # Labels
        hero_label = self.font.render("Hero Range:", True, self.TEXT_COLOR)
        self.surface.blit(hero_label, (200, 50))

        villain_label = self.font.render("Villain Range:", True, self.TEXT_COLOR)
        self.surface.blit(villain_label, (200, 80))

        # Input boxes
        pygame.draw.rect(self.surface, (255, 255, 255), self.hero_range_rect)
        pygame.draw.rect(self.surface, self.BORDER_COLOR, self.hero_range_rect, 1)
        hero_text = self.font.render(self.hero_range_text[-20:], True, self.TEXT_COLOR)  # Show last 20 chars
        self.surface.blit(hero_text, (self.hero_range_rect.x + 5, self.hero_range_rect.y + 5))

        pygame.draw.rect(self.surface, (255, 255, 255), self.villain_range_rect)
        pygame.draw.rect(self.surface, self.BORDER_COLOR, self.villain_range_rect, 1)
        villain_text = self.font.render(self.villain_range_text[-20:], True, self.TEXT_COLOR)
        self.surface.blit(villain_text, (self.villain_range_rect.x + 5, self.villain_range_rect.y + 5))

        # Browse buttons
        mouse_pos = pygame.mouse.get_pos()
        for rect, label in [(self.hero_browse_rect, "Browse"), (self.villain_browse_rect, "Browse")]:
            color = self.BUTTON_HOVER_COLOR if rect.collidepoint(mouse_pos) else self.BUTTON_COLOR
            pygame.draw.rect(self.surface, color, rect)
            pygame.draw.rect(self.surface, self.BORDER_COLOR, rect, 1)
            text = self.font.render(label, True, self.TEXT_COLOR)
            text_rect = text.get_rect(center=rect.center)
            self.surface.blit(text, text_rect)

    def _draw_results(self):
        """Draw results area."""
        pygame.draw.rect(self.surface, (255, 255, 255), self.results_rect)
        pygame.draw.rect(self.surface, self.BORDER_COLOR, self.results_rect, 1)

        if hasattr(self, 'results_text'):
            lines = self.results_text.split('\n')
            y_offset = self.results_rect.y + 10
            for line in lines[:20]:  # Limit to 20 lines
                if y_offset > self.results_rect.bottom - 20:
                    break
                text = self.font.render(line, True, self.TEXT_COLOR)
                self.surface.blit(text, (self.results_rect.x + 10, y_offset))
                y_offset += 20