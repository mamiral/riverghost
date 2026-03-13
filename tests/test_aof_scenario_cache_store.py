import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


def _store(tmp_path):
    return AoFScenarioCacheStore(
        db_path=str(tmp_path / "aof_store.sqlite3"),
        signatures=CacheSignatures(
            schema_version="1",
            solver_signature="solver-v1",
            policy_signature="policy-v1",
            runtime_signature="runtime-v1",
        ),
    )


def _payload():
    return {
        "context": {"position": "UTG", "metric": "EV", "position_actions": {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}},
        "cells": [{"row": 0, "col": 0, "hand_key": "AA", "value": 1.0, "status": "AVAILABLE", "display": "1.000"}],
        "status_message": None,
    }


def test_scenario_key_builder_is_deterministic(tmp_path):
    store = _store(tmp_path)
    p1 = {"a": 1, "b": {"c": 2}}
    p2 = {"b": {"c": 2}, "a": 1}

    assert store.build_scenario_key(p1) == store.build_scenario_key(p2)


def test_upsert_and_read_payload_shape(tmp_path):
    store = _store(tmp_path)
    key = store.build_scenario_key({"scenario": 1})

    outcome = store.upsert_payload(key, _payload(), runtime_signature="runtime-v1")
    assert outcome in {"INSERTED", "UPDATED"}

    result = store.get_payload(key, expected_runtime_signature="runtime-v1")
    assert result is not None
    assert set(result.keys()) == {"context", "cells", "status_message"}
    assert result["cells"][0]["hand_key"] == "AA"


def test_runtime_signature_mismatch_returns_miss(tmp_path):
    store = _store(tmp_path)
    key = store.build_scenario_key({"scenario": 2})
    store.upsert_payload(key, _payload(), runtime_signature="runtime-v1")

    result = store.get_payload(key, expected_runtime_signature="runtime-v2")
    assert result is None
