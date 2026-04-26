"""Helpers for the production matrix sweep scenario and run contract."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Mapping


MATRIX_SWEEP_RUN_KIND = "matrix_sweep"
MATRIX_SWEEP_SIZE = "13x13"
RUN_STATUS_CREATED = "created"
RUN_STATUS_RAW_COMPLETE = "raw_sweep_complete"
RUN_STATUS_AGGREGATED = "aggregated"
RUN_STATUS_FAILED = "failed"

REQUIRED_SCENARIO_FIELDS = (
    "selected_position",
    "hero_action",
    "position_actions",
    "active_players",
    "num_opponents",
    "pot_size",
    "bet_amount",
    "sims_per_combo",
    "matrix_size",
    "game_type",
    "run_kind",
)


class MatrixSweepContractError(ValueError):
    """Raised when the matrix sweep contract is invalid."""


def normalize_scenario_contract(scenario_contract: Mapping[str, Any]) -> dict[str, Any]:
    """Return a normalized copy of the persisted matrix sweep scenario contract."""
    if not isinstance(scenario_contract, Mapping):
        raise MatrixSweepContractError("Scenario contract must be a mapping")

    normalized = deepcopy(dict(scenario_contract))

    if "sims_per_combo" not in normalized and "num_simulations" in normalized:
        normalized["sims_per_combo"] = normalized["num_simulations"]

    if "num_simulations" not in normalized and "sims_per_combo" in normalized:
        normalized["num_simulations"] = normalized["sims_per_combo"]

    return normalized


def validate_scenario_contract(scenario_contract: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize and validate a matrix sweep scenario contract."""
    normalized = normalize_scenario_contract(scenario_contract)

    missing_fields = [field for field in REQUIRED_SCENARIO_FIELDS if field not in normalized]
    if missing_fields:
        raise MatrixSweepContractError(
            f"Scenario contract is missing required fields: {', '.join(missing_fields)}"
        )

    if normalized["run_kind"] != MATRIX_SWEEP_RUN_KIND:
        raise MatrixSweepContractError(
            f"run_kind must be '{MATRIX_SWEEP_RUN_KIND}', got: {normalized['run_kind']!r}"
        )

    if normalized["matrix_size"] != MATRIX_SWEEP_SIZE:
        raise MatrixSweepContractError(
            f"matrix_size must be '{MATRIX_SWEEP_SIZE}', got: {normalized['matrix_size']!r}"
        )

    if not isinstance(normalized["selected_position"], str) or not normalized["selected_position"].strip():
        raise MatrixSweepContractError("selected_position must be a non-empty string")

    if not isinstance(normalized["hero_action"], str) or not normalized["hero_action"].strip():
        raise MatrixSweepContractError("hero_action must be a non-empty string")

    if not isinstance(normalized["position_actions"], Mapping) or not normalized["position_actions"]:
        raise MatrixSweepContractError("position_actions must be a non-empty mapping")

    active_players = normalized["active_players"]
    if not isinstance(active_players, list) or not active_players:
        raise MatrixSweepContractError("active_players must be a non-empty list")

    if any(not isinstance(player, str) or not player.strip() for player in active_players):
        raise MatrixSweepContractError("active_players must contain only non-empty strings")

    num_opponents = normalized["num_opponents"]
    if not isinstance(num_opponents, int) or num_opponents < 1:
        raise MatrixSweepContractError("num_opponents must be an integer >= 1")

    sims_per_combo = normalized["sims_per_combo"]
    if not isinstance(sims_per_combo, int) or sims_per_combo < 1:
        raise MatrixSweepContractError("sims_per_combo must be an integer >= 1")

    if normalized["num_simulations"] != sims_per_combo:
        raise MatrixSweepContractError("num_simulations must match sims_per_combo for compatibility")

    for numeric_field in ("pot_size", "bet_amount"):
        value = normalized[numeric_field]
        if not isinstance(value, (int, float)) or value < 0:
            raise MatrixSweepContractError(f"{numeric_field} must be a non-negative number")

    if not isinstance(normalized["game_type"], str) or not normalized["game_type"].strip():
        raise MatrixSweepContractError("game_type must be a non-empty string")

    start_id = normalized.get("raw_game_state_id_start")
    end_id = normalized.get("raw_game_state_id_end")
    if start_id is not None and (not isinstance(start_id, int) or start_id < 1):
        raise MatrixSweepContractError("raw_game_state_id_start must be an integer >= 1 when present")
    if end_id is not None and (not isinstance(end_id, int) or end_id < 1):
        raise MatrixSweepContractError("raw_game_state_id_end must be an integer >= 1 when present")
    if start_id is not None and end_id is not None and start_id > end_id:
        raise MatrixSweepContractError("raw_game_state_id_start cannot be greater than raw_game_state_id_end")

    return normalized


def build_run_parameters(
    scenario_contract: Mapping[str, Any],
    *,
    status: str = RUN_STATUS_CREATED,
    raw_game_state_id_start: int | None = None,
) -> dict[str, Any]:
    """Create persisted run parameters with default run-boundary metadata."""
    parameters = validate_scenario_contract(scenario_contract)
    parameters.update(
        {
            "status": status,
            "raw_game_state_id_start": raw_game_state_id_start,
            "raw_game_state_id_end": None,
            "raw_rows_written": 0,
            "raw_players_written": 0,
            "failed_combinations": 0,
            "mapping_failures": 0,
            "matrix_id": None,
            "run_started_at": datetime.now(UTC).isoformat(),
            "run_completed_at": None,
        }
    )
    return parameters


def update_run_parameters(
    parameters: Mapping[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    """Return an updated, revalidated run-parameter mapping."""
    merged = normalize_scenario_contract(parameters)
    merged.update(updates)

    completed_at = merged.get("run_completed_at")
    if isinstance(completed_at, datetime):
        merged["run_completed_at"] = completed_at.isoformat()

    validate_scenario_contract(merged)
    return merged


def mark_raw_sweep_complete(
    parameters: Mapping[str, Any],
    *,
    raw_game_state_id_end: int,
    raw_rows_written: int,
    raw_players_written: int,
    failed_combinations: int,
) -> dict[str, Any]:
    """Mark a run as finished with raw-write counters captured."""
    return update_run_parameters(
        parameters,
        status=RUN_STATUS_RAW_COMPLETE,
        raw_game_state_id_end=raw_game_state_id_end,
        raw_rows_written=raw_rows_written,
        raw_players_written=raw_players_written,
        failed_combinations=failed_combinations,
    )


def mark_aggregation_complete(
    parameters: Mapping[str, Any],
    *,
    matrix_id: int,
    mapping_failures: int,
    run_completed_at: datetime | None = None,
) -> dict[str, Any]:
    """Mark a run as aggregated with final matrix metadata."""
    return update_run_parameters(
        parameters,
        status=RUN_STATUS_AGGREGATED,
        matrix_id=matrix_id,
        mapping_failures=mapping_failures,
        run_completed_at=run_completed_at or datetime.now(UTC),
    )


def mark_run_failed(parameters: Mapping[str, Any], error_message: str) -> dict[str, Any]:
    """Mark a run as failed while preserving the existing boundary metadata."""
    return update_run_parameters(
        parameters,
        status=RUN_STATUS_FAILED,
        error_message=error_message,
        run_completed_at=datetime.now(UTC),
    )