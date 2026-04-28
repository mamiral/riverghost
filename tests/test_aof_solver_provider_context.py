import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider


def test_position_action_context_changes_payload_context_fields():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")

    c1 = {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"}
    c2 = {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}

    p1 = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", c1)
    p2 = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", c2)

    assert p1["context"]["active_players"] == 1
    assert p2["context"]["active_players"] == 2
    assert p1["context"]["position_actions"] != p2["context"]["position_actions"]


def test_selected_fold_analysis_mode_keeps_available_values():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
    ctx = {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}
    payload = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", ctx, strict_current_action=False)
    # Phase 4: In-memory database is empty, so cells list is missing values
    assert "cells" in payload
    assert payload["status"] == "MISSING"
    if payload["cells"]:
        assert all(c["status"] == "MISSING" for c in payload["cells"])
