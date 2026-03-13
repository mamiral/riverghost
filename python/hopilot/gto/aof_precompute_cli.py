from __future__ import annotations

import argparse

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline AoF scenario precompute and persist to SQLite cache")
    parser.add_argument("--db-path", default="python/hopilot/cache/aof_scenario_cache.sqlite3", help="SQLite cache path")
    parser.add_argument("--schema-version", default="1", help="Cache schema version")
    parser.add_argument("--solver-signature", default="aof-solver-v1", help="Solver signature")
    parser.add_argument("--policy-signature", default="aof-cache-policy-v1", help="Policy signature")
    parser.add_argument("--max-scenarios", type=int, default=None, help="Optional cap for scenario count")
    parser.add_argument("--resume-run-id", type=int, default=None, help="Resume an existing run id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=args.db_path)
    store = AoFScenarioCacheStore(
        db_path=args.db_path,
        signatures=CacheSignatures(
            schema_version=args.schema_version,
            solver_signature=args.solver_signature,
            policy_signature=args.policy_signature,
            runtime_signature=provider._runtime_signature_base(),  # pylint: disable=protected-access
        ),
    )
    runner = AoFPrecomputeRunner(provider=provider, store=store)
    run_id = runner.run(profile=PrecomputeProfile(), run_id=args.resume_run_id, max_scenarios=args.max_scenarios)
    print(f"Precompute run finished. run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
