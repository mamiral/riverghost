"""Integration tests for the production matrix sweep service."""

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.database import DatabaseConnection
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.matrix_sweep_service import MatrixSweepService
from hopilot.models import AggregatedMetric, GameState, HandMatrix, MatrixCell, Player, Simulation
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.database.persistence import DatabasePersistenceStrategy
from tests.integration.matrix_sweep_db_utils import build_matrix_sweep_contract, create_matrix_sweep_db_fixture


def test_matrix_sweep_raw_phase_writes_only_raw_records_before_aggregation() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        service = MatrixSweepService(repository, PokerAnalyzer(), DatabasePersistenceStrategy)

        raw_result = service.run_raw_sweep(build_matrix_sweep_contract(sims_per_combo=1))

        with repository.db_connection.session_scope() as session:
            assert session.query(Simulation).count() == 1
            assert session.query(GameState).count() == raw_result["raw_game_states_written"]
            assert session.query(Player).count() == raw_result["raw_players_written"]
            assert session.query(HandMatrix).count() == 0
            assert session.query(MatrixCell).count() == 0
            assert session.query(AggregatedMetric).count() == 0

        assert raw_result["status"] == "raw_sweep_complete"
        assert raw_result["raw_game_states_written"] > 0
        assert raw_result["raw_players_written"] >= raw_result["raw_game_states_written"] * 2
        assert raw_result["failed_combinations"] == 0
    finally:
        fixture.cleanup()