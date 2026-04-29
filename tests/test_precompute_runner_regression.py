"""Regression tests for AoFPrecomputeRunner bugs."""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add python directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.precompute_orchestration import PrecomputeOrchestrationService


@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing."""
    # Use in-memory SQLite to avoid file locking issues
    repo = DatabaseRepository(database_url="sqlite:///:memory:")
    
    yield repo
    
    # Cleanup - close connection
    try:
        repo.connection.close()
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def mock_provider():
    """Create a mock precompute provider for fast tests."""
    provider = Mock()
    
    def mock_build_context(*args, **kwargs):
        position = kwargs.get("position", args[0] if len(args) > 0 else "UTG")
        metric = kwargs.get("metric", args[1] if len(args) > 1 else "WIN_LOSE_PROBABILITY")
        position_actions = kwargs.get("position_actions", args[2] if len(args) > 2 else {})
        action = position_actions.get(position, "UNKNOWN")
        strict_current_action = kwargs.get("strict_current_action", False)

        return {
            "position": position,
            "action": action,
            "metric": metric,
            "position_actions": position_actions,
            "active_players": sum(1 for act in position_actions.values() if act != "FOLD"),
            "pot_size": float(kwargs.get("pot_size", 20.0)),
            "bet_amount": float(kwargs.get("bet_amount", 10.0)),
            "effective_mode": "strict-current-action" if strict_current_action else "analysis",
            "timeout_ms": 30000,
        }

    def mock_get_matrix_payload(*args, **kwargs):
        """Return a payload with successful cells."""
        position = kwargs.get("position", args[0] if len(args) > 0 else "UTG")
        metric = kwargs.get("metric", args[1] if len(args) > 1 else "WIN_LOSE_PROBABILITY")
        position_actions = kwargs.get("position_actions", args[2] if len(args) > 2 else {})
        action = position_actions.get(position, "UNKNOWN")
        strict_current_action = kwargs.get("strict_current_action", False)
        context = {
            "position": position,
            "action": action,
            "metric": metric,
            "position_actions": position_actions,
            "active_players": sum(1 for act in position_actions.values() if act != "FOLD"),
            "pot_size": float(kwargs.get("pot_size", 20.0)),
            "bet_amount": float(kwargs.get("bet_amount", 10.0)),
            "effective_mode": "strict-current-action" if strict_current_action else "analysis",
            "timeout_ms": 30000,
        }
        return {
            "context": context,
            "cells": [
                {
                    "row": i,
                    "col": j,
                    "hand_key": f"{chr(65+i)}vs{chr(65+j)}",
                    "metrics": {
                        "win_equity": 0.5 + i * 0.01,
                        "lose_equity": 0.3 - i * 0.01,
                        "tie_equity": 0.2,
                        "ev": 2.0 + i * 0.1,
                        "eqr": 1.2,
                    },
                    "status": "AVAILABLE",
                }
                for i in range(3)
                for j in range(3)
            ],
            "status": "AVAILABLE",
            "status_message": "Computation complete",
        }
    
    provider._build_context = Mock(side_effect=mock_build_context)
    provider.get_matrix_payload = Mock(side_effect=mock_get_matrix_payload)
    
    return provider


class TestEnumerateScenariosRegression:
    """Test that enumerate_scenarios includes required scenario_key field."""
    
    def test_scenarios_include_scenario_key(self):
        """Bug: enumerate_scenarios didn't include scenario_key, causing KeyError in run()."""
        profile = PrecomputeProfile(
            positions=["UTG"],
            metrics=["WinRate"],
            strict_modes=[True],
        )
        
        runner = AoFPrecomputeRunner(Mock(), database_url="sqlite:///:memory:")
        scenarios = runner.enumerate_scenarios(profile)
        
        # Should have at least one scenario
        assert len(scenarios) > 0, "Should enumerate at least one scenario"
        
        # Each scenario must have scenario_key
        for scenario in scenarios:
            assert "scenario_key" in scenario, (
                f"Scenario missing 'scenario_key': {scenario}"
            )
            assert isinstance(scenario["scenario_key"], str), (
                f"scenario_key must be string, got {type(scenario['scenario_key'])}"
            )
            assert len(scenario["scenario_key"]) > 0, (
                "scenario_key must not be empty"
            )
    
    def test_scenario_key_includes_position_and_metric(self):
        """Each scenario_key should be identifiable by position."""
        profile = PrecomputeProfile(
            positions=["UTG", "BTN"],
            metrics=["WinRate", "EachWayEV"],
            strict_modes=[True],
        )
        
        runner = AoFPrecomputeRunner(Mock(), database_url="sqlite:///:memory:")
        scenarios = runner.enumerate_scenarios(profile)
        
        seen_keys = set()
        for scenario in scenarios:
            key = scenario["scenario_key"]
            # Keys should be unique (position:action format)
            assert key not in seen_keys, f"Duplicate scenario_key: {key}"
            seen_keys.add(key)
            
            # Key should contain the position
            assert scenario["position"] in key, (
                f"Key '{key}' should contain position '{scenario['position']}'"
            )
            
            # Key should have position:action format (parseable by persist code)
            assert ":" in key, f"Key '{key}' should have position:action format with ':' separator"
    
    def test_scenario_has_all_required_fields(self):
        """Each scenario must have all fields needed by run()."""
        profile = PrecomputeProfile(
            positions=["UTG"],
            metrics=["WinRate"],
            strict_modes=[True],
        )
        
        runner = AoFPrecomputeRunner(Mock(), database_url="sqlite:///:memory:")
        scenarios = runner.enumerate_scenarios(profile)
        
        required_fields = {
            "scenario_key",
            "position",
            "metric",
            "position_actions",
            "strict_current_action",
        }
        
        for scenario in scenarios:
            missing = required_fields - set(scenario.keys())
            assert not missing, f"Scenario missing fields: {missing}"


class TestPrecomputeRunNoKeyError:
    """Test that precompute run() doesn't crash with KeyError on scenario_key."""
    
    def test_run_with_small_profile_completes(self, temp_db, mock_provider):
        """Bug: run() would crash with KeyError: 'scenario_key' before fix."""
        profile = PrecomputeProfile(
            positions=["UTG"],
            metrics=["WinRate"],
            strict_modes=[True],
            simulations_per_cell=1,
        )
        
        runner = AoFPrecomputeRunner(
            provider=mock_provider,
            database_url="sqlite:///:memory:"
        )
        
        # This should not raise KeyError
        result = runner.run(profile, max_scenarios=2)
        
        # Should complete without error
        assert result == 0, f"Run should return 0, got {result}"

    def test_run_does_not_invoke_payload_contract_during_orchestration(self, temp_db, mock_provider):
        """Regression: orchestration should not invoke provider payload retrieval."""
        mock_provider.get_matrix_payload.side_effect = AssertionError(
            "Payload contract should not be called during orchestration"
        )

        runner = AoFPrecomputeRunner(
            provider=mock_provider,
            database_url="sqlite:///:memory:"
        )

        profile = PrecomputeProfile(
            positions=["UTG"],
            metrics=["WinRate"],
            strict_modes=[True],
            simulations_per_cell=1,
        )

        result = runner.run(profile, max_scenarios=1)

        assert result == 0
        assert not mock_provider.get_matrix_payload.called
    
    def test_run_accesses_scenario_key_without_error(self, temp_db, mock_provider):
        """Verify the run() method can access scenario_key from enumerated scenarios."""
        profile = PrecomputeProfile(
            positions=["BTN"],
            metrics=["EachWayEV"],
            strict_modes=[False],
            simulations_per_cell=1,
        )
        
        runner = AoFPrecomputeRunner(
            provider=mock_provider,
            database_url="sqlite:///:memory:"
        )
        runner.precompute_orchestration_service.resolve_scenario_context = MagicMock(
            side_effect=runner.precompute_orchestration_service.resolve_scenario_context
        )
        
        # Run should successfully access scenario_key for logging and processing
        result = runner.run(profile, max_scenarios=1)
        
        assert result == 0
        
        # Verify provider context builder was used to orchestrate the run.
        assert mock_provider._build_context.called, (
            "Provider _build_context should have been called during run()"
        )
        assert runner.precompute_orchestration_service.resolve_scenario_context.called, (
            "Runner should delegate context resolution to PrecomputeOrchestrationService"
        )


class TestDataPersistenceAfterFix:
    """Test that data is actually persisted to database after bug fixes."""
    
    def test_scenarios_persist_simulation_record(self, temp_db, mock_provider):
        """After fixes, simulations should be persisted to database."""
        profile = PrecomputeProfile(
            positions=["SB"],
            metrics=["WinRate"],
            strict_modes=[True],
            simulations_per_cell=1,
        )
        
        runner = AoFPrecomputeRunner(
            provider=mock_provider,
            database_url="sqlite:///:memory:"
        )
        
        # Run precompute
        result = runner.run(profile, max_scenarios=2)
        assert result == 0
        
        # Check that simulations were recorded
        from sqlalchemy import text
        
        with runner.database_repository.connection.session_scope() as session:
            result = session.execute(text("SELECT COUNT(*) FROM simulations"))
            sim_count = result.scalar()
            
            assert sim_count > 0, (
                "After run(), database should have simulation records"
            )
    
    def test_scenarios_persist_hand_matrices(self, temp_db, mock_provider):
        """After fixes, hand matrices should be persisted."""
        profile = PrecomputeProfile(
            positions=["BB"],
            metrics=["EachWayEV"],
            strict_modes=[True],
            simulations_per_cell=1,
        )
        
        runner = AoFPrecomputeRunner(
            provider=mock_provider,
            database_url="sqlite:///:memory:"
        )
        
        result = runner.run(profile, max_scenarios=1)
        assert result == 0
        
        from sqlalchemy import text
        
        with runner.database_repository.connection.session_scope() as session:
            result = session.execute(text("SELECT COUNT(*) FROM hand_matrices"))
            matrix_count = result.scalar()
            
            assert matrix_count > 0, (
                "After run(), database should have hand_matrix records"
            )
    
    def test_scenarios_persist_matrix_cells_with_equity(self, temp_db, mock_provider):
        """After fixes, matrix cells should be persisted with equity data."""
        profile = PrecomputeProfile(
            positions=["UTG"],
            metrics=["WinRate"],
            strict_modes=[False],
            simulations_per_cell=1,
        )
        
        runner = AoFPrecomputeRunner(
            provider=mock_provider,
            database_url="sqlite:///:memory:"
        )
        
        result = runner.run(profile, max_scenarios=1)
        assert result == 0
        
        from sqlalchemy import text
        
        with runner.database_repository.connection.session_scope() as session:
            # Check matrix cells
            result = session.execute(text("SELECT COUNT(*) FROM matrix_cells"))
            cell_count = result.scalar()
            assert cell_count > 0, "Should have persisted matrix cells"
            
            # Check aggregated metrics (equity storage)
            result = session.execute(text("SELECT COUNT(*) FROM aggregated_metrics"))
            metric_count = result.scalar()
            assert metric_count > 0, "Should have persisted aggregated metrics with equity"
            
            # Verify equity values are non-null
            result = session.execute(
                text("SELECT COUNT(*) FROM aggregated_metrics WHERE equity IS NOT NULL")
            )
            equity_count = result.scalar()
            assert equity_count == metric_count, (
                "All aggregated metrics should have equity values"
            )


class TestScenarioStructureConsistency:
    """Test that scenario structure remains consistent across different profiles."""
    
    def test_different_profiles_same_structure(self):
        """All scenarios, regardless of profile, should have same structure."""
        runner = AoFPrecomputeRunner(Mock(), database_url="sqlite:///:memory:")
        
        profile1 = PrecomputeProfile(
            positions=["UTG"],
            metrics=["WinRate"],
            strict_modes=[True],
        )
        
        profile2 = PrecomputeProfile(
            positions=["UTG", "BTN"],
            metrics=["WinRate", "EachWayEV"],
            strict_modes=[True, False],
        )
        
        scenarios1 = runner.enumerate_scenarios(profile1)
        scenarios2 = runner.enumerate_scenarios(profile2)
        
        # All scenarios should have same keys
        keys1 = set(scenarios1[0].keys())
        keys2 = set(scenarios2[0].keys())
        
        assert keys1 == keys2, (
            f"Scenario structure differs: {keys1} vs {keys2}"
        )
    
    def test_position_actions_consistent_structure(self):
        """position_actions should always have same keys."""
        runner = AoFPrecomputeRunner(Mock(), database_url="sqlite:///:memory:")
        
        profile = PrecomputeProfile(
            positions=["UTG", "BTN"],
            metrics=["WinRate"],
            strict_modes=[True, False],
        )
        
        scenarios = runner.enumerate_scenarios(profile)
        
        expected_actions = {"UTG", "BTN", "SB", "BB"}
        
        for scenario in scenarios:
            actions = scenario["position_actions"]
            assert set(actions.keys()) == expected_actions, (
                f"position_actions should have keys {expected_actions}, got {set(actions.keys())}"
            )
            
            # Each action should be FOLD or ALL_IN
            for action in actions.values():
                assert action in {"FOLD", "ALL_IN"}, (
                    f"Action should be FOLD or ALL_IN, got {action}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
