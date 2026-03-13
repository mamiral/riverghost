import os
import sys
import time

import pygame
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.aof_gto_browser_gui import AoFGTOBrowserGUI
from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


@pytest.fixture
def app():
    pygame.init()
    gui = AoFGTOBrowserGUI(width=1000, height=760)
    yield gui
    pygame.quit()


def test_aof_browser_app_initialization(app):
    assert app.width == 1000
    assert app.height == 760
    assert app.panel.state.selected_position == "UTG"
    assert app.panel.state.selected_action == "FOLD"
    assert app.panel.state.selected_metric == "WIN_LOSE_PROBABILITY"


def test_position_selector_interaction(app):
    btn = app.panel.position_selector.rects["BB"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=btn.center)
    app.panel.handle_event(event)
    assert app.panel.state.selected_position == "BB"


def test_action_selector_interaction(app):
    btn = app.panel.action_selector.rects["ALL_IN"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=btn.center)
    app.panel.handle_event(event)
    assert app.panel.state.selected_action == "ALL_IN"


def test_metric_selector_interaction(app):
    current = app.panel.state.selected_metric
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.metric_dropdown.rect.center)
    app.panel.handle_event(event)
    assert app.panel.state.selected_metric != current


def test_combined_active_state_highlighting_state(app):
    pos_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.position_selector.rects["SB"].center)
    action_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.action_selector.rects["ALL_IN"].center)
    metric_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.metric_dropdown.rect.center)
    app.panel.handle_event(pos_event)
    app.panel.handle_event(action_event)
    app.panel.handle_event(metric_event)

    assert app.panel.state.selected_position == "SB"
    assert app.panel.state.selected_action == "ALL_IN"
    assert app.panel.state.selected_metric in ("EV", "EQUITY", "EQR")


def test_data_provider_has_169_cells():
    provider = AoFBrowserDataProvider()
    payload = provider.get_matrix_payload("UTG", "FOLD", "EV")
    assert len(payload["cells"]) == 169


def test_startup_time_under_30_seconds():
    pygame.init()
    start = time.perf_counter()
    gui = AoFGTOBrowserGUI(width=1000, height=760)
    elapsed = time.perf_counter() - start
    assert elapsed <= 30.0
    assert gui.panel is not None
    pygame.quit()


def test_rapid_switching_uses_latest_context(app):
    pos_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.position_selector.rects["UTG"].center)
    action_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.action_selector.rects["ALL_IN"].center)
    metric_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.metric_dropdown.rect.center)

    for _ in range(5):
        app.panel.handle_event(pos_event)
        app.panel.handle_event(action_event)
        app.panel.handle_event(metric_event)

    context = app.panel.payload["context"]
    assert context["position"] == app.panel.state.selected_position
    assert context["action"] == app.panel.state.selected_action
    assert context["metric"] == app.panel.state.selected_metric


def test_empty_state_for_missing_metric_context():
    provider = AoFBrowserDataProvider()
    payload = provider.get_matrix_payload("UTG", "FOLD", "UNKNOWN_METRIC")
    assert len(payload["cells"]) == 169
    assert all(c["status"] == "MISSING" for c in payload["cells"])
