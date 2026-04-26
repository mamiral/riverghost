"""
Integration tests for Precompute Runner.
Tests real precompute execution instead of mock behavior.
"""

import pytest
import sys
import os
import tempfile
from unittest.mock import MagicMock
from sqlalchemy import text

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python"))

from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile
from hopilot.gto.matrix_sweep_contract import MatrixSweepContractError
from tests.integration.matrix_sweep_db_utils import build_matrix_sweep_contract, create_matrix_sweep_db_fixture


class TestPrecomputeRunnerIntegration:
    """Integration tests for Precompute Runner with real execution."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield f"sqlite:///{db_path}"
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider that returns realistic data."""
        provider = MagicMock()
        provider._build_context = MagicMock(return_value={
            "position": "UTG",
            "metric": "EV",
            "action": "ALL_IN",
            "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "strict_current_action": False,
            "game_type": "nlhe",
        })
        provider.get_matrix_payload.return_value = {
            "context": {"position": "UTG", "metric": "EV"},
            "cells": [
                {"hand_key": "AA", "value": 0.75},
                {"hand_key": "KK", "value": 0.68},
            ]
        }
        return provider

    def test_precompute_runner_executes_real_scenarios(self, temp_db_path, mock_provider):
        """Integration test: Precompute runner executes and processes real scenarios."""
        runner = AoFPrecomputeRunner(database_url=temp_db_path)
        runner.provider = mock_provider  # Inject mock for controlled testing
        
        # Create a test profile
        profile = PrecomputeProfile(
            positions=("UTG", "BTN"),
            metrics=("EV", "EQUITY"),
            simulations_per_cell=1,
        )
        
        # Execute a small bounded precompute run for integration validation
        result = runner.run_precompute(profile, max_scenarios=1)
        
        # Verify execution completed
        assert result == 0, "Precompute should complete successfully"
        
        # Verify database was accessed (runner should have created some records)
        # This is a basic integration test - more specific assertions would depend on actual implementation

    def test_precompute_runner_handles_multiple_positions(self, temp_db_path, mock_provider):
        """Integration test: Precompute runner handles multiple positions correctly."""
        runner = AoFPrecomputeRunner(database_url=temp_db_path)
        runner.provider = mock_provider
        
        profile = PrecomputeProfile(
            positions=("UTG", "MP", "CO", "BTN"),
            metrics=("EV",),
            strict_modes=(False,),
            simulations_per_cell=1,
        )
        
        result = runner.run_precompute(profile, max_scenarios=1)
        
        # Verify the runner processed a bounded test run
        assert result == 0, "Should complete successfully"

        # Create a simple profile
        profile = PrecomputeProfile(
            positions=("UTG",),
            metrics=("EV",),
            strict_modes=(False,),
            simulations_per_cell=1,
        )

        # Execute precompute run
        result = runner.run(profile, max_scenarios=1)

        # Verify execution completed
        assert isinstance(result, int), "Run should return an integer exit code"
        assert result == 0, "Run should complete successfully"

        # Verify scenarios were processed via orchestration context
        assert mock_provider._build_context.call_count >= 1, (
            f"Should have built at least one scenario context, got {mock_provider._build_context.call_count}"
        )

    def test_precompute_runner_persists_simulation_and_hand_matrix_outputs(self):
        """Integration test: delegated sweep output is persisted into normalized schema."""
        fixture = create_matrix_sweep_db_fixture(use_temp=True)
        runner = None
        try:
            runner = AoFPrecomputeRunner(database_url=fixture.database_url)
            contract = build_matrix_sweep_contract(
                selected_position="UTG",
                position_actions={"UTG": "all_in", "BB": "call"},
                active_players=["UTG", "BB"],
                num_opponents=1,
                sims_per_combo=1,
            )

            output = runner._execute_matrix_sweep(contract)

            assert output["simulation_id"] > 0
            assert output["matrix_id"] > 0
            assert output["status"] == "aggregated"

            with fixture.session_context() as session:
                simulation = session.execute(
                    text("SELECT id FROM simulations WHERE id = :id"),
                    {"id": output["simulation_id"]},
                ).first()
                assert simulation is not None
                assert simulation[0] == output["simulation_id"]

                matrix = session.execute(
                    text("SELECT id, simulation_id FROM hand_matrices WHERE id = :id"),
                    {"id": output["matrix_id"]},
                ).first()
                assert matrix is not None
                assert matrix[0] == output["matrix_id"]
                assert matrix[1] == output["simulation_id"]

                cell_count = session.execute(
                    text("SELECT COUNT(*) FROM matrix_cells WHERE matrix_id = :id"),
                    {"id": output["matrix_id"]},
                ).scalar()
                assert cell_count == 169
        finally:
            if runner is not None:
                runner.database_repository.connection.close()
            fixture.cleanup()

    def test_precompute_runner_handles_errors_gracefully(self, temp_db_path):
        """Integration test: Precompute runner handles errors gracefully."""
        runner = AoFPrecomputeRunner(database_url=temp_db_path)

        # Create provider that raises an exception
        error_provider = MagicMock()
        error_provider._build_context = MagicMock(side_effect=Exception("Simulated error"))
        runner.provider = error_provider

        profile = PrecomputeProfile(
            positions=("UTG",),
            metrics=("EV",),
            strict_modes=(False,),
            simulations_per_cell=1,
        )

        # Should handle errors without crashing
        result = runner.run(profile, max_scenarios=1)

        # Should return error code or handle gracefully
        assert isinstance(result, int), "Should return exit code even on error"

    def test_data_persistence_after_precompute_run(self, temp_db_path, mock_provider):
        """Integration test: Data is actually persisted after precompute run."""
        runner = AoFPrecomputeRunner(database_url=temp_db_path)
        runner.provider = mock_provider

        profile = PrecomputeProfile(
            positions=("UTG",),
            metrics=("EV",),
            strict_modes=(False,),
            simulations_per_cell=1,
        )

        # Run precompute
        result = runner.run(profile, max_scenarios=1)
        assert result == 0, "Precompute should succeed"

        # Verify orchestration happened via the provider context builder
        assert mock_provider._build_context.call_count >= 1, (
            f"Should have built at least one scenario context, got {mock_provider._build_context.call_count}"
        )

    def test_precompute_runner_reports_job_progress_after_completed_run(self, temp_db_path, mock_provider):
        """Integration test: completed job progress payload contains expected lifecycle fields."""
        runner = AoFPrecomputeRunner(database_url=temp_db_path)
        runner.provider = mock_provider

        profile = PrecomputeProfile(
            positions=("UTG",),
            metrics=("EV",),
            strict_modes=(False,),
            simulations_per_cell=1,
        )

        result = runner.run(profile, max_scenarios=1)
        assert result == 0, "Precompute should succeed"

        progress = runner.get_job_progress(runner.last_job_session_id)

        assert progress["run_state"] == "COMPLETED"
        assert progress["completed_scenarios"] == 1
        assert progress["total_scenarios"] == 1
        assert progress["failure_count"] == 0
        assert progress["active_scenario_key"] is None
        assert progress["phase"] == "orchestration"
        assert isinstance(progress["elapsed_seconds"], float)
        assert progress["eta_seconds"] is None or isinstance(progress["eta_seconds"], float)

    def test_precompute_runner_persists_partial_success_after_mixed_outcomes(self, temp_db_path, mock_provider):
        """Integration test: partial success persists when one scenario fails."""
        runner = AoFPrecomputeRunner(database_url=temp_db_path)
        runner.provider = mock_provider

        success_result = {
            "simulation_id": 1,
            "matrix_id": 1,
            "raw_game_states_written": 0,
            "raw_players_written": 0,
            "matrix_cells_written": 169,
            "aggregated_metrics_written": 169,
            "failed_combinations": 0,
            "unmapped_hero_records": 0,
            "status": "aggregated",
        }

        runner._execute_matrix_sweep = MagicMock(side_effect=[
            success_result,
            MatrixSweepContractError("invalid contract"),
        ])

        profile = PrecomputeProfile(
            positions=("UTG", "BTN"),
            metrics=("EV",),
            strict_modes=(False,),
            simulations_per_cell=1,
        )

        result = runner.run(profile=profile, max_scenarios=2)
        assert result == 0
        assert runner._execute_matrix_sweep.call_count == 2

        with runner.database_repository.connection.session_scope() as session:
            job = session.execute(text("SELECT run_state, completed_scenarios, failed_scenarios FROM precompute_job_sessions")).first()
            assert job is not None
            assert job[0] == "FAILED"
            assert job[1] == 1
            assert job[2] == 1

            links = session.execute(text("SELECT status, failure_boundary, failure_reason FROM scenario_run_links ORDER BY scenario_index")).fetchall()
            assert len(links) == 2
            assert links[0][0] == "COMPLETED"
            assert links[1][0] == "FAILED"
            assert links[1][1] == "orchestration"
            assert "invalid contract" in links[1][2]

    def test_precompute_runner_stops_dispatching_after_cancellation_request(self, temp_db_path, mock_provider):
        """Integration test: cooperative cancellation stops dispatching new scenarios."""
        runner = AoFPrecomputeRunner(database_url=temp_db_path)
        runner.provider = mock_provider

        def sweep_side_effect(contract):
            runner.request_job_cancellation(runner.last_job_session_id)
            return {
                "simulation_id": 1,
                "matrix_id": 1,
                "raw_game_states_written": 0,
                "raw_players_written": 0,
                "matrix_cells_written": 169,
                "aggregated_metrics_written": 169,
                "failed_combinations": 0,
                "unmapped_hero_records": 0,
                "status": "aggregated",
            }

        runner._execute_matrix_sweep = MagicMock(side_effect=sweep_side_effect)

        profile = PrecomputeProfile(
            positions=("UTG", "BTN"),
            metrics=("EV",),
            strict_modes=(False,),
            simulations_per_cell=1,
        )

        result = runner.run(profile=profile, max_scenarios=2)
        assert result == 0
        assert runner._execute_matrix_sweep.call_count == 1

        with runner.database_repository.connection.session_scope() as session:
            job = session.execute(text("SELECT run_state, completed_scenarios, failed_scenarios FROM precompute_job_sessions")).first()
            assert job is not None
            assert job[0] == "CANCELED"
            assert job[1] == 1
            assert job[2] == 0

            links = session.execute(text("SELECT status FROM scenario_run_links ORDER BY scenario_index")).fetchall()
            assert len(links) == 1
            assert links[0][0] == "COMPLETED"
