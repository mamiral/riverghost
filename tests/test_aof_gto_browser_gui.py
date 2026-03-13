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
    assert app.panel.state.get_position_action("UTG") == "FOLD"
    assert app.panel.state.selected_metric == "WIN_LOSE_PROBABILITY"


def test_position_selector_interaction(app):
    btn = app.panel.action_selector.card_rects["BB"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=btn.center)
    app.panel.handle_event(event)
    assert app.panel.state.selected_position == "BB"


def test_action_selector_interaction(app):
    btn = app.panel.action_selector.rects[("UTG", "ALL_IN")]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=btn.center)
    app.panel.handle_event(event)
    assert app.panel.state.get_position_action("UTG") == "ALL_IN"


def test_metric_selector_interaction(app):
    current = app.panel.state.selected_metric
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.metric_dropdown.rect.center)
    app.panel.handle_event(event)
    assert app.panel.state.selected_metric != current


def test_combined_active_state_highlighting_state(app):
    pos_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.action_selector.card_rects["SB"].center)
    action_event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.action_selector.rects[("SB", "ALL_IN")].center,
    )
    metric_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.metric_dropdown.rect.center)
    app.panel.handle_event(pos_event)
    app.panel.handle_event(action_event)
    app.panel.handle_event(metric_event)

    assert app.panel.state.selected_position == "SB"
    assert app.panel.state.get_position_action("SB") == "ALL_IN"
    assert app.panel.state.selected_metric in ("EV", "EQUITY", "EQR")


def test_data_provider_has_169_cells():
    provider = AoFBrowserDataProvider()
    payload = provider.get_matrix_payload("UTG", "EV", {"UTG": "FOLD", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"})
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
    pos_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.action_selector.card_rects["UTG"].center)
    action_event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.action_selector.rects[("UTG", "ALL_IN")].center,
    )
    metric_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.metric_dropdown.rect.center)

    for _ in range(5):
        app.panel.handle_event(pos_event)
        app.panel.handle_event(action_event)
        app.panel.handle_event(metric_event)

    context = app.panel.payload["context"]
    assert context["position"] == app.panel.state.selected_position
    assert context["action"] == app.panel.state.get_position_action(app.panel.state.selected_position)
    assert context["metric"] == app.panel.state.selected_metric


def test_empty_state_for_missing_metric_context():
    provider = AoFBrowserDataProvider()
    payload = provider.get_matrix_payload(
        "UTG",
        "UNKNOWN_METRIC",
        {"UTG": "FOLD", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
    )
    assert len(payload["cells"]) == 169
    assert all(c["status"] == "MISSING" for c in payload["cells"])


def test_multi_position_all_in_updates_context_and_values(app):
    baseline = app.panel.payload
    utg_all_in = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.action_selector.rects[("UTG", "ALL_IN")].center,
    )
    sb_all_in = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.action_selector.rects[("SB", "ALL_IN")].center,
    )
    app.panel.handle_event(utg_all_in)
    app.panel.handle_event(sb_all_in)

    updated = app.panel.payload
    assert updated["context"]["active_players"] == 2
    assert baseline["cells"][0]["value"] != updated["cells"][0]["value"]
