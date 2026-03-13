import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_scenario_cache_models import ScenarioPayloadModel
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


class _CountingSolver:
    def __init__(self):
        self.calls = 0

    def evaluate_hand_key(self, *args, **kwargs):
        self.calls += 1
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.9}


def _store(tmp_path, *, schema_version: str = "1", solver_signature: str = "solver-v1", policy_signature: str = "policy-v1"):
    return AoFScenarioCacheStore(
        db_path=str(tmp_path / "aof_invalidation.sqlite3"),
        signatures=CacheSignatures(
            schema_version=schema_version,
            solver_signature=solver_signature,
            policy_signature=policy_signature,
            runtime_signature="runtime-v1",
        ),
    )


def _payload():
    return {
        "context": {
            "position": "UTG",
            "metric": "EV",
            "position_actions": {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
        },
        "cells": [{"row": 0, "col": 0, "hand_key": "AA", "value": 1.0, "status": "AVAILABLE", "display": "1.000"}],
        "status_message": None,
    }


def _ctx() -> dict[str, str]:
    return {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"}


def test_stale_schema_or_signature_is_invalidated(tmp_path):
    store_v1 = _store(tmp_path, schema_version="1", solver_signature="solver-v1", policy_signature="policy-v1")
    key = store_v1.build_scenario_key({"scenario": "stale-signature"})
    store_v1.upsert_payload(key, _payload(), runtime_signature="runtime-v1")

    store_schema_bump = _store(tmp_path, schema_version="2", solver_signature="solver-v1", policy_signature="policy-v1")
    assert store_schema_bump.get_payload(key, expected_runtime_signature="runtime-v1") is None

    store_solver_bump = _store(tmp_path, schema_version="1", solver_signature="solver-v2", policy_signature="policy-v1")
    assert store_solver_bump.get_payload(key, expected_runtime_signature="runtime-v1") is None


def test_corrupt_payload_row_returns_deterministic_miss(tmp_path):
    store = _store(tmp_path)
    key = store.build_scenario_key({"scenario": "corrupt"})
    store.upsert_payload(key, _payload(), runtime_signature="runtime-v1")

    with store._session_factory() as session:  # pylint: disable=protected-access
        row = session.get(ScenarioPayloadModel, key)
        assert row is not None
        row.cells_json = "{not-json"
        session.commit()

    assert store.get_payload(key, expected_runtime_signature="runtime-v1") is None


def test_stale_refresh_returns_current_payload_via_provider(tmp_path):
    db_path = str(tmp_path / "aof_invalidation.sqlite3")

    provider_first = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    solver_first = _CountingSolver()
    provider_first._solver = solver_first
    provider_first.get_matrix_payload("UTG", "EV", _ctx())
    assert solver_first.calls > 0

    key = provider_first._build_solver_equivalence_key(provider_first._build_context(  # pylint: disable=protected-access
        position="UTG",
        metric="EV",
        position_actions=_ctx(),
    ))

    store = _store(tmp_path)
    with store._session_factory() as session:  # pylint: disable=protected-access
        row = session.get(ScenarioPayloadModel, key)
        assert row is not None
        assert row.metadata_row is not None
        row.metadata_row.schema_version = "stale-schema"
        session.commit()

    provider_second = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    solver_second = _CountingSolver()
    provider_second._solver = solver_second
    payload = provider_second.get_matrix_payload("UTG", "EV", _ctx())

    assert solver_second.calls > 0
    assert any(cell["status"] == "AVAILABLE" for cell in payload["cells"])
