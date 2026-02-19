import pygame
from typing import List, Optional

from .card_picker import CardPicker


class PlayerSeat:
    """
    Represents a player seat (hero or villain) with two hole cards.
    Handles card assignment and display.
    """

    def __init__(self, screen: pygame.Surface, x: int, y: int, name: str, cards: List[Optional[str]]):
        self.screen = screen
        self.x = x
        self.y = y
        self.name = name
        self.cards = cards  # List of 2 card names or None
        self.width = 120
        self.height = 80
        self.font = pygame.font.SysFont(None, 20)

    def draw(self):
        """Draw the player seat."""
        # Draw seat background
        pygame.draw.rect(self.screen, (0, 0, 0), (self.x, self.y, self.width, self.height), 2)

        # Draw name
        name_text = self.font.render(self.name, True, (255, 255, 255))
        self.screen.blit(name_text, (self.x + 10, self.y + 5))

        # Draw cards
        for i, card in enumerate(self.cards):
            card_x = self.x + 10 + i * 50
            card_y = self.y + 25
            if card:
                pygame.draw.rect(self.screen, (255, 255, 255), (card_x, card_y, 40, 50))
                card_text = self.font.render(card, True, (0, 0, 0))
                self.screen.blit(card_text, (card_x + 5, card_y + 15))
            else:
                pygame.draw.rect(self.screen, (128, 128, 128), (card_x, card_y, 40, 50), 2)
                random_text = self.font.render("Random", True, (128, 128, 128))
                self.screen.blit(random_text, (card_x + 5, card_y + 15))

    def handle_event(self, event, gui) -> bool:
        """Handle mouse clicks on cards."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            for i in range(2):
                card_x = self.x + 10 + i * 50
                card_y = self.y + 25
                if card_x <= mouse_x <= card_x + 40 and card_y <= mouse_y <= card_y + 50:
                    # Open card picker for this card
                    def on_select(card):
                        self.cards[i] = card
                    
                    def on_random():
                        self.cards[i] = None
                    
                    def on_cancel():
                        # Do nothing - keep current card
                        pass
                    
                    assigned_cards = gui.get_assigned_cards()
                    if self.cards[i]:  # If currently assigned, allow re-selecting it
                        assigned_cards.discard(self.cards[i])
                    gui.card_picker = CardPicker(gui.screen, on_select, on_random, on_cancel, assigned_cards, self.cards[i])
                    return True
        return False