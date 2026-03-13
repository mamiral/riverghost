import pygame


class AoFPositionSelector:
    def __init__(self, x: int, y: int):
        self.positions = ["UTG", "BTN", "SB", "BB"]
        self.rects: dict[str, pygame.Rect] = {}
        width = 80
        height = 32
        gap = 12
        for i, pos in enumerate(self.positions):
            self.rects[pos] = pygame.Rect(x + i * (width + gap), y, width, height)

    def handle_event(self, event) -> str | None:
        if event.type != pygame.MOUSEBUTTONDOWN:
            return None
        for pos, rect in self.rects.items():
            if rect.collidepoint(event.pos):
                return pos
        return None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: str):
        for pos, rect in self.rects.items():
            color = (66, 135, 245) if pos == selected else (70, 70, 70)
            pygame.draw.rect(surface, color, rect, border_radius=4)
            pygame.draw.rect(surface, (220, 220, 220), rect, 1, border_radius=4)
            text = font.render(pos, True, (255, 255, 255))
            surface.blit(text, text.get_rect(center=rect.center))
