import pygame


class AoFHandMatrixPanel:
    def __init__(self, x: int, y: int, cell_size: int = 40):
        self.x = x
        self.y = y
        self.cell_size = cell_size
        self.width = 13 * cell_size
        self.height = 13 * cell_size

    def set_bounds(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.cell_size = max(28, min(width // 13, height // 13))
        self.width = 13 * self.cell_size
        self.height = 13 * self.cell_size

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, cells: list[dict], active_metric: str):
        pygame.draw.rect(
            surface,
            (26, 31, 37),
            pygame.Rect(self.x - 6, self.y - 6, self.width + 12, self.height + 12),
            border_radius=8,
        )

        value_font_size = max(10, min(16, int(self.cell_size * 0.34)))
        value_font = pygame.font.SysFont("arial", value_font_size)

        for cell in cells:
            row = cell["row"]
            col = cell["col"]
            rect = pygame.Rect(self.x + col * self.cell_size, self.y + row * self.cell_size, self.cell_size, self.cell_size)
            status = cell["status"]
            if status == "AVAILABLE":
                value = cell["value"]
                if value is None:
                    color = (60, 60, 60)
                elif value >= 0.65:
                    color = (228, 63, 67)
                elif value >= 0.45:
                    color = (205, 110, 72)
                else:
                    color = (62, 126, 190)
            elif status == "INVALID":
                color = (120, 50, 50)
            else:
                color = (55, 55, 55)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (30, 30, 30), rect, 1)

            label = cell["hand_key"]
            txt = font.render(label, True, (230, 230, 230))
            surface.blit(txt, (rect.x + 3, rect.y + 2))

            value = value_font.render(cell["display"], True, (245, 245, 245))
            value_y = rect.y + self.cell_size - value.get_height() - 2
            surface.blit(value, (rect.x + 3, value_y))
