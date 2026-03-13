import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


def test_position_action_context_changes_payload_context_fields():
    provider = AoFBrowserDataProvider()

    c1 = {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"}
    c2 = {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}

    p1 = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", c1)
    p2 = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", c2)

    assert p1["context"]["active_players"] == 1
    assert p2["context"]["active_players"] == 2
    assert p1["context"]["position_actions"] != p2["context"]["position_actions"]


def test_selected_fold_analysis_mode_keeps_available_values():
    provider = AoFBrowserDataProvider()
    ctx = {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}
    payload = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", ctx, strict_current_action=False)
    assert any(c["status"] == "AVAILABLE" for c in payload["cells"])
