import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


class _TimeoutSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "TIMEOUT"}


class _ErrorSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "ERROR"}


def test_timeout_returns_timeout_cells_and_message():
    provider = AoFBrowserDataProvider()
    provider._solver = _TimeoutSolver()
    payload = provider.get_matrix_payload("UTG", "EV", {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"})
    assert any(c["status"] == "TIMEOUT" for c in payload["cells"])


def test_solver_failure_returns_error_cells_and_message():
    provider = AoFBrowserDataProvider()
    provider._solver = _ErrorSolver()
    payload = provider.get_matrix_payload("UTG", "EV", {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"})
    assert any(c["status"] == "ERROR" for c in payload["cells"])
