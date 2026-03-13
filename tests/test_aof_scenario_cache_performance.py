import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider


class _AvailableSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.9}


def _ctx() -> dict[str, str]:
    return {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}


def test_cached_retrieval_p95_under_250ms_for_200_requests(tmp_path):
    db_path = str(tmp_path / "aof_perf.sqlite3")

    writer = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    writer._solver = _AvailableSolver()
    writer.get_matrix_payload("UTG", "EV", _ctx())

    reader = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    reader._solver = _AvailableSolver()

    samples_ms: list[float] = []
    for _ in range(200):
        reader.clear_cache()
        start = time.perf_counter()
        payload = reader.get_matrix_payload("UTG", "EV", _ctx())
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert any(cell["status"] == "AVAILABLE" for cell in payload["cells"])
        samples_ms.append(elapsed_ms)

    p95 = statistics.quantiles(samples_ms, n=20)[18]
    assert p95 <= 250.0
