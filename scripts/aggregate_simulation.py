#!/usr/bin/env python3
"""
Utility script to trigger aggregated metrics computation for a given simulation ID.

Usage:
    python scripts/aggregate_simulation.py <simulation_id> [--database-url <url>]

If --database-url is not provided, it will load from config/gto_defaults.yaml
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
    """Load database URL from config file, similar to the GUI."""
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
    parser = argparse.ArgumentParser(description="Aggregate metrics for a simulation run")
    parser.add_argument("simulation_id", type=int, help="Simulation ID to aggregate")
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

        # Check if simulation has already been aggregated
        sim_record = repository.get_simulation_record(args.simulation_id)
        if sim_record is None:
            raise ValueError(f"Simulation {args.simulation_id} does not exist")
        
        current_status = sim_record.parameters.get("status", "unknown")
        logger.info(f"Current simulation status: {current_status}")
        
        # Perform aggregation
        if current_status == "aggregated":
            logger.info("Re-aggregating existing simulation")
            result = aggregator.rerun_aggregation(args.simulation_id)
        else:
            logger.info("Aggregating simulation for the first time")
            result = aggregator.aggregate_run(args.simulation_id)

        logger.info("Aggregation completed successfully!")
        print(f"Result: {result}")

        # Print summary
        if result["status"] == "aggregation_complete":
            print("✓ Aggregation successful")
            print(f"  Matrix ID: {result['matrix_id']}")
            print(f"  Matrix cells written: {result['matrix_cells_written']}")
            print(f"  Aggregated metrics written: {result['aggregated_metrics_written']}")
            print(f"  Unmapped hero records: {result['unmapped_hero_records']}")
        else:
            print(f"⚠ Aggregation completed with status: {result['status']}")

    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()