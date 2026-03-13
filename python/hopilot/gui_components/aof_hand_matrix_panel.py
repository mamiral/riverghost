import pygame


class AoFHandMatrixPanel:
    def __init__(self, x: int, y: int, cell_size: int = 26):
        self.x = x
        self.y = y
        self.cell_size = cell_size
        self.width = 13 * cell_size
        self.height = 13 * cell_size

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, cells: list[dict], active_metric: str):
        for cell in cells:
            row = cell["row"]
            col = cell["col"]
            rect = pygame.Rect(self.x + col * self.cell_size, self.y + row * self.cell_size, self.cell_size, self.cell_size)
            status = cell["status"]
            if status == "AVAILABLE":
                color = (39, 95, 49)
            elif status == "INVALID":
                color = (120, 50, 50)
            else:
                color = (55, 55, 55)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (30, 30, 30), rect, 1)

            label = cell["hand_key"]
            txt = font.render(label, True, (230, 230, 230))
            surface.blit(txt, (rect.x + 2, rect.y + 2))

            value = font.render(cell["display"], True, (245, 245, 245))
            surface.blit(value, (rect.x + 2, rect.y + 13))
