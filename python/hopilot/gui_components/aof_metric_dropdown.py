import pygame


class AoFMetricDropdown:
    OPTIONS = ["WIN_LOSE_PROBABILITY", "EV", "EQUITY"]

    def __init__(self, x: int, y: int, width: int = 220, height: int = 32):
        self.rect = pygame.Rect(x, y, width, height)

    def set_bounds(self, x: int, y: int, width: int, height: int = 32) -> None:
        self.rect = pygame.Rect(x, y, width, height)

    @staticmethod
    def _fit_text(font: pygame.font.Font, text: str, max_width: int) -> str:
        if font.size(text)[0] <= max_width:
            return text
        ellipsis = "..."
        candidate = text
        while candidate and font.size(candidate + ellipsis)[0] > max_width:
            candidate = candidate[:-1]
        return (candidate + ellipsis) if candidate else ellipsis

    def handle_event(self, event, current: str) -> str | None:
        if event.type != pygame.MOUSEBUTTONDOWN or not self.rect.collidepoint(event.pos):
            return None
        idx = self.OPTIONS.index(current) if current in self.OPTIONS else 0
        return self.OPTIONS[(idx + 1) % len(self.OPTIONS)]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: str):
        pygame.draw.rect(surface, (70, 70, 70), self.rect, border_radius=4)
        pygame.draw.rect(surface, (220, 220, 220), self.rect, 1, border_radius=4)
        label = selected.replace("_", " ")
        raw = f"Metric: {label}"
        fitted = self._fit_text(font, raw, self.rect.width - 16)
        text = font.render(fitted, True, (255, 255, 255))
        surface.blit(text, (self.rect.x + 8, self.rect.y + 6))
