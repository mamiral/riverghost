import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


class _CountingSolver:
    def __init__(self):
        self.calls = 0

    def evaluate_hand_key(self, *args, **kwargs):
        self.calls += 1
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.9}


def test_cache_hit_and_invalidation_behavior():
    provider = AoFBrowserDataProvider()
    solver = _CountingSolver()
    provider._solver = solver

    ctx1 = {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"}
    ctx2 = {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}

    provider.get_matrix_payload("UTG", "EV", ctx1)
    first_calls = solver.calls
    provider.get_matrix_payload("UTG", "EV", ctx1)
    assert solver.calls == first_calls

    provider.get_matrix_payload("UTG", "EV", ctx2)
    assert solver.calls > first_calls
