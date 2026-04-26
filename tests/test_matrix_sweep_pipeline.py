"""Integration tests for matrix sweep run querying and isolation."""

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.database.persistence import DatabasePersistenceStrategy
from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.matrix_sweep_service import MatrixSweepService
from hopilot.models import Simulation
from hopilot.poker_analyzer import PokerAnalyzer
from tests.integration.matrix_sweep_db_utils import build_matrix_sweep_contract, create_matrix_sweep_db_fixture


def test_find_run_by_contract_returns_only_selected_run_summary() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        repository = DatabaseRepository(fixture.database_url)
        service = MatrixSweepService(repository, PokerAnalyzer(), DatabasePersistenceStrategy)

        first_contract = build_matrix_sweep_contract(
            selected_position="UTG",
            position_actions={"UTG": "all_in", "BB": "call"},
            active_players=["UTG", "BB"],
        )
        second_contract = build_matrix_sweep_contract(
            selected_position="BTN",
            position_actions={"BTN": "all_in", "BB": "call"},
            active_players=["BTN", "BB"],
        )

        first_run = service.run_sweep(first_contract)
        second_run = service.run_sweep(second_contract)
        provider = BrowserDatabaseProvider(fixture.database_url)

        selected_run = service.find_run_by_contract(first_contract)
        selected_summary = service.get_run_summary(selected_run.id)
        provider_summary = provider.get_matrix_sweep_run_summary(first_contract)

        assert selected_run.id == first_run["simulation_id"]
        assert selected_run.id != second_run["simulation_id"]
        assert selected_summary["simulation"].id == first_run["simulation_id"]
        assert selected_summary["hand_matrix"].simulation_id == first_run["simulation_id"]
        assert len(selected_summary["matrix_cells"]) == 169
        assert len(selected_summary["aggregated_metrics"]) == 169
        assert selected_summary["simulation"].parameters["selected_position"] == "UTG"
        assert provider_summary["simulation"].id == first_run["simulation_id"]
        assert provider_summary["hand_matrix"].simulation_id == first_run["simulation_id"]
    finally:
        fixture.cleanup()


def test_completed_run_persists_required_contract_fields() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        repository = DatabaseRepository(fixture.database_url)
        service = MatrixSweepService(repository, PokerAnalyzer(), DatabasePersistenceStrategy)

        contract = build_matrix_sweep_contract(
            selected_position="CO",
            position_actions={"CO": "all_in", "BB": "call"},
            active_players=["CO", "BB"],
            pot_size=25.0,
            bet_amount=12.5,
        )
        run_result = service.run_sweep(contract)

        with repository.connection.session_scope() as session:
            simulation = session.query(Simulation).filter(Simulation.id == run_result["simulation_id"]).first()

        assert simulation is not None
        assert simulation.parameters["selected_position"] == contract["selected_position"]
        assert simulation.parameters["hero_action"] == contract["hero_action"]
        assert simulation.parameters["position_actions"] == contract["position_actions"]
        assert simulation.parameters["active_players"] == contract["active_players"]
        assert simulation.parameters["num_opponents"] == contract["num_opponents"]
        assert simulation.parameters["pot_size"] == contract["pot_size"]
        assert simulation.parameters["bet_amount"] == contract["bet_amount"]
        assert simulation.parameters["sims_per_combo"] == contract["sims_per_combo"]
        assert simulation.parameters["num_simulations"] == contract["sims_per_combo"]
        assert simulation.parameters["matrix_size"] == "13x13"
        assert simulation.parameters["game_type"] == contract["game_type"]
        assert simulation.parameters["run_kind"] == "matrix_sweep"
        assert simulation.parameters["raw_game_state_id_start"] is not None
        assert simulation.parameters["raw_game_state_id_end"] is not None
        assert simulation.parameters["matrix_id"] == run_result["matrix_id"]
        assert simulation.parameters["status"] == "aggregated"
    finally:
        fixture.cleanup()


def test_new_run_appends_without_mutating_existing_run_summaries() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        repository = DatabaseRepository(fixture.database_url)
        service = MatrixSweepService(repository, PokerAnalyzer(), DatabasePersistenceStrategy)

        first_contract = build_matrix_sweep_contract(selected_position="UTG")
        second_contract = build_matrix_sweep_contract(
            selected_position="BTN",
            position_actions={"BTN": "all_in", "BB": "call"},
            active_players=["BTN", "BB"],
        )

        first_run = service.run_sweep(first_contract)
        first_summary_before = service.get_run_summary(first_run["simulation_id"])
        first_cell_ids_before = [cell.id for cell in first_summary_before["matrix_cells"]]
        first_metric_ids_before = [metric.id for metric in first_summary_before["aggregated_metrics"]]

        second_run = service.run_sweep(second_contract)
        first_summary_after = service.get_run_summary(first_run["simulation_id"])

        with repository.connection.session_scope() as session:
            assert session.query(Simulation).count() == 2

        assert second_run["simulation_id"] != first_run["simulation_id"]
        assert second_run["matrix_id"] != first_run["matrix_id"]
        assert [cell.id for cell in first_summary_after["matrix_cells"]] == first_cell_ids_before
        assert [metric.id for metric in first_summary_after["aggregated_metrics"]] == first_metric_ids_before
    finally:
        fixture.cleanup()