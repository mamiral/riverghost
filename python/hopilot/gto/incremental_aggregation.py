"""
Incremental Aggregation Engine.

This module implements incremental updates for MatrixCells and AggregatedMetrics
when new GameStates are added, avoiding full recomputation for better performance.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from hopilot.database import DatabaseConnection
from hopilot.gto.aof_hand_matrix import hand_coordinates_from_hole_cards
from hopilot.gto.aggregation_engine import AggregationEngine
from hopilot.gto.matrix_cells_derivation import MatrixCellsDerivationEngine
from hopilot.models import GameState, MatrixCell, AggregatedMetric, HandMatrix
from hopilot.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


class IncrementalAggregationEngine:
    """
    Engine for incremental updates to MatrixCells and AggregatedMetrics.

    This class handles updating existing aggregations when new GameStates are added,
    avoiding the need for full recomputation of all matrix cells.
    """

    def __init__(self, database_url: str):
        """
        Initialize the incremental aggregation engine.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.aggregation_engine = AggregationEngine(database_url)
        self.derivation_engine = MatrixCellsDerivationEngine(database_url)
        self.performance_monitor = PerformanceMonitor()

    def update_matrix_from_new_game_states(
        self,
        matrix_id: int,
        new_game_state_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Update matrix aggregations incrementally with new GameStates.

        Args:
            matrix_id: Hand matrix ID to update
            new_game_state_ids: Optional list of specific GameState IDs to include.
                               If None, finds all GameStates added since last update.

        Returns:
            Update summary with statistics
        """
        with self.performance_monitor.track_operation("incremental_matrix_update"):
            with self.db_connection.session_scope() as session:
                # Get matrix info
                hand_matrix = session.query(HandMatrix).filter(HandMatrix.id == matrix_id).first()
                if not hand_matrix:
                    raise ValueError(f"Hand matrix {matrix_id} not found")

                # Find GameStates that need to be included in aggregations
                game_states_to_process = self._identify_game_states_to_process(
                    session, matrix_id, new_game_state_ids
                )

                if not game_states_to_process:
                    return {
                        'matrix_id': matrix_id,
                        'status': 'no_updates_needed',
                        'cells_updated': 0,
                        'game_states_processed': 0
                    }

                # Group GameStates by matrix cell
                cells_to_update = self._group_game_states_by_cell(game_states_to_process)

                # Update each affected cell
                cells_updated = 0
                total_game_states_processed = len(game_states_to_process)

                for cell_coords, cell_game_states in cells_to_update.items():
                    row_idx, col_idx = cell_coords

                    # Get the MatrixCell object
                    matrix_cell = session.query(MatrixCell).filter(
                        and_(
                            MatrixCell.matrix_id == matrix_id,
                            MatrixCell.row_index == row_idx,
                            MatrixCell.col_index == col_idx
                        )
                    ).first()

                    if matrix_cell:
                        success = self._update_single_cell_incrementally(
                            session, matrix_id, row_idx, col_idx, cell_game_states, matrix_cell
                        )
                        if success:
                            cells_updated += 1

                session.commit()

                logger.info(
                    f"Incremental matrix update completed for matrix {matrix_id}: "
                    f"{cells_updated} cells updated, {total_game_states_processed} game states processed"
                )

                return {
                    'matrix_id': matrix_id,
                    'status': 'completed',
                    'cells_updated': cells_updated,
                    'game_states_processed': total_game_states_processed,
                    'cells_identified': len(cells_to_update)
                }

    def _identify_game_states_to_process(
        self,
        session: Session,
        matrix_id: int,
        new_game_state_ids: Optional[List[int]] = None
    ) -> List[GameState]:
        """
        Identify GameStates that need to be processed for incremental updates.

        Args:
            session: Database session
            matrix_id: Hand matrix ID
            new_game_state_ids: Optional specific GameState IDs

        Returns:
            List of GameState objects to process
        """
        matrix_cells = session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).all()
        valid_cell_coords = {(cell.row_index, cell.col_index) for cell in matrix_cells}

        query = session.query(GameState).options(joinedload(GameState.players))

        if new_game_state_ids:
            query = query.filter(GameState.id.in_(new_game_state_ids))

        game_states = query.all()

        return [
            gs for gs in game_states
            if self._game_state_matches_matrix_cell(gs, valid_cell_coords)
        ]

    def _group_game_states_by_cell(self, game_states: List[GameState]) -> Dict[tuple, List[GameState]]:
        """
        Group GameStates by their matrix cell coordinates.

        Args:
            game_states: List of GameState objects

        Returns:
            Dictionary mapping (row_idx, col_idx) to list of GameStates
        """
        cell_groups = {}

        for gs in game_states:
            coords = self._get_game_state_cell_coords(gs)
            if coords is None:
                continue

            if coords not in cell_groups:
                cell_groups[coords] = []
            cell_groups[coords].append(gs)

        return cell_groups

    def _get_game_state_cell_coords(self, game_state: GameState) -> Optional[tuple[int, int]]:
        hero_player = next((player for player in game_state.players if player.is_hero), None)
        if hero_player is None:
            return None

        try:
            return hand_coordinates_from_hole_cards(hero_player.hole_cards)
        except Exception:
            return None

    def _game_state_matches_matrix_cell(self, game_state: GameState, valid_cell_coords: Set[tuple[int, int]]) -> bool:
        coords = self._get_game_state_cell_coords(game_state)
        return coords in valid_cell_coords if coords is not None else False

    def _update_single_cell_incrementally(
        self,
        session: Session,
        matrix_id: int,
        row_idx: int,
        col_idx: int,
        new_game_states: List[GameState],
        matrix_cell: MatrixCell
    ) -> bool:
        """
        Update a single matrix cell incrementally with new GameStates.

        Args:
            session: Database session
            matrix_id: Hand matrix ID
            row_idx: Row index
            col_idx: Column index
            new_game_states: New GameStates for this cell

        Returns:
            True if update was successful
        """
        try:
            # Get existing MatrixCell
            matrix_cell = session.query(MatrixCell).filter(
                and_(
                    MatrixCell.matrix_id == matrix_id,
                    MatrixCell.row_index == row_idx,
                    MatrixCell.col_index == col_idx
                )
            ).first()

            if not matrix_cell:
                logger.warning(f"MatrixCell not found for ({row_idx}, {col_idx}) in matrix {matrix_id}")
                return False

            # Get existing AggregatedMetric
            existing_metric = session.query(AggregatedMetric).filter(
                AggregatedMetric.cell_id == matrix_cell.id
            ).first()

            if not existing_metric:
                # No existing metric, fall back to full computation
                return self._compute_cell_from_scratch(session, matrix_cell)

            # Perform incremental update
            updated_metric = self._incrementally_update_metric(
                session, existing_metric, new_game_states
            )

            # Update the metric in database
            logger.debug(f"Updating metric with: {updated_metric}")
            for key, value in updated_metric.items():
                if hasattr(existing_metric, key):
                    old_value = getattr(existing_metric, key)
                    setattr(existing_metric, key, value)
                    logger.debug(f"Set {key}: {old_value} -> {value}")
                else:
                    logger.warning(f"Metric does not have attribute: {key}")

            existing_metric.last_updated = datetime.now(timezone.utc).isoformat()

            logger.debug(f"Incrementally updated cell ({row_idx}, {col_idx}): {len(new_game_states)} new game states")
            return True

        except Exception as e:
            logger.error(f"Failed to update cell ({row_idx}, {col_idx}) incrementally: {e}")
            logger.error(f"Matrix cell exists: {matrix_cell is not None}")
            logger.error(f"Existing metric exists: {existing_metric is not None}")
            logger.error(f"New game states count: {len(new_game_states)}")
            return False

    def _incrementally_update_metric(
        self,
        session: Session,
        existing_metric: AggregatedMetric,
        new_game_states: List[GameState]
    ) -> Dict[str, Any]:
        """
        Incrementally update an existing metric with new GameStates.

        This implements a running average approach to avoid full recomputation.

        Args:
            session: Database session
            existing_metric: Existing AggregatedMetric
            new_game_states: New GameStates to include

        Returns:
            Updated metric values
        """
        # Get current statistics from existing metric
        # Note: We recalculate total_games from all GameStates for this cell
        # since it's not stored in the AggregatedMetric model

        # Get the matrix cell from the existing metric
        matrix_cell = session.query(MatrixCell).filter(MatrixCell.id == existing_metric.cell_id).first()
        if not matrix_cell:
            raise ValueError(f"MatrixCell not found for aggregated metric {existing_metric.id}")

        game_states = session.query(GameState).options(joinedload(GameState.players)).all()
        total_games_in_cell = sum(
            1 for gs in game_states
            if self._game_state_matches_cell(gs, matrix_cell.row_index, matrix_cell.col_index)
        )

        current_total_games = float(total_games_in_cell or 0) - len(new_game_states)  # Subtract new ones
        current_equity = float(existing_metric.equity) if existing_metric.equity else 0.0
        current_ev = float(existing_metric.ev) if existing_metric.ev else 0.0

        # Calculate statistics for new GameStates
        new_total_games = len(new_game_states)

        # New equity calculation
        new_wins = sum(1.0 for gs in new_game_states if gs.outcome in ['win', 'jackpot_win'])
        new_ties = sum(0.5 for gs in new_game_states if gs.outcome in ['tie', 'jackpot_tie'])
        new_equity = (new_wins + new_ties) / new_total_games if new_total_games > 0 else 0.0

        # New EV calculation
        new_ev_sum = sum(
            float(gs.pot_size) if gs.outcome in ['win', 'jackpot_win'] else
            (-float(gs.pot_size) if gs.outcome in ['loss', 'jackpot_loss'] else 0.0)
            for gs in new_game_states
        )
        new_avg_ev = new_ev_sum / new_total_games if new_total_games > 0 else 0.0

        # Combine old and new statistics using running average formula
        total_games = current_total_games + new_total_games

        if total_games > 0:
            # Running average: (old_avg * old_count + new_avg * new_count) / total_count
            combined_equity = (
                (current_equity * current_total_games) +
                (new_equity * new_total_games)
            ) / total_games

            combined_ev = (
                (current_ev * current_total_games) +
                (new_avg_ev * new_total_games)
            ) / total_games
        else:
            combined_equity = 0.0
            combined_ev = 0.0

        # For jackpot statistics, we'd need more complex incremental logic
        # For now, mark as needing full recomputation
        jackpot_frequency = getattr(existing_metric, 'jackpot_frequency', 0)
        avg_jackpot_payout = getattr(existing_metric, 'avg_jackpot_payout', 0)

        # Determine convergence status
        if total_games >= 10000:
            convergence_status = 'converged'
        elif total_games >= 1000:
            convergence_status = 'converging'
        else:
            convergence_status = 'insufficient_samples'

        return {
            'equity': combined_equity,
            'ev': combined_ev,
            'jackpot_frequency': jackpot_frequency,  # Keep existing for now
            'avg_jackpot_payout': avg_jackpot_payout,  # Keep existing for now
            'convergence_status': convergence_status
        }

    def _compute_cell_from_scratch(
        self,
        session: Session,
        matrix_cell: MatrixCell
    ) -> bool:
        """
        Compute a cell from scratch when no existing metric exists.

        Args:
            session: Database session
            matrix_cell: MatrixCell to compute

        Returns:
            True if computation was successful
        """
        try:
            # Use the derivation engine to create the metric
            result = self.derivation_engine._derive_single_matrix_cell(
                matrix_cell.matrix_id, matrix_cell.row_index, matrix_cell.col_index, min_samples=1
            )

            return result.get('status') == 'created'

        except Exception as e:
            logger.error(f"Failed to compute cell {matrix_cell.id} from scratch: {e}")
            return False

    def get_incremental_update_status(self, matrix_id: int) -> Dict[str, Any]:
        """
        Get status information about incremental updates for a matrix.

        Args:
            matrix_id: Hand matrix ID

        Returns:
            Status information
        """
        with self.db_connection.session_scope() as session:
            # Get basic matrix info
            hand_matrix = session.query(HandMatrix).filter(HandMatrix.id == matrix_id).first()
            if not hand_matrix:
                return {'error': 'Matrix not found'}

            # Count cells and metrics
            total_cells = session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).count()
            cells_with_metrics = session.query(AggregatedMetric).join(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id
            ).count()

            # Get latest update timestamp
            latest_update = session.query(func.max(AggregatedMetric.last_updated)).join(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id
            ).scalar()

            return {
                'matrix_id': matrix_id,
                'matrix_size': hand_matrix.matrix_size,
                'total_cells': total_cells,
                'cells_with_metrics': cells_with_metrics,
                'coverage_percentage': (cells_with_metrics / total_cells * 100) if total_cells > 0 else 0,
                'latest_update': latest_update,
                'incremental_updates_supported': True
            }