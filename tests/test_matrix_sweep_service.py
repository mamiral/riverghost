"""Integration tests for the production matrix sweep service."""

import os
import sys
import threading
import time


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.database import DatabaseConnection
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.matrix_sweep_service import MatrixSweepService
from hopilot.models import AggregatedMetric, GameState, HandMatrix, MatrixCell, Player, Simulation
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.database.persistence import BatchingPersistenceStrategy, DatabasePersistenceStrategy
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


def test_matrix_sweep_raw_phase_accepts_max_workers_contract() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        service = MatrixSweepService(repository, PokerAnalyzer(), DatabasePersistenceStrategy)

        raw_result = service.run_raw_sweep(
            build_matrix_sweep_contract(sims_per_combo=1, max_workers=4)
        )

        assert raw_result["status"] == "raw_sweep_complete"
        assert raw_result["raw_game_states_written"] > 0
        assert raw_result["raw_players_written"] >= raw_result["raw_game_states_written"] * 2
        assert raw_result["failed_combinations"] == 0
    finally:
        fixture.cleanup()


def test_matrix_sweep_raw_phase_accepts_queue_maxsize_parameter() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        service = MatrixSweepService(repository, PokerAnalyzer(), DatabasePersistenceStrategy)

        raw_result = service.run_raw_sweep(
            build_matrix_sweep_contract(sims_per_combo=1), queue_maxsize=15000
        )

        assert raw_result["status"] == "raw_sweep_complete"
        assert raw_result["raw_game_states_written"] > 0
        assert raw_result["failed_combinations"] == 0
    finally:
        fixture.cleanup()


def test_matrix_sweep_raw_phase_stops_active_combo_evaluation_when_stop_event_is_triggered() -> None:
    class SlowCancelableAnalyzer:
        def calculate_odds_random_opponents(
            self,
            hero_hole_cards,
            board_cards,
            num_opponents,
            num_simulations,
            persistence=None,
            return_individual_outcomes=False,
            pot_size=0.0,
            bet_amount=0.0,
            cancel_check=None,
        ):
            for _ in range(20):
                time.sleep(0.02)
                if cancel_check is not None and cancel_check():
                    return None
            return {"valid_simulations": 1}

    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        service = MatrixSweepService(
            repository,
            SlowCancelableAnalyzer(),
            DatabasePersistenceStrategy,
        )

        stop_event = threading.Event()
        threading.Timer(0.05, stop_event.set).start()

        raw_result = service.run_raw_sweep(
            build_matrix_sweep_contract(
                sims_per_combo=1,
                max_workers=1,
                stop_event=stop_event,
            )
        )

        assert raw_result["status"] == "raw_sweep_stopped"
        assert raw_result["failed_combinations"] > 0
    finally:
        fixture.cleanup()


def test_matrix_sweep_raw_phase_flushes_buffered_rows_before_capturing_boundaries() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        service = MatrixSweepService(
            repository,
            PokerAnalyzer(),
            lambda session: BatchingPersistenceStrategy(session=session, batch_size=1_000_000),
        )

        raw_result = service.run_raw_sweep(build_matrix_sweep_contract(sims_per_combo=1))

        assert raw_result["raw_game_states_written"] > 0
        assert raw_result["raw_players_written"] >= raw_result["raw_game_states_written"] * 2
        assert raw_result["failed_combinations"] == 0
    finally:
        fixture.cleanup()