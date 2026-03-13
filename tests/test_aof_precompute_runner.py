import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


class _FastSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.9}


def _make_store(tmp_path):
    return AoFScenarioCacheStore(
        db_path=str(tmp_path / "aof_precompute.sqlite3"),
        signatures=CacheSignatures(
            schema_version="1",
            solver_signature="aof-solver-v1",
            policy_signature="aof-cache-policy-v1",
            runtime_signature="runtime-v1",
        ),
    )


def test_precompute_run_creates_completed_run(tmp_path):
    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(tmp_path / "aof_precompute.sqlite3"))
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    profile = PrecomputeProfile(positions=("UTG",), metrics=("EV",), strict_modes=(False,))
    run_id = runner.run(profile=profile, max_scenarios=2)

    run = store.get_run(run_id)
    assert run is not None
    assert run.status in {"COMPLETED", "FAILED"}
    assert run.completed_scenarios + run.failed_scenarios <= run.total_scenarios


def test_precompute_is_idempotent_for_current_rows(tmp_path):
    db_path = str(tmp_path / "aof_precompute.sqlite3")
    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    profile = PrecomputeProfile(positions=("UTG",), metrics=("EV",), strict_modes=(False,))
    first_run_id = runner.run(profile=profile, max_scenarios=1)
    second_run_id = runner.run(profile=profile, max_scenarios=1)

    assert first_run_id != second_run_id
    second_run = store.get_run(second_run_id)
    assert second_run is not None
    assert second_run.completed_scenarios >= 1


def test_precompute_resume_cursor_continues_progress(tmp_path):
    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(tmp_path / "aof_precompute.sqlite3"))
    provider._solver = _FastSolver()
    store = _make_store(tmp_path)
    runner = AoFPrecomputeRunner(provider, store)

    profile = PrecomputeProfile(positions=("UTG",), metrics=("EV",), strict_modes=(False,))
    run_id = store.begin_run(total_scenarios=3)
    store.update_run_progress(run_id, completed=1, failed=0, resume_cursor=1)

    resumed_id = runner.run(profile=profile, run_id=run_id, max_scenarios=3)
    assert resumed_id == run_id

    run = store.get_run(run_id)
    assert run is not None
    assert run.resume_cursor == 3
