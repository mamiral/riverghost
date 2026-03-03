"""
Strategy Visualizer GUI Component

Displays GTO results with color-coded hand grid and EV breakdowns.
Shows which hands should be played vs folded based on calculated thresholds.
"""

import pygame
from typing import Optional, Dict, List, Tuple, Any
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class StrategyVisualizer:
    """
    GUI component for visualizing GTO strategy results.

    Displays a color-coded grid of poker hands showing which ones should be
    played (green) vs folded (red) based on GTO threshold calculations.
    """

    def __init__(self, screen: pygame.Surface, x: int = 50, y: int = 50, width: int = 700, height: int = 600):
        self.screen = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # Fonts
        self.title_font = pygame.font.SysFont("arial", 24, bold=True)
        self.label_font = pygame.font.SysFont("arial", 16)
        self.small_font = pygame.font.SysFont("arial", 12)

        # Colors
        self.BG_COLOR = (40, 40, 40)
        self.BORDER_COLOR = (200, 200, 200)
        self.TEXT_COLOR = (255, 255, 255)
        self.GREEN_PLAY = (0, 180, 0)      # Profitable hands
        self.RED_FOLD = (180, 0, 0)        # Unprofitable hands
        self.YELLOW_BORDER = (255, 255, 0) # Selected hand
        self.BLUE_INFO = (0, 120, 200)     # Info panels

        # Hand grid layout
        self.grid_x = self.x + 20
        self.grid_y = self.y + 80
        self.cell_size = 35
        self.cell_margin = 2

        # Results data
        self.gto_results: Optional[Dict[str, Any]] = None
        self.selected_hand: Optional[str] = None
        self.selected_hand_info: Optional[Dict[str, Any]] = None

        # Scroll position for large grids
        self.scroll_y = 0
        self.max_scroll = 0

        logger.info("StrategyVisualizer initialized")

    def set_results(self, gto_results: Dict[str, Any]) -> None:
        """
        Set GTO calculation results to display.

        Args:
            gto_results: Results from AllInFoldGTOSolver.find_gto_threshold()
        """
        self.gto_results = gto_results
        self.selected_hand = None
        self.selected_hand_info = None
        self.scroll_y = 0

        # Calculate max scroll based on results
        if 'optimal_range' in gto_results:
            self.max_scroll = max(0, len(gto_results['optimal_range']) * (self.cell_size + self.cell_margin) - (self.height - 150))

        logger.info(f"StrategyVisualizer results set: {len(gto_results.get('optimal_range', []))} optimal hands")

    def draw(self) -> None:
        """Draw the strategy visualizer."""
        if not self.gto_results:
            self._draw_empty_state()
            return

        # Main panel background
        pygame.draw.rect(self.screen, self.BG_COLOR, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, self.BORDER_COLOR, (self.x, self.y, self.width, self.height), 2)

        # Title
        title = self.title_font.render("GTO Strategy Visualization", True, self.TEXT_COLOR)
        self.screen.blit(title, (self.x + 20, self.y + 10))

        # Summary stats
        self._draw_summary_stats()

        # Hand grid
        self._draw_hand_grid()

        # Selected hand details
        if self.selected_hand_info:
            self._draw_hand_details()

    def _draw_empty_state(self) -> None:
        """Draw empty state when no results are available."""
        pygame.draw.rect(self.screen, self.BG_COLOR, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, self.BORDER_COLOR, (self.x, self.y, self.width, self.height), 2)

        title = self.title_font.render("GTO Strategy Visualization", True, self.TEXT_COLOR)
        self.screen.blit(title, (self.x + 20, self.y + 10))

        no_data = self.label_font.render("No GTO results to display", True, (150, 150, 150))
        self.screen.blit(no_data, (self.x + 20, self.y + 100))

        instructions = self.small_font.render("Run GTO analysis to see strategy visualization", True, (150, 150, 150))
        self.screen.blit(instructions, (self.x + 20, self.y + 130))

    def _draw_summary_stats(self) -> None:
        """Draw summary statistics from GTO results."""
        if not self.gto_results:
            return

        stats_y = self.y + 40

        # Threshold equity
        threshold = self.gto_results.get('threshold_equity', 0.0)
        threshold_text = f"Equity Threshold: {threshold:.3f}"
        threshold_render = self.label_font.render(threshold_text, True, self.TEXT_COLOR)
        self.screen.blit(threshold_render, (self.x + 20, stats_y))

        # Optimal hands count
        optimal_count = self.gto_results.get('optimal_hands', 0)
        total_count = self.gto_results.get('total_hands', 0)
        hands_text = f"Optimal Hands: {optimal_count}/{total_count}"
        hands_render = self.label_font.render(hands_text, True, self.TEXT_COLOR)
        self.screen.blit(hands_render, (self.x + 250, stats_y))

        # Bonus payouts info
        if 'bonus_payouts' in self.gto_results:
            bonus_text = "Bonus Payouts: Active"
            bonus_render = self.label_font.render(bonus_text, True, (0, 255, 0))
            self.screen.blit(bonus_render, (self.x + 450, stats_y))

    def _draw_hand_grid(self) -> None:
        """Draw the color-coded hand grid."""
        if not self.gto_results or 'optimal_range' not in self.gto_results:
            return

        optimal_hands = set(self.gto_results['optimal_range'])
        top_hands = self.gto_results.get('top_10_hands', [])

        # Define hand ranks (simplified for display)
        ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

        # Draw grid headers
        for i, rank1 in enumerate(ranks):
            x = self.grid_x + i * (self.cell_size + self.cell_margin)
            y = self.grid_y - 25

            # Row header (vertical)
            header_render = self.small_font.render(rank1, True, self.TEXT_COLOR)
            self.screen.blit(header_render, (x + self.cell_size//2 - 5, y))

        for i, rank2 in enumerate(ranks):
            x = self.grid_x - 25
            y = self.grid_y + i * (self.cell_size + self.cell_margin)

            # Column header (horizontal)
            header_render = self.small_font.render(rank2, True, self.TEXT_COLOR)
            self.screen.blit(header_render, (x, y + self.cell_size//2 - 5))

        # Draw hand cells
        for i, rank1 in enumerate(ranks):
            for j, rank2 in enumerate(ranks):
                x = self.grid_x + i * (self.cell_size + self.cell_margin)
                y = self.grid_y + j * (self.cell_size + self.cell_margin) - self.scroll_y

                # Skip if scrolled out of view
                if y < self.grid_y - self.cell_size or y > self.y + self.height - 50:
                    continue

                # Determine hand type
                if rank1 == rank2:
                    hand = f"{rank1}{rank2}"  # Pocket pair
                elif i < j:  # Suited (arbitrary ordering)
                    hand = f"{rank1}{rank2}s"
                else:  # Offsuit
                    hand = f"{rank1}{rank2}o"

                # Determine color
                if hand in optimal_hands:
                    color = self.GREEN_PLAY
                else:
                    color = self.RED_FOLD

                # Selected hand highlight
                if self.selected_hand == hand:
                    pygame.draw.rect(self.screen, self.YELLOW_BORDER, (x-2, y-2, self.cell_size+4, self.cell_size+4), 3)

                # Draw cell
                pygame.draw.rect(self.screen, color, (x, y, self.cell_size, self.cell_size))

                # Hand text
                text_render = self.small_font.render(hand, True, self.TEXT_COLOR)
                text_x = x + self.cell_size//2 - text_render.get_width()//2
                text_y = y + self.cell_size//2 - text_render.get_height()//2
                self.screen.blit(text_render, (text_x, text_y))

    def _draw_hand_details(self) -> None:
        """Draw detailed information for selected hand."""
        if not self.selected_hand_info:
            return

        # Info panel
        panel_x = self.x + self.width - 250
        panel_y = self.y + 80
        panel_width = 230
        panel_height = 200

        pygame.draw.rect(self.screen, self.BLUE_INFO, (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, self.BORDER_COLOR, (panel_x, panel_y, panel_width, panel_height), 2)

        # Hand name
        hand_name = self.selected_hand_info.get('hand', 'Unknown')
        name_render = self.label_font.render(f"Hand: {hand_name}", True, self.TEXT_COLOR)
        self.screen.blit(name_render, (panel_x + 10, panel_y + 10))

        # Equity
        equity = self.selected_hand_info.get('equity', 0.0)
        equity_render = self.label_font.render(f"Equity: {equity:.3f}", True, self.TEXT_COLOR)
        self.screen.blit(equity_render, (panel_x + 10, panel_y + 35))

        # EV
        ev = self.selected_hand_info.get('ev', 0.0)
        ev_color = self.GREEN_PLAY if ev > 0 else self.RED_FOLD
        ev_render = self.label_font.render(f"EV: {ev:.3f}", True, ev_color)
        self.screen.blit(ev_render, (panel_x + 10, panel_y + 60))

        # Strategy recommendation
        if ev > 0:
            strategy = "PLAY (Profitable)"
            strategy_color = self.GREEN_PLAY
        else:
            strategy = "FOLD (Unprofitable)"
            strategy_color = self.RED_FOLD

        strategy_render = self.label_font.render(strategy, True, strategy_color)
        self.screen.blit(strategy_render, (panel_x + 10, panel_y + 85))

        # Bonus payout info if applicable
        if 'bonus_multiplier' in self.selected_hand_info:
            bonus = self.selected_hand_info['bonus_multiplier']
            bonus_render = self.label_font.render(f"Bonus: {bonus}x", True, (255, 255, 0))
            self.screen.blit(bonus_render, (panel_x + 10, panel_y + 110))

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """
        Handle pygame events for the visualizer.

        Args:
            event: Pygame event

        Returns:
            Action string if event handled, None otherwise
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos

            # Check if click is in grid area
            if (self.grid_x <= mouse_x <= self.grid_x + 13 * (self.cell_size + self.cell_margin) and
                self.grid_y <= mouse_y <= self.grid_y + 13 * (self.cell_size + self.cell_margin)):

                # Calculate which cell was clicked
                grid_x = (mouse_x - self.grid_x) // (self.cell_size + self.cell_margin)
                grid_y = (mouse_y - self.grid_y + self.scroll_y) // (self.cell_size + self.cell_margin)

                if 0 <= grid_x < 13 and 0 <= grid_y < 13:
                    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
                    rank1 = ranks[grid_x]
                    rank2 = ranks[grid_y]

                    if rank1 == rank2:
                        hand = f"{rank1}{rank2}"
                    elif grid_x < grid_y:
                        hand = f"{rank1}{rank2}s"
                    else:
                        hand = f"{rank1}{rank2}o"

                    self._select_hand(hand)
                    return f"hand_selected:{hand}"

        elif event.type == pygame.MOUSEWHEEL:
            # Handle scrolling
            self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - event.y * 20))

        return None

    def _select_hand(self, hand: str) -> None:
        """
        Select a hand and prepare its detailed information.

        Args:
            hand: Hand shorthand (e.g., "AKs", "22")
        """
        self.selected_hand = hand

        # Find hand information from results
        if self.gto_results and 'top_10_hands' in self.gto_results:
            for hand_info in self.gto_results['top_10_hands']:
                if hand_info.get('shorthand') == hand:
                    self.selected_hand_info = hand_info
                    return

        # If not in top 10, create basic info
        self.selected_hand_info = {
            'hand': hand,
            'equity': 0.0,  # Unknown
            'ev': 0.0,      # Unknown
        }

    def export_results(self, filename: str) -> bool:
        """
        Export current results to a file.

        Args:
            filename: Export filename

        Returns:
            True if successful, False otherwise
        """
        if not self.gto_results:
            return False

        try:
            import json
            with open(filename, 'w') as f:
                json.dump(self.gto_results, f, indent=2, default=str)
            logger.info(f"Results exported to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to export results: {e}")
            return False