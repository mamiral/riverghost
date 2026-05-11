"""Run-scoped post-processing for GameStates-first matrix sweep data."""

from __future__ import annotations

from datetime import datetime, timezone

from hopilot.gto.aof_hand_matrix import hand_coordinates_from_hole_cards, hand_key_from_index, iter_canonical_matrix_cells
from hopilot.gto.incremental_aggregation_service import IncrementalAggregationService
from hopilot.gto.matrix_sweep_contract import mark_aggregation_complete, normalize_scenario_contract, RUN_STATUS_AGGREGATED
from hopilot.logging_config import get_logger
from hopilot.models import AggregatedMetric, MatrixCell


logger = get_logger(__name__)


class MatrixSweepAggregationService:
    """Aggregates raw game states into one 169-cell hand matrix per run."""

    def __init__(self, repository):
        self.repository = repository

    def aggregate_run_incremental(self, simulation_id, enable_convergence_tracking=False, emit_interval=100):
        """
        Perform incremental aggregation with optional convergence tracking.

        Args:
            simulation_id: Simulation ID to aggregate
            enable_convergence_tracking: Whether to emit convergence events
            emit_interval: Sample count interval for convergence emissions

        Returns:
            Aggregation summary dictionary
        """
        simulation = self.repository.get_simulation_record(simulation_id)
        if simulation is None:
            raise ValueError(f"Simulation {simulation_id} does not exist")

        parameters = normalize_scenario_contract(simulation.parameters)
        raw_start = parameters.get("raw_game_state_id_start")
        raw_end = parameters.get("raw_game_state_id_end")
        if raw_start is None or raw_end is None:
            raise ValueError(f"Simulation {simulation_id} has no completed raw run boundary")

        # Get betting parameters
        bet_amount = parameters.get("bet_amount", 0.0)

        # Create matrix and cells first
        matrix_id = self.repository.get_or_create_hand_matrix_for_simulation(simulation_id)
        timestamp = datetime.now(timezone.utc).isoformat()

        session = self.repository.get_session()
        cell_id_map = {}

        try:
            # Check for existing cells to avoid duplicates
            existing_cells = session.query(MatrixCell).filter_by(matrix_id=matrix_id).all()
            if existing_cells:
                logger.info(f"Using {len(existing_cells)} existing matrix cells for simulation {simulation_id}")
                cell_id_map = {cell.hand_combination: cell.id for cell in existing_cells}
            else:
                # Create all matrix cells if they don't exist
                for row_index, col_index, hand_key in iter_canonical_matrix_cells():
                    cell = MatrixCell(
                        matrix_id=matrix_id,
                        row_index=row_index,
                        col_index=col_index,
                        hand_combination=hand_key,
                    )
                    session.add(cell)
                    session.flush()
                    cell_id_map[hand_key] = cell.id
                session.commit()
        finally:
            session.close()

        # Set up incremental aggregation if convergence tracking is enabled
        incremental_service = None
        if enable_convergence_tracking:
            from hopilot.database import DatabaseConnection
            from hopilot.poker_analyzer import PokerAnalyzer
            from hopilot.gto.convergence_events import ConvergenceEventEmitter

            db_connection = self.repository.db_connection
            poker_analyzer = PokerAnalyzer()
            event_emitter = ConvergenceEventEmitter()

            # Attach database observer for convergence tracking
            from hopilot.gto.database_convergence_observer import DatabaseConvergenceObserver
            db_observer = DatabaseConvergenceObserver(db_connection)
            event_emitter.attach(db_observer)

            incremental_service = IncrementalAggregationService(
                db_connection=db_connection,
                poker_analyzer=poker_analyzer,
                event_emitter=event_emitter,
                emit_interval=emit_interval
            )

        # Process each cell
        total_cells = 0
        total_metrics = 0

        for row_index, col_index, hand_key in iter_canonical_matrix_cells():
            cell_id = cell_id_map[hand_key]

            if incremental_service:
                # Use incremental aggregation with convergence tracking
                final_metrics = incremental_service.aggregate_cell_incremental(
                    cell_id=cell_id,
                    hand_key=hand_key,
                    simulation_id=simulation_id,
                    bet_amount=bet_amount,
                    raw_start=raw_start,
                    raw_end=raw_end
                )
            else:
                # Use traditional batch aggregation
                final_metrics = self._aggregate_cell_batch(
                    cell_id, simulation_id, raw_start, raw_end, bet_amount
                )

            # Store final aggregated metric (using merge to handle existing metrics)
            session = self.repository.get_session()
            try:
                # Check for existing metric
                existing_metric = session.query(AggregatedMetric).filter_by(cell_id=cell_id).first()
                if existing_metric:
                    existing_metric.equity = final_metrics.get('equity')
                    existing_metric.win_probability = final_metrics.get('win_probability')
                    existing_metric.ev = final_metrics.get('ev')
                    existing_metric.sample_count = final_metrics.get('sample_count', 0)
                    sample_count = final_metrics.get('sample_count', 0)
                    if sample_count >= 100:
                        existing_metric.convergence_status = "CONVERGED"
                    elif sample_count > 0:
                        existing_metric.convergence_status = "CONVERGING"
                    else:
                        existing_metric.convergence_status = "NO_DATA"
                    existing_metric.last_updated = timestamp
                else:
                    sample_count = final_metrics.get('sample_count', 0)
                    if sample_count >= 100:
                        convergence_status = "CONVERGED"
                    elif sample_count > 0:
                        convergence_status = "CONVERGING"
                    else:
                        convergence_status = "NO_DATA"
                    new_metric = AggregatedMetric(
                        cell_id=cell_id,
                        equity=final_metrics.get('equity'),
                        win_probability=final_metrics.get('win_probability'),
                        ev=final_metrics.get('ev'),
                        sample_count=sample_count,
                        convergence_status=convergence_status,
                        last_updated=timestamp,
                    )
                    session.add(new_metric)
                session.commit()
                total_metrics += 1
            except Exception as e:
                logger.error(f"Failed to save metric for cell {cell_id}: {e}")
                session.rollback()
            finally:
                session.close()

            total_cells += 1

        updated_parameters = mark_aggregation_complete(
            parameters,
            matrix_id=matrix_id,
            mapping_failures=0,  # Not tracking this in incremental mode
        )
        self.repository.update_matrix_sweep_simulation(simulation_id, parameters=updated_parameters)

        return {
            "simulation_id": simulation_id,
            "matrix_id": matrix_id,
            "matrix_cells_written": total_cells,
            "aggregated_metrics_written": total_metrics,
            "convergence_tracking_enabled": enable_convergence_tracking,
            "status": RUN_STATUS_AGGREGATED,
        }

    def _aggregate_cell_batch(self, cell_id, simulation_id, raw_start, raw_end, bet_amount):
        """Aggregate a single cell using traditional batch processing."""
        # Get game states for this cell
        game_states = list(self.repository.get_run_game_states(raw_start, raw_end))
        cell_game_states = [gs for gs in game_states if gs.cell_id == cell_id]

        if not cell_game_states:
            return {'equity': None, 'win_probability': None, 'ev': None, 'sample_count': 0}

        wins = 0
        ties = 0
        ev_sum = 0.0
        total = len(cell_game_states)

        for game_state in cell_game_states:
            game_state_pot = float(game_state.pot_size)
            if game_state.outcome == "WIN":
                wins += 1
                ev_sum += game_state_pot - bet_amount
            elif game_state.outcome == "TIE":
                ties += 1
                ev_sum += game_state_pot / 2.0 - bet_amount / 2.0
            else:
                ev_sum -= bet_amount

        equity = (wins + 0.5 * ties) / total
        win_probability = wins / total
        ev = ev_sum / total

        return {
            'equity': equity,
            'win_probability': win_probability,
            'ev': ev,
            'sample_count': total
        }

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
                "ev_sum": 0.0,
            }
            for row_index, col_index, hand_key in iter_canonical_matrix_cells()
        }

        bet_amount = parameters.get("bet_amount", 0.0)
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
            game_state_pot = float(game_state.pot_size)
            if game_state.outcome == "WIN":
                stats["wins"] += 1
                stats["ev_sum"] += game_state_pot - bet_amount
            elif game_state.outcome == "TIE":
                stats["ties"] += 1
                stats["ev_sum"] += game_state_pot / 2.0 - bet_amount / 2.0
            else:
                stats["ev_sum"] -= bet_amount

        matrix_id = self.repository.get_or_create_hand_matrix_for_simulation(simulation_id)
        timestamp = datetime.now(timezone.utc).isoformat()

        session = self.repository.get_session()
        try:
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
                ev = None
                convergence_status = "no_samples"
                if total > 0:
                    equity = (stats["wins"] + 0.5 * stats["ties"]) / total
                    win_probability = stats["wins"] / total
                    ev = stats["ev_sum"] / total
                    convergence_status = "complete"

                session.add(
                    AggregatedMetric(
                        cell_id=cell.id,
                        equity=equity,
                        win_probability=win_probability,
                        ev=ev,
                        sample_count=total,
                        convergence_status=convergence_status,
                        last_updated=timestamp,
                    )
                )
            session.commit()
        finally:
            session.close()

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