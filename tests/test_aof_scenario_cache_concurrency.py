import os
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


def _store(tmp_path):
    return AoFScenarioCacheStore(
        db_path=str(tmp_path / "aof_concurrency.sqlite3"),
        signatures=CacheSignatures(
            schema_version="1",
            solver_signature="solver-v1",
            policy_signature="policy-v1",
            runtime_signature="runtime-v1",
        ),
    )


def _payload(tag: str):
    return {
        "context": {
            "position": "UTG",
            "metric": "EV",
            "position_actions": {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
            "tag": tag,
        },
        "cells": [{"row": 0, "col": 0, "hand_key": "AA", "value": 1.0, "status": "AVAILABLE", "display": "1.000"}],
        "status_message": tag,
    }


def test_concurrent_read_write_same_key_stress(tmp_path):
    store = _store(tmp_path)
    key = store.build_scenario_key({"scenario": "shared"})
    stop = Event()
    read_results: list[bool] = []

    def writer() -> None:
        for i in range(80):
            store.upsert_payload(key, _payload(f"w{i}"), runtime_signature="runtime-v1")
        stop.set()

    def reader() -> None:
        while not stop.is_set():
            payload = store.get_payload(key, expected_runtime_signature="runtime-v1")
            read_results.append(payload is None or ("context" in payload and "cells" in payload))

    wt = Thread(target=writer)
    rt = Thread(target=reader)
    wt.start()
    rt.start()
    wt.join()
    rt.join()

    assert read_results
    assert all(read_results)


def test_concurrent_writer_contention_preserves_valid_row(tmp_path):
    store = _store(tmp_path)
    key = store.build_scenario_key({"scenario": "contended"})

    def worker(i: int) -> str:
        return store.upsert_payload(key, _payload(f"worker-{i}"), runtime_signature="runtime-v1")

    with ThreadPoolExecutor(max_workers=10) as pool:
        outcomes = list(pool.map(worker, range(40)))

    assert all(outcome in {"INSERTED", "UPDATED"} for outcome in outcomes)
    final_payload = store.get_payload(key, expected_runtime_signature="runtime-v1")
    assert final_payload is not None
    assert final_payload["context"]["position"] == "UTG"
    assert isinstance(final_payload["cells"], list)
