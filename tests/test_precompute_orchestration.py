"""Unit tests for PrecomputeOrchestrationService."""

import os
import sys
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest

from hopilot.gto.precompute_orchestration import PrecomputeOrchestrationService


def test_resolve_scenario_context_uses_provider_build_context() -> None:
    provider = Mock()
    provider._build_context = MagicMock(return_value={
        "position": "UTG",
        "action": "ALL_IN",
        "metric": "EV",
        "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
        "pot_size": 20.0,
        "bet_amount": 10.0,
        "strict_current_action": False,
    })
    service = PrecomputeOrchestrationService(provider=provider, database_repository=Mock())

    scenario = {
        "scenario_key": "UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
        "position": "UTG",
        "metric": "EV",
        "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
        "strict_current_action": False,
    }

    context = service.resolve_scenario_context(scenario)

    provider._build_context.assert_called_once_with(
        position="UTG",
        metric="EV",
        position_actions={"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
        strict_current_action=False,
    )
    assert context["action"] == "ALL_IN"
    assert context["position_actions"]["BTN"] == "FOLD"


def test_resolve_scenario_context_rejects_incomplete_context() -> None:
    provider = Mock()
    provider._build_context = MagicMock(return_value={"position": "UTG"})
    service = PrecomputeOrchestrationService(provider=provider, database_repository=Mock())

    scenario = {
        "scenario_key": "UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
        "position": "UTG",
        "metric": "EV",
        "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
        "strict_current_action": False,
    }

    with pytest.raises(ValueError, match="Failed to build scenario context"):
        service.resolve_scenario_context(scenario)


def test_build_matrix_sweep_contract_includes_scenario_key() -> None:
    provider = Mock()
    service = PrecomputeOrchestrationService(provider=provider, database_repository=Mock())

    context = {
        "position": "UTG",
        "action": "ALL_IN",
        "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
        "pot_size": 20.0,
        "bet_amount": 10.0,
        "game_type": "nlhe",
    }
    class DummyProfile:
        simulations_per_cell = 1

    contract = service.build_matrix_sweep_contract(
        context=context,
        profile=DummyProfile(),
        job_session_id=123,
        scenario_key="UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
    )

    assert contract["precompute_job_session_id"] == 123
    assert contract["scenario_key"] == "UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False"
    assert contract["selected_position"] == "UTG"
    assert contract["hero_action"] == "ALL_IN"
    assert contract["num_simulations"] == 1
    assert contract["run_kind"] == "matrix_sweep"
