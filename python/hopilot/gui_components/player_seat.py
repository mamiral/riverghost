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
        self.font = pygame.font.SysFont("arial", 20, bold=True)  # Bold font for cards
        
        # Suit colors for backgrounds
        self.suit_bg_colors = {'s': (0, 0, 0), 'h': (255, 0, 0), 'd': (0, 0, 255), 'c': (0, 128, 0)}

    def draw(self):
        """Draw the player seat."""
        # Draw seat background (extended upward to include label area)
        pygame.draw.rect(self.screen, (0, 0, 0), (self.x, self.y - 20, self.width, self.height + 20), 2)

        # Draw name (moved up to avoid overlap)
        name_text = self.font.render(self.name, True, (255, 255, 255))
        self.screen.blit(name_text, (self.x + 10, self.y - 5))

        # Draw cards
        for i, card in enumerate(self.cards):
            card_x = self.x + 10 + i * 50
            card_y = self.y + 25
            if card:
                # Parse card to get rank and suit
                rank = card[0]
                suit = card[1]
                bg_color = self.suit_bg_colors.get(suit, (255, 255, 255))
                
                pygame.draw.rect(self.screen, bg_color, (card_x, card_y, 40, 50))
                # Draw rank and suit together with white text
                card_text = self.font.render(card, True, (255, 255, 255))
                self.screen.blit(card_text, (card_x + 2, card_y + 2))
            else:
                pygame.draw.rect(self.screen, (128, 128, 128), (card_x, card_y, 40, 50), 2)
                # Draw diagonal hatch pattern for random cards (parallel 45-degree lines)
                for i in range(-40, 50, 8):
                    # Draw diagonal lines from top-left to bottom-right
                    start_x = card_x
                    start_y = card_y + i
                    end_x = card_x + 40
                    end_y = card_y + i + 40
                    
                    # Clip the line to the card boundaries
                    if start_y < card_y:
                        # Line starts above card, clip to top
                        start_x = card_x + (card_y - start_y)
                        start_y = card_y
                    if end_y > card_y + 50:
                        # Line ends below card, clip to bottom
                        end_x = card_x + 40 - (end_y - (card_y + 50))
                        end_y = card_y + 50
                    
                    if start_x < end_x and start_y >= card_y and start_y <= card_y + 50 and end_y >= card_y and end_y <= card_y + 50:
                        pygame.draw.line(self.screen, (128, 128, 128), (start_x, start_y), (end_x, end_y), 1)

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