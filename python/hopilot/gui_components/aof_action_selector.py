import pygame


class AoFActionSelector:
    def __init__(self, x: int, y: int):
        self.actions = ["FOLD", "ALL_IN"]
        self.rects: dict[str, pygame.Rect] = {
            "FOLD": pygame.Rect(x, y, 100, 32),
            "ALL_IN": pygame.Rect(x + 112, y, 100, 32),
        }

    def handle_event(self, event) -> str | None:
        if event.type != pygame.MOUSEBUTTONDOWN:
            return None
        for action, rect in self.rects.items():
            if rect.collidepoint(event.pos):
                return action
        return None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: str):
        for action, rect in self.rects.items():
            color = (227, 81, 81) if action == selected else (70, 70, 70)
            pygame.draw.rect(surface, color, rect, border_radius=4)
            pygame.draw.rect(surface, (220, 220, 220), rect, 1, border_radius=4)
            text = font.render(action.replace("_", "-"), True, (255, 255, 255))
            surface.blit(text, text.get_rect(center=rect.center))
