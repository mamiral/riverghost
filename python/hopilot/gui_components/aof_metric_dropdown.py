import pygame


class AoFMetricDropdown:
    OPTIONS = ["WIN_LOSE_PROBABILITY", "EV", "EQUITY", "EQR"]

    def __init__(self, x: int, y: int):
        self.rect = pygame.Rect(x, y, 220, 32)

    def handle_event(self, event, current: str) -> str | None:
        if event.type != pygame.MOUSEBUTTONDOWN or not self.rect.collidepoint(event.pos):
            return None
        idx = self.OPTIONS.index(current) if current in self.OPTIONS else 0
        return self.OPTIONS[(idx + 1) % len(self.OPTIONS)]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: str):
        pygame.draw.rect(surface, (70, 70, 70), self.rect, border_radius=4)
        pygame.draw.rect(surface, (220, 220, 220), self.rect, 1, border_radius=4)
        label = selected.replace("_", " ")
        text = font.render(f"Metric: {label}", True, (255, 255, 255))
        surface.blit(text, (self.rect.x + 8, self.rect.y + 6))
