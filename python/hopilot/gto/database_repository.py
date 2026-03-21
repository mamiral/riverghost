"""
Database repository for normalized poker schema integration.

Provides data access layer for the browser to interact with the normalized
database schema, translating browser contexts to efficient database queries.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from sqlalchemy import and_, select, func, text
from sqlalchemy.orm import Session

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger
from hopilot.models import (
    AggregatedMetric,
    MatrixCell,
    Simulation,
    HandMatrix,
    GameState,
    Bet
)
from hopilot.gto.data_model import PositionContext, ActionContext, MetricType, ConvergencePoint, JackpotStats

logger = get_logger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection or query fails."""
    pass


class InvalidContextError(Exception):
    """Raised when position/action/metric combination is invalid."""
    pass


class DatabaseRepository:
    """
    Repository for accessing normalized poker database.

    Translates browser-specific contexts (position, action, metric) into
    efficient database queries against the normalized schema.
    """

    def __init__(self, database_url: str):
        """
        Initialize repository with database connection.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        self.connection = DatabaseConnection(database_url)
        # Initialize database schema on first connection
        self.connection.create_tables()
        logger.info(f"DatabaseRepository initialized with: {database_url}")

    async def get_strategy_matrix(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: MetricType
    ) -> Dict[str, Dict[str, float]]:
        """
        Retrieve complete 13x13 strategy matrix for given context.

        Args:
            position: Player position context
            action: Decision action context
            metric: Display metric type

        Returns:
            Dictionary mapping hand keys to metric values

        Raises:
            DatabaseConnectionError: If database connection fails
            InvalidContextError: If position/action/metric combination is invalid
        """
        def _query_matrix() -> Dict[str, Dict[str, float]]:
            try:
                with self.connection.session_scope() as session:
                    # Find simulation matching position and action
                    position_filter = self._build_position_filter(position)
                    action_filter = self._build_action_filter(action)
                    
                    # Get the simulation
                    simulation = session.query(Simulation).filter(
                        and_(position_filter, action_filter)
                    ).order_by(Simulation.created_at.desc()).first()
                    
                    if not simulation:
                        return {}
                    
                    # Get the hand_matrix for this simulation
                    hand_matrix = session.query(HandMatrix).filter(
                        HandMatrix.simulation_id == simulation.id
                    ).first()
                    
                    if not hand_matrix:
                        return {}
                    
                    # Get metric column
                    metric_column = self._get_metric_column(metric)
                    
                    # Query all aggregated_metrics for this matrix
                    results = session.query(
                        MatrixCell.hand_combination,
                        metric_column
                    ).join(
                        AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id
                    ).filter(
                        MatrixCell.matrix_id == hand_matrix.id
                    ).all()
                    
                    # Build the matrix data dict
                    matrix_data = {}
                    for hand_combination, value in results:
                        if value is not None:
                            # Extract hero hand from combination (e.g., "AA vs Random" -> "AA")
                            hero_hand = hand_combination.split(' vs ')[0]
                            matrix_data[hero_hand] = {metric.id: float(value)}
                    
                    return matrix_data
            except Exception as e:
                logger.error(f"Database query failed for matrix {position.id}/{action.id}/{metric.id}: {e}")
                raise DatabaseConnectionError(f"Failed to retrieve strategy matrix: {e}") from e

        # Run in thread pool to avoid blocking
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _query_matrix)
        except Exception as e:
            logger.error(f"Async execution failed: {e}")
            raise DatabaseConnectionError(f"Async database operation failed: {e}") from e

    def get_strategy_matrix_sync(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: MetricType
    ) -> Dict[str, Dict[str, float]]:
        """
        Synchronous version of get_strategy_matrix.
        """
        def _query_matrix() -> Dict[str, Dict[str, float]]:
            try:
                with self.connection.session_scope() as session:
                    # Find simulation matching position and action
                    position_filter = self._build_position_filter(position)
                    action_filter = self._build_action_filter(action)
                    
                    # Get the simulation
                    simulation = session.query(Simulation).filter(
                        and_(position_filter, action_filter)
                    ).order_by(Simulation.created_at.desc()).first()
                    
                    if not simulation:
                        return {}
                    
                    # Get the hand_matrix for this simulation
                    hand_matrix = session.query(HandMatrix).filter(
                        HandMatrix.simulation_id == simulation.id
                    ).first()
                    
                    if not hand_matrix:
                        return {}
                    
                    # Get metric column
                    metric_column = self._get_metric_column(metric)
                    
                    # Query all aggregated_metrics for this matrix
                    results = session.query(
                        MatrixCell.hand_combination,
                        metric_column
                    ).join(
                        AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id
                    ).filter(
                        MatrixCell.matrix_id == hand_matrix.id
                    ).all()
                    
                    # Build the matrix data dict
                    matrix_data = {}
                    for hand_combination, value in results:
                        if value is not None:
                            # Extract hero hand from combination (e.g., "AA vs Random" -> "AA")
                            hero_hand = hand_combination.split(' vs ')[0]
                            matrix_data[hero_hand] = {metric.id: float(value)}
                    
                    return matrix_data
            except Exception as e:
                logger.error(f"Database query failed for matrix {position.id}/{action.id}/{metric.id}: {e}")
                raise DatabaseConnectionError(f"Failed to retrieve strategy matrix: {e}") from e

        return _query_matrix()

    async def get_hand_metric(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: MetricType,
        hand_key: str
    ) -> Optional[float]:
        """
        Retrieve specific hand metric value.

        Args:
            position: Player position context
            action: Decision action context
            metric: Display metric type
            hand_key: Specific hand identifier (e.g., "AKs")

        Returns:
            Metric value for the hand, or None if not found

        Raises:
            DatabaseConnectionError: If database connection fails
            InvalidContextError: If hand_key is invalid
        """
        def _query_hand() -> Optional[float]:
            try:
                with self.connection.session_scope() as session:
                    # Convert hand key to matrix coordinates
                    row_idx, col_idx = self._hand_key_to_matrix_coords(hand_key)
                    if row_idx is None or col_idx is None:
                        raise InvalidContextError(f"Invalid hand key: {hand_key}")

                    # Build filters
                    position_filter = self._build_position_filter(position)
                    action_filter = self._build_action_filter(action)
                    metric_column = self._get_metric_column(metric)

                    # Query specific cell using the optimized view
                    stmt = select(metric_column).select_from(text("matrix_data_with_context")).where(
                        and_(
                            text(f"row_index = {row_idx}"),
                            text(f"col_index = {col_idx}"),
                            text(f"position = '{position.id}'"),
                            text(f"action = '{action.id}'")
                        )
                    )

                    result = session.execute(stmt).scalar()
                    return float(result) if result is not None else None
            except InvalidContextError:
                raise
            except Exception as e:
                logger.error(f"Database query failed for hand {hand_key} in {position.id}/{action.id}/{metric.id}: {e}")
                raise DatabaseConnectionError(f"Failed to retrieve hand metric: {e}") from e

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _query_hand)
        except InvalidContextError:
            raise
        except Exception as e:
            logger.error(f"Async execution failed: {e}")
            raise DatabaseConnectionError(f"Async database operation failed: {e}") from e

    def _build_position_filter(self, position: PositionContext):
        """Build SQLAlchemy filter for position context."""
        # Simple like filter
        return Simulation.parameters.like(f'%{position.id}%')

    def _build_action_filter(self, action: ActionContext):
        """Build SQLAlchemy filter for action context."""
        # Simple like filter
        return Simulation.parameters.like(f'%{action.id}%')

    def _get_metric_column(self, metric: MetricType):
        """Get SQLAlchemy column for metric type."""
        column_map = {
            'WIN_LOSE_PROBABILITY': AggregatedMetric.equity,
            'EV': AggregatedMetric.jackpot_adjusted_ev,
            'EQUITY': AggregatedMetric.equity,
            'EQR': AggregatedMetric.jackpot_adjusted_ev
        }
        return column_map.get(metric.id, AggregatedMetric.equity)

    def _matrix_coords_to_hand_key(self, row_idx: int, col_idx: int) -> str:
        """Convert matrix coordinates to hand key (e.g., 'AKs')."""
        # Poker hand ranking: A=12, K=11, Q=10, J=9, T=8, 9=7, ..., 2=0
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

        rank1 = ranks[row_idx]
        rank2 = ranks[col_idx]

        if row_idx > col_idx:
            # Suited (higher rank first)
            return f"{rank1}{rank2}s"
        elif row_idx < col_idx:
            # Offsuit (higher rank first)
            return f"{rank2}{rank1}o"
        else:
            # Pair
            return f"{rank1}{rank2}"

    def _hand_key_to_matrix_coords(self, hand_key: str) -> tuple[Optional[int], Optional[int]]:
        """Convert hand key to matrix coordinates."""
        if len(hand_key) < 2:
            return None, None

        # Parse ranks
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        rank_map = {rank: idx for idx, rank in enumerate(ranks)}

        rank1, rank2 = hand_key[0], hand_key[1]
        suit_type = hand_key[2] if len(hand_key) > 2 else ''

        idx1 = rank_map.get(rank1)
        idx2 = rank_map.get(rank2)

        if idx1 is None or idx2 is None:
            return None, None

        # Determine matrix position based on suit type
        if suit_type == 's':  # suited
            return max(idx1, idx2), min(idx1, idx2)
        elif suit_type == 'o':  # offsuit
            return max(idx1, idx2), min(idx1, idx2)
        else:  # pair
            return idx1, idx1

    async def get_convergence_data(
        self,
        position: PositionContext,
        action: ActionContext
    ) -> List[ConvergencePoint]:
        """
        Retrieve convergence analysis data for position/action.

        Shows how equity values stabilize over time as more simulations are run.

        Args:
            position: Player position context
            action: Decision action context

        Returns:
            List of convergence data points over time
        """
        def _query_convergence() -> List[ConvergencePoint]:
            try:
                with self.connection.session_scope() as session:
                    # Build filters for position and action
                    position_filter = self._build_position_filter(position)
                    action_filter = self._build_action_filter(action)

                    # Query aggregated metrics grouped by simulation count
                    # This simulates convergence by showing equity at different sample sizes
                    query = (
                        session.query(
                            func.count(AggregatedMetric.id).label('simulation_count'),
                            func.avg(AggregatedMetric.equity).label('average_equity')
                        )
                        .join(MatrixCell, AggregatedMetric.cell_id == MatrixCell.id)
                        .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
                        .join(Simulation, HandMatrix.simulation_id == Simulation.id)
                        .where(and_(position_filter, action_filter))
                        .where(AggregatedMetric.convergence_status == 'CONVERGED')
                        .group_by(Simulation.id)  # Group by individual simulations
                        .order_by(func.count(AggregatedMetric.id))
                        .limit(20)  # Limit to reasonable number of data points
                    )

                    results = query.all()

                    # Convert to ConvergencePoint objects
                    convergence_points = []
                    cumulative_count = 0
                    for result in results:
                        cumulative_count += result.simulation_count
                        convergence_points.append(
                            ConvergencePoint.from_simulations(
                                num_simulations=cumulative_count,
                                average_equity=float(result.average_equity) if result.average_equity else 0.0
                            )
                        )

                    return convergence_points

            except Exception as e:
                logger.error(f"Convergence data query failed: {e}")
                raise DatabaseConnectionError(f"Failed to retrieve convergence data: {e}") from e

        # Run query in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query_convergence)

    async def get_jackpot_statistics(self) -> List[JackpotStats]:
        """
        Retrieve jackpot frequency and payout statistics.

        Returns:
            List of jackpot statistics by type

        Raises:
            DatabaseConnectionError: If database connection fails
        """
        def _query_jackpots() -> List[JackpotStats]:
            try:
                with self.connection.session_scope() as session:
                    # Query jackpot statistics grouped by type
                    stmt = select(
                        text("jackpot_type"),
                        func.count().label('frequency'),
                        func.avg(text("payout_amount")).label('avg_payout'),
                        func.sum(text("payout_amount")).label('total_payout')
                    ).select_from(text("Jackpots")).group_by(text("jackpot_type")).order_by(func.count().desc())

                    result = session.execute(stmt)
                    jackpot_stats = []

                    for row in result:
                        jackpot_type, frequency, avg_payout, total_payout = row
                        jackpot_stats.append(
                            JackpotStats(
                                jackpot_type=jackpot_type,
                                frequency=frequency,
                                avg_payout=float(avg_payout) if avg_payout else 0.0,
                                total_payout=float(total_payout) if total_payout else 0.0
                            )
                        )

                    return jackpot_stats

            except Exception as e:
                logger.error(f"Jackpot statistics query failed: {e}")
                raise DatabaseConnectionError(f"Failed to retrieve jackpot statistics: {e}") from e

        # Run query in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query_jackpots)

    async def get_simulation_summary(
        self,
        position: Optional[PositionContext] = None,
        action: Optional[ActionContext] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve summary statistics across simulations with optional filtering.

        Performs complex join across Simulations, HandMatrices, MatrixCells, and AggregatedMetrics
        to provide aggregated statistics by simulation parameters.

        Args:
            position: Optional position filter
            action: Optional action filter

        Returns:
            List of simulation summaries with aggregated metrics
        """
        def _query_simulation_summary() -> List[Dict[str, any]]:
            try:
                # Build base query with complex joins
                query = (
                    select(
                        Simulation.id.label('simulation_id'),
                        Simulation.parameters,
                        Simulation.created_at,
                        func.count(MatrixCell.id).label('total_cells'),
                        func.avg(AggregatedMetric.equity).label('avg_equity'),
                        func.avg(AggregatedMetric.jackpot_adjusted_ev).label('avg_jackpot_ev'),
                        func.count(func.distinct(AggregatedMetric.id)).filter(
                            AggregatedMetric.convergence_status == 'CONVERGED'
                        ).label('converged_cells'),
                        func.max(AggregatedMetric.last_updated).label('last_updated')
                    )
                    .select_from(Simulation)
                    .join(HandMatrix, Simulation.id == HandMatrix.simulation_id)
                    .join(MatrixCell, HandMatrix.id == MatrixCell.matrix_id)
                    .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
                    .group_by(Simulation.id, Simulation.parameters, Simulation.created_at)
                )

                # Apply optional filters
                if position:
                    query = query.where(
                        Simulation.parameters.like(f'%position:{position.id}%')
                    )
                if action:
                    query = query.where(
                        Simulation.parameters.like(f'%action:{action.id}%')
                    )

                query = query.order_by(Simulation.created_at.desc())

                with self.db_connection.session() as session:
                    results = session.execute(query).fetchall()

                    summaries = []
                    for row in results:
                        summaries.append({
                            'simulation_id': row.simulation_id,
                            'parameters': row.parameters,
                            'created_at': row.created_at,
                            'total_cells': row.total_cells,
                            'avg_equity': float(row.avg_equity) if row.avg_equity else None,
                            'avg_jackpot_ev': float(row.avg_jackpot_ev) if row.avg_jackpot_ev else None,
                            'converged_cells': row.converged_cells,
                            'convergence_rate': row.converged_cells / row.total_cells if row.total_cells > 0 else 0,
                            'last_updated': row.last_updated
                        })

                    return summaries

            except Exception as e:
                logger.error(f"Simulation summary query failed: {e}")
                raise DatabaseConnectionError(f"Failed to retrieve simulation summary: {e}") from e

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query_simulation_summary)

    async def get_hand_performance_comparison(
        self,
        hand_keys: List[str],
        position: Optional[PositionContext] = None,
        action: Optional[ActionContext] = None
    ) -> List[Dict[str, any]]:
        """
        Compare performance of specific hands across different simulation contexts.

        Performs complex multi-table join to compare hand performance metrics.

        Args:
            hand_keys: List of hand keys to compare (e.g., ["AKs", "QQ", "JTs"])
            position: Optional position filter
            action: Optional action filter

        Returns:
            List of hand performance comparisons with metrics across contexts
        """
        def _query_hand_comparison() -> List[Dict[str, any]]:
            try:
                # Build query for hand-specific performance
                query = (
                    select(
                        MatrixCell.hand_key,
                        Simulation.parameters,
                        AggregatedMetric.equity,
                        AggregatedMetric.jackpot_adjusted_ev,
                        AggregatedMetric.convergence_status,
                        AggregatedMetric.last_updated
                    )
                    .select_from(MatrixCell)
                    .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
                    .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
                    .join(Simulation, HandMatrix.simulation_id == Simulation.id)
                    .where(MatrixCell.hand_key.in_(hand_keys))
                )

                # Apply optional filters
                if position:
                    query = query.where(
                        Simulation.parameters.like(f'%position:{position.id}%')
                    )
                if action:
                    query = query.where(
                        Simulation.parameters.like(f'%action:{action.id}%')
                    )

                query = query.order_by(MatrixCell.hand_key, Simulation.created_at.desc())

                with self.db_connection.session() as session:
                    results = session.execute(query).fetchall()

                    comparisons = []
                    for row in results:
                        comparisons.append({
                            'hand_key': row.hand_key,
                            'simulation_params': row.parameters,
                            'equity': float(row.equity) if row.equity else None,
                            'jackpot_adjusted_ev': float(row.jackpot_adjusted_ev) if row.jackpot_adjusted_ev else None,
                            'convergence_status': row.convergence_status,
                            'last_updated': row.last_updated
                        })

                    return comparisons

            except Exception as e:
                logger.error(f"Hand performance comparison query failed: {e}")
                raise DatabaseConnectionError(f"Failed to retrieve hand performance comparison: {e}") from e

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query_hand_comparison)

    async def get_matrix_statistics(
        self,
        position: PositionContext,
        action: ActionContext
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive statistics for a complete strategy matrix.

        Performs complex aggregation across all cells in a matrix context.

        Args:
            position: Position context
            action: Action context

        Returns:
            Dictionary with matrix-wide statistics and distributions
        """
        def _query_matrix_stats() -> Dict[str, any]:
            try:
                # Query for matrix-wide statistics
                stats_query = (
                    select(
                        func.count(MatrixCell.id).label('total_cells'),
                        func.count(AggregatedMetric.id).filter(
                            AggregatedMetric.convergence_status == 'CONVERGED'
                        ).label('converged_cells'),
                        func.avg(AggregatedMetric.equity).label('avg_equity'),
                        func.min(AggregatedMetric.equity).label('min_equity'),
                        func.max(AggregatedMetric.equity).label('max_equity'),
                        func.stddev(AggregatedMetric.equity).label('equity_stddev'),
                        func.avg(AggregatedMetric.jackpot_adjusted_ev).label('avg_jackpot_ev'),
                        func.min(AggregatedMetric.jackpot_adjusted_ev).label('min_jackpot_ev'),
                        func.max(AggregatedMetric.jackpot_adjusted_ev).label('max_jackpot_ev'),
                        func.stddev(AggregatedMetric.jackpot_adjusted_ev).label('jackpot_ev_stddev')
                    )
                    .select_from(MatrixCell)
                    .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
                    .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
                    .join(Simulation, HandMatrix.simulation_id == Simulation.id)
                    .where(Simulation.parameters.like(f'%position:{position.id}%'))
                    .where(Simulation.parameters.like(f'%action:{action.id}%'))
                )

                # Query for equity distribution buckets
                equity_dist_query = (
                    select(
                        func.floor(AggregatedMetric.equity * 10).label('equity_bucket'),
                        func.count(AggregatedMetric.id).label('count')
                    )
                    .select_from(MatrixCell)
                    .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
                    .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
                    .join(Simulation, HandMatrix.simulation_id == Simulation.id)
                    .where(Simulation.parameters.like(f'%position:{position.id}%'))
                    .where(Simulation.parameters.like(f'%action:{action.id}%'))
                    .where(AggregatedMetric.equity.isnot(None))
                    .group_by(func.floor(AggregatedMetric.equity * 10))
                    .order_by(func.floor(AggregatedMetric.equity * 10))
                )

                with self.db_connection.session() as session:
                    # Get main statistics
                    stats_result = session.execute(stats_query).first()

                    # Get equity distribution
                    equity_dist = session.execute(equity_dist_query).fetchall()

                    if not stats_result:
                        return {
                            'total_cells': 0,
                            'converged_cells': 0,
                            'convergence_rate': 0,
                            'equity_stats': {},
                            'jackpot_ev_stats': {},
                            'equity_distribution': []
                        }

                    # Build distribution data
                    distribution = [
                        {
                            'equity_range': f"{i/10:.1f}-{(i+1)/10:.1f}",
                            'count': count
                        }
                        for i, count in [(row.equity_bucket, row.count) for row in equity_dist]
                    ]

                    return {
                        'total_cells': stats_result.total_cells,
                        'converged_cells': stats_result.converged_cells,
                        'convergence_rate': stats_result.converged_cells / stats_result.total_cells if stats_result.total_cells > 0 else 0,
                        'equity_stats': {
                            'average': float(stats_result.avg_equity) if stats_result.avg_equity else None,
                            'minimum': float(stats_result.min_equity) if stats_result.min_equity else None,
                            'maximum': float(stats_result.max_equity) if stats_result.max_equity else None,
                            'standard_deviation': float(stats_result.equity_stddev) if stats_result.equity_stddev else None
                        },
                        'jackpot_ev_stats': {
                            'average': float(stats_result.avg_jackpot_ev) if stats_result.avg_jackpot_ev else None,
                            'minimum': float(stats_result.min_jackpot_ev) if stats_result.min_jackpot_ev else None,
                            'maximum': float(stats_result.max_jackpot_ev) if stats_result.max_jackpot_ev else None,
                            'standard_deviation': float(stats_result.jackpot_ev_stddev) if stats_result.jackpot_ev_stddev else None
                        },
                        'equity_distribution': distribution
                    }

            except Exception as e:
                logger.error(f"Matrix statistics query failed: {e}")
                raise DatabaseConnectionError(f"Failed to retrieve matrix statistics: {e}") from e

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query_matrix_stats)

    # ========================================================================
    # PHASE 3: WRITE METHODS for Precompute System
    # ========================================================================

    def create_simulation(self, parameters: str) -> int:
        """Create a new Simulation record and return its ID."""
        with self.connection.session_scope() as session:
            # Generate name from timestamp
            sim_name = f"sim_{datetime.now(timezone.utc).isoformat()}"
            sim = Simulation(
                name=sim_name,
                parameters=parameters,
                start_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.commit()
            return sim.id

    def create_hand_matrix(self, simulation_id: int, matrix_size: str = "13x13") -> int:
        """Create HandMatrix record for storing strategy data."""
        with self.connection.session_scope() as session:
            matrix = HandMatrix(
                simulation_id=simulation_id,
                matrix_size=matrix_size
            )
            session.add(matrix)
            session.commit()
            return matrix.id

    def upsert_matrix_cell(self, matrix_id: int, row_idx: int, col_idx: int, hand_key: str, metrics: Dict[str, float], status: str) -> None:
        """
        Create or update MatrixCell and associated AggregatedMetric with equity data.
        
        According to schema:
        - MatrixCell stores: row_index, col_index, hand_combination
        - AggregatedMetric stores: equity, convergence_status, etc.
        (Many-to-one relationship: one AggregatedMetric per MatrixCell)
        """
        with self.connection.session_scope() as session:
            from sqlalchemy import and_
            
            # Step 1: Create or update MatrixCell
            existing_cell = session.query(MatrixCell).filter(
                and_(
                    MatrixCell.matrix_id == matrix_id,
                    MatrixCell.row_index == row_idx,
                    MatrixCell.col_index == col_idx
                )
            ).first()

            if existing_cell:
                cell_id = existing_cell.id
                existing_cell.hand_combination = hand_key
            else:
                cell = MatrixCell(
                    matrix_id=matrix_id,
                    row_index=row_idx,
                    col_index=col_idx,
                    hand_combination=hand_key
                )
                session.add(cell)
                session.flush()
                cell_id = cell.id

            # Step 2: Create or update AggregatedMetric with equity data
            existing_metric = session.query(AggregatedMetric).filter_by(
                cell_id=cell_id
            ).first()
            
            equity = metrics.get("equity", 0.5)
            jackpot_adjusted_ev = metrics.get("jackpot_adjusted_ev", 0.0)
            
            if existing_metric:
                # Update existing metric
                existing_metric.equity = equity
                existing_metric.jackpot_adjusted_ev = jackpot_adjusted_ev
                existing_metric.convergence_status = status
                existing_metric.last_updated = datetime.now(timezone.utc)
            else:
                # Create new metric
                metric_record = AggregatedMetric(
                    cell_id=cell_id,
                    equity=equity,
                    jackpot_adjusted_ev=jackpot_adjusted_ev,
                    convergence_status=status,
                    last_updated=datetime.now(timezone.utc)
                )
                session.add(metric_record)
            
            session.commit()


