import pygame

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_browser_state import AoFBrowserViewState
from hopilot.gui_components.aof_action_selector import AoFActionSelector
from hopilot.gui_components.aof_hand_matrix_panel import AoFHandMatrixPanel
from hopilot.gui_components.aof_metric_dropdown import AoFMetricDropdown
from hopilot.logging_config import get_logger


class AoFBrowserPanel:
    def __init__(self, width: int, height: int, fixture_path: str | None = None):
        self.logger = get_logger(__name__)
        self.width = width
        self.height = height
        self.state = AoFBrowserViewState()
        self.provider = AoFBrowserDataProvider(fixture_path=fixture_path)

        self.top_margin = 20
        self.control_h = 112
        self.side_panel_w = 300
        self.outer_margin = 20

        matrix_region_width = width - self.side_panel_w - (self.outer_margin * 2)
        self.action_selector = AoFActionSelector(self.outer_margin, self.top_margin + 28, width=matrix_region_width)
        self.metric_dropdown = AoFMetricDropdown(width - self.side_panel_w + 54, self.top_margin + 24)
        self.matrix = AoFHandMatrixPanel(self.outer_margin, self.top_margin + self.control_h + 10)
        self._reflow_layout()

        self.font = pygame.font.SysFont("arial", 18)
        self.small_font = pygame.font.SysFont("arial", 12)
        self.payload = self.provider.get_matrix_payload(
            self.state.selected_position,
            self.state.selected_metric,
            self.state.position_actions,
        )

    def _reflow_layout(self) -> None:
        matrix_x = self.outer_margin
        matrix_y = self.top_margin + self.control_h + 10
        matrix_w = self.width - self.side_panel_w - (self.outer_margin * 2)
        matrix_h = self.height - matrix_y - self.outer_margin
        self.matrix.set_bounds(matrix_x, matrix_y, matrix_w, matrix_h)

    def _refresh(self):
        self.payload = self.provider.get_matrix_payload(
            self.state.selected_position,
            self.state.selected_metric,
            self.state.position_actions,
        )
        self.state.status_message = self.payload.get("status_message")

    def handle_event(self, event):
        position_action = self.action_selector.handle_event(event)
        if position_action:
            position, action = position_action
            self.state.set_position(position)
            if action:
                self.state.set_position_action(position, action)
            self._refresh()
            return True

        metric = self.metric_dropdown.handle_event(event, self.state.selected_metric)
        if metric:
            self.state.set_metric(metric)
            self._refresh()
            return True

        return False

    def draw(self, screen: pygame.Surface):
        self._reflow_layout()

        title = self.font.render("AoF GTO Solution Browser", True, (245, 245, 245))
        screen.blit(title, title.get_rect(center=(self.width // 2, 14)))

        self.action_selector.draw(
            screen,
            self.small_font,
            self.state.selected_position,
            self.state.position_actions or {},
        )
        self.metric_dropdown.draw(screen, self.font, self.state.selected_metric)

        self.matrix.draw(screen, self.small_font, self.payload["cells"], self.state.selected_metric)

        info_x = self.width - self.side_panel_w + 20
        info_y = self.top_margin + self.control_h + 10
        info_rect = pygame.Rect(info_x, info_y, self.side_panel_w - 40, 220)
        pygame.draw.rect(screen, (31, 31, 31), info_rect, border_radius=6)
        pygame.draw.rect(screen, (90, 90, 90), info_rect, 1, border_radius=6)

        ctx = self.payload.get("context", {})
        current_action = self.state.get_position_action(self.state.selected_position)
        lines = [
            f"Position: {self.state.selected_position}",
            f"Action: {current_action}",
            f"Metric: {self.state.selected_metric.replace('_', ' ')}",
            f"All-in players: {ctx.get('active_players', 0)}",
        ]
        for idx, line in enumerate(lines):
            text = self.font.render(line, True, (230, 230, 230))
            screen.blit(text, (info_rect.x + 12, info_rect.y + 14 + idx * 34))

        if self.state.status_message:
            msg = self.font.render(self.state.status_message, True, (255, 205, 100))
            status_y = self.top_margin + self.control_h - 8
            screen.blit(msg, msg.get_rect(center=(self.width // 2, status_y)))
