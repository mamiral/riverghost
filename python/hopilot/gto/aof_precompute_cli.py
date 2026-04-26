from __future__ import annotations

import argparse

from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline AoF scenario precompute and persist to normalized database")
    parser.add_argument(
        "--database-url",
        required=True,
        help="Database URL for normalized schema (e.g., sqlite:///path/to/db.sqlite3)"
    )
    parser.add_argument("--max-scenarios", type=int, default=None, help="Optional cap for scenario count")
    parser.add_argument("--resume-run-id", type=int, default=None, help="Resume an existing run id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    # Create a precompute provider that generates matrices with synthetic data
    from hopilot.gto.precompute_provider import PrecomputeProvider
    
    provider = PrecomputeProvider(database_url=args.database_url)
    
    runner = AoFPrecomputeRunner(provider=provider, database_url=args.database_url)
    
    # Run precompute with database persistence
    runner.run(
        profile=PrecomputeProfile(),
        run_id=args.resume_run_id,
        max_scenarios=args.max_scenarios,
    )
    run_id = runner.last_job_session_id

    logger.info(f"Precompute run finished. run_id={run_id} - Data persisted to normalized database")
    print(f"Precompute run finished. run_id={run_id}")

    if run_id is not None:
        try:
            mappings = runner.get_job_scenario_mappings(run_id)
            if mappings:
                print("Scenario mappings:")
                for mapping in mappings:
                    print(
                        f"  [{mapping['scenario_index']}] {mapping['scenario_key']} "
                        f"status={mapping['status']} simulation_id={mapping['simulation_id']} "
                        f"matrix_id={mapping['matrix_id']} "
                        f"failure_boundary={mapping['failure_boundary']} "
                        f"failure_reason={mapping['failure_reason']}"
                    )
        except Exception as exc:
            logger.warning("Unable to print scenario mappings for run_id=%s: %s", run_id, exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
