import pytest

from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, RunnerPhase
from hopilot.gto.matrix_sweep_contract import (
    FAILURE_BOUNDARY_AGGREGATION,
    FAILURE_BOUNDARY_ORCHESTRATION,
    FAILURE_BOUNDARY_SOLVER_WRITE,
    MatrixSweepPhase,
    REQUIRED_SWEEP_RESULT_FIELDS,
    RUN_STATUS_AGGREGATED,
    RUN_STATUS_CREATED,
    RUN_STATUS_FAILED,
    RUN_STATUS_RAW_COMPLETE,
    build_run_parameters,
    normalize_scenario_contract,
    validate_scenario_contract,
    validate_sweep_result,
)


def build_valid_scenario_contract() -> dict[str, object]:
    return {
        "selected_position": "UTG",
        "hero_action": "ALL_IN",
        "position_actions": {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
        "active_players": ["UTG", "BB"],
        "num_opponents": 1,
        "pot_size": 20.0,
        "bet_amount": 10.0,
        "sims_per_combo": 1,
        "num_simulations": 1,
        "matrix_size": "13x13",
        "game_type": "nlhe",
        "run_kind": "matrix_sweep",
    }


def test_normalize_scenario_contract_legacy_field_mapping() -> None:
    contract = build_valid_scenario_contract()
    contract.pop("sims_per_combo")
    normalized = normalize_scenario_contract(contract)

    assert normalized["sims_per_combo"] == 1
    assert normalized["num_simulations"] == 1


def test_normalize_scenario_contract_preserves_stop_event() -> None:
    stop_event = object()
    contract = build_valid_scenario_contract()
    contract["stop_event"] = stop_event

    normalized = normalize_scenario_contract(contract)

    assert normalized["stop_event"] is stop_event
    assert normalized["selected_position"] == contract["selected_position"]


def test_build_run_parameters_strips_runtime_stop_event() -> None:
    stop_event = object()
    contract = build_valid_scenario_contract()
    contract["stop_event"] = stop_event

    parameters = build_run_parameters(contract)

    assert "stop_event" not in parameters
    assert parameters["status"] == RUN_STATUS_CREATED
    assert parameters["sims_per_combo"] == contract["sims_per_combo"]


def test_validate_scenario_contract_rejects_missing_required_fields() -> None:
    contract = build_valid_scenario_contract()
    contract.pop("selected_position")

    with pytest.raises(Exception, match="missing required fields"):
        validate_scenario_contract(contract)


def test_build_run_parameters_includes_expected_status_fields() -> None:
    contract = build_valid_scenario_contract()
    parameters = build_run_parameters(contract, status=RUN_STATUS_CREATED)

    assert parameters["status"] == RUN_STATUS_CREATED
    assert parameters["raw_rows_written"] == 0
    assert parameters["raw_players_written"] == 0
    assert parameters["failed_combinations"] == 0


def test_contract_phase_and_failure_boundary_constants_are_defined() -> None:
    assert MatrixSweepPhase.ORCHESTRATION.value == "orchestration"
    assert MatrixSweepPhase.SOLVER_WRITE.value == "solver_write"
    assert MatrixSweepPhase.AGGREGATION.value == "aggregation"
    assert FAILURE_BOUNDARY_ORCHESTRATION == "orchestration"
    assert FAILURE_BOUNDARY_SOLVER_WRITE == "solver_write"
    assert FAILURE_BOUNDARY_AGGREGATION == "aggregation"


def test_validate_sweep_result_accepts_required_success_output_fields() -> None:
    result = {
        "simulation_id": 123,
        "matrix_id": 456,
        "status": "aggregated",
    }

    validated = validate_sweep_result(result)

    assert validated["simulation_id"] == 123
    assert validated["matrix_id"] == 456
    assert validated["status"] == "aggregated"
    assert list(REQUIRED_SWEEP_RESULT_FIELDS) == ["simulation_id", "matrix_id", "status"]


def test_job_progress_payload_contains_expected_fields_and_phase() -> None:
    runner = AoFPrecomputeRunner(database_url="sqlite:///:memory:")
    job_session_id = runner.database_repository.create_precompute_job_session(
        scenario_fingerprint="test",
        requested_scenarios=1,
    )
    runner.database_repository.create_scenario_run_link(
        job_session_id=job_session_id,
        scenario_index=0,
        scenario_key="UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
        scenario_contract={},
        status="RUNNING",
    )

    progress = runner.get_job_progress(job_session_id)

    expected_keys = {
        "run_state",
        "completed_scenarios",
        "total_scenarios",
        "active_scenario_key",
        "phase",
        "elapsed_seconds",
        "eta_seconds",
        "failure_count",
    }

    assert set(progress.keys()) == expected_keys
    assert progress["phase"] in {phase.value for phase in RunnerPhase}
    assert progress["run_state"] == "RUNNING"
    assert progress["total_scenarios"] == 1
    assert progress["failure_count"] == 0
