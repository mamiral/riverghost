import pygame


class AoFActionSelector:
    POSITIONS = ["UTG", "BTN", "SB", "BB"]

    def __init__(self, x: int, y: int, width: int = 860):
        self.actions = ["FOLD", "ALL_IN"]
        self.card_rects: dict[str, pygame.Rect] = {}
        self.position_header_rects: dict[str, pygame.Rect] = {}
        self.action_rects: dict[tuple[str, str], pygame.Rect] = {}
        self.rects = self.action_rects

        card_gap = 6
        card_width = min(96, max(82, int((width - card_gap * 3) / 4)))
        card_height = 84
        header_h = 20
        row_h = 20
        group_start_x = x

        for i, position in enumerate(self.POSITIONS):
            left = group_start_x + i * (card_width + card_gap)
            card = pygame.Rect(left, y, card_width, card_height)
            self.card_rects[position] = card
            self.position_header_rects[position] = pygame.Rect(left + 7, y + 6, card_width - 14, header_h)
            self.action_rects[(position, "FOLD")] = pygame.Rect(left + 7, y + 31, card_width - 14, row_h)
            self.action_rects[(position, "ALL_IN")] = pygame.Rect(left + 7, y + 56, card_width - 14, row_h)

    def handle_event(self, event) -> tuple[str, str | None] | None:
        if event.type != pygame.MOUSEBUTTONDOWN:
            return None
        for key, rect in self.action_rects.items():
            if rect.collidepoint(event.pos):
                return key
        for position, rect in self.card_rects.items():
            if rect.collidepoint(event.pos):
                return (position, None)
        return None

    def draw(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        selected_position: str,
        position_actions: dict[str, str],
    ):
        for position in self.POSITIONS:
            card = self.card_rects[position]
            is_selected = position == selected_position
            card_color = (38, 47, 56) if is_selected else (28, 28, 28)
            border_color = (40, 180, 140) if is_selected else (100, 100, 100)
            pygame.draw.rect(surface, card_color, card, border_radius=6)
            pygame.draw.rect(surface, border_color, card, 1, border_radius=6)

            header_rect = self.position_header_rects[position]
            pygame.draw.rect(surface, (20, 20, 20), header_rect, border_radius=3)
            pos_text = font.render(position, True, (220, 220, 220))
            surface.blit(pos_text, (header_rect.x + 5, header_rect.y + 2))

            current_action = position_actions.get(position, "FOLD")
            for action in self.actions:
                rect = self.action_rects[(position, action)]
                is_active = current_action == action
                if action == "ALL_IN":
                    color = (202, 64, 64) if is_active else (60, 41, 41)
                else:
                    color = (70, 116, 156) if is_active else (43, 59, 74)
                pygame.draw.rect(surface, color, rect, border_radius=4)
                pygame.draw.rect(surface, (210, 210, 210), rect, 1, border_radius=4)
                text = font.render(action.replace("_", "-"), True, (245, 245, 245))
                surface.blit(text, (rect.x + 7, rect.y + 2))
