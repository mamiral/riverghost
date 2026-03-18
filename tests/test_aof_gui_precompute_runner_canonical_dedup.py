import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


class _CountingSolver:
    def __init__(self):
        self.calls = 0

    def evaluate_hand_key(self, *args, **kwargs):
        self.calls += 1
        return {"status": "AVAILABLE", "win_probability": 0.63, "equity": 0.6, "ev": 0.95}


class _DistinctContestSolver:
    def __init__(self):
        self.calls = 0

    def evaluate_hand_key(self, *args, **kwargs):
        self.calls += 1
        return {"status": "AVAILABLE", "win_probability": 0.42, "equity": 0.41, "ev": 0.25}


def test_canonical_dedup_reuses_persisted_cells_with_request_local_context(tmp_path):
    db_path = str(tmp_path / "aof_gui_canonical.sqlite3")
    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    solver = _CountingSolver()
    provider._solver = solver

    payload_a = provider.get_matrix_payload(
        position="UTG",
        metric="EV",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
    )
    calls_after_first = solver.calls

    payload_b = provider.get_matrix_payload(
        position="UTG",
        metric="WIN_LOSE_PROBABILITY",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
    )

    assert calls_after_first > 0
    assert solver.calls == calls_after_first
    assert payload_a["context"]["position"] == "UTG"
    assert payload_b["context"]["position"] == "UTG"
    assert all("metrics" in cell for cell in payload_b["cells"])


def test_uncontested_payload_not_reused_for_contested_scenario(tmp_path):
    db_path = str(tmp_path / "aof_gui_canonical_separation.sqlite3")
    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    solver = _DistinctContestSolver()
    provider._solver = solver

    uncontested = provider.get_matrix_payload(
        position="BB",
        metric="WIN_LOSE_PROBABILITY",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"},
    )
    calls_after_uncontested = solver.calls

    contested = provider.get_matrix_payload(
        position="SB",
        metric="WIN_LOSE_PROBABILITY",
        position_actions={"UTG": "FOLD", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
    )

    assert solver.calls == calls_after_uncontested
    assert contested["status_message"] == "All positions are folded"
    assert uncontested["status_message"] != "Uncontested all-in capture"
