"""Integration tests for matrix sweep aggregation and rerun behavior."""

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.database import DatabaseConnection
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.matrix_sweep_aggregation_service import MatrixSweepAggregationService
from hopilot.models import AggregatedMetric, GameState, HandMatrix, MatrixCell, Simulation
from tests.integration.matrix_sweep_db_utils import create_matrix_sweep_db_fixture, seed_matrix_sweep_raw_run


def test_aggregate_run_writes_one_simulation_one_matrix_and_169_cell_summaries() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        seed = seed_matrix_sweep_raw_run(repository)
        service = MatrixSweepAggregationService(repository)

        result = service.aggregate_run(seed["simulation_id"])

        with repository.db_connection.session_scope() as session:
            assert session.query(Simulation).count() == 1
            assert session.query(HandMatrix).count() == 1
            assert session.query(MatrixCell).count() == 169
            assert session.query(AggregatedMetric).count() == 169

        assert result["simulation_id"] == seed["simulation_id"]
        assert result["matrix_cells_written"] == 169
        assert result["aggregated_metrics_written"] == 169
        assert result["unmapped_hero_records"] == 0
        assert result["status"] == "aggregated"
    finally:
        fixture.cleanup()


def test_rerun_aggregation_replaces_only_selected_run_summaries_and_keeps_raw_rows() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        seed = seed_matrix_sweep_raw_run(repository)
        service = MatrixSweepAggregationService(repository)

        initial_result = service.aggregate_run(seed["simulation_id"])
        initial_summary = repository.get_matrix_sweep_summary(seed["simulation_id"])
        initial_cell_ids = [cell.id for cell in initial_summary["matrix_cells"]]
        initial_metric_ids = [metric.id for metric in initial_summary["aggregated_metrics"]]

        rerun_result = service.rerun_aggregation(seed["simulation_id"])
        rerun_summary = repository.get_matrix_sweep_summary(seed["simulation_id"])
        rerun_cell_ids = [cell.id for cell in rerun_summary["matrix_cells"]]
        rerun_metric_ids = [metric.id for metric in rerun_summary["aggregated_metrics"]]

        with repository.db_connection.session_scope() as session:
            assert session.query(GameState).count() == seed["raw_counts"]["raw_game_states"]
            assert session.query(MatrixCell).count() == 169
            assert session.query(AggregatedMetric).count() == 169

        assert initial_result["matrix_id"] == rerun_result["matrix_id"]
        assert initial_cell_ids != rerun_cell_ids
        assert initial_metric_ids != rerun_metric_ids
        assert rerun_result["matrix_cells_recreated"] == 169
        assert rerun_result["aggregated_metrics_recreated"] == 169
        assert rerun_result["status"] == "aggregated"
    finally:
        fixture.cleanup()


def test_aggregate_run_excludes_unmappable_hero_records_and_reports_them() -> None:
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        seed = seed_matrix_sweep_raw_run(repository, include_unmapped_hero_record=True)
        service = MatrixSweepAggregationService(repository)

        result = service.aggregate_run(seed["simulation_id"])
        summary = repository.get_matrix_sweep_summary(seed["simulation_id"])

        assert len(summary["matrix_cells"]) == 169
        assert len(summary["aggregated_metrics"]) == 169
        assert result["unmapped_hero_records"] == 1
        assert result["status"] == "aggregated"
    finally:
        fixture.cleanup()


def test_aggregate_run_calculates_ev_correctly_based_on_simulation_parameters() -> None:
    """Test that EV is calculated correctly using pot_size from simulation parameters."""
    fixture = create_matrix_sweep_db_fixture(use_temp=True)
    try:
        conn = DatabaseConnection(fixture.database_url)
        conn.create_tables()
        repository = SimulationRepository(conn)
        seed = seed_matrix_sweep_raw_run(repository)
        service = MatrixSweepAggregationService(repository)

        result = service.aggregate_run(seed["simulation_id"])
        summary = repository.get_matrix_sweep_summary(seed["simulation_id"])

        # Check that EV is calculated for metrics with samples
        metrics_with_ev = [m for m in summary["aggregated_metrics"] if m.ev is not None and m.sample_count and m.sample_count > 0]
        assert len(metrics_with_ev) > 0, "Should have metrics with EV calculated"

        # Get simulation parameters to verify EV calculation
        sim = repository.get_simulation_record(seed["simulation_id"])
        pot_size = sim.parameters.get("pot_size", 0.0)

        # Verify EV calculation: EV should equal equity * pot_size for all-in scenarios
        for metric in metrics_with_ev:
            if metric.equity is not None and metric.equity > 0:
                expected_ev = float(metric.equity) * pot_size
                actual_ev = float(metric.ev)
                assert abs(actual_ev - expected_ev) < 0.0001, f"EV calculation incorrect: expected {expected_ev}, got {actual_ev}"
                
                # EV should be positive and not exceed pot_size
                assert actual_ev > 0, f"EV should be positive, got {actual_ev}"
                assert actual_ev <= pot_size, f"EV should not exceed pot_size {pot_size}, got {actual_ev}"

    finally:
        fixture.cleanup()
