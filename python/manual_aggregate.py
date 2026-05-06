import os
import sys

# Ensure hopilot is in path
sys.path.insert(0, os.path.join(os.getcwd()))

from hopilot.database import DatabaseConnection
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.matrix_sweep_aggregation_service import MatrixSweepAggregationService

db_path = 'hopilot/data/normalized_poker.sqlite3'
if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

db_url = f"sqlite:///{db_path}"
conn = DatabaseConnection(db_url)
repository = SimulationRepository(conn)
aggregator = MatrixSweepAggregationService(repository)

SIM_ID = 2

print(f"--- Attempting Manual Aggregation for Simulation ID {SIM_ID} ---")
try:
    result = aggregator.aggregate_run(SIM_ID)
    print("Aggregation successful!")
    print(f"Result: {result}")
except Exception as e:
    print(f"Aggregation FAILED: {e}")
    import traceback
    traceback.print_exc()
