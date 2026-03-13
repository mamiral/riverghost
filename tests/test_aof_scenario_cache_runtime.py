import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


class _CountingAvailableSolver:
    def __init__(self):
        self.calls = 0

    def evaluate_hand_key(self, *args, **kwargs):
        self.calls += 1
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.9}


class _TimeoutSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "TIMEOUT"}


class _ErrorSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "ERROR"}


def _ctx() -> dict[str, str]:
    return {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}


def test_cache_hit_after_restart_uses_persistent_store(tmp_path):
    db_path = tmp_path / "aof_runtime_cache.sqlite3"

    provider_1 = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
    solver_1 = _CountingAvailableSolver()
    provider_1._solver = solver_1

    first_payload = provider_1.get_matrix_payload("UTG", "EV", _ctx())
    assert solver_1.calls > 0
    assert any(cell["status"] == "AVAILABLE" for cell in first_payload["cells"])

    provider_2 = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
    solver_2 = _CountingAvailableSolver()
    provider_2._solver = solver_2

    second_payload = provider_2.get_matrix_payload("UTG", "EV", _ctx())
    assert solver_2.calls == 0
    assert second_payload["context"] == first_payload["context"]


def test_miss_writeback_then_hit_transition(tmp_path):
    db_path = tmp_path / "aof_runtime_cache.sqlite3"

    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
    solver = _CountingAvailableSolver()
    provider._solver = solver

    provider.get_matrix_payload("UTG", "EV", _ctx())
    first_calls = solver.calls
    assert first_calls > 0

    provider.clear_cache()
    provider.get_matrix_payload("UTG", "EV", _ctx())
    assert solver.calls == first_calls


def test_timeout_payload_is_not_written_as_current(tmp_path):
    db_path = tmp_path / "aof_runtime_cache.sqlite3"

    provider_timeout = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
    provider_timeout._solver = _TimeoutSolver()
    timeout_payload = provider_timeout.get_matrix_payload("UTG", "EV", _ctx())
    assert any(cell["status"] == "TIMEOUT" for cell in timeout_payload["cells"])

    provider_available = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
    available_solver = _CountingAvailableSolver()
    provider_available._solver = available_solver
    payload = provider_available.get_matrix_payload("UTG", "EV", _ctx())

    assert available_solver.calls > 0
    assert any(cell["status"] == "AVAILABLE" for cell in payload["cells"])


def test_error_payload_is_not_written_as_current(tmp_path):
    db_path = tmp_path / "aof_runtime_cache.sqlite3"

    provider_error = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
    provider_error._solver = _ErrorSolver()
    error_payload = provider_error.get_matrix_payload("UTG", "EV", _ctx())
    assert any(cell["status"] == "ERROR" for cell in error_payload["cells"])

    provider_available = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
    available_solver = _CountingAvailableSolver()
    provider_available._solver = available_solver
    payload = provider_available.get_matrix_payload("UTG", "EV", _ctx())

    assert available_solver.calls > 0
    assert any(cell["status"] == "AVAILABLE" for cell in payload["cells"])


def test_solver_equivalent_positions_reuse_persistent_cells(tmp_path):
    db_path = tmp_path / "aof_runtime_cache.sqlite3"
    actions = {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}

    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
    solver = _CountingAvailableSolver()
    provider._solver = solver

    utg_payload = provider.get_matrix_payload("UTG", "EV", actions)
    calls_after_utg = solver.calls
    assert calls_after_utg > 0

    provider.clear_cache()
    btn_payload = provider.get_matrix_payload("BTN", "EV", actions)

    # Canonical persistent key should dedup solver-equivalent seat labels.
    assert solver.calls == calls_after_utg
    assert utg_payload["cells"] == btn_payload["cells"]
    assert utg_payload["context"]["position"] == "UTG"
    assert btn_payload["context"]["position"] == "BTN"
