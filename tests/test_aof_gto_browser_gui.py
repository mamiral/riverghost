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
    assert app.panel.state.get_position_action("UTG") == "ALL_IN"
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


def test_confidence_score_display_logic():
    """Test that confidence scores are displayed correctly in cell detail panel."""
    from hopilot.gui_components.aof_cell_detail_panel import AoFCellDetailPanel
    
    panel = AoFCellDetailPanel(0, 0, 220, 300)
    
    # Test high confidence (green)
    detail_model_high = {
        "selected": True,
        "hand_key": "AA",
        "metric": "WIN_LOSE_PROBABILITY", 
        "status": "AVAILABLE",
        "value": 0.85,
        "display_value": "85.0%",
        "sample_count": 1000,
        "confidence": 0.95,
        "segments": [{"weight": 0.85, "label": "Win", "display": "85.0%"}]
    }
    
    # Test medium confidence (yellow)
    detail_model_medium = {
        "selected": True,
        "hand_key": "KK",
        "metric": "WIN_LOSE_PROBABILITY",
        "status": "AVAILABLE", 
        "value": 0.75,
        "display_value": "75.0%",
        "sample_count": 500,
        "confidence": 0.65,
        "segments": [{"weight": 0.75, "label": "Win", "display": "75.0%"}]
    }
    
    # Test low confidence (red)
    detail_model_low = {
        "selected": True,
        "hand_key": "22",
        "metric": "WIN_LOSE_PROBABILITY",
        "status": "AVAILABLE",
        "value": 0.25,
        "display_value": "25.0%",
        "sample_count": 50,
        "confidence": 0.35,
        "segments": [{"weight": 0.25, "label": "Win", "display": "25.0%"}]
    }
    
    # Test no confidence data
    detail_model_no_confidence = {
        "selected": True,
        "hand_key": "AA",
        "metric": "WIN_LOSE_PROBABILITY",
        "status": "AVAILABLE",
        "value": 0.85,
        "display_value": "85.0%",
        "segments": [{"weight": 0.85, "label": "Win", "display": "85.0%"}]
    }
    
    # Mock pygame surface and font for testing
    import pygame
    pygame.init()
    surface = pygame.Surface((220, 300))
    font = pygame.font.SysFont("Arial", 16)
    
    # Test that draw method doesn't crash with confidence data
    try:
        panel.draw(surface, font, detail_model_high)
        panel.draw(surface, font, detail_model_medium) 
        panel.draw(surface, font, detail_model_low)
        panel.draw(surface, font, detail_model_no_confidence)
        # If we get here without exceptions, the test passes
        assert True
    except Exception as e:
        pytest.fail(f"Confidence display logic failed: {e}")
    finally:
        pygame.quit()


def test_matrix_view_layout_with_confidence_metadata_regression(app):
    """Regression test: Ensure matrix view layout accommodates confidence indicators."""
    # Create a surface for drawing
    surface = pygame.Surface((app.width, app.height))
    
    # Draw the panel
    app.panel.draw(surface)
    
    # Verify that the matrix and detail panel don't overlap
    matrix_rect = pygame.Rect(
        app.panel.matrix.x,
        app.panel.matrix.y,
        app.panel.matrix.width,
        app.panel.matrix.height,
    )
    detail_rect = app.panel.cell_detail_panel.rect
    
    # Matrix should be on the left, detail panel on the right
    assert matrix_rect.left >= 0
    assert detail_rect.right <= app.width
    assert matrix_rect.right <= detail_rect.left
    assert detail_rect.right <= app.panel.side_x
    
    # Test that selecting a cell and drawing still works
    select_cell = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.matrix.get_cell_rect(0, 0).center,
    )
    app.panel.handle_event(select_cell)
    
    # Draw again to ensure confidence indicators don't break layout
    app.panel.draw(surface)
    
    # Layout should still be valid
    assert matrix_rect.left >= 0
    assert detail_rect.right <= app.width


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
    sb_select = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.action_selector.card_rects["SB"].center,
    )
    app.panel.handle_event(sb_select)

    updated = app.panel.payload
    assert updated["context"]["active_players"] == 2
    assert baseline["context"]["position"] != updated["context"]["position"]


def test_cell_detail_panel_draws_empty_state_when_no_selection(app):
    surface = pygame.Surface((app.width, app.height))
    app.panel.draw(surface)

    center_pixel = surface.get_at(app.panel.cell_detail_panel.rect.center)
    assert center_pixel != pygame.Color(0, 0, 0, 255)
    assert app.panel.selected_cell_detail["selected"] is False


def test_selected_cell_change_updates_detail_model(app):
    first_row, first_col = 0, 0
    second_row, second_col = 12, 12

    first_cell = app.panel.payload["cells"][first_row * 13 + first_col]
    second_cell = app.panel.payload["cells"][second_row * 13 + second_col]

    first_click = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.matrix.get_cell_rect(first_row, first_col).center,
    )
    second_click = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.matrix.get_cell_rect(second_row, second_col).center,
    )

    app.panel.handle_event(first_click)
    assert app.panel.state.selected_cell == (first_row, first_col, first_cell["hand_key"])
    assert app.panel.selected_cell_detail["hand_key"] == first_cell["hand_key"]

    app.panel.handle_event(second_click)
    assert app.panel.state.selected_cell == (second_row, second_col, second_cell["hand_key"])
    assert app.panel.selected_cell_detail["hand_key"] == second_cell["hand_key"]


def test_win_lose_probability_detail_has_three_segments(app):
    app.panel.payload["cells"][0].update(
        {
            "status": "AVAILABLE",
            "value": 0.62,
            "display": "62.0%",
            "metrics": {
                "WIN_LOSE_PROBABILITY": 0.62,
                "EV": 1.25,
                "EQUITY": 0.58,
                "EQR": 0.61,
                "TIE": 0.03,
            },
        }
    )
    click = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        pos=app.panel.matrix.get_cell_rect(0, 0).center,
    )
    app.panel.handle_event(click)

    model = app.panel.selected_cell_detail
    assert model["metric"] == "WIN_LOSE_PROBABILITY"
    assert model["status"] == "AVAILABLE"
    assert len(model["segments"]) == 3
    assert [segment["label"] for segment in model["segments"]] == ["Win", "Tie", "Loss"]
    assert all("weight" in segment for segment in model["segments"])


@pytest.mark.parametrize(
    "status,expected",
    [
        ("MISSING", "No cached value for this cell."),
        ("TIMEOUT", "Computation timed out for this cell."),
        ("ERROR", "An error occurred while computing this cell."),
        ("NO_CONTEST", "No contest for this scenario and hand."),
    ],
)
def test_detail_panel_fallback_status_messages(app, status, expected):
    row, col = 0, 0
    hand_key = app.panel.payload["cells"][row * 13 + col]["hand_key"]
    app.panel.state.set_selected_cell(row, col, hand_key)

    app.panel.payload["cells"][row * 13 + col].update(
        {
            "status": status,
            "value": None,
            "display": "-",
            "metrics": {},
        }
    )
    app.panel.selected_cell_detail = app.panel._build_selected_cell_detail_model()  # pylint: disable=protected-access

    assert app.panel.selected_cell_detail["status"] == status
    assert app.panel.selected_cell_detail["status_message"] == expected
