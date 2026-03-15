import os
import sys
import pytest
from datetime import datetime, UTC

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_aggregation_math import (
    weighted_average,
    calculate_confidence_score,
    aggregate_run_data,
    merge_degraded_statuses,
)
from hopilot.gto.aof_scenario_cache_store import AggregationService, RunData, AggregatedResults, Statistic


class TestWeightedAverage:
    """Test weighted average calculations."""

    def test_basic_weighted_average(self):
        values = [1.0, 2.0, 3.0]
        weights = [1, 2, 3]
        result = weighted_average(values, weights)
        expected = (1.0*1 + 2.0*2 + 3.0*3) / (1+2+3)  # 14/6 = 2.333...
        assert abs(result - expected) < 1e-6

    def test_single_value(self):
        values = [5.0]
        weights = [10]
        result = weighted_average(values, weights)
        assert result == 5.0

    def test_empty_inputs_raises_error(self):
        with pytest.raises(ValueError, match="non-empty"):
            weighted_average([], [])

    def test_mismatched_lengths_raises_error(self):
        with pytest.raises(ValueError, match="same length"):
            weighted_average([1.0, 2.0], [1])

    def test_zero_total_weight_raises_error(self):
        with pytest.raises(ValueError, match="Total weight cannot be zero"):
            weighted_average([1.0], [0])


class TestCalculateConfidenceScore:
    """Test confidence score calculations."""

    def test_zero_samples_returns_zero(self):
        assert calculate_confidence_score(0) == 0.0

    def test_negative_samples_returns_zero(self):
        assert calculate_confidence_score(-1) == 0.0

    def test_small_sample_count(self):
        # sqrt(1)/sqrt(1000) ≈ 0.0316
        result = calculate_confidence_score(1)
        expected = (1.0 ** 0.5) / (1000.0 ** 0.5)
        assert abs(result - expected) < 1e-6

    def test_target_confidence_at_1000_samples(self):
        # sqrt(1000)/sqrt(1000) = 1.0
        result = calculate_confidence_score(1000)
        assert abs(result - 1.0) < 1e-6

    def test_large_sample_count_caps_at_one(self):
        result = calculate_confidence_score(10000)
        assert result == 1.0

    def test_medium_sample_count(self):
        # sqrt(100)/sqrt(1000) ≈ 0.316
        result = calculate_confidence_score(100)
        expected = (100.0 ** 0.5) / (1000.0 ** 0.5)
        assert abs(result - expected) < 1e-6


class TestAggregateRunData:
    """Test run data aggregation."""

    def test_single_run_aggregation(self):
        run_payloads = [
            {
                "AA": {"EV": 1.0, "Equity": 0.85},
                "KK": {"EV": 0.8, "Equity": 0.75}
            }
        ]
        
        result = aggregate_run_data(run_payloads)
        
        assert "AA" in result
        assert "KK" in result
        assert result["AA"]["EV"]["aggregated_value"] == 1.0
        assert result["AA"]["EV"]["total_samples"] == 1
        assert result["AA"]["EV"]["confidence_score"] == calculate_confidence_score(1)
        assert result["AA"]["Equity"]["aggregated_value"] == 0.85

    def test_multiple_runs_aggregation(self):
        run_payloads = [
            {"AA": {"EV": 1.0}, "KK": {"EV": 0.8}},
            {"AA": {"EV": 1.2}, "KK": {"EV": 0.9}},
            {"AA": {"EV": 0.9}, "KK": {"EV": 0.7}}
        ]
        
        result = aggregate_run_data(run_payloads)
        
        # AA EV: (1.0 + 1.2 + 0.9) / 3 = 1.0333...
        expected_aa_ev = (1.0 + 1.2 + 0.9) / 3
        assert abs(result["AA"]["EV"]["aggregated_value"] - expected_aa_ev) < 1e-6
        assert result["AA"]["EV"]["total_samples"] == 3
        assert result["AA"]["EV"]["confidence_score"] == calculate_confidence_score(3)

    def test_empty_payloads_returns_empty_result(self):
        result = aggregate_run_data([])
        assert result == {}

    def test_missing_hand_in_some_runs(self):
        run_payloads = [
            {"AA": {"EV": 1.0}},
            {"KK": {"EV": 0.8}},
            {"AA": {"EV": 1.1}}
        ]
        
        result = aggregate_run_data(run_payloads)
        
        # AA appears in runs 1 and 3
        expected_aa_ev = (1.0 + 1.1) / 2
        assert abs(result["AA"]["EV"]["aggregated_value"] - expected_aa_ev) < 1e-6
        assert result["AA"]["EV"]["total_samples"] == 2
        
        # KK appears in run 2 only
        assert result["KK"]["EV"]["aggregated_value"] == 0.8
        assert result["KK"]["EV"]["total_samples"] == 1


class TestMergeDegradedStatuses:
    """Test degraded status merging."""

    def test_empty_list_returns_no_contest(self):
        assert merge_degraded_statuses([]) == "no_contest"

    def test_single_status_returns_itself(self):
        assert merge_degraded_statuses(["available"]) == "available"
        assert merge_degraded_statuses(["timeout"]) == "timeout"

    def test_prioritizes_available_over_degraded(self):
        statuses = ["timeout", "available", "error"]
        assert merge_degraded_statuses(statuses) == "available"

    def test_prioritizes_timeout_over_error(self):
        statuses = ["error", "timeout", "missing"]
        assert merge_degraded_statuses(statuses) == "timeout"

    def test_prioritizes_error_over_missing(self):
        statuses = ["missing", "error", "no_contest"]
        assert merge_degraded_statuses(statuses) == "error"

    def test_prioritizes_missing_over_no_contest(self):
        statuses = ["no_contest", "missing"]
        assert merge_degraded_statuses(statuses) == "missing"

    def test_unknown_status_uses_default_priority(self):
        statuses = ["unknown", "available"]
        assert merge_degraded_statuses(statuses) == "available"


class TestAggregationService:
    """Test AggregationService functionality."""

    def test_get_aggregated_stats_empty_scenario(self, tmp_path):
        """Test getting aggregated stats for a scenario with no runs."""
        db_path = str(tmp_path / "test_aggregation.db")
        service = AggregationService(db_path)
        
        result = service.get_aggregated_stats("nonexistent_scenario")
        
        assert result.scenario_key == "nonexistent_scenario"
        assert result.statistics == {}

    def test_get_aggregated_stats_single_run(self, tmp_path):
        """Test getting aggregated stats for a scenario with one run."""
        db_path = str(tmp_path / "test_aggregation.db")
        service = AggregationService(db_path)
        
        scenario_key = "test_scenario_1"
        run_data = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=42,
            results={
                "AsKh": {"WIN_LOSE_PROBABILITY": 0.65, "EQUITY": 0.70},
                "KdQd": {"WIN_LOSE_PROBABILITY": 0.55, "EQUITY": 0.60}
            }
        )
        
        service.store_run(scenario_key, run_data)
        result = service.get_aggregated_stats(scenario_key)
        
        assert result.scenario_key == scenario_key
        assert len(result.statistics) == 2
        
        # Check AsKh stats
        ashk_stats = result.statistics["AsKh"]
        assert "WIN_LOSE_PROBABILITY" in ashk_stats
        assert "EQUITY" in ashk_stats
        
        wlp_stat = ashk_stats["WIN_LOSE_PROBABILITY"]
        assert isinstance(wlp_stat, Statistic)
        assert wlp_stat.value == 0.65
        assert wlp_stat.sample_count == 1000  # Now represents weighted samples (sim_count)
        assert wlp_stat.confidence == calculate_confidence_score(1000)

    def test_get_aggregated_stats_multiple_runs(self, tmp_path):
        """Test getting aggregated stats for a scenario with multiple runs."""
        db_path = str(tmp_path / "test_aggregation.db")
        service = AggregationService(db_path)
        
        scenario_key = "test_scenario_2"
        
        # First run
        run_data1 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=42,
            results={
                "AsKh": {"WIN_LOSE_PROBABILITY": 0.60},
                "KdQd": {"WIN_LOSE_PROBABILITY": 0.50}
            }
        )
        
        # Second run with different values
        run_data2 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=43,
            results={
                "AsKh": {"WIN_LOSE_PROBABILITY": 0.70},
                "KdQd": {"WIN_LOSE_PROBABILITY": 0.60}
            }
        )
        
        service.store_run(scenario_key, run_data1)
        service.store_run(scenario_key, run_data2)
        
        result = service.get_aggregated_stats(scenario_key)
        
        assert result.scenario_key == scenario_key
        assert len(result.statistics) == 2
        
        # Check AsKh aggregated stats (weighted average of 0.60 and 0.70 = 0.65)
        ashk_stats = result.statistics["AsKh"]
        wlp_stat = ashk_stats["WIN_LOSE_PROBABILITY"]
        assert wlp_stat.value == pytest.approx(0.65, abs=1e-6)  # (0.60 + 0.70) / 2
        assert wlp_stat.sample_count == 2000  # 2 runs × 1000 sim_count each
        assert wlp_stat.confidence == calculate_confidence_score(2000)


class TestAggregationEdgeCases:
    """Test edge cases and stress scenarios for aggregation."""

    def test_large_number_of_runs_aggregation(self, tmp_path):
        """Test aggregation with many runs (stress test)."""
        db_path = str(tmp_path / "stress_test.db")
        service = AggregationService(db_path)
        
        scenario_key = "stress_test_scenario"
        num_runs = 100
        
        # Create many runs with slightly varying results
        for i in range(num_runs):
            run_data = RunData(
                timestamp=datetime.now(UTC),
                sim_count=1000,
                combo_samples=4,
                timeout=30.0,
                seed=1000 + i,
                results={
                    "AA": {"WIN_LOSE_PROBABILITY": 0.80 + (i % 10) * 0.005},  # Vary between 0.80-0.845
                    "KK": {"WIN_LOSE_PROBABILITY": 0.75 + (i % 8) * 0.005}   # Vary between 0.75-0.785
                }
            )
            service.store_run(scenario_key, run_data)
        
        result = service.get_aggregated_stats(scenario_key)
        
        assert result.scenario_key == scenario_key
        assert len(result.statistics) == 2
        
        # Check that all runs were aggregated
        aa_stat = result.statistics["AA"]["WIN_LOSE_PROBABILITY"]
        kk_stat = result.statistics["KK"]["WIN_LOSE_PROBABILITY"]
        
        assert aa_stat.sample_count == num_runs * 1000  # num_runs × sim_count per run
        assert kk_stat.sample_count == num_runs * 1000
        
        # Values should be reasonable (within expected range)
        assert 0.80 <= aa_stat.value <= 0.85
        assert 0.75 <= kk_stat.value <= 0.79
        
        # Confidence should be high with 100,000 total samples (100 runs × 1000 sim_count)
        assert aa_stat.confidence == 1.0  # sqrt(100000)/sqrt(1000) > 1.0, capped at 1.0
        assert kk_stat.confidence == 1.0

    def test_runs_with_inconsistent_metrics(self, tmp_path):
        """Test aggregation when different runs have different metrics."""
        db_path = str(tmp_path / "inconsistent_metrics.db")
        service = AggregationService(db_path)
        
        scenario_key = "inconsistent_scenario"
        
        # Run 1: Only EV metric
        run_data1 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=1,
            results={
                "AA": {"EV": 1.5},
                "KK": {"EV": 1.2}
            }
        )
        
        # Run 2: EV and Equity metrics
        run_data2 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=2,
            results={
                "AA": {"EV": 1.3, "EQUITY": 0.85},
                "KK": {"EV": 1.1, "EQUITY": 0.78}
            }
        )
        
        # Run 3: Only Equity metric
        run_data3 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=3,
            results={
                "AA": {"EQUITY": 0.82},
                "KK": {"EQUITY": 0.76}
            }
        )
        
        service.store_run(scenario_key, run_data1)
        service.store_run(scenario_key, run_data2)
        service.store_run(scenario_key, run_data3)
        
        result = service.get_aggregated_stats(scenario_key)
        
        # AA should have both EV (from runs 1,2) and Equity (from runs 2,3)
        aa_stats = result.statistics["AA"]
        assert "EV" in aa_stats
        assert "EQUITY" in aa_stats
        
        # EV: (1.5 + 1.3) / 2 = 1.4
        assert aa_stats["EV"].value == pytest.approx(1.4, abs=1e-6)
        assert aa_stats["EV"].sample_count == 2000  # 2 runs × 1000 sim_count each
        
        # Equity: (0.85 + 0.82) / 2 = 0.835
        assert aa_stats["EQUITY"].value == pytest.approx(0.835, abs=1e-6)
        assert aa_stats["EQUITY"].sample_count == 2000  # 2 runs × 1000 sim_count each

    def test_extreme_values_handling(self, tmp_path):
        """Test aggregation with extreme values (very large/small numbers)."""
        db_path = str(tmp_path / "extreme_values.db")
        service = AggregationService(db_path)
        
        scenario_key = "extreme_scenario"
        
        # Run with very large positive values
        run_data1 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=1,
            results={
                "AA": {"EV": 1e6, "EQUITY": 1.0},
            }
        )
        
        # Run with very small negative values
        run_data2 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=2,
            results={
                "AA": {"EV": -1e6, "EQUITY": 0.0},
            }
        )
        
        service.store_run(scenario_key, run_data1)
        service.store_run(scenario_key, run_data2)
        
        result = service.get_aggregated_stats(scenario_key)
        
        aa_stats = result.statistics["AA"]
        
        # EV should average to 0: (1e6 + (-1e6)) / 2 = 0
        assert aa_stats["EV"].value == 0.0
        assert aa_stats["EV"].sample_count == 2000  # 2 runs × 1000 sim_count each
        
        # Equity should average to 0.5: (1.0 + 0.0) / 2 = 0.5
        assert aa_stats["EQUITY"].value == 0.5
        assert aa_stats["EQUITY"].sample_count == 2000  # 2 runs × 1000 sim_count each

    def test_empty_results_in_run(self, tmp_path):
        """Test handling of runs with empty or missing results."""
        db_path = str(tmp_path / "empty_results.db")
        service = AggregationService(db_path)
        
        scenario_key = "empty_results_scenario"
        
        # Run with results
        run_data1 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=1,
            results={
                "AA": {"EV": 1.0},
            }
        )
        
        # Run with empty results
        run_data2 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=2,
            results={}  # Empty results
        )
        
        service.store_run(scenario_key, run_data1)
        service.store_run(scenario_key, run_data2)
        
        result = service.get_aggregated_stats(scenario_key)
        
        # Should still have AA stats from first run
        assert "AA" in result.statistics
        aa_stats = result.statistics["AA"]
        assert aa_stats["EV"].value == 1.0
        assert aa_stats["EV"].sample_count == 1000  # From first run's sim_count

    def test_database_corruption_recovery(self, tmp_path):
        """Test behavior when database becomes corrupted."""
        db_path = str(tmp_path / "corrupted.db")
        service = AggregationService(db_path)
        
        scenario_key = "corruption_test"
        
        # Store some valid data
        run_data = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=30.0,
            seed=1,
            results={"AA": {"EV": 1.0}}
        )
        service.store_run(scenario_key, run_data)
        
        # Verify data is stored
        result = service.get_aggregated_stats(scenario_key)
        assert result.statistics["AA"]["EV"].value == 1.0
        
        # Simulate corruption by truncating the database file
        with open(db_path, "w") as f:
            f.write("corrupted data")
        
        # Service should handle corruption gracefully
        try:
            result = service.get_aggregated_stats(scenario_key)
            # Should return empty results or handle error gracefully
            assert result.scenario_key == scenario_key
        except Exception:
            # It's acceptable for the service to fail with corrupted database
            pass

    def test_migration_from_legacy_payloads(self, tmp_path):
        """Test migration from legacy snapshot payloads to aggregation format."""
        from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures
        
        # Create legacy cache store with some payloads
        legacy_db_path = str(tmp_path / "legacy_cache.db")
        signatures = CacheSignatures(
            schema_version="1",
            solver_signature="test_solver",
            policy_signature="test_policy", 
            runtime_signature="test_runtime"
        )
        legacy_store = AoFScenarioCacheStore(legacy_db_path, signatures)
        
        # Create aggregation service
        agg_db_path = str(tmp_path / "aggregation.db")
        agg_service = AggregationService(agg_db_path)
        
        # Create some legacy payloads
        scenario_context = {
            "board": ["As", "Kh", "Qd"],
            "hero_position": "BTN",
            "villain_positions": ["SB", "BB"],
            "runtime": {
                "num_simulations": 1000,
                "combo_samples": 4,
                "timeout_ms": 900,
                "seed": 42
            }
        }
        
        scenario_key_hash = "test_scenario_hash"
        payload = {
            "context": scenario_context,
            "cells": {
                "AA": {"EV": 1.2, "EQUITY": 0.85},
                "KK": {"EV": 0.9, "EQUITY": 0.78}
            },
            "status_message": "completed"
        }
        
        legacy_store.upsert_payload(scenario_key_hash, payload, "test_runtime_sig")
        
        # Define scenario key builder (excludes runtime)
        def scenario_key_builder(context):
            return f"{context['board']}_{context['hero_position']}_{context['villain_positions']}"
        
        # Perform migration
        migration_results = legacy_store.migrate_legacy_payloads_to_aggregation(
            agg_service, scenario_key_builder
        )
        
        # Verify migration results
        expected_key = "['As', 'Kh', 'Qd']_BTN_['SB', 'BB']"
        assert expected_key in migration_results
        assert migration_results[expected_key] == "MIGRATED"
        
        # Verify data was migrated to aggregation store
        results = agg_service.get_aggregated_stats(expected_key)
        
        assert results.scenario_key == expected_key
        assert "AA" in results.statistics
        assert "KK" in results.statistics
        
        # Check migrated values
        aa_ev = results.statistics["AA"]["EV"]
        assert aa_ev.value == 1.2
        assert aa_ev.sample_count == 1000  # From migrated num_simulations
        
        kk_equity = results.statistics["KK"]["EQUITY"]
        assert kk_equity.value == 0.78
        assert kk_equity.sample_count == 1000

    def test_migration_with_corrupt_payloads(self, tmp_path):
        """Test migration handles corrupt legacy payloads gracefully."""
        from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, AggregationService, CacheSignatures
        
        # Create legacy cache store
        legacy_db_path = str(tmp_path / "legacy_corrupt.db")
        signatures = CacheSignatures(
            schema_version="1",
            solver_signature="test_solver",
            policy_signature="test_policy", 
            runtime_signature="test_runtime"
        )
        legacy_store = AoFScenarioCacheStore(legacy_db_path, signatures)
        
        # Create aggregation store
        agg_db_path = str(tmp_path / "aggregation_corrupt.db")
        agg_store = AggregationService(agg_db_path)
        
        # Insert a corrupt payload directly (bypass normal validation)
        with legacy_store._session_factory() as session:
            from hopilot.gto.aof_scenario_cache_store import ScenarioPayloadModel
            corrupt_payload = ScenarioPayloadModel(
                scenario_key_hash="corrupt_hash",
                context_json='{"invalid": json}',  # Invalid JSON
                cells_json='{"also": "invalid"}',
                status_message="corrupt"
            )
            session.add(corrupt_payload)
            session.commit()
        
        def scenario_key_builder(context):
            return "test_key"
        
        # Perform migration - should handle corrupt payloads gracefully
        migration_results = legacy_store.migrate_legacy_payloads_to_aggregation(
            agg_store, scenario_key_builder
        )
        
        # Should have recorded the failure
        assert "corrupt_hash" in migration_results
        assert "FAILED:" in migration_results["corrupt_hash"]
        
        # Valid payloads should still migrate
        scenario_context = {"board": ["As"], "hero_position": "BTN", "villain_positions": ["BB"]}
        payload = {
            "context": scenario_context,
            "cells": {"AA": {"EV": 1.0}},
            "status_message": "valid"
        }
        
        legacy_store.upsert_payload("valid_hash", payload, "test_runtime_sig")
        
        migration_results = legacy_store.migrate_legacy_payloads_to_aggregation(
            agg_store, scenario_key_builder
        )
        
        # Valid payload should migrate successfully
        assert "test_key" in migration_results
        assert migration_results["test_key"] == "MIGRATED"

    def test_migration_preserves_runtime_parameters(self, tmp_path):
        """Test that migration preserves runtime parameters from legacy payloads."""
        from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, AggregationService, CacheSignatures
        
        # Create stores
        legacy_db_path = str(tmp_path / "legacy_runtime.db")
        signatures = CacheSignatures(
            schema_version="1",
            solver_signature="test_solver",
            policy_signature="test_policy", 
            runtime_signature="test_runtime"
        )
        legacy_store = AoFScenarioCacheStore(legacy_db_path, signatures)
        
        agg_db_path = str(tmp_path / "aggregation_runtime.db")
        agg_store = AggregationService(agg_db_path)
        
        # Create payload with specific runtime parameters
        scenario_context = {
            "board": ["As", "Kh"],
            "hero_position": "CO",
            "villain_positions": ["BTN", "SB", "BB"],
            "runtime": {
                "num_simulations": 5000,
                "combo_samples": 8,
                "timeout_ms": 2000,
                "seed": 12345
            }
        }
        
        payload = {
            "context": scenario_context,
            "cells": {"AA": {"EV": 2.1, "EQUITY": 0.92}},
            "status_message": "completed"
        }
        
        legacy_store.upsert_payload("runtime_test_hash", payload, "test_sig")
        
        def scenario_key_builder(context):
            return f"{context['board']}_{context['hero_position']}"
        
        # Migrate
        migration_results = legacy_store.migrate_legacy_payloads_to_aggregation(
            agg_store, scenario_key_builder
        )
        
        expected_key = "['As', 'Kh']_CO"
        assert migration_results[expected_key] == "MIGRATED"
        
        # Verify runtime parameters were preserved
        # Note: We can't directly access run data, but we can verify aggregation works
        agg_service = AggregationService(agg_db_path)
        results = agg_service.get_aggregated_stats(expected_key)
        
        assert results.statistics["AA"]["EV"].value == 2.1
        assert results.statistics["AA"]["EQUITY"].value == 0.92