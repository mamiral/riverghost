import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_state import AoFBrowserViewState


def test_set_position_action_applies_manual_override():
    state = AoFBrowserViewState()
    state.set_position("BTN")
    assert state.position_actions["BTN"] == "ALL_IN"

    state.set_selected_cell(0, 0, "AK")
    assert state.selected_cell == (0, 0, "AK")

    state.set_position_action("BTN", "FOLD")
    assert state.position_actions["BTN"] == "FOLD"
    assert state.active_players() == 2
    assert state.selected_cell is None
