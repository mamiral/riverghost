import pygame

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_browser_state import AoFBrowserViewState
from hopilot.gui_components.aof_action_selector import AoFActionSelector
from hopilot.gui_components.aof_hand_matrix_panel import AoFHandMatrixPanel
from hopilot.gui_components.aof_metric_dropdown import AoFMetricDropdown
from hopilot.gui_components.aof_position_selector import AoFPositionSelector
from hopilot.logging_config import get_logger


class AoFBrowserPanel:
    def __init__(self, width: int, height: int, fixture_path: str | None = None):
        self.logger = get_logger(__name__)
        self.width = width
        self.height = height
        self.state = AoFBrowserViewState()
        self.provider = AoFBrowserDataProvider(fixture_path=fixture_path)

        center_x = width // 2
        self.position_selector = AoFPositionSelector(center_x - 180, 24)
        self.action_selector = AoFActionSelector(center_x - 110, 72)
        self.metric_dropdown = AoFMetricDropdown(center_x - 110, 116)
        self.matrix = AoFHandMatrixPanel(center_x - 169, 180)

        self.font = pygame.font.SysFont("arial", 18)
        self.small_font = pygame.font.SysFont("arial", 12)
        self.payload = self.provider.get_matrix_payload(
            self.state.selected_position,
            self.state.selected_action,
            self.state.selected_metric,
        )

    def _refresh(self):
        self.payload = self.provider.get_matrix_payload(
            self.state.selected_position,
            self.state.selected_action,
            self.state.selected_metric,
        )
        if any(c["status"] != "AVAILABLE" for c in self.payload["cells"]):
            self.state.status_message = "Some hands are unavailable for this context"
        else:
            self.state.status_message = None

    def handle_event(self, event):
        pos = self.position_selector.handle_event(event)
        if pos:
            self.state.set_position(pos)
            self._refresh()
            return True

        action = self.action_selector.handle_event(event)
        if action:
            self.state.set_action(action)
            self._refresh()
            return True

        metric = self.metric_dropdown.handle_event(event, self.state.selected_metric)
        if metric:
            self.state.set_metric(metric)
            self._refresh()
            return True

        return False

    def draw(self, screen: pygame.Surface):
        title = self.font.render("AoF GTO Solution Browser", True, (245, 245, 245))
        screen.blit(title, title.get_rect(center=(self.width // 2, 14)))

        self.position_selector.draw(screen, self.font, self.state.selected_position)
        self.action_selector.draw(screen, self.font, self.state.selected_action)
        self.metric_dropdown.draw(screen, self.font, self.state.selected_metric)

        self.matrix.draw(screen, self.small_font, self.payload["cells"], self.state.selected_metric)

        if self.state.status_message:
            msg = self.font.render(self.state.status_message, True, (255, 205, 100))
            screen.blit(msg, msg.get_rect(center=(self.width // 2, 160)))
