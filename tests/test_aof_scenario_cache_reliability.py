import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


class _AvailableSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "AVAILABLE", "win_probability": 0.61, "equity": 0.58, "ev": 0.9}


class _TimeoutSolver:
    def evaluate_hand_key(self, *args, **kwargs):
        return {"status": "TIMEOUT"}


def test_offline_precomputed_load_timeout_free_rate_at_least_99_percent(tmp_path):
    db_path = str(tmp_path / "aof_reliability.sqlite3")

    provider_builder = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    provider_builder._solver = _AvailableSolver()
    store = AoFScenarioCacheStore(
        db_path=db_path,
        signatures=CacheSignatures(
            schema_version="1",
            solver_signature="aof-solver-v1",
            policy_signature="aof-cache-policy-v1",
            runtime_signature="runtime-v1",
        ),
    )
    runner = AoFPrecomputeRunner(provider_builder, store)
    profile = PrecomputeProfile(positions=("UTG",), metrics=("EV",), strict_modes=(False,))
    scenarios = runner.enumerate_scenarios(profile)[:100]
    runner.run(profile=profile, max_scenarios=100)

    provider_reader = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)
    provider_reader._solver = _TimeoutSolver()

    timeout_free = 0
    for scenario in scenarios:
        provider_reader.clear_cache()
        payload = provider_reader.get_matrix_payload(
            position=scenario["position"],
            metric=scenario["metric"],
            position_actions=scenario["position_actions"],
            strict_current_action=scenario["strict_current_action"],
        )
        statuses = {cell["status"] for cell in payload["cells"]}
        if "TIMEOUT" not in statuses:
            timeout_free += 1

    rate = timeout_free / len(scenarios)
    assert rate >= 0.99
