import pygame
from typing import Optional, Callable

from hopilot.logging_config import get_logger
from hopilot.hand_range import split_range_to_components

logger = get_logger(__name__)


class RangePicker:
    """
    Dialog for selecting poker hand ranges using a matrix interface.
    Shows a grid of hand combinations with suited/offsuit options.
    """

    def __init__(self, screen: pygame.Surface, on_select: Callable[[str], None], on_cancel: Callable[[], None], initial_range: Optional[str] = None, on_switch_to_cards: Optional[Callable[[], None]] = None):
        self.screen = screen
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.on_switch_to_cards = on_switch_to_cards
        self.width = 700
        self.height = 620  # Increased height to accommodate larger cells
        self.x = (screen.get_width() - self.width) // 2
        self.y = (screen.get_height() - self.height) // 2
        self.font = pygame.font.SysFont("arial", 14, bold=True)
        self.small_font = pygame.font.SysFont("arial", 10)

        # Ranks for the matrix (Ace to 2)
        self.ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

        # Selected ranges (for highlighting)
        self.selected_ranges = set()
        
        # Initialize with current range if provided
        if initial_range:
            self.selected_ranges = split_range_to_components(initial_range)

    def draw(self):
        """Draw the range picker dialog."""
        # Draw semi-transparent background
        background = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        background.set_alpha(128)
        background.fill((0, 0, 0))
        self.screen.blit(background, (0, 0))

        # Draw background
        pygame.draw.rect(self.screen, (200, 200, 200), (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, (0, 0, 0), (self.x, self.y, self.width, self.height), 2)

        # Title
        title = self.font.render("Select Hand Range", True, (0, 0, 0))
        self.screen.blit(title, (self.x + 20, self.y + 20))

        # Instructions
        instr1 = self.small_font.render("Click cells to select/deselect ranges", True, (100, 100, 100))
        instr2 = self.small_font.render("Selected ranges are highlighted", True, (100, 100, 100))
        self.screen.blit(instr1, (self.x + 20, self.y + 45))
        self.screen.blit(instr2, (self.x + 20, self.y + 60))

        # OK, Cancel, and Select Cards buttons
        select_cards_button_rect = (self.x + self.width - 270, self.y + self.height - 50, 100, 30)
        ok_button_rect = (self.x + self.width - 160, self.y + self.height - 50, 70, 30)
        cancel_button_rect = (self.x + self.width - 80, self.y + self.height - 50, 70, 30)

        if self.on_switch_to_cards:
            pygame.draw.rect(self.screen, (0, 0, 255), select_cards_button_rect)
            cards_text = self.font.render("Cards", True, (255, 255, 255))
            self.screen.blit(cards_text, (select_cards_button_rect[0] + 10, select_cards_button_rect[1] + 5))

        pygame.draw.rect(self.screen, (0, 255, 0), ok_button_rect)
        pygame.draw.rect(self.screen, (255, 0, 0), cancel_button_rect)

        ok_text = self.font.render("OK", True, (255, 255, 255))
        cancel_text = self.font.render("Cancel", True, (255, 255, 255))
        self.screen.blit(ok_text, (ok_button_rect[0] + 20, ok_button_rect[1] + 5))
        self.screen.blit(cancel_text, (cancel_button_rect[0] + 10, cancel_button_rect[1] + 5))

        # Draw the range matrix
        self._draw_matrix()

    def _draw_matrix(self):
        """Draw the poker range matrix."""
        cell_size = 35  # Increased cell size to fit full text
        start_x = self.x + 30  # Adjusted start position
        start_y = self.y + 85  # Adjusted to better fit the taller dialog

        # Draw cells
        for row, rank1 in enumerate(self.ranks):
            for col, rank2 in enumerate(self.ranks):
                cell_x = start_x + col * (cell_size + 2)
                cell_y = start_y + row * (cell_size + 2)

                # Determine range string and display text
                if row == col:
                    # Pocket pairs
                    range_str = f"{rank1}{rank2}"
                    display_text = f"{rank1}{rank2}"
                    base_color = (100, 100, 255)
                    selected_color = (0, 0, 255)
                    text_color = (255, 255, 255)
                elif row < col:
                    # Upper triangle - suited hands (higher rank first)
                    range_str = f"{rank1}{rank2}s"
                    display_text = f"{rank1}{rank2}s"
                    base_color = (100, 255, 100)
                    selected_color = (0, 255, 0)
                    text_color = (0, 0, 0)
                else:
                    # Lower triangle - offsuit hands (higher rank first)
                    range_str = f"{rank2}{rank1}o"
                    display_text = f"{rank2}{rank1}o"
                    base_color = (255, 100, 100)
                    selected_color = (255, 0, 0)
                    text_color = (255, 255, 255)

                # Determine colors
                is_selected = range_str in self.selected_ranges
                cell_color = selected_color if is_selected else base_color
                border_color = (255, 255, 0) if is_selected else (0, 0, 0)  # Yellow border for selected
                border_width = 3 if is_selected else 1

                # Draw cell
                pygame.draw.rect(self.screen, cell_color, (cell_x, cell_y, cell_size, cell_size))
                pygame.draw.rect(self.screen, border_color, (cell_x, cell_y, cell_size, cell_size), border_width)

                # Draw range text
                text = self.small_font.render(display_text, True, text_color)
                text_rect = text.get_rect(center=(cell_x + cell_size // 2, cell_y + cell_size // 2))
                self.screen.blit(text, text_rect)

    def handle_event(self, event) -> bool:
        """Handle events in the range picker."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos

            # Check Select Cards button
            if self.on_switch_to_cards:
                select_cards_button_rect = (self.x + self.width - 270, self.y + self.height - 50, 100, 30)
                if (select_cards_button_rect[0] <= mouse_x <= select_cards_button_rect[0] + select_cards_button_rect[2] and
                    select_cards_button_rect[1] <= mouse_y <= select_cards_button_rect[1] + select_cards_button_rect[3]):
                    self.on_switch_to_cards()
                    return True

            # Check OK button
            ok_button_rect = (self.x + self.width - 160, self.y + self.height - 50, 70, 30)
            if (ok_button_rect[0] <= mouse_x <= ok_button_rect[0] + ok_button_rect[2] and
                ok_button_rect[1] <= mouse_y <= ok_button_rect[1] + ok_button_rect[3]):
                # Convert selected ranges to a combined range string
                if self.selected_ranges:
                    combined_range = "+".join(sorted(self.selected_ranges))
                    self.on_select(combined_range)
                else:
                    # No ranges selected - clear the range (go back to random)
                    self.on_select("")
                return True

            # Check Cancel button
            cancel_button_rect = (self.x + self.width - 80, self.y + self.height - 50, 70, 30)
            if (cancel_button_rect[0] <= mouse_x <= cancel_button_rect[0] + cancel_button_rect[2] and
                cancel_button_rect[1] <= mouse_y <= cancel_button_rect[1] + cancel_button_rect[3]):
                self.on_cancel()
                return True

            # Check matrix cells
            cell_size = 35  # Updated to match draw method
            start_x = self.x + 30  # Updated to match draw method
            start_y = self.y + 85  # Updated to match draw method

            for row, rank1 in enumerate(self.ranks):
                for col, rank2 in enumerate(self.ranks):
                    cell_x = start_x + col * (cell_size + 2)
                    cell_y = start_y + row * (cell_size + 2)

                    if (cell_x <= mouse_x <= cell_x + cell_size and
                        cell_y <= mouse_y <= cell_y + cell_size):

                        # Determine range string
                        if row == col:
                            range_str = f"{rank1}{rank2}"
                        elif row < col:
                            range_str = f"{rank1}{rank2}s"
                        else:
                            range_str = f"{rank2}{rank1}o"

                        # Toggle selection
                        if range_str in self.selected_ranges:
                            self.selected_ranges.remove(range_str)
                        else:
                            self.selected_ranges.add(range_str)
                        return True

            # Click outside to cancel
            if not (self.x <= mouse_x <= self.x + self.width and
                    self.y <= mouse_y <= self.y + self.height):
                self.on_cancel()
                return True

        return False