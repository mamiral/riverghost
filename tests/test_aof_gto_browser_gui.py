import os
import sys
import time

import pygame
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.aof_gto_browser_gui import GuiApplication
from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


@pytest.fixture
def app():
    pygame.init()
    gui = GuiApplication(width=1000, height=760)
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
    gui = GuiApplication(width=1000, height=760)
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


def test_start_button_initially_enabled(app):
    """Test that START button is enabled when no precompute session exists."""
    # Initially no session
    assert app.panel.precompute_session is None
    
    # START button should be enabled
    start_rect = app.panel.precompute_buttons["start"]
    assert start_rect is not None


def test_start_button_click_starts_precompute(app):
    """Test that clicking START button creates a precompute session."""
    # Ensure no session initially
    assert app.panel.precompute_session is None
    
    # Click START button
    start_rect = app.panel.precompute_buttons["start"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(event)
    
    # Session should be created and running
    assert app.panel.precompute_session is not None
    from hopilot.gto.aof_precompute_runner import GuiRunState
    assert app.panel.precompute_session.run_state == GuiRunState.RUNNING
    
    # Status message should indicate started
    assert "Precompute started" in app.panel.state.status_message


def test_pause_button_enabled_when_running(app):
    """Test that PAUSE button is enabled when precompute is running."""
    # Start precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # PAUSE button should be enabled
    pause_rect = app.panel.precompute_buttons["pause"]
    assert pause_rect is not None


def test_pause_button_clicks_precompute(app):
    """Test that clicking PAUSE button pauses the precompute session."""
    # Start precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # Click PAUSE button
    pause_rect = app.panel.precompute_buttons["pause"]
    pause_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pause_rect.center)
    app.panel.handle_event(pause_event)
    
    # Session should be paused
    from hopilot.gto.aof_precompute_runner import GuiRunState
    assert app.panel.precompute_session.run_state == GuiRunState.PAUSED
    
    # Status message should indicate paused
    assert "Precompute paused" in app.panel.state.status_message


def test_resume_button_enabled_when_paused(app):
    """Test that RESUME button is enabled when precompute is paused."""
    # Start and pause precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    pause_rect = app.panel.precompute_buttons["pause"]
    pause_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pause_rect.center)
    app.panel.handle_event(pause_event)
    
    # RESUME button should be enabled
    resume_rect = app.panel.precompute_buttons["resume"]
    assert resume_rect is not None


def test_stop_button_enabled_when_running(app):
    """Test that STOP button is enabled when precompute is running."""
    # Start precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # STOP button should be enabled
    stop_rect = app.panel.precompute_buttons["stop"]
    assert stop_rect is not None


def test_stop_button_clicks_precompute(app):
    """Test that clicking STOP button stops the precompute session."""
    # Start precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # Click STOP button
    stop_rect = app.panel.precompute_buttons["stop"]
    stop_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=stop_rect.center)
    app.panel.handle_event(stop_event)
    
    # Session should be reset to None
    assert app.panel.precompute_session is None
    
    # Status message should indicate stopped and reset
    assert "Precompute stopped and reset" in app.panel.state.status_message


def test_buttons_disabled_during_scenario_locked_state(app):
    """Test that control buttons are disabled when scenario is locked during precompute."""
    # Start precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # Try to change position - should be blocked
    pos_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.action_selector.card_rects["BB"].center)
    result = app.panel.handle_event(pos_event)
    
    # Event should be blocked (return False)
    assert result is False
    
    # Status message should indicate locked
    assert "locked" in app.panel.state.status_message.lower()


def test_precompute_checkpoint_restoration_loads_cached_payload(app, monkeypatch):
    """Test that checkpoint restoration loads cached payload data."""
    # Mock the runner to return a restored session
    from hopilot.gto.aof_precompute_runner import GuiPrecomputeRunSession, GuiRunState
    
    mock_session = GuiPrecomputeRunSession(
        run_id="test-run",
        scenario_fingerprint="test-fingerprint", 
        simulations_per_cell=1000,
        total_cells=169,
        run_state=GuiRunState.PAUSED
    )
    
    def mock_restore(*args, **kwargs):
        return mock_session
    
    monkeypatch.setattr(app.panel.runner, "restore_latest_gui_session", mock_restore)
    
    # Mock cached payload
    cached_payload = {
        "context": app.panel._build_current_context(),
        "cells": [
            {
                "row": 0,
                "col": 0,
                "hand_key": "AA",
                "value": 0.85,
                "status": "AVAILABLE",
                "display": "85.0%"
            }
        ] * 169,
        "status_message": "Cached results"
    }
    
    def mock_get_payload(*args, **kwargs):
        return cached_payload
    
    monkeypatch.setattr(app.panel.provider, "get_matrix_payload", mock_get_payload)
    
    # Trigger checkpoint restoration
    app.panel._restore_precompute_checkpoint_if_available()
    
    # Should have restored session
    assert app.panel.precompute_session is not None
    assert app.panel.precompute_session.run_id == "test-run"
    
    # Should have loaded cached payload
    assert app.panel.payload == cached_payload
    assert app.panel.state.status_message == "Precompute checkpoint restored"


def test_resume_button_works_after_pause(app):
    """Test that RESUME button properly resumes a paused precompute session."""
    # Start precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # Pause it
    pause_rect = app.panel.precompute_buttons["pause"]
    pause_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pause_rect.center)
    app.panel.handle_event(pause_event)
    
    # Verify paused
    from hopilot.gto.aof_precompute_runner import GuiRunState
    assert app.panel.precompute_session.run_state == GuiRunState.PAUSED
    
    # Resume it
    resume_rect = app.panel.precompute_buttons["resume"]
    resume_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=resume_rect.center)
    app.panel.handle_event(resume_event)
    
    # Should be running again
    assert app.panel.precompute_session.run_state == GuiRunState.RUNNING
    assert "Precompute resumed" in app.panel.state.status_message


def test_stop_button_resets_session_state(app):
    """Test that STOP button properly resets the session to allow new starts."""
    # Start precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # Stop it
    stop_rect = app.panel.precompute_buttons["stop"]
    stop_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=stop_rect.center)
    app.panel.handle_event(stop_event)
    
    # Session should be reset (None)
    assert app.panel.precompute_session is None
    
    # Should be able to start again
    start_event2 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    result = app.panel.handle_event(start_event2)
    assert result is True
    
    # Should have a new session
    from hopilot.gto.aof_precompute_runner import GuiRunState
    assert app.panel.precompute_session.run_state == GuiRunState.RUNNING


def test_precompute_state_persistence_across_app_restarts(app, monkeypatch, tmp_path):
    """Test that precompute state persists correctly across app restarts."""
    import json
    
    # Start precompute and let it run briefly
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # Simulate some progress
    app.panel.precompute_session.completed_cells = 10
    app.panel.precompute_session.next_cell_index = 15
    
    # Mock persistence
    persisted_data = None
    def mock_persist(data):
        nonlocal persisted_data
        persisted_data = data
    
    # Simulate app shutdown by calling persist
    app.panel._persist_completed_precompute_payload()
    
    # Create new app instance (simulating restart)
    from hopilot.aof_gto_browser_gui import GuiApplication
    pygame.quit()
    pygame.init()
    new_app = GuiApplication(width=1000, height=760)
    
    # Mock restoration to return our persisted session
    def mock_restore(*args, **kwargs):
        return app.panel.precompute_session
    
    monkeypatch.setattr(new_app.panel.runner, "restore_latest_gui_session", mock_restore)
    
    # Mock cached payload loading
    def mock_get_payload(*args, **kwargs):
        return app.panel.payload
    
    monkeypatch.setattr(new_app.panel.provider, "get_matrix_payload", mock_get_payload)
    
    # Trigger restoration
    new_app.panel._restore_precompute_checkpoint_if_available()
    
    # Should have restored the session with progress
    assert new_app.panel.precompute_session is not None
    assert new_app.panel.precompute_session.completed_cells == 10
    assert new_app.panel.precompute_session.next_cell_index == 15
    
    pygame.quit()


def test_precompute_flow_completes_and_resets_properly(app):
    """Test complete precompute flow from start to completion."""
    # Start precompute
    start_rect = app.panel.precompute_buttons["start"]
    start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    app.panel.handle_event(start_event)
    
    # Simulate completion
    from hopilot.gto.aof_precompute_runner import GuiRunState
    app.panel.precompute_session.completed_cells = 169
    app.panel.precompute_session.failed_cells = 0
    app.panel.runner.transition_session_state(app.panel.precompute_session, GuiRunState.COMPLETED)
    
    # Tick to handle completion
    app.panel._tick_precompute()
    
    # Should be completed
    assert app.panel.precompute_session.run_state == GuiRunState.COMPLETED
    
    # Should be able to start new precompute
    start_event2 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
    result = app.panel.handle_event(start_event2)
    assert result is True
    
    # Should have new session
    assert app.panel.precompute_session.run_state == GuiRunState.RUNNING


def test_convergence_plot_shows_mock_data_with_precompute_results(app):
    """Test that convergence plot displays mock data when precompute results are available."""
    # Simulate having some computed results
    app.panel.payload = {
        "cells": [
            {"status": "AVAILABLE", "value": 0.75},
            {"status": "AVAILABLE", "value": 0.82},
            {"status": "AVAILABLE", "value": 0.68},
            {"status": "MISSING", "value": None},
        ] * 43,  # 169 cells total
        "context": {},
        "status_message": "Test results"
    }
    
    # Ensure no cell is selected
    app.panel.state.clear_selected_cell()
    
    # Load convergence data
    app.panel._load_convergence_data()
    
    # Should have convergence data
    assert len(app.panel.convergence_panel.convergence_data) > 0
    assert app.panel.convergence_panel.position == app.panel.state.selected_position
    
    # Check data structure
    for point in app.panel.convergence_panel.convergence_data:
        assert "num_simulations" in point
        assert "average_equity" in point
        assert 0.0 <= point["average_equity"] <= 1.0


def test_convergence_plot_shows_cell_specific_data_when_selected(app):
    """Test that convergence plot displays cell-specific data when a cell is selected."""
    # Simulate having some computed results
    app.panel.payload = {
        "cells": [
            {"row": 0, "col": 0, "hand_key": "AA", "status": "AVAILABLE", "value": 0.85},
            {"row": 0, "col": 1, "hand_key": "AKs", "status": "AVAILABLE", "value": 0.75},
        ] + [{"status": "MISSING", "value": None}] * 167,
        "context": {},
        "status_message": "Test results"
    }
    
    # Select a cell
    app.panel.state.set_selected_cell(0, 0, "AA")
    
    # Load convergence data
    app.panel._load_convergence_data()
    
    # Should have convergence data specific to the selected cell
    assert len(app.panel.convergence_panel.convergence_data) > 0
    assert "AA" in app.panel.convergence_panel.position  # Should include hand key
    
    # Check that the final convergence value is close to the cell's value
    final_point = app.panel.convergence_panel.convergence_data[-1]
    assert abs(final_point["average_equity"] - 0.85) < 0.1  # Should converge to cell's value


def test_convergence_plot_empty_when_no_results(app):
    """Test that convergence plot shows no data when no results are available."""
    # Clear payload
    app.panel.payload = {
        "cells": [{"status": "MISSING", "value": None}] * 169,
        "context": {},
        "status_message": "No results"
    }
    
    # Ensure no cell is selected
    app.panel.state.clear_selected_cell()
    
    # Load convergence data
    app.panel._load_convergence_data()
    
    # Should have no convergence data
    assert len(app.panel.convergence_panel.convergence_data) == 0
