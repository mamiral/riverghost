#!/usr/bin/env python3
"""
Utility script to trigger incremental aggregation with convergence tracking.
"""

import argparse
import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

import yaml
from hopilot.database import DatabaseConnection
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.matrix_sweep_aggregation_service import MatrixSweepAggregationService
from hopilot.logging_config import get_logger


def load_database_url_from_config():
    """Load database URL from config file."""
    config_path = Path(__file__).resolve().parents[1] / "config" / "gto_defaults.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    if "database" in config_data and "url" in config_data["database"]:
        database_url = config_data["database"]["url"]

        # Convert relative sqlite path to absolute
        if database_url.startswith("sqlite:///"):
            rel_path = database_url.replace("sqlite:///", "")
            abs_path = (config_path.parent.parent / rel_path).resolve()
            database_url = f"sqlite:///{abs_path}"

        return database_url
    else:
        raise ValueError("Database URL not found in config file")


def main():
    parser = argparse.ArgumentParser(description="Aggregate metrics for a simulation run with convergence tracking")
    parser.add_argument("simulation_id", type=int, help="Simulation ID to aggregate")
    parser.add_argument("--interval", type=int, default=100, help="Convergence emit interval (default: 100)")
    parser.add_argument("--database-url", help="Database URL (defaults to config file)")

    args = parser.parse_args()

    logger = get_logger(__name__)

    try:
        database_url = args.database_url or load_database_url_from_config()
        logger.info(f"Using database URL: {database_url}")

        # Initialize database connection and repository
        conn = DatabaseConnection(database_url)
        repository = SimulationRepository(conn)
        aggregator = MatrixSweepAggregationService(repository)

        # Check if simulation exists
        sim_record = repository.get_simulation_record(args.simulation_id)
        if sim_record is None:
            raise ValueError(f"Simulation {args.simulation_id} does not exist")
        
        logger.info(f"Aggregating simulation {args.simulation_id} with convergence tracking (interval={args.interval})...")
        
        # Perform incremental aggregation
        result = aggregator.aggregate_run_incremental(
            args.simulation_id, 
            enable_convergence_tracking=True,
            emit_interval=args.interval
        )

        logger.info("Incremental aggregation completed successfully!")
        print(f"Result: {result}")

        # Check for snapshots
        from hopilot.models.convergence_snapshot import ConvergenceSnapshot
        with conn.session_scope() as session:
            count = session.query(ConvergenceSnapshot).filter_by(simulation_id=args.simulation_id).count()
            print(f"✓ Created {count} convergence snapshots")

    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
