import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


def test_payload_contract_shape_and_cell_count():
    provider = AoFBrowserDataProvider()
    payload = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"})

    assert "context" in payload
    assert "cells" in payload
    assert len(payload["cells"]) == 169

    sample = payload["cells"][0]
    assert {"row", "col", "hand_key", "value", "status", "display"}.issubset(sample.keys())


def test_provider_uses_solver_path_not_heuristic():
    provider = AoFBrowserDataProvider()

    called = {"count": 0}

    def _fake_eval(*args, **kwargs):
        called["count"] += 1
        return {"status": "AVAILABLE", "win_probability": 0.6, "equity": 0.62, "ev": 1.2}

    provider._solver.evaluate_hand_key = _fake_eval
    payload = provider.get_matrix_payload("UTG", "EV", {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"})

    assert called["count"] > 0
    assert any(cell["status"] == "AVAILABLE" for cell in payload["cells"])
