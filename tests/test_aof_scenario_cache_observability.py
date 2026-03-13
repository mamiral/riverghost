import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


class _AvailableSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.9}


class _TimeoutSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "TIMEOUT"}


class _ErrorSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "ERROR"}


def _ctx() -> dict[str, str]:
    return {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}


def _messages(caplog) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


def test_observability_contract_for_cache_hit_miss_and_writeback(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    db_path = str(tmp_path / "aof_obs.sqlite3")

    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    provider._solver = _AvailableSolver()

    provider.get_matrix_payload("UTG", "EV", _ctx())
    provider.clear_cache()
    provider.get_matrix_payload("UTG", "EV", _ctx())

    output = _messages(caplog)
    assert "event=cache_miss" in output
    assert "event=fallback_compute_started" in output
    assert "event=write_back_inserted_or_updated" in output
    assert "event=cache_hit" in output


def test_observability_contract_for_timeout_and_error(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    db_timeout = str(tmp_path / "aof_obs_timeout.sqlite3")

    timeout_provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_timeout)
    timeout_provider._solver = _TimeoutSolver()
    timeout_provider.get_matrix_payload("UTG", "EV", _ctx())

    db_error = str(tmp_path / "aof_obs_error.sqlite3")
    error_provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_error)
    error_provider._solver = _ErrorSolver()
    error_provider.get_matrix_payload("UTG", "EV", _ctx())

    output = _messages(caplog)
    assert "event=fallback_compute_timeout" in output
    assert "event=fallback_compute_error" in output
