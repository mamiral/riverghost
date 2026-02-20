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
        self.board_cards = board_cards  # Reference to gui's board_cards
        self.index = index  # Index in board_cards
        self.width = 60
        self.height = 80
        self.font = pygame.font.SysFont("arial", 16, bold=True)  # Bold font for cards
        
        # Suit colors for backgrounds
        self.suit_bg_colors = {'s': (0, 0, 0), 'h': (255, 0, 0), 'd': (0, 0, 255), 'c': (0, 128, 0)}

    @property
    def card(self):
        """Get the current card from board_cards."""
        return self.board_cards[self.index]
    
    @card.setter
    def card(self, value):
        """Set the card in board_cards."""
        self.board_cards[self.index] = value

    def draw(self):
        """Draw the board slot."""
        # Draw slot background (extended upward to include label area)
        pygame.draw.rect(self.screen, (0, 0, 0), (self.x, self.y - 20, self.width, self.height + 20), 2)

        # Draw name (moved up to avoid overlap)
        name_text = self.font.render(self.name, True, (255, 255, 255))
        self.screen.blit(name_text, (self.x + 5, self.y - 5))

        # Draw card
        card_y = self.y + 20
        if self.card:
            # Parse card to get rank and suit
            rank = self.card[0]
            suit = self.card[1]
            bg_color = self.suit_bg_colors.get(suit, (255, 255, 255))
            
            pygame.draw.rect(self.screen, bg_color, (self.x + 10, card_y, 40, 50))
            # Draw rank and suit together with white text
            card_text = self.font.render(self.card, True, (255, 255, 255))
            self.screen.blit(card_text, (self.x + 12, card_y + 2))
        else:
            pygame.draw.rect(self.screen, (128, 128, 128), (self.x + 10, card_y, 40, 50), 2)
            # Draw diagonal hatch pattern for random cards (parallel 45-degree lines)
            card_x = self.x + 10
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
                
                def on_random():
                    self.card = None
                    self.board_cards[self.index] = None
                
                def on_cancel():
                    # Do nothing - keep current card
                    pass
                
                assigned_cards = gui.get_assigned_cards()
                if self.card:  # If currently assigned, allow re-selecting it
                    assigned_cards.discard(self.card)
                gui.card_picker = CardPicker(gui.screen, on_select, on_random, on_cancel, lambda: None, assigned_cards, self.card)
                return True
        return False