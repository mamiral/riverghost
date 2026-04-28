"""Run-scoped post-processing for GameStates-first matrix sweep data."""

from __future__ import annotations

from datetime import datetime, timezone

from hopilot.gto.aof_hand_matrix import hand_coordinates_from_hole_cards, hand_key_from_index, iter_canonical_matrix_cells
from hopilot.gto.matrix_sweep_contract import mark_aggregation_complete, normalize_scenario_contract, RUN_STATUS_AGGREGATED
from hopilot.logging_config import get_logger
from hopilot.models import AggregatedMetric, MatrixCell


logger = get_logger(__name__)


class MatrixSweepAggregationService:
    """Aggregates raw game states into one 169-cell hand matrix per run."""

    def __init__(self, repository):
        self.repository = repository

    def aggregate_run(self, simulation_id):
        simulation = self.repository.get_simulation_record(simulation_id)
        if simulation is None:
            raise ValueError(f"Simulation {simulation_id} does not exist")

        parameters = normalize_scenario_contract(simulation.parameters)
        raw_start = parameters.get("raw_game_state_id_start")
        raw_end = parameters.get("raw_game_state_id_end")
        if raw_start is None or raw_end is None:
            raise ValueError(f"Simulation {simulation_id} has no completed raw run boundary")

        cell_stats = {
            hand_key: {
                "row_index": row_index,
                "col_index": col_index,
                "wins": 0,
                "ties": 0,
                "total": 0,
            }
            for row_index, col_index, hand_key in iter_canonical_matrix_cells()
        }

        unmapped_hero_records = 0
        for game_state in self.repository.get_run_game_states(raw_start, raw_end):
            hero_player = next((player for player in game_state.players if player.is_hero), None)
            if hero_player is None:
                continue

            try:
                row_index, col_index = hand_coordinates_from_hole_cards(hero_player.hole_cards)
            except ValueError:
                unmapped_hero_records += 1
                continue

            hand_key = hand_key_from_index(row_index, col_index)
            stats = cell_stats[hand_key]
            stats["total"] += 1
            if game_state.outcome == "WIN":
                stats["wins"] += 1
            elif game_state.outcome == "TIE":
                stats["ties"] += 1

        matrix_id = self.repository.get_or_create_hand_matrix_for_simulation(simulation_id)
        timestamp = datetime.now(timezone.utc).isoformat()

        with self.repository.connection.session_scope() as session:
            for row_index, col_index, hand_key in iter_canonical_matrix_cells():
                cell = MatrixCell(
                    matrix_id=matrix_id,
                    row_index=row_index,
                    col_index=col_index,
                    hand_combination=hand_key,
                )
                session.add(cell)
                session.flush()

                stats = cell_stats[hand_key]
                total = stats["total"]
                equity = None
                win_probability = None
                convergence_status = "no_samples"
                if total > 0:
                    equity = (stats["wins"] + 0.5 * stats["ties"]) / total
                    win_probability = stats["wins"] / total
                    convergence_status = "complete"

                session.add(
                    AggregatedMetric(
                        cell_id=cell.id,
                        equity=equity,
                        win_probability=win_probability,
                        sample_count=total,
                        convergence_status=convergence_status,
                        last_updated=timestamp,
                    )
                )

        updated_parameters = mark_aggregation_complete(
            parameters,
            matrix_id=matrix_id,
            mapping_failures=unmapped_hero_records,
        )
        self.repository.update_matrix_sweep_simulation(simulation_id, parameters=updated_parameters)

        return {
            "simulation_id": simulation_id,
            "matrix_id": matrix_id,
            "matrix_cells_written": 169,
            "aggregated_metrics_written": 169,
            "unmapped_hero_records": unmapped_hero_records,
            "status": RUN_STATUS_AGGREGATED,
        }

    def rerun_aggregation(self, simulation_id):
        summary = self.repository.get_matrix_sweep_summary(simulation_id)
        if summary is None:
            raise ValueError(f"Simulation {simulation_id} does not exist")

        hand_matrix = summary["hand_matrix"]
        if hand_matrix is not None:
            self.repository.delete_matrix_summaries(hand_matrix.id)

        result = self.aggregate_run(simulation_id)
        return {
            "simulation_id": simulation_id,
            "matrix_id": result["matrix_id"],
            "matrix_cells_recreated": result["matrix_cells_written"],
            "aggregated_metrics_recreated": result["aggregated_metrics_written"],
            "status": result["status"],
        }