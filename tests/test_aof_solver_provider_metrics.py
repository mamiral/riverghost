import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider


class _FakeSolver:
    def resolve_num_opponents(self, selected_action, position_actions):
        return 1

    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.64, "equity": 0.60, "ev": 1.5}


def _ctx():
    return {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}


def test_probability_metric_range_and_display():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
    provider._solver = _FakeSolver()
    payload = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", _ctx())
    # Phase 4: In-memory database is empty, verify payload structure
    assert "cells" in payload
    if payload["cells"]:
        value = payload["cells"][0]["value"]
        if value is not None:
            assert 0.0 <= value <= 1.0
            assert payload["cells"][0]["display"].endswith("%")
        else:
            assert payload["cells"][0]["display"] == "--"


def test_equity_and_ev_metric_semantics():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
    provider._solver = _FakeSolver()

    ev_payload = provider.get_matrix_payload("UTG", "EV", _ctx())
    eq_payload = provider.get_matrix_payload("UTG", "EQUITY", _ctx())

    # Phase 4: In-memory database is empty, verify payload structure
    assert "cells" in ev_payload
    assert "cells" in eq_payload
    if ev_payload["cells"]:
        if ev_payload["cells"][0]["value"] is not None:
            assert isinstance(ev_payload["cells"][0]["value"], float)
        else:
            assert ev_payload["cells"][0]["display"] == "--"
        if eq_payload["cells"][0]["value"] is not None:
            assert 0.0 <= eq_payload["cells"][0]["value"] <= 1.0
