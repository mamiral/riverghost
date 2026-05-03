"""Production orchestration for GameStates-first matrix sweep runs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func

from hopilot.gto.aof_hand_matrix import iter_canonical_matrix_cells
from hopilot.gto.matrix_sweep_aggregation_service import MatrixSweepAggregationService
from hopilot.gto.matrix_sweep_contract import build_run_parameters, mark_raw_sweep_complete, mark_run_failed, validate_scenario_contract
from hopilot.hand_range import HandRange
from hopilot.logging_config import get_logger
from hopilot.models import HandMatrix, Simulation


logger = get_logger(__name__)


class MatrixSweepService:
    """Owns one full fixed-scenario matrix sweep run."""

    def __init__(self, repository, analyzer, persistence_factory):
        self.repository = repository
        self.analyzer = analyzer
        self.persistence_factory = persistence_factory

    def _capture_append_baseline(self):
        return {
            "max_simulation_id": self.repository.get_max_simulation_id(),
            "max_matrix_id": self.repository.get_max_matrix_id(),
        }

    def _validate_append_only_run(self, baseline, result):
        if result["simulation_id"] <= baseline["max_simulation_id"]:
            raise ValueError("Matrix sweep runs must append a new simulation record")
        if result["matrix_id"] <= baseline["max_matrix_id"]:
            raise ValueError("Matrix sweep runs must append a new hand matrix record")

    def run_raw_sweep(self, scenario_contract):
        normalized_contract = validate_scenario_contract(scenario_contract)
        raw_game_state_id_start = self.repository.get_latest_game_state_id() + 1
        parameters = build_run_parameters(
            normalized_contract,
            raw_game_state_id_start=raw_game_state_id_start,
        )
        simulation_id = self.repository.create_matrix_sweep_simulation(
            parameters,
            start_timestamp=datetime.now(timezone.utc),
        )

        session = self.repository.get_session()
        persistence = self.persistence_factory(session)
        failed_combinations = 0

        try:
            for _, _, hand_key in iter_canonical_matrix_cells():
                for card_one, card_two in HandRange.parse_shorthand(hand_key):
                    result = self.analyzer.calculate_odds_random_opponents(
                        hero_hole_cards=[card_one, card_two],
                        board_cards=[],
                        num_opponents=normalized_contract["num_opponents"],
                        num_simulations=normalized_contract["sims_per_combo"],
                        persistence=persistence,
                    )
                    if not result or result.get("valid_simulations", 0) == 0:
                        failed_combinations += 1

            # Ensure any buffered rows are flushed before we capture the end boundary.
            persistence.close()
            raw_game_state_id_end = self.repository.get_latest_game_state_id()
            raw_counts = self.repository.get_run_raw_counts(raw_game_state_id_start, raw_game_state_id_end)
            completed_parameters = mark_raw_sweep_complete(
                parameters,
                raw_game_state_id_end=raw_game_state_id_end,
                raw_rows_written=raw_counts["raw_game_states"],
                raw_players_written=raw_counts["raw_players"],
                failed_combinations=failed_combinations,
            )
            self.repository.update_matrix_sweep_simulation(
                simulation_id,
                parameters=completed_parameters,
                end_timestamp=datetime.now(timezone.utc),
            )
            return {
                "simulation_id": simulation_id,
                "raw_game_states_written": raw_counts["raw_game_states"],
                "raw_players_written": raw_counts["raw_players"],
                "failed_combinations": failed_combinations,
                "status": "raw_sweep_complete",
            }
        except Exception as error:
            persistence.rollback_transaction()
            failed_parameters = mark_run_failed(parameters, str(error))
            self.repository.update_matrix_sweep_simulation(
                simulation_id,
                parameters=failed_parameters,
                end_timestamp=datetime.now(timezone.utc),
            )
            raise
        finally:
            persistence.close()
            session.close()

    def run_sweep(self, scenario_contract):
        baseline = self._capture_append_baseline()
        raw_result = self.run_raw_sweep(scenario_contract)
        aggregation_result = MatrixSweepAggregationService(self.repository).aggregate_run(
            raw_result["simulation_id"]
        )
        result = {
            "simulation_id": raw_result["simulation_id"],
            "matrix_id": aggregation_result["matrix_id"],
            "raw_game_states_written": raw_result["raw_game_states_written"],
            "raw_players_written": raw_result["raw_players_written"],
            "matrix_cells_written": aggregation_result["matrix_cells_written"],
            "aggregated_metrics_written": aggregation_result["aggregated_metrics_written"],
            "failed_combinations": raw_result["failed_combinations"],
            "unmapped_hero_records": aggregation_result["unmapped_hero_records"],
            "status": aggregation_result["status"],
        }
        self._validate_append_only_run(baseline, result)
        logger.info(
            "Completed append-only matrix sweep run simulation_id=%s matrix_id=%s",
            result["simulation_id"],
            result["matrix_id"],
        )
        return result

    def find_run_by_contract(self, scenario_contract):
        normalized_contract = validate_scenario_contract(scenario_contract)
        return self.repository.find_matrix_sweep_run_by_contract(normalized_contract)

    def get_run_summary(self, simulation_id):
        return self.repository.get_matrix_sweep_summary(simulation_id)