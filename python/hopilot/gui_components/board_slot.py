import pygame
from typing import Optional

from .card_picker import CardPicker


class BoardSlot:
    """
    Represents a board card slot (flop, turn, river).
    Handles card assignment and display.
    """

    def __init__(self, screen: pygame.Surface, x: int, y: int, name: str, card: Optional[str], board_cards: list, index: int):
        self.screen = screen
        self.x = x
        self.y = y
        self.name = name
        self.card = card  # Card name or None
        self.board_cards = board_cards  # Reference to gui's board_cards
        self.index = index  # Index in board_cards
        self.width = 60
        self.height = 80
        self.font = pygame.font.SysFont(None, 16)

    def draw(self):
        """Draw the board slot."""
        # Draw slot background
        pygame.draw.rect(self.screen, (0, 0, 0), (self.x, self.y, self.width, self.height), 2)

        # Draw name
        name_text = self.font.render(self.name, True, (255, 255, 255))
        self.screen.blit(name_text, (self.x + 5, self.y + 5))

        # Draw card
        card_y = self.y + 20
        if self.card:
            pygame.draw.rect(self.screen, (255, 255, 255), (self.x + 10, card_y, 40, 50))
            card_text = self.font.render(self.card, True, (0, 0, 0))
            self.screen.blit(card_text, (self.x + 15, card_y + 15))
        else:
            pygame.draw.rect(self.screen, (128, 128, 128), (self.x + 10, card_y, 40, 50), 2)
            random_text = self.font.render("Random", True, (128, 128, 128))
            self.screen.blit(random_text, (self.x + 15, card_y + 15))

    def handle_event(self, event, gui) -> bool:
        """Handle mouse clicks on the card."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            card_x = self.x + 10
            card_y = self.y + 20
            if card_x <= mouse_x <= card_x + 40 and card_y <= mouse_y <= card_y + 50:
                # Open card picker for this card
                def on_select(card):
                    self.card = card
                    self.board_cards[self.index] = card
                
                assigned_cards = gui.get_assigned_cards()
                if self.card:  # If currently assigned, allow re-selecting it
                    assigned_cards.discard(self.card)
                gui.card_picker = CardPicker(gui.screen, on_select, assigned_cards)
                return True
        return False