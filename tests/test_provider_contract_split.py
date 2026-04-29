"""Tests for provider contract separation between orchestration and browser payload paths."""

import os
import sys
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, PrecomputeProfile
from hopilot.gto.precompute_orchestration import PrecomputeOrchestrationService


class TestProviderContractSplit:
    def test_orchestration_supports_direct_context_contract_only(self):
        provider = Mock()
        provider._build_context = MagicMock(return_value={
            "position": "UTG",
            "action": "ALL_IN",
            "metric": "EV",
            "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "strict_current_action": False,
            "game_type": "nlhe",
        })
        provider.get_matrix_payload = MagicMock(side_effect=AssertionError("Payload contract must not be used for orchestration"))

        orchestration = PrecomputeOrchestrationService(provider=provider, database_repository=Mock())

        context = orchestration.resolve_scenario_context({
            "position": "UTG",
            "metric": "EV",
            "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
            "strict_current_action": False,
        })

        assert context["position"] == "UTG"
        assert context["action"] == "ALL_IN"
        assert provider._build_context.called
        assert not provider.get_matrix_payload.called

    def test_provider_contract_helpers_identify_orchestration_and_payload_capabilities(self):
        provider = Mock()
        provider._build_context = Mock()
        provider.get_matrix_payload = Mock()

        assert PrecomputeOrchestrationService.supports_direct_context_contract(provider)
        assert PrecomputeOrchestrationService.supports_payload_contract(provider)

        assert not PrecomputeOrchestrationService.supports_direct_context_contract(None)
        assert not PrecomputeOrchestrationService.supports_payload_contract(None)

    def test_runner_does_not_invoke_payload_contract_during_orchestration(self):
        provider = Mock()
        provider._build_context = MagicMock(return_value={
            "position": "UTG",
            "action": "ALL_IN",
            "metric": "EV",
            "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "strict_current_action": False,
            "game_type": "nlhe",
        })
        provider.get_matrix_payload = MagicMock(side_effect=AssertionError("Browser payload contract must not be invoked during orchestration"))

        runner = AoFPrecomputeRunner(provider=provider, database_url="sqlite:///:memory:")
        runner._execute_matrix_sweep = MagicMock(return_value={
            "simulation_id": 1,
            "matrix_id": 1,
            "raw_game_states_written": 0,
            "raw_players_written": 0,
            "matrix_cells_written": 169,
            "aggregated_metrics_written": 169,
            "failed_combinations": 0,
            "unmapped_hero_records": 0,
            "status": "aggregated",
        })

        result = runner.run(profile=PrecomputeProfile(simulations_per_cell=1), max_scenarios=1)

        assert result == 0
        assert provider._build_context.called
        assert not provider.get_matrix_payload.called
