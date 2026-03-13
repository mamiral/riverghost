import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


class _FakeSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.64, "equity": 0.60, "ev": 1.5}


def _ctx():
    return {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}


def test_probability_metric_range_and_display():
    provider = AoFBrowserDataProvider()
    provider._solver = _FakeSolver()
    payload = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", _ctx())
    value = payload["cells"][0]["value"]
    assert 0.0 <= value <= 1.0
    assert payload["cells"][0]["display"].endswith("%")


def test_equity_and_ev_and_eqr_metric_semantics():
    provider = AoFBrowserDataProvider()
    provider._solver = _FakeSolver()

    ev_payload = provider.get_matrix_payload("UTG", "EV", _ctx())
    eq_payload = provider.get_matrix_payload("UTG", "EQUITY", _ctx())
    eqr_payload = provider.get_matrix_payload("UTG", "EQR", _ctx())

    assert isinstance(ev_payload["cells"][0]["value"], float)
    assert 0.0 <= eq_payload["cells"][0]["value"] <= 1.0
    assert 0.0 <= eqr_payload["cells"][0]["value"] <= 1.0
