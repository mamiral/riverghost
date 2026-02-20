import pygame
from typing import Optional, Callable


class CardPicker:
    """
    Dialog for selecting a specific card from the deck.
    Shows all available cards and allows selection.
    """

    def __init__(self, screen: pygame.Surface, on_select: Callable[[Optional[str]], None], on_random: Callable[[], None], on_cancel: Callable[[], None], on_select_range: Callable[[], None], assigned_cards: set, current_card: Optional[str] = None):
        self.screen = screen
        self.on_select = on_select
        self.on_random = on_random
        self.on_cancel = on_cancel
        self.on_select_range = on_select_range
        self.assigned_cards = assigned_cards  # Set of already assigned card names
        self.current_card = current_card  # Currently selected card for this position
        self.width = 600
        self.height = 400
        self.x = (screen.get_width() - self.width) // 2
        self.y = (screen.get_height() - self.height) // 2
        # Use Arial for better crispness and readability
        self.font = pygame.font.SysFont("arial", 16, bold=True)

        # Card ranks and suits
        self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        self.suits = ['s', 'h', 'd', 'c']  # Spades, hearts, diamonds, clubs
        # Use letter representations instead of symbols
        self.suit_letters = {'s': 's', 'h': 'h', 'd': 'd', 'c': 'c'}
        # Color backgrounds by suit with white text
        self.suit_bg_colors = {'s': (0, 0, 0), 'h': (255, 0, 0), 'd': (0, 0, 255), 'c': (0, 128, 0)}

    def draw(self):
        """Draw the card picker dialog."""
        # Draw semi-transparent background
        background = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        background.set_alpha(128)
        background.fill((0, 0, 0))
        self.screen.blit(background, (0, 0))
        
        # Draw background
        pygame.draw.rect(self.screen, (200, 200, 200), (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, (0, 0, 0), (self.x, self.y, self.width, self.height), 2)

        # Title
        title = self.font.render("Select Card (or Random)", True, (0, 0, 0))
        self.screen.blit(title, (self.x + 20, self.y + 20))

        # Random button
        pygame.draw.rect(self.screen, (100, 100, 100), (self.x + 20, self.y + 50, 100, 30))
        random_text = self.font.render("Random", True, (255, 255, 255))
        self.screen.blit(random_text, (self.x + 30, self.y + 55))

        # Select Range button
        pygame.draw.rect(self.screen, (0, 0, 255), (self.x + 140, self.y + 50, 120, 30))
        range_text = self.font.render("Select Range", True, (255, 255, 255))
        self.screen.blit(range_text, (self.x + 150, self.y + 55))

        # Draw cards grid
        card_size = 40
        cols = 13
        rows = 4
        start_x = self.x + 20
        start_y = self.y + 100

        for row, suit in enumerate(self.suits):
            for col, rank in enumerate(self.ranks):
                card_name = f"{rank}{suit}"
                card_x = start_x + col * (card_size + 5)
                card_y = start_y + row * (card_size + 5)

                # Check card status
                if card_name == self.current_card:
                    color = self.suit_bg_colors[suit]  # Normal suit color
                    border_color = (255, 255, 0)  # Yellow border for current card
                    border_width = 3
                    text_color = (255, 255, 255)  # White text
                elif card_name in self.assigned_cards:
                    color = (128, 128, 128)  # Gray out assigned cards
                    border_color = (0, 0, 0)
                    border_width = 1
                    text_color = (255, 255, 255)  # White text for gray cards
                else:
                    color = self.suit_bg_colors[suit]  # Suit-colored background for available cards
                    border_color = (0, 0, 0)
                    border_width = 1
                    text_color = (255, 255, 255)  # White text

                pygame.draw.rect(self.screen, color, (card_x, card_y, card_size, card_size))
                pygame.draw.rect(self.screen, border_color, (card_x, card_y, card_size, card_size), border_width)

                # Draw rank and suit together
                card_text = self.font.render(card_name, True, text_color)
                self.screen.blit(card_text, (card_x + 2, card_y + 2))

    def handle_event(self, event) -> bool:
        """Handle events in the card picker."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos

            # Check random button
            if (self.x + 20 <= mouse_x <= self.x + 120 and
                self.y + 50 <= mouse_y <= self.y + 80):
                self.on_random()  # Random
                return True

            # Check select range button
            if (self.x + 140 <= mouse_x <= self.x + 260 and
                self.y + 50 <= mouse_y <= self.y + 80):
                self.on_select_range()  # Select Range
                return True

            # Check card grid
            card_size = 40
            start_x = self.x + 20
            start_y = self.y + 100

            for row, suit in enumerate(self.suits):
                for col, rank in enumerate(self.ranks):
                    card_x = start_x + col * (card_size + 5)
                    card_y = start_y + row * (card_size + 5)

                    if (card_x <= mouse_x <= card_x + card_size and
                        card_y <= mouse_y <= card_y + card_size):
                        card_name = f"{rank}{suit}"
                        if card_name not in self.assigned_cards:
                            self.on_select(card_name)
                            return True

            # Click outside to cancel
            if not (self.x <= mouse_x <= self.x + self.width and
                    self.y <= mouse_y <= self.y + self.height):
                self.on_cancel()  # Cancel
                return True

        return False