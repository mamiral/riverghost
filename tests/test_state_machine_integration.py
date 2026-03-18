import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_precompute_runner import GuiRunState
from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
from hopilot.gui_components.precompute_config import PrecomputeConfig
from hopilot.gui_components.state_machine_controller import StateMachineController
from hopilot.state_machine_config import SimulationState


@pytest.fixture(scope="module", autouse=True)
def pygame_runtime():
    pygame.init()
    yield
    pygame.quit()


def test_panel_attachment_syncs_restored_session_state():
    panel = AoFBrowserPanel.__new__(AoFBrowserPanel)
    panel.logger = Mock()
    panel.precompute_session = SimpleNamespace(run_state=GuiRunState.PAUSED)
    panel.precompute_max_workers = 3
    panel.precompute_simulations_per_cell = 120
    panel.state_machine_controller = None

    controller = StateMachineController(
        panel=None,
        config=PrecomputeConfig(max_workers=3, simulations_per_cell=120),
    )

    AoFBrowserPanel.set_state_machine_controller(panel, controller)

    assert panel.state_machine_controller is controller
    assert controller.panel is panel
    assert controller.get_current_state() == SimulationState.PAUSED
    assert panel.precompute_max_workers == 3
    assert panel.precompute_simulations_per_cell == 120


@pytest.mark.parametrize(
    ("button_name", "expected_event", "click_pos"),
    [
        ("start", "start", (5, 5)),
        ("pause", "pause", (25, 5)),
        ("resume", "resume", (45, 5)),
        ("stop", "stop", (65, 5)),
    ],
)
def test_panel_routes_button_events_to_state_machine(button_name, expected_event, click_pos):
    panel = AoFBrowserPanel.__new__(AoFBrowserPanel)
    panel.state_machine_controller = Mock()
    panel.state_machine_controller.trigger_event.return_value = True
    panel.precompute_buttons = {
        "start": pygame.Rect(0, 0, 10, 10),
        "pause": pygame.Rect(20, 0, 10, 10),
        "resume": pygame.Rect(40, 0, 10, 10),
        "stop": pygame.Rect(60, 0, 10, 10),
    }

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=click_pos)

    result = AoFBrowserPanel._handle_state_machine_event(panel, event)

    assert result is True
    panel.state_machine_controller.trigger_event.assert_called_once_with(expected_event)


def test_gui_application_initializes_controller_and_uses_60_fps_cap():
    config = PrecomputeConfig(max_workers=3, simulations_per_cell=120)

    with patch("pygame.init"), \
         patch("pygame.display.set_mode"), \
         patch("pygame.display.set_caption"), \
            patch("pygame.display.flip"), \
         patch("pygame.quit"), \
         patch("sys.exit", side_effect=SystemExit), \
         patch("pygame.event.get", return_value=[pygame.event.Event(pygame.QUIT)]), \
         patch("pygame.time.Clock") as clock_cls, \
         patch("hopilot.aof_gto_browser_gui.AoFBrowserPanel") as panel_cls, \
         patch("hopilot.aof_gto_browser_gui.PrecomputeConfig.from_yaml", return_value=config):
        from hopilot.aof_gto_browser_gui import GuiApplication

        clock = Mock()
        clock_cls.return_value = clock
        panel = panel_cls.return_value

        app = GuiApplication(width=1000, height=760)

        attached_controller = panel.set_state_machine_controller.call_args.args[0]
        assert attached_controller.panel is panel

        with pytest.raises(SystemExit):
            app.run()

        clock.tick.assert_called_once_with(app.TARGET_FPS)
        assert app.TARGET_FPS == 60