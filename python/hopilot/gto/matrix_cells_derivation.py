"""
Matrix Cells Derivation Engine.

This module implements the logic to create MatrixCells and AggregatedMetrics
from computed aggregation results, completing the GameStates-first architecture.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from hopilot.database import DatabaseConnection
from hopilot.gto.aggregation_engine import AggregationEngine
from hopilot.models import MatrixCell, AggregatedMetric, HandMatrix
from hopilot.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


class MatrixCellsDerivationEngine:
    """
    Engine for deriving MatrixCells and AggregatedMetrics from aggregation results.

    This class takes the computed aggregation metrics and creates the corresponding
    MatrixCells and AggregatedMetrics records that the GUI can consume.
    """

    # Standard poker hand ordering (strongest to weakest)
    POKER_HANDS = [
        "AA", "AK", "AQ", "AJ", "AT", "A9", "A8", "A7", "A6", "A5", "A4", "A3", "A2",
        "KK", "KQ", "KJ", "KT", "K9", "K8", "K7", "K6", "K5", "K4", "K3", "K2",
        "QQ", "QJ", "QT", "Q9", "Q8", "Q7", "Q6", "Q5", "Q4", "Q3", "Q2",
        "JJ", "JT", "J9", "J8", "J7", "J6", "J5", "J4", "J3", "J2",
        "TT", "T9", "T8", "T7", "T6", "T5", "T4", "T3", "T2",
        "99", "98", "97", "96", "95", "94", "93", "92",
        "88", "87", "86", "85", "84", "83", "82",
        "77", "76", "75", "74", "73", "72",
        "66", "65", "64", "63", "62",
        "55", "54", "53", "52",
        "44", "43", "42",
        "33", "32",
        "22",
    ]

    def __init__(self, database_url: str):
        """
        Initialize the matrix cells derivation engine.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.aggregation_engine = AggregationEngine(database_url)
        self.performance_monitor = PerformanceMonitor()

    def derive_matrix_cells_from_aggregations(
        self,
        matrix_id: int,
        min_samples: int = 100
    ) -> Dict[str, Any]:
        """
        Derive MatrixCells and AggregatedMetrics from GameStates aggregations.

        This is the main method that creates MatrixCells for all positions in a hand matrix
        where sufficient GameStates data exists.

        Args:
            matrix_id: Hand matrix ID to populate
            min_samples: Minimum GameStates required for cell creation

        Returns:
            Summary of derivation results
        """
        with self.performance_monitor.track_operation("derive_matrix_cells"):
            with self.db_connection.session_scope() as session:
                # Get the hand matrix to understand its structure
                hand_matrix = session.query(HandMatrix).filter(HandMatrix.id == matrix_id).first()
                if not hand_matrix:
                    raise ValueError(f"Hand matrix {matrix_id} not found")

                # Parse matrix size
                try:
                    rows, cols = map(int, hand_matrix.matrix_size.split('x'))
                except ValueError:
                    raise ValueError(f"Invalid matrix size format: {hand_matrix.matrix_size}")

                created_cells = 0
                updated_cells = 0
                skipped_cells = 0

                # Process each matrix position
                for row_idx in range(rows):
                    for col_idx in range(cols):
                        result = self._derive_single_matrix_cell(
                            matrix_id, row_idx, col_idx, min_samples
                        )

                        if result['status'] == 'created':
                            created_cells += 1
                        elif result['status'] == 'updated':
                            updated_cells += 1
                        elif result['status'] == 'skipped':
                            skipped_cells += 1

                session.commit()

                summary = {
                    'matrix_id': matrix_id,
                    'matrix_size': hand_matrix.matrix_size,
                    'created_cells': created_cells,
                    'updated_cells': updated_cells,
                    'skipped_cells': skipped_cells,
                    'total_processed': created_cells + updated_cells + skipped_cells
                }

                logger.info(
                    f"Matrix cells derivation completed for matrix {matrix_id}: "
                    f"{created_cells} created, {updated_cells} updated, {skipped_cells} skipped"
                )

                return summary

    def _derive_single_matrix_cell(
        self,
        matrix_id: int,
        row_idx: int,
        col_idx: int,
        min_samples: int
    ) -> Dict[str, Any]:
        """
        Derive a single MatrixCell and its AggregatedMetric from aggregations.

        Args:
            matrix_id: Hand matrix ID
            row_idx: Row index in the matrix
            col_idx: Column index in the matrix
            min_samples: Minimum samples required

        Returns:
            Result status and details
        """
        try:
            # Compute aggregations for this cell position
            aggregation_result = self.aggregation_engine.compute_matrix_cell_from_game_states(
                matrix_id, row_idx, col_idx, min_samples
            )

            if not aggregation_result:
                return {
                    'status': 'skipped',
                    'reason': 'insufficient_data',
                    'row': row_idx,
                    'col': col_idx
                }

            # Generate hand combination description
            hand_combination = self._generate_hand_combination(row_idx, col_idx)

            # Create or update MatrixCell
            cell_id = self._ensure_matrix_cell_exists(
                matrix_id, row_idx, col_idx, hand_combination
            )

            # Create or update AggregatedMetric
            self._update_aggregated_metric(cell_id, aggregation_result)

            return {
                'status': 'created',  # We'll determine if it was created or updated
                'cell_id': cell_id,
                'row': row_idx,
                'col': col_idx,
                'samples': aggregation_result['total_games']
            }

        except Exception as e:
            logger.error(f"Failed to derive matrix cell ({row_idx}, {col_idx}): {e}")
            return {
                'status': 'error',
                'error': str(e),
                'row': row_idx,
                'col': col_idx
            }

    def _generate_hand_combination(self, row_idx: int, col_idx: int) -> str:
        """
        Generate a descriptive hand combination string for matrix cell.

        Args:
            row_idx: Row index
            col_idx: Column index

        Returns:
            Hand combination description
        """
        # For a 13x13 matrix, we have 169 possible hand combinations
        total_hands = len(self.POKER_HANDS)

        # Map indices to hand names
        hero_hand_idx = row_idx
        villain_hand_idx = col_idx

        if hero_hand_idx >= total_hands or villain_hand_idx >= total_hands:
            return f"Unknown_{row_idx}_{col_idx}"

        hero_hand = self.POKER_HANDS[hero_hand_idx]
        villain_hand = self.POKER_HANDS[villain_hand_idx]

        # Create matchup description
        if hero_hand == villain_hand:
            return f"{hero_hand} vs {hero_hand}"
        else:
            return f"{hero_hand} vs {villain_hand}"

    def _ensure_matrix_cell_exists(
        self,
        matrix_id: int,
        row_idx: int,
        col_idx: int,
        hand_combination: str
    ) -> int:
        """
        Ensure a MatrixCell exists for the given position, creating it if necessary.

        Args:
            matrix_id: Hand matrix ID
            row_idx: Row index
            col_idx: Column index
            hand_combination: Hand combination description

        Returns:
            MatrixCell ID
        """
        with self.db_connection.session_scope() as session:
            # Check if cell already exists
            existing_cell = session.query(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id,
                MatrixCell.row_index == row_idx,
                MatrixCell.col_index == col_idx
            ).first()

            if existing_cell:
                # Update hand combination if it changed
                if existing_cell.hand_combination != hand_combination:
                    existing_cell.hand_combination = hand_combination
                    logger.debug(f"Updated hand combination for cell ({row_idx}, {col_idx})")
                return existing_cell.id

            # Create new cell
            new_cell = MatrixCell(
                matrix_id=matrix_id,
                row_index=row_idx,
                col_index=col_idx,
                hand_combination=hand_combination
            )
            session.add(new_cell)
            session.flush()  # Get the ID

            logger.debug(f"Created new MatrixCell: {hand_combination} at ({row_idx}, {col_idx})")
            return new_cell.id

    def _update_aggregated_metric(self, cell_id: int, aggregation_result: Dict[str, Any]) -> None:
        """
        Create or update the AggregatedMetric for a MatrixCell.

        Args:
            cell_id: MatrixCell ID
            aggregation_result: Aggregation results from AggregationEngine
        """
        with self.db_connection.session_scope() as session:
            # Check if aggregated metric already exists
            existing_metric = session.query(AggregatedMetric).filter(
                AggregatedMetric.cell_id == cell_id
            ).first()

            metric_data = {
                'cell_id': cell_id,
                'equity': aggregation_result.get('equity'),
                'win_probability': aggregation_result.get('win_probability'),
                'ev': aggregation_result.get('ev'),
                'jackpot_adjusted_ev': aggregation_result.get('jackpot_adjusted_ev'),
                'jackpot_frequency': aggregation_result.get('jackpot_frequency'),
                'avg_jackpot_payout': aggregation_result.get('avg_jackpot_payout'),
                'convergence_status': aggregation_result.get('convergence_status'),
                'last_updated': aggregation_result.get('last_updated', datetime.now(timezone.utc).isoformat())
            }

            if existing_metric:
                # Update existing metric
                for key, value in metric_data.items():
                    if hasattr(existing_metric, key):
                        setattr(existing_metric, key, value)
                logger.debug(f"Updated AggregatedMetric for cell {cell_id}")
            else:
                # Create new metric
                new_metric = AggregatedMetric(**metric_data)
                session.add(new_metric)
                logger.debug(f"Created new AggregatedMetric for cell {cell_id}")

    def get_matrix_completion_status(self, matrix_id: int) -> Dict[str, Any]:
        """
        Get completion status for a hand matrix.

        Args:
            matrix_id: Hand matrix ID

        Returns:
            Completion statistics
        """
        with self.db_connection.session_scope() as session:
            # Get matrix info
            hand_matrix = session.query(HandMatrix).filter(HandMatrix.id == matrix_id).first()
            if not hand_matrix:
                return {'error': 'Matrix not found'}

            # Parse matrix size
            try:
                rows, cols = map(int, hand_matrix.matrix_size.split('x'))
                total_cells = rows * cols
            except ValueError:
                return {'error': 'Invalid matrix size'}

            # Count existing cells and metrics
            cells_count = session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).count()
            metrics_count = session.query(AggregatedMetric).join(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id
            ).count()

            return {
                'matrix_id': matrix_id,
                'matrix_size': hand_matrix.matrix_size,
                'total_cells': total_cells,
                'cells_created': cells_count,
                'metrics_populated': metrics_count,
                'completion_percentage': (cells_count / total_cells * 100) if total_cells > 0 else 0,
                'metrics_completion_percentage': (metrics_count / total_cells * 100) if total_cells > 0 else 0
            }