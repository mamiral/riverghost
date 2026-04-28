"""
Database repository for normalized poker schema integration.

Provides data access layer for the browser to interact with the normalized
database schema, translating browser contexts to efficient database queries.
"""

import asyncio
from types import SimpleNamespace
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from sqlalchemy import and_, select, func, text, or_
from sqlalchemy.orm import Session, selectinload

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger
from hopilot.models import (
    AggregatedMetric,
    MatrixCell,
    Simulation,
    HandMatrix,
    GameState,
    Player,
    Bet,
    Jackpot,
    PrecomputeJobSession,
    ScenarioRunLink,
)
from hopilot.gto.data_model import PositionContext, ActionContext, MetricType, ConvergencePoint, JackpotStats
from hopilot.gto.aggregation_engine import AggregationEngine
from hopilot.gto.matrix_sweep_contract import normalize_scenario_contract

logger = get_logger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection or query fails."""
    pass


class InvalidContextError(Exception):
    """Raised when position/action/metric combination is invalid."""
    pass


class DataIntegrityError(Exception):
    """Raised when data integrity constraints are violated."""
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
        # Initialize aggregation engine for on-demand matrix computation
        self.aggregation_engine = AggregationEngine(database_url)
        logger.info(f"DatabaseRepository initialized with: {database_url}")

    # ===== DATA INTEGRITY VALIDATION METHODS =====

    def _validate_game_state_exists(self, game_state_id: int) -> None:
        """
        Validate that a game state exists.

        Args:
            game_state_id: GameState ID to validate

        Raises:
            DataIntegrityError: If game state does not exist
        """
        try:
            with self.connection.session_scope() as session:
                exists = session.query(GameState.id).filter(GameState.id == game_state_id).first() is not None
                if not exists:
                    raise DataIntegrityError(f"GameState with ID {game_state_id} does not exist")
        except DataIntegrityError:
            raise
        except Exception as e:
            logger.error(f"Error validating game state {game_state_id}: {e}")
            raise DatabaseConnectionError(f"Failed to validate game state existence: {e}") from e

    def _validate_player_exists(self, player_id: int) -> None:
        """
        Validate that a player exists.

        Args:
            player_id: Player ID to validate

        Raises:
            DataIntegrityError: If player does not exist
        """
        try:
            with self.connection.session_scope() as session:
                exists = session.query(Player.id).filter(Player.id == player_id).first() is not None
                if not exists:
                    raise DataIntegrityError(f"Player with ID {player_id} does not exist")
        except DataIntegrityError:
            raise
        except Exception as e:
            logger.error(f"Error validating player {player_id}: {e}")
            raise DatabaseConnectionError(f"Failed to validate player existence: {e}") from e

    def _validate_bet_exists(self, bet_id: int) -> None:
        """
        Validate that a bet exists.

        Args:
            bet_id: Bet ID to validate

        Raises:
            DataIntegrityError: If bet does not exist
        """
        try:
            with self.connection.session_scope() as session:
                exists = session.query(Bet.id).filter(Bet.id == bet_id).first() is not None
                if not exists:
                    raise DataIntegrityError(f"Bet with ID {bet_id} does not exist")
        except DataIntegrityError:
            raise
        except Exception as e:
            logger.error(f"Error validating bet {bet_id}: {e}")
            raise DatabaseConnectionError(f"Failed to validate bet existence: {e}") from e

    def _validate_jackpot_exists(self, jackpot_id: int) -> None:
        """
        Validate that a jackpot exists.

        Args:
            jackpot_id: Jackpot ID to validate

        Raises:
            DataIntegrityError: If jackpot does not exist
        """
        try:
            with self.connection.session_scope() as session:
                exists = session.query(Jackpot.id).filter(Jackpot.id == jackpot_id).first() is not None
                if not exists:
                    raise DataIntegrityError(f"Jackpot with ID {jackpot_id} does not exist")
        except DataIntegrityError:
            raise
        except Exception as e:
            logger.error(f"Error validating jackpot {jackpot_id}: {e}")
            raise DatabaseConnectionError(f"Failed to validate jackpot existence: {e}") from e

    def _validate_matrix_cell_exists(self, cell_id: int) -> None:
        """
        Validate that a matrix cell exists.

        Args:
            cell_id: MatrixCell ID to validate

        Raises:
            DataIntegrityError: If matrix cell does not exist
        """
        try:
            with self.connection.session_scope() as session:
                exists = session.query(MatrixCell.id).filter(MatrixCell.id == cell_id).first() is not None
                if not exists:
                    raise DataIntegrityError(f"MatrixCell with ID {cell_id} does not exist")
        except DataIntegrityError:
            raise
        except Exception as e:
            logger.error(f"Error validating matrix cell {cell_id}: {e}")
            raise DatabaseConnectionError(f"Failed to validate matrix cell existence: {e}") from e

    def _validate_game_state_data(self, game_state_data: Dict[str, Any]) -> None:
        """
        Validate game state data before creation/update.

        Args:
            game_state_data: Game state data to validate

        Raises:
            DataIntegrityError: If validation fails
        """
        required_fields = ['pot_size']
        for field in required_fields:
            if field not in game_state_data:
                raise DataIntegrityError(f"Missing required field: {field}")

        if 'board_cards_str' not in game_state_data:
            raise DataIntegrityError("Missing required field: board_cards_str")

        # Validate optional legacy fields
        if 'cell_id' in game_state_data:
            self._validate_matrix_cell_exists(game_state_data['cell_id'])

        # Validate pot_size
        if game_state_data['pot_size'] < 0:
            raise DataIntegrityError("Pot size cannot be negative")

        # Validate round if provided
        if 'round' in game_state_data and game_state_data['round'] not in ['preflop', 'flop', 'turn', 'river']:
            raise DataIntegrityError("Round must be 'preflop', 'flop', 'turn', or 'river'")

        if 'board_cards_str' in game_state_data and not isinstance(game_state_data['board_cards_str'], str):
            raise DataIntegrityError("board_cards_str must be a string")

    def _resolve_board_cards_str(self, game_state_data: Dict[str, Any]) -> str:
        """Resolve raw board cards string from provided game state data."""
        board_cards_str = game_state_data.get('board_cards_str')
        if board_cards_str is None:
            raise DataIntegrityError("Missing required field: board_cards_str")
        return board_cards_str

    def _validate_player_data(self, player_data: Dict[str, Any]) -> None:
        """
        Validate player data before creation/update.

        Args:
            player_data: Player data to validate

        Raises:
            DataIntegrityError: If validation fails
        """
        required_fields = ['game_state_id', 'position', 'hole_cards', 'stack_size']
        for field in required_fields:
            if field not in player_data:
                raise DataIntegrityError(f"Missing required field: {field}")

        # Validate foreign keys
        self._validate_game_state_exists(player_data['game_state_id'])

        # Validate position
        if not player_data['position'] or not player_data['position'].strip():
            raise DataIntegrityError("Position cannot be empty")

        # Validate hole cards format (basic check)
        hole_cards = player_data['hole_cards']
        if len(hole_cards) != 4:
            raise DataIntegrityError(f"Hole cards must be 4 characters (rank+suit + rank+suit), got: {hole_cards}")

        # Validate stack size
        if player_data['stack_size'] < 0:
            raise DataIntegrityError("Stack size cannot be negative")

    def _validate_bet_data(self, bet_data: Dict[str, Any]) -> None:
        """
        Validate bet data before creation/update.

        Args:
            bet_data: Bet data to validate

        Raises:
            DataIntegrityError: If validation fails
        """
        required_fields = ['game_state_id', 'player_id', 'amount']
        for field in required_fields:
            if field not in bet_data:
                raise DataIntegrityError(f"Missing required field: {field}")

        # Validate foreign keys
        self._validate_game_state_exists(bet_data['game_state_id'])
        self._validate_player_exists(bet_data['player_id'])

        # Validate amount
        if bet_data['amount'] <= 0:
            raise DataIntegrityError("Bet amount must be positive")

        # Validate action type
        action_type = bet_data.get('action_type', 'raise')
        if action_type not in ['fold', 'call', 'raise']:
            raise DataIntegrityError("Action type must be 'fold', 'call', or 'raise'")

        # Validate round
        round_value = bet_data.get('round', 'preflop')
        if round_value not in ['preflop', 'flop', 'turn', 'river']:
            raise DataIntegrityError("Round must be 'preflop', 'flop', 'turn', or 'river'")

    def _validate_board_card_data(self, board_card_data: Dict[str, Any]) -> None:
        """
        Validate board card data before creation/update.

        Args:
            board_card_data: Board card data to validate

        Raises:
            DataIntegrityError: If validation fails
        """
        required_fields = ['flop1', 'flop2', 'flop3', 'turn', 'river']
        for field in required_fields:
            if field not in board_card_data:
                raise DataIntegrityError(f"Missing required field: {field}")

        # All validation is handled by the BoardCard model itself
        # The model will raise ValueError for invalid data

    def _validate_jackpot_data(self, jackpot_data: Dict[str, Any]) -> None:
        """
        Validate jackpot data before creation/update.

        Args:
            jackpot_data: Jackpot data to validate

        Raises:
            DataIntegrityError: If validation fails
        """
        required_fields = ['game_state_id', 'player_id', 'jackpot_type', 'payout_amount', 'qualifying_cards']
        for field in required_fields:
            if field not in jackpot_data:
                raise DataIntegrityError(f"Missing required field: {field}")

        # Validate foreign keys
        self._validate_game_state_exists(jackpot_data['game_state_id'])
        self._validate_player_exists(jackpot_data['player_id'])

        # Validate payout amount
        if jackpot_data['payout_amount'] <= 0:
            raise DataIntegrityError("Payout amount must be positive")

        # Validate qualifying cards
        qualifying_cards = jackpot_data['qualifying_cards']
        if not isinstance(qualifying_cards, list) or len(qualifying_cards) == 0:
            raise DataIntegrityError("Qualifying cards must be a non-empty list")

        # Validate jackpot type (allow custom types)
        jackpot_type = jackpot_data['jackpot_type']
        if not jackpot_type or not jackpot_type.strip():
            raise DataIntegrityError("Jackpot type cannot be empty")

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
                    ).order_by(Simulation.id.desc()).first()
                    
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
        Get strategy matrix using on-demand aggregation from GameStates.

        This method replaces the old AggregatedMetric-based approach with
        real-time computation using the aggregation engine.
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
                    ).order_by(Simulation.id.desc()).first()

                    if not simulation:
                        logger.debug(f"No simulation found for position={position.id}, action={action.id}")
                        return {}

                    # Get the hand_matrix for this simulation
                    hand_matrix = session.query(HandMatrix).filter(
                        HandMatrix.simulation_id == simulation.id
                    ).first()

                    if not hand_matrix:
                        logger.debug(f"No hand matrix found for simulation {simulation.id}")
                        return {}

                    # Get all matrix cells for this matrix
                    matrix_cells = session.query(MatrixCell).filter(
                        MatrixCell.matrix_id == hand_matrix.id
                    ).all()

                    if not matrix_cells:
                        logger.debug(f"No matrix cells found for matrix {hand_matrix.id}")
                        return {}

                    # Build matrix data by computing aggregations for each cell
                    matrix_data = {}
                    for cell in matrix_cells:
                        # Use aggregation engine to compute metrics for this cell
                        aggregated_data = self.aggregation_engine.compute_matrix_cell_from_game_states(
                            matrix_id=hand_matrix.id,
                            row_index=cell.row_index,
                            col_index=cell.col_index,
                            min_samples=100  # Minimum samples for reliable aggregation
                        )

                        if aggregated_data:
                            # Extract the requested metric
                            metric_value = None
                            if metric.id == "EQUITY":
                                metric_value = aggregated_data.get('equity', 0.0)
                            elif metric.id == "EV":
                                metric_value = aggregated_data.get('jackpot_adjusted_ev', 0.0)
                            elif metric.id == "WIN_LOSE_PROBABILITY":
                                # For win/lose probability, use equity as approximation
                                metric_value = aggregated_data.get('equity', 0.0)
                            else:
                                logger.warning(f"Unsupported metric: {metric.id}")
                                continue

                            # Use hand_combination as the key (e.g., "AA vs Random")
                            matrix_data[cell.hand_combination] = {metric.id: float(metric_value)}

                    logger.info(f"Computed matrix data for {len(matrix_data)} cells using aggregation engine")
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

    def create_simulation(self, parameters: Any) -> int:
        """Create a new Simulation record and return its ID."""
        if isinstance(parameters, str):
            import json
            parameters = json.loads(parameters)

        with self.connection.session_scope() as session:
            # Generate name from timestamp
            sim_name = f"sim_{datetime.now(timezone.utc).isoformat()}"
            sim = Simulation(
                name=sim_name,
                parameters=dict(parameters),
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

    def create_matrix_sweep_simulation(
        self,
        parameters: Dict[str, Any],
        *,
        name: Optional[str] = None,
        start_timestamp: Optional[datetime] = None,
    ) -> int:
        """Create one simulation row for a matrix-sweep run."""
        with self.connection.session_scope() as session:
            simulation = Simulation(
                name=name or f"matrix_sweep_{datetime.now(timezone.utc).isoformat()}",
                parameters=dict(parameters),
                start_timestamp=start_timestamp or datetime.now(timezone.utc),
            )
            session.add(simulation)
            session.flush()
            return simulation.id

    def update_matrix_sweep_simulation(
        self,
        simulation_id: int,
        *,
        parameters: Optional[Dict[str, Any]] = None,
        end_timestamp: Optional[datetime] = None,
    ) -> None:
        """Update persisted matrix-sweep metadata for an existing simulation."""
        with self.connection.session_scope() as session:
            simulation = session.query(Simulation).filter(Simulation.id == simulation_id).first()
            if simulation is None:
                raise DataIntegrityError(f"Simulation with ID {simulation_id} does not exist")

            if parameters is not None:
                simulation.parameters = dict(parameters)
            if end_timestamp is not None:
                simulation.end_timestamp = end_timestamp

    def create_precompute_job_session(
        self,
        *,
        scenario_fingerprint: str,
        requested_scenarios: int,
    ) -> int:
        """Create a durable precompute job session for UI-driven run tracing."""
        with self.connection.session_scope() as session:
            job_session = PrecomputeJobSession(
                scenario_fingerprint=scenario_fingerprint,
                run_state="RUNNING",
                requested_scenarios=requested_scenarios,
                completed_scenarios=0,
                failed_scenarios=0,
                started_at=datetime.now(timezone.utc),
                elapsed_active_ms=0,
            )
            session.add(job_session)
            session.flush()
            return job_session.id

    def update_precompute_job_session(
        self,
        job_session_id: int,
        *,
        run_state: Optional[str] = None,
        completed_scenarios: Optional[int] = None,
        failed_scenarios: Optional[int] = None,
        finished_at: Optional[datetime] = None,
        elapsed_active_ms: Optional[int] = None,
    ) -> None:
        """Update an existing precompute job session record."""
        with self.connection.session_scope() as session:
            job_session = session.query(PrecomputeJobSession).filter(PrecomputeJobSession.id == job_session_id).first()
            if job_session is None:
                raise DataIntegrityError(f"Precompute job session {job_session_id} does not exist")
            if run_state is not None:
                job_session.run_state = run_state
            if completed_scenarios is not None:
                job_session.completed_scenarios = completed_scenarios
            if failed_scenarios is not None:
                job_session.failed_scenarios = failed_scenarios
            if finished_at is not None:
                job_session.finished_at = finished_at
            if elapsed_active_ms is not None:
                job_session.elapsed_active_ms = elapsed_active_ms

    def get_precompute_job_session(self, job_session_id: int) -> Optional[PrecomputeJobSession]:
        """Return a durable precompute job session record."""
        with self.connection.session_scope() as session:
            return session.query(PrecomputeJobSession).filter(PrecomputeJobSession.id == job_session_id).first()

    def get_scenario_run_link(self, scenario_link_id: int) -> Optional[ScenarioRunLink]:
        """Return a durable scenario run link record."""
        with self.connection.session_scope() as session:
            return session.query(ScenarioRunLink).filter(ScenarioRunLink.id == scenario_link_id).first()

    def get_scenario_run_links_for_job(self, job_session_id: int) -> list[ScenarioRunLink]:
        """Return scenario run links for a precompute job session."""
        with self.connection.session_scope() as session:
            return (
                session.query(ScenarioRunLink)
                .filter(ScenarioRunLink.job_session_id == job_session_id)
                .order_by(ScenarioRunLink.scenario_index)
                .all()
            )

    def create_scenario_run_link(
        self,
        *,
        job_session_id: int,
        scenario_index: int,
        scenario_key: str,
        scenario_contract: Dict[str, Any],
        status: str = "PENDING",
    ) -> int:
        """Create a durable scenario linkage record for a precompute job."""
        with self.connection.session_scope() as session:
            link = ScenarioRunLink(
                job_session_id=job_session_id,
                scenario_index=scenario_index,
                scenario_key=scenario_key,
                scenario_contract=dict(scenario_contract),
                status=status,
            )
            session.add(link)
            session.flush()
            return link.id

    def update_scenario_run_link(
        self,
        scenario_link_id: int,
        *,
        status: Optional[str] = None,
        simulation_id: Optional[int] = None,
        matrix_id: Optional[int] = None,
        failure_boundary: Optional[str] = None,
        failure_reason: Optional[str] = None,
        scenario_contract: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update a scenario run link with outcome and diagnostics."""
        with self.connection.session_scope() as session:
            link = session.query(ScenarioRunLink).filter(ScenarioRunLink.id == scenario_link_id).first()
            if link is None:
                raise DataIntegrityError(f"Scenario run link {scenario_link_id} does not exist")
            if status is not None:
                link.status = status
            if simulation_id is not None:
                link.simulation_id = simulation_id
            if matrix_id is not None:
                link.matrix_id = matrix_id
            if failure_boundary is not None:
                link.failure_boundary = failure_boundary
            if failure_reason is not None:
                link.failure_reason = failure_reason
            if scenario_contract is not None:
                link.scenario_contract = dict(scenario_contract)

    def get_simulation_record(self, simulation_id: int) -> Optional[Simulation]:
        """Return one simulation ORM object with its hand matrix eagerly loaded."""
        with self.connection.session_scope() as session:
            simulation = (
                session.query(Simulation)
                .options(
                    selectinload(Simulation.hand_matrix).selectinload(HandMatrix.matrix_cells)
                )
                .filter(Simulation.id == simulation_id)
                .first()
            )
            return simulation

    def get_simulation_for_hand_matrix(self, hand_matrix_id: int) -> Optional[Simulation]:
        """Return the simulation for a given hand matrix ID."""
        with self.connection.session_scope() as session:
            matrix = session.query(HandMatrix).filter(HandMatrix.id == hand_matrix_id).first()
            if matrix is None:
                return None
            return matrix.simulation

    def get_or_create_hand_matrix_for_simulation(
        self,
        simulation_id: int,
        *,
        matrix_size: str = "13x13",
    ) -> int:
        """Return the hand matrix ID for a simulation, creating it when missing."""
        with self.connection.session_scope() as session:
            matrix = session.query(HandMatrix).filter(HandMatrix.simulation_id == simulation_id).first()
            if matrix is None:
                matrix = HandMatrix(simulation_id=simulation_id, matrix_size=matrix_size)
                session.add(matrix)
                session.flush()
            return matrix.id

    def get_hand_matrix_by_simulation(self, simulation_id: int) -> Optional[HandMatrix]:
        """Return the hand matrix for a simulation with cells and metrics loaded."""
        with self.connection.session_scope() as session:
            matrix = (
                session.query(HandMatrix)
                .options(selectinload(HandMatrix.matrix_cells).selectinload(MatrixCell.aggregated_metric))
                .filter(HandMatrix.simulation_id == simulation_id)
                .first()
            )
            return matrix

    def get_latest_game_state_id(self) -> int:
        """Return the latest raw game-state ID, or 0 when no rows exist."""
        with self.connection.session_scope() as session:
            latest_id = session.query(func.max(GameState.id)).scalar()
            return int(latest_id or 0)

    def get_run_game_states(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> List[GameState]:
        """Return raw game states and players inside one persisted run boundary."""
        with self.connection.session_scope() as session:
            return (
                session.query(GameState)
                .options(selectinload(GameState.players))
                .filter(GameState.id >= raw_game_state_id_start, GameState.id <= raw_game_state_id_end)
                .order_by(GameState.id.asc())
                .all()
            )

    def get_run_raw_counts(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> Dict[str, int]:
        """Return raw row counts for one run boundary."""
        with self.connection.session_scope() as session:
            raw_game_states = session.query(func.count(GameState.id)).filter(
                GameState.id >= raw_game_state_id_start,
                GameState.id <= raw_game_state_id_end,
            ).scalar()
            raw_players = session.query(func.count(Player.id)).join(GameState).filter(
                GameState.id >= raw_game_state_id_start,
                GameState.id <= raw_game_state_id_end,
            ).scalar()
            return {
                "raw_game_states": int(raw_game_states or 0),
                "raw_players": int(raw_players or 0),
            }

    def delete_matrix_summaries(self, matrix_id: int) -> None:
        """Delete only summary rows for one hand matrix, preserving raw rows."""
        with self.connection.session_scope() as session:
            cells = session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).all()
            for cell in cells:
                session.delete(cell)

    def find_matrix_sweep_run_by_contract(self, scenario_contract: Dict[str, Any]) -> Optional[Simulation]:
        """Find one persisted matrix-sweep run by its canonical scenario contract."""
        normalized_contract = normalize_scenario_contract(scenario_contract)
        contract_keys = [
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
        ]

        with self.connection.session_scope() as session:
            candidates = (
                session.query(Simulation)
                .filter(Simulation.parameters["run_kind"].as_string() == normalized_contract["run_kind"])
                .order_by(Simulation.end_timestamp.desc().nulls_last(), Simulation.id.desc())
                .all()
            )

            for candidate in candidates:
                try:
                    parameters = normalize_scenario_contract(candidate.parameters)
                except Exception:
                    continue

                if not all(parameters.get(key) == normalized_contract.get(key) for key in contract_keys):
                    continue

                if candidate.end_timestamp is None:
                    continue

                aggregated_exists = (
                    session.query(AggregatedMetric.id)
                    .join(MatrixCell, AggregatedMetric.cell_id == MatrixCell.id)
                    .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
                    .filter(HandMatrix.simulation_id == candidate.id)
                    .first()
                )
                if aggregated_exists is None:
                    continue

                return candidate

            return None

    def list_matrix_sweep_runs_by_contract(self, scenario_contract: Dict[str, Any]) -> List[Simulation]:
        """Return all completed runs matching the canonical scenario contract."""
        normalized_contract = normalize_scenario_contract(scenario_contract)
        contract_keys = [
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
        ]

        with self.connection.session_scope() as session:
            candidates = (
                session.query(Simulation)
                .filter(Simulation.parameters["run_kind"].as_string() == normalized_contract["run_kind"])
                .order_by(Simulation.end_timestamp.desc().nulls_last(), Simulation.id.desc())
                .all()
            )

            matches: List[Simulation] = []
            for candidate in candidates:
                try:
                    parameters = normalize_scenario_contract(candidate.parameters)
                except Exception:
                    continue

                if not all(parameters.get(key) == normalized_contract.get(key) for key in contract_keys):
                    continue

                if candidate.end_timestamp is None:
                    continue

                aggregated_exists = (
                    session.query(AggregatedMetric.id)
                    .join(MatrixCell, AggregatedMetric.cell_id == MatrixCell.id)
                    .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
                    .filter(HandMatrix.simulation_id == candidate.id)
                    .first()
                )
                if aggregated_exists is None:
                    continue

                matches.append(candidate)

            return matches

    def get_cross_run_matrix_summary(self, scenario_contract: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return a merged matrix summary across all completed runs for one contract."""
        runs = self.list_matrix_sweep_runs_by_contract(scenario_contract)
        if not runs:
            return None

        merged_cells: dict[tuple[int, int], dict[str, Any]] = {}

        for run in runs:
            summary = self.get_matrix_sweep_summary(run.id)
            if summary is None or not summary.get("matrix_cells"):
                continue

            for cell in summary["matrix_cells"]:
                coord = (int(cell.row_index), int(cell.col_index))
                if coord not in merged_cells:
                    merged_cells[coord] = {
                        "row_index": int(cell.row_index),
                        "col_index": int(cell.col_index),
                        "hand_combination": cell.hand_combination,
                        "equity_sum": 0.0,
                        "win_probability_sum": 0.0,
                        "ev_sum": 0.0,
                        "jackpot_adjusted_ev_sum": 0.0,
                        "sample_count_sum": 0,
                        "latest_updated": None,
                        "latest_convergence_status": None,
                    }

                metric = getattr(cell, "aggregated_metric", None)
                sample_count = 0
                if metric is not None:
                    if metric.sample_count is not None:
                        sample_count = int(metric.sample_count)
                    else:
                        sample_count = 1

                if sample_count <= 0:
                    continue

                data = merged_cells[coord]
                if metric is not None:
                    if metric.equity is not None:
                        data["equity_sum"] += float(metric.equity) * sample_count
                    if metric.win_probability is not None:
                        data["win_probability_sum"] += float(metric.win_probability) * sample_count
                    if metric.ev is not None:
                        data["ev_sum"] += float(metric.ev) * sample_count
                    if metric.jackpot_adjusted_ev is not None:
                        data["jackpot_adjusted_ev_sum"] += float(metric.jackpot_adjusted_ev) * sample_count
                    data["sample_count_sum"] += sample_count
                    if metric.last_updated:
                        if data["latest_updated"] is None or metric.last_updated > data["latest_updated"]:
                            data["latest_updated"] = metric.last_updated
                    if metric.convergence_status:
                        data["latest_convergence_status"] = metric.convergence_status

        if not merged_cells:
            return None

        merged_summary = []
        for coord in sorted(merged_cells.keys()):
            data = merged_cells[coord]
            sample_count_sum = data["sample_count_sum"]
            aggregated_metric = None
            if sample_count_sum > 0:
                aggregated_metric = SimpleNamespace(
                    equity=(data["equity_sum"] / sample_count_sum) if data["equity_sum"] else None,
                    win_probability=(data["win_probability_sum"] / sample_count_sum) if data["win_probability_sum"] else None,
                    ev=(data["ev_sum"] / sample_count_sum) if data["ev_sum"] else None,
                    jackpot_adjusted_ev=(data["jackpot_adjusted_ev_sum"] / sample_count_sum) if data["jackpot_adjusted_ev_sum"] else None,
                    sample_count=sample_count_sum,
                    convergence_status=data["latest_convergence_status"],
                    last_updated=data["latest_updated"],
                )

            merged_summary.append(SimpleNamespace(
                row_index=data["row_index"],
                col_index=data["col_index"],
                hand_combination=data["hand_combination"],
                aggregated_metric=aggregated_metric,
            ))

        return {
            "simulation": None,
            "hand_matrix": None,
            "matrix_cells": merged_summary,
            "aggregated_metrics": [cell.aggregated_metric for cell in merged_summary if cell.aggregated_metric is not None],
        }

    def resolve_scenario_run_selection(
        self,
        scenario_contract: Dict[str, Any],
        explicit_run_id: Optional[int] = None,
    ) -> tuple[Optional[Simulation], List[Simulation]]:
        """Resolve the run to use for scenario-contract queries."""
        matches = self.list_matrix_sweep_runs_by_contract(scenario_contract)
        if explicit_run_id is not None:
            selected = next((run for run in matches if run.id == explicit_run_id), None)
            return selected, matches

        if len(matches) == 1:
            return matches[0], matches

        return None, matches

    def is_run_boundary_readable(self, simulation: Simulation) -> bool:
        """Return True when the simulation has a valid raw run boundary."""
        try:
            parameters = normalize_scenario_contract(simulation.parameters)
        except Exception:
            return False

        return (
            parameters.get("raw_game_state_id_start") is not None
            and parameters.get("raw_game_state_id_end") is not None
        )

    def _serialize_run_reference(self, simulation: Simulation) -> Dict[str, Any]:
        return {
            "simulation_id": simulation.id,
            "name": simulation.name,
            "raw_game_state_id_start": simulation.parameters.get("raw_game_state_id_start"),
            "raw_game_state_id_end": simulation.parameters.get("raw_game_state_id_end"),
        }

    def build_empty_scope_result(
        self,
        status: str,
        status_message: str,
        matched_runs: Optional[List[Simulation]] = None,
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "status_message": status_message,
            "matched_runs": [self._serialize_run_reference(run) for run in matched_runs] if matched_runs else [],
            "game_states": [],
        }

    def get_run_raw_projection(
        self,
        raw_game_state_id_start: int,
        raw_game_state_id_end: int,
    ) -> List[Dict[str, Any]]:
        """Return raw GameState views ordered by GameState.id and hero-hole extraction."""
        with self.connection.session_scope() as session:
            game_states = (
                session.query(GameState)
                .options(selectinload(GameState.players))
                .filter(
                    GameState.id >= raw_game_state_id_start,
                    GameState.id <= raw_game_state_id_end,
                )
                .order_by(GameState.id.asc())
                .all()
            )

            projection = []
            for game_state in game_states:
                hero_player = next((player for player in game_state.players if player.is_hero), None)
                projection.append({
                    "game_state_id": game_state.id,
                    "timestamp": game_state.timestamp.isoformat() if game_state.timestamp else None,
                    "round": game_state.round,
                    "pot_size": float(game_state.pot_size) if game_state.pot_size is not None else 0.0,
                    "board_cards_str": game_state.board_cards_str or "",
                    "outcome": game_state.outcome,
                    "hero_hole_cards": hero_player.hole_cards if hero_player else None,
                    "players": [
                        {
                            "player_id": player.id,
                            "position": player.position,
                            "hole_cards": player.hole_cards,
                            "stack_size": float(player.stack_size) if player.stack_size is not None else 0.0,
                            "is_hero": bool(player.is_hero),
                        }
                        for player in game_state.players
                    ],
                })
            return projection

    def get_matrix_sweep_summary(self, simulation_id: int) -> Optional[Dict[str, Any]]:
        """Return one run-scoped projection of simulation, matrix, cells, and metrics."""
        with self.connection.session_scope() as session:
            simulation = session.query(Simulation).filter(Simulation.id == simulation_id).first()
            if simulation is None:
                return None

            matrix = (
                session.query(HandMatrix)
                .options(selectinload(HandMatrix.matrix_cells).selectinload(MatrixCell.aggregated_metric))
                .filter(HandMatrix.simulation_id == simulation_id)
                .first()
            )

            if matrix is None:
                return {
                    "simulation": simulation,
                    "hand_matrix": None,
                    "matrix_cells": [],
                    "aggregated_metrics": [],
                }

            matrix_cells = sorted(matrix.matrix_cells, key=lambda cell: (cell.row_index, cell.col_index))
            aggregated_metrics = [
                cell.aggregated_metric for cell in matrix_cells if cell.aggregated_metric is not None
            ]
            return {
                "simulation": simulation,
                "hand_matrix": matrix,
                "matrix_cells": matrix_cells,
                "aggregated_metrics": aggregated_metrics,
            }

    def upsert_matrix_cell(self, matrix_id: int, row_idx: int, col_idx: int, hand_key: str, metrics: Dict[str, float], status: str) -> int:
        """
        Create or update MatrixCell and associated AggregatedMetric with equity data.
        
        According to schema:
        - MatrixCell stores: row_index, col_index, hand_combination
        - AggregatedMetric stores: equity, convergence_status, etc.
        (Many-to-one relationship: one AggregatedMetric per MatrixCell)
        
        Returns:
            The ID of the MatrixCell
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
            return cell_id

    # ===== GAMESTATES CRUD OPERATIONS =====

    def create_game_state(self, game_state_data: Dict[str, Any]) -> int:
        """
        Create a new game state with complete game data.

        Args:
            game_state_data: Dictionary containing game state information including:
                - timestamp: Game timestamp (optional, defaults to now)
                - round: Game round (preflop/flop/turn/river)
                - pot_size: Current pot size
                - board_cards_str: Comma-separated board cards string
                - board_cards_id: Optional legacy BoardCards ID
                - outcome: Game outcome (optional)

        Returns:
            ID of the created game state

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_game_state_data(game_state_data)

        try:
            with self.connection.session_scope() as session:
                board_cards_str = self._resolve_board_cards_str(game_state_data)
                game_state = GameState(
                    timestamp=game_state_data.get('timestamp', datetime.now(timezone.utc)),
                    round=game_state_data.get('round', 'preflop'),
                    pot_size=game_state_data['pot_size'],
                    board_cards_str=board_cards_str,
                    outcome=game_state_data.get('outcome')
                )
                session.add(game_state)
                session.flush()  # Get the ID

                game_state_id = game_state.id
                logger.info(f"Created game state {game_state_id}")
                return game_state_id

        except Exception as e:
            logger.error(f"Failed to create game state: {e}")
            raise DatabaseConnectionError(f"Failed to create game state: {e}") from e

    def get_game_state(self, game_state_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a game state by ID with all relationships loaded.

        Args:
            game_state_id: GameState ID

        Returns:
            Dictionary containing game state data with related entities, or None if not found

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                # Query with eager loading of relationships
                game_state = session.query(GameState).options(
                    selectinload(GameState.players),
                    selectinload(GameState.bets),
                    selectinload(GameState.jackpots)
                ).filter(GameState.id == game_state_id).first()

                if not game_state:
                    return None

                # Convert to dictionary with relationships
                return {
                    'id': game_state.id,
                    'timestamp': game_state.timestamp,
                    'round': game_state.round,
                    'pot_size': float(game_state.pot_size),
                    'board_cards_str': game_state.board_cards_str,
                    'outcome': game_state.outcome,
                    'players': [
                        {
                            'id': player.id,
                            'position': player.position,
                            'hole_cards': player.hole_cards,
                            'stack_size': float(player.stack_size) if player.stack_size else None,
                            'is_hero': player.is_hero
                        }
                        for player in game_state.players
                    ],
                    'bets': [
                        {
                            'id': bet.id,
                            'player_id': bet.player_id,
                            'amount': float(bet.amount),
                            'action_type': bet.action_type,
                            'round': bet.round
                        }
                        for bet in game_state.bets
                    ],
                    'jackpots': [
                        {
                            'id': jackpot.id,
                            'jackpot_type': jackpot.jackpot_type,
                            'payout_amount': float(jackpot.payout_amount),
                            'qualifying_cards': jackpot.qualifying_cards
                        }
                        for jackpot in game_state.jackpots
                    ]
                }

        except Exception as e:
            logger.error(f"Failed to retrieve game state {game_state_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve game state: {e}") from e

    def update_game_state(self, game_state_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an existing game state.

        Args:
            game_state_id: GameState ID to update
            updates: Dictionary of fields to update

        Returns:
            True if update was successful, False if game state not found

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_game_state_exists(game_state_id)

        if 'pot_size' in updates and updates['pot_size'] < 0:
            raise DataIntegrityError("Pot size cannot be negative")
        if 'round' in updates and updates['round'] not in ['preflop', 'flop', 'turn', 'river']:
            raise DataIntegrityError("Round must be 'preflop', 'flop', 'turn', or 'river'")

        try:
            with self.connection.session_scope() as session:
                game_state = session.query(GameState).filter(GameState.id == game_state_id).first()

                if not game_state:
                    return False

                # Update allowed fields
                allowed_fields = {'round', 'pot_size', 'outcome', 'board_cards_str'}
                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(game_state, field, value)

                session.commit()
                logger.info(f"Updated game state {game_state_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to update game state {game_state_id}: {e}")
            raise DatabaseConnectionError(f"Failed to update game state: {e}") from e

    def delete_game_state(self, game_state_id: int) -> bool:
        """
        Delete a game state and all related entities (cascade delete).

        Args:
            game_state_id: GameState ID to delete

        Returns:
            True if deletion was successful, False if game state not found

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_game_state_exists(game_state_id)

        try:
            with self.connection.session_scope() as session:
                game_state = session.query(GameState).filter(GameState.id == game_state_id).first()

                if not game_state:
                    return False

                # Delete the game state (cascade will handle related entities)
                session.delete(game_state)
                session.commit()

                logger.info(f"Deleted game state {game_state_id} with cascade")
                return True

        except Exception as e:
            logger.error(f"Failed to delete game state {game_state_id}: {e}")
            raise DatabaseConnectionError(f"Failed to delete game state: {e}") from e

    # ===== PLAYERS CRUD OPERATIONS =====

    def create_player(self, player_data: Dict[str, Any]) -> int:
        """
        Create a new player linked to a game state.

        Args:
            player_data: Dictionary containing player information including:
                - game_state_id: GameState ID (required)
                - position: Player position (required)
                - hole_cards: Player's hole cards (required, format: "AsKh")
                - stack_size: Player's stack size (required)
                - is_hero: Whether this is the hero player (optional, default False)

        Returns:
            ID of the created player

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_player_data(player_data)

        try:
            with self.connection.session_scope() as session:
                # Create Player
                player = Player(
                    game_state_id=player_data['game_state_id'],
                    position=player_data['position'],
                    hole_cards=player_data['hole_cards'],
                    stack_size=player_data['stack_size'],
                    is_hero=player_data.get('is_hero', False)
                )
                session.add(player)
                session.flush()  # Get the ID

                player_id = player.id
                logger.info(f"Created player {player_id} for game state {player_data['game_state_id']}")
                return player_id

        except Exception as e:
            logger.error(f"Failed to create player: {e}")
            raise DatabaseConnectionError(f"Failed to create player: {e}") from e

    def create_players_bulk(self, players_data: List[Dict[str, Any]]) -> List[int]:
        """
        Create multiple players for a game state in bulk.

        Args:
            players_data: List of player data dictionaries, each containing:
                - game_state_id: GameState ID (required)
                - position: Player position (required)
                - hole_cards: Player's hole cards (required)
                - stack_size: Player's stack size (required)
                - is_hero: Whether this is the hero player (optional)

        Returns:
            List of created player IDs in the same order as input

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                player_ids = []

                for player_data in players_data:
                    # Create Player
                    player = Player(
                        game_state_id=player_data['game_state_id'],
                        position=player_data['position'],
                        hole_cards=player_data['hole_cards'],
                        stack_size=player_data['stack_size'],
                        is_hero=player_data.get('is_hero', False)
                    )
                    session.add(player)
                    session.flush()  # Get the ID

                    player_ids.append(player.id)

                session.commit()
                logger.info(f"Created {len(player_ids)} players in bulk for game state {players_data[0]['game_state_id'] if players_data else 'unknown'}")
                return player_ids

        except Exception as e:
            logger.error(f"Failed to create players in bulk: {e}")
            raise DatabaseConnectionError(f"Failed to create players in bulk: {e}") from e

    def get_player(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a player by ID with related entities.

        Args:
            player_id: Player ID

        Returns:
            Dictionary containing player data with related entities, or None if not found

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                # Query with eager loading of relationships
                player = session.query(Player).options(
                    selectinload(Player.game_state),
                    selectinload(Player.bets),
                    selectinload(Player.jackpots)
                ).filter(Player.id == player_id).first()

                if not player:
                    return None

                # Convert to dictionary
                return {
                    'id': player.id,
                    'game_state_id': player.game_state_id,
                    'position': player.position,
                    'hole_cards': player.hole_cards,
                    'stack_size': float(player.stack_size) if player.stack_size else None,
                    'is_hero': player.is_hero,
                    'game_state': {
                        'id': player.game_state.id,
                        'round': player.game_state.round,
                        'pot_size': float(player.game_state.pot_size),
                        'outcome': player.game_state.outcome
                    } if player.game_state else None,
                    'bets': [
                        {
                            'id': bet.id,
                            'amount': float(bet.amount),
                            'action_type': bet.action_type,
                            'round': bet.round
                        }
                        for bet in player.bets
                    ],
                    'jackpots': [
                        {
                            'id': jackpot.id,
                            'jackpot_type': jackpot.jackpot_type,
                            'payout_amount': float(jackpot.payout_amount)
                        }
                        for jackpot in player.jackpots
                    ]
                }

        except Exception as e:
            logger.error(f"Failed to retrieve player {player_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve player: {e}") from e

    def get_players_by_game_state(self, game_state_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all players for a specific game state.

        Args:
            game_state_id: GameState ID

        Returns:
            List of player dictionaries for the game state

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                players = session.query(Player).options(
                    selectinload(Player.bets),
                    selectinload(Player.jackpots)
                ).filter(Player.game_state_id == game_state_id).all()

                # Convert to dictionaries
                return [
                    {
                        'id': player.id,
                        'game_state_id': player.game_state_id,
                        'position': player.position,
                        'hole_cards': player.hole_cards,
                        'stack_size': float(player.stack_size) if player.stack_size else None,
                        'is_hero': player.is_hero,
                        'bets': [
                            {
                                'id': bet.id,
                                'amount': float(bet.amount),
                                'action_type': bet.action_type,
                                'round': bet.round
                            }
                            for bet in player.bets
                        ],
                        'jackpots': [
                            {
                                'id': jackpot.id,
                                'jackpot_type': jackpot.jackpot_type,
                                'payout_amount': float(jackpot.payout_amount)
                            }
                            for jackpot in player.jackpots
                        ]
                    }
                    for player in players
                ]

        except Exception as e:
            logger.error(f"Failed to retrieve players for game state {game_state_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve players: {e}") from e

    def update_player(self, player_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an existing player.

        Args:
            player_id: Player ID to update
            updates: Dictionary of fields to update (position, hole_cards, stack_size, is_hero)

        Returns:
            True if update was successful, False if player not found

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_player_exists(player_id)

        # Validate update data (only check provided fields)
        update_data = {'game_state_id': 1, 'position': 'dummy', 'hole_cards': 'AsKs', 'stack_size': 1000}  # dummy values
        update_data.update(updates)
        self._validate_player_data(update_data)

        try:
            with self.connection.session_scope() as session:
                player = session.query(Player).filter(Player.id == player_id).first()

                if not player:
                    return False

                # Update allowed fields
                allowed_fields = {'position', 'hole_cards', 'stack_size', 'is_hero'}
                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(player, field, value)

                session.commit()
                logger.info(f"Updated player {player_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to update player {player_id}: {e}")
            raise DatabaseConnectionError(f"Failed to update player: {e}") from e

    def delete_player(self, player_id: int) -> bool:
        """
        Delete a player and all related entities (cascade delete).

        Args:
            player_id: Player ID to delete

        Returns:
            True if deletion was successful, False if player not found

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_player_exists(player_id)

        try:
            with self.connection.session_scope() as session:
                player = session.query(Player).filter(Player.id == player_id).first()

                if not player:
                    return False

                # Delete the player (cascade will handle related entities)
                session.delete(player)
                session.commit()

                logger.info(f"Deleted player {player_id} with cascade")
                return True

        except Exception as e:
            logger.error(f"Failed to delete player {player_id}: {e}")
            raise DatabaseConnectionError(f"Failed to delete player: {e}") from e

    # ===== BETS CRUD OPERATIONS =====

    def create_bet(self, bet_data: Dict[str, Any]) -> int:
        """
        Create a new bet linked to a game state and player.

        Args:
            bet_data: Dictionary containing bet information including:
                - game_state_id: GameState ID (required)
                - player_id: Player ID (required)
                - amount: Bet amount (required)
                - action_type: Type of action ('fold', 'call', 'raise') (optional, default 'raise')
                - round: Poker round ('preflop', 'flop', 'turn', 'river') (optional, default 'preflop')

        Returns:
            ID of the created bet

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_bet_data(bet_data)

        try:
            with self.connection.session_scope() as session:
                # Create Bet
                bet = Bet(
                    game_state_id=bet_data['game_state_id'],
                    player_id=bet_data['player_id'],
                    amount=bet_data['amount'],
                    action_type=bet_data.get('action_type', 'raise'),
                    round=bet_data.get('round', 'preflop')
                )
                session.add(bet)
                session.flush()  # Get the ID

                bet_id = bet.id
                logger.info(f"Created bet {bet_id} for player {bet_data['player_id']} in game state {bet_data['game_state_id']}")
                return bet_id

        except Exception as e:
            logger.error(f"Failed to create bet: {e}")
            raise DatabaseConnectionError(f"Failed to create bet: {e}") from e

    def create_bets_bulk(self, bets_data: List[Dict[str, Any]]) -> List[int]:
        """
        Create multiple bets for a game state in bulk.

        Args:
            bets_data: List of bet data dictionaries, each containing:
                - game_state_id: GameState ID (required)
                - player_id: Player ID (required)
                - amount: Bet amount (required)
                - action_type: Type of action (optional)
                - round: Poker round (optional)

        Returns:
            List of created bet IDs in the same order as input

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                bet_ids = []

                for bet_data in bets_data:
                    # Create Bet
                    bet = Bet(
                        game_state_id=bet_data['game_state_id'],
                        player_id=bet_data['player_id'],
                        amount=bet_data['amount'],
                        action_type=bet_data.get('action_type', 'raise'),
                        round=bet_data.get('round', 'preflop')
                    )
                    session.add(bet)
                    session.flush()  # Get the ID

                    bet_ids.append(bet.id)

                session.commit()
                logger.info(f"Created {len(bet_ids)} bets in bulk")
                return bet_ids

        except Exception as e:
            logger.error(f"Failed to create bets in bulk: {e}")
            raise DatabaseConnectionError(f"Failed to create bets in bulk: {e}") from e

    def get_bet(self, bet_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a bet by ID with related entities.

        Args:
            bet_id: Bet ID

        Returns:
            Dictionary containing bet data with related player and game state, or None if not found

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                # Query with eager loading of relationships
                bet = session.query(Bet).options(
                    selectinload(Bet.player),
                    selectinload(Bet.game_state)
                ).filter(Bet.id == bet_id).first()

                if not bet:
                    return None

                # Convert to dictionary
                return {
                    'id': bet.id,
                    'game_state_id': bet.game_state_id,
                    'player_id': bet.player_id,
                    'amount': float(bet.amount),
                    'action_type': bet.action_type,
                    'round': bet.round,
                    'player': {
                        'id': bet.player.id,
                        'position': bet.player.position,
                        'hole_cards': bet.player.hole_cards,
                        'is_hero': bet.player.is_hero
                    } if bet.player else None,
                    'game_state': {
                        'id': bet.game_state.id,
                        'round': bet.game_state.round,
                        'pot_size': float(bet.game_state.pot_size),
                        'outcome': bet.game_state.outcome
                    } if bet.game_state else None
                }

        except Exception as e:
            logger.error(f"Failed to retrieve bet {bet_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve bet: {e}") from e

    def get_bets_by_game_state(self, game_state_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all bets for a specific game state, ordered by round and amount.

        This enables bet history reconstruction for game replay.

        Args:
            game_state_id: GameState ID

        Returns:
            List of bet dictionaries ordered for chronological reconstruction

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                bets = session.query(Bet).options(
                    selectinload(Bet.player)
                ).filter(Bet.game_state_id == game_state_id).order_by(
                    Bet.round, Bet.amount  # Order by round, then by bet amount
                ).all()

                # Convert to dictionaries
                return [
                    {
                        'id': bet.id,
                        'game_state_id': bet.game_state_id,
                        'player_id': bet.player_id,
                        'amount': float(bet.amount),
                        'action_type': bet.action_type,
                        'round': bet.round,
                        'player': {
                            'id': bet.player.id,
                            'position': bet.player.position,
                            'hole_cards': bet.player.hole_cards,
                            'is_hero': bet.player.is_hero
                        } if bet.player else None
                    }
                    for bet in bets
                ]

        except Exception as e:
            logger.error(f"Failed to retrieve bets for game state {game_state_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve bets: {e}") from e

    def get_bets_by_player(self, player_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all bets made by a specific player across all game states.

        Args:
            player_id: Player ID

        Returns:
            List of bet dictionaries for the player

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                bets = session.query(Bet).options(
                    selectinload(Bet.game_state)
                ).filter(Bet.player_id == player_id).order_by(
                    Bet.game_state_id, Bet.round
                ).all()

                # Convert to dictionaries
                return [
                    {
                        'id': bet.id,
                        'game_state_id': bet.game_state_id,
                        'player_id': bet.player_id,
                        'amount': float(bet.amount),
                        'action_type': bet.action_type,
                        'round': bet.round,
                        'game_state': {
                            'id': bet.game_state.id,
                            'round': bet.game_state.round,
                            'pot_size': float(bet.game_state.pot_size),
                            'outcome': bet.game_state.outcome
                        } if bet.game_state else None
                    }
                    for bet in bets
                ]

        except Exception as e:
            logger.error(f"Failed to retrieve bets for player {player_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve bets: {e}") from e

    def update_bet(self, bet_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an existing bet.

        Args:
            bet_id: Bet ID to update
            updates: Dictionary of fields to update (amount, action_type, round)

        Returns:
            True if update was successful, False if bet not found

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_bet_exists(bet_id)

        # Validate update data (only check provided fields)
        update_data = {'game_state_id': 1, 'player_id': 1, 'amount': 100}  # dummy values
        update_data.update(updates)
        self._validate_bet_data(update_data)

        try:
            with self.connection.session_scope() as session:
                bet = session.query(Bet).filter(Bet.id == bet_id).first()

                if not bet:
                    return False

                # Update allowed fields
                allowed_fields = {'amount', 'action_type', 'round'}
                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(bet, field, value)

                session.commit()
                logger.info(f"Updated bet {bet_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to update bet {bet_id}: {e}")
            raise DatabaseConnectionError(f"Failed to update bet: {e}") from e

    def delete_bet(self, bet_id: int) -> bool:
        """
        Delete a bet.

        Args:
            bet_id: Bet ID to delete

        Returns:
            True if deletion was successful, False if bet not found

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_bet_exists(bet_id)

        try:
            with self.connection.session_scope() as session:
                bet = session.query(Bet).filter(Bet.id == bet_id).first()

                if not bet:
                    return False

                # Delete the bet
                session.delete(bet)
                session.commit()

                logger.info(f"Deleted bet {bet_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete bet {bet_id}: {e}")
            raise DatabaseConnectionError(f"Failed to delete bet: {e}") from e

    # Legacy BoardCards operations have been removed in favor of GameStates-first board_cards_str storage.

    # ===== JACKPOTS CRUD OPERATIONS =====

    def create_jackpot(self, jackpot_data: Dict[str, Any]) -> int:
        """
        Create a new jackpot event with payout details.

        Args:
            jackpot_data: Dictionary containing jackpot information including:
                - game_state_id: GameState ID (required)
                - player_id: Player ID (required)
                - jackpot_type: Type of jackpot (required, e.g., 'royal_flush')
                - payout_amount: Payout amount (required)
                - qualifying_cards: List of cards that formed the jackpot (required)

        Returns:
            ID of the created jackpot

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_jackpot_data(jackpot_data)

        try:
            with self.connection.session_scope() as session:
                # Create Jackpot
                jackpot = Jackpot(
                    game_state_id=jackpot_data['game_state_id'],
                    player_id=jackpot_data['player_id'],
                    jackpot_type=jackpot_data['jackpot_type'],
                    payout_amount=jackpot_data['payout_amount'],
                    qualifying_cards=jackpot_data['qualifying_cards']
                )
                session.add(jackpot)
                session.flush()  # Get the ID

                jackpot_id = jackpot.id
                logger.info(f"Created jackpot {jackpot_id}: {jackpot.jackpot_type} for player {jackpot.player_id} (${jackpot.payout_amount})")
                return jackpot_id

        except Exception as e:
            logger.error(f"Failed to create jackpot: {e}")
            raise DatabaseConnectionError(f"Failed to create jackpot: {e}") from e

    def create_jackpots_bulk(self, jackpots_data: List[Dict[str, Any]]) -> List[int]:
        """
        Create multiple jackpot events in bulk.

        Args:
            jackpots_data: List of jackpot data dictionaries, each containing:
                - game_state_id: GameState ID (required)
                - player_id: Player ID (required)
                - jackpot_type: Type of jackpot (required)
                - payout_amount: Payout amount (required)
                - qualifying_cards: List of cards (required)

        Returns:
            List of created jackpot IDs in the same order as input

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                jackpot_ids = []

                for jackpot_data in jackpots_data:
                    # Create Jackpot
                    jackpot = Jackpot(
                        game_state_id=jackpot_data['game_state_id'],
                        player_id=jackpot_data['player_id'],
                        jackpot_type=jackpot_data['jackpot_type'],
                        payout_amount=jackpot_data['payout_amount'],
                        qualifying_cards=jackpot_data['qualifying_cards']
                    )
                    session.add(jackpot)
                    session.flush()  # Get the ID

                    jackpot_ids.append(jackpot.id)

                session.commit()
                logger.info(f"Created {len(jackpot_ids)} jackpots in bulk")
                return jackpot_ids

        except Exception as e:
            logger.error(f"Failed to create jackpots in bulk: {e}")
            raise DatabaseConnectionError(f"Failed to create jackpots in bulk: {e}") from e

    def get_jackpot(self, jackpot_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a jackpot by ID with related entities.

        Args:
            jackpot_id: Jackpot ID

        Returns:
            Dictionary containing jackpot data with related player and game state, or None if not found

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                # Query with eager loading of relationships
                jackpot = session.query(Jackpot).options(
                    selectinload(Jackpot.player),
                    selectinload(Jackpot.game_state)
                ).filter(Jackpot.id == jackpot_id).first()

                if not jackpot:
                    return None

                # Convert to dictionary
                return {
                    'id': jackpot.id,
                    'game_state_id': jackpot.game_state_id,
                    'player_id': jackpot.player_id,
                    'jackpot_type': jackpot.jackpot_type,
                    'payout_amount': float(jackpot.payout_amount),
                    'qualifying_cards': jackpot.qualifying_cards,
                    'payout_multiplier': jackpot.payout_multiplier,
                    'player': {
                        'id': jackpot.player.id,
                        'position': jackpot.player.position,
                        'hole_cards': jackpot.player.hole_cards,
                        'is_hero': jackpot.player.is_hero
                    } if jackpot.player else None,
                    'game_state': {
                        'id': jackpot.game_state.id,
                        'round': jackpot.game_state.round,
                        'pot_size': float(jackpot.game_state.pot_size),
                        'outcome': jackpot.game_state.outcome
                    } if jackpot.game_state else None
                }

        except Exception as e:
            logger.error(f"Failed to retrieve jackpot {jackpot_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve jackpot: {e}") from e

    def get_jackpots_by_game_state(self, game_state_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all jackpots for a specific game state.

        Args:
            game_state_id: GameState ID

        Returns:
            List of jackpot dictionaries for the game state

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                jackpots = session.query(Jackpot).options(
                    selectinload(Jackpot.player)
                ).filter(Jackpot.game_state_id == game_state_id).all()

                # Convert to dictionaries
                return [
                    {
                        'id': jackpot.id,
                        'game_state_id': jackpot.game_state_id,
                        'player_id': jackpot.player_id,
                        'jackpot_type': jackpot.jackpot_type,
                        'payout_amount': float(jackpot.payout_amount),
                        'qualifying_cards': jackpot.qualifying_cards,
                        'payout_multiplier': jackpot.payout_multiplier,
                        'player': {
                            'id': jackpot.player.id,
                            'position': jackpot.player.position,
                            'hole_cards': jackpot.player.hole_cards,
                            'is_hero': jackpot.player.is_hero
                        } if jackpot.player else None
                    }
                    for jackpot in jackpots
                ]

        except Exception as e:
            logger.error(f"Failed to retrieve jackpots for game state {game_state_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve jackpots: {e}") from e

    def get_jackpots_by_player(self, player_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all jackpots won by a specific player.

        Args:
            player_id: Player ID

        Returns:
            List of jackpot dictionaries for the player

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                jackpots = session.query(Jackpot).options(
                    selectinload(Jackpot.game_state)
                ).filter(Jackpot.player_id == player_id).order_by(
                    Jackpot.game_state_id
                ).all()

                # Convert to dictionaries
                return [
                    {
                        'id': jackpot.id,
                        'game_state_id': jackpot.game_state_id,
                        'player_id': jackpot.player_id,
                        'jackpot_type': jackpot.jackpot_type,
                        'payout_amount': float(jackpot.payout_amount),
                        'qualifying_cards': jackpot.qualifying_cards,
                        'payout_multiplier': jackpot.payout_multiplier,
                        'game_state': {
                            'id': jackpot.game_state.id,
                            'round': jackpot.game_state.round,
                            'pot_size': float(jackpot.game_state.pot_size),
                            'outcome': jackpot.game_state.outcome
                        } if jackpot.game_state else None
                    }
                    for jackpot in jackpots
                ]

        except Exception as e:
            logger.error(f"Failed to retrieve jackpots for player {player_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve jackpots: {e}") from e

    def get_jackpot_statistics(self) -> List[Dict[str, Any]]:
        """
        Retrieve jackpot frequency and payout statistics by type.

        This supports jackpot frequency analysis queries.

        Returns:
            List of jackpot statistics dictionaries with frequency, average payout, etc.

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                # Query jackpot statistics grouped by type
                result = session.query(
                    Jackpot.jackpot_type,
                    func.count(Jackpot.id).label('frequency'),
                    func.avg(Jackpot.payout_amount).label('avg_payout'),
                    func.sum(Jackpot.payout_amount).label('total_payout'),
                    func.min(Jackpot.payout_amount).label('min_payout'),
                    func.max(Jackpot.payout_amount).label('max_payout')
                ).group_by(Jackpot.jackpot_type).order_by(func.count(Jackpot.id).desc()).all()

                # Convert to dictionaries
                return [
                    {
                        'jackpot_type': row.jackpot_type,
                        'frequency': row.frequency,
                        'avg_payout': float(row.avg_payout) if row.avg_payout else 0.0,
                        'total_payout': float(row.total_payout) if row.total_payout else 0.0,
                        'min_payout': float(row.min_payout) if row.min_payout else 0.0,
                        'max_payout': float(row.max_payout) if row.max_payout else 0.0
                    }
                    for row in result
                ]

        except Exception as e:
            logger.error(f"Failed to retrieve jackpot statistics: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve jackpot statistics: {e}") from e

    def get_jackpot_statistics_by_player(self, player_id: int) -> Dict[str, Any]:
        """
        Retrieve jackpot statistics for a specific player.

        Args:
            player_id: Player ID

        Returns:
            Dictionary with player's jackpot statistics

        Raises:
            DatabaseConnectionError: If database operation fails
        """
        try:
            with self.connection.session_scope() as session:
                # Query player's jackpot statistics
                result = session.query(
                    func.count(Jackpot.id).label('total_jackpots'),
                    func.sum(Jackpot.payout_amount).label('total_payout'),
                    func.avg(Jackpot.payout_amount).label('avg_payout'),
                    func.max(Jackpot.payout_amount).label('max_single_payout')
                ).filter(Jackpot.player_id == player_id).first()

                return {
                    'player_id': player_id,
                    'total_jackpots': result.total_jackpots or 0,
                    'total_payout': float(result.total_payout) if result.total_payout else 0.0,
                    'avg_payout': float(result.avg_payout) if result.avg_payout else 0.0,
                    'max_single_payout': float(result.max_single_payout) if result.max_single_payout else 0.0
                }

        except Exception as e:
            logger.error(f"Failed to retrieve jackpot statistics for player {player_id}: {e}")
            raise DatabaseConnectionError(f"Failed to retrieve jackpot statistics: {e}") from e

    def update_jackpot(self, jackpot_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an existing jackpot.

        Args:
            jackpot_id: Jackpot ID to update
            updates: Dictionary of fields to update (jackpot_type, payout_amount, qualifying_cards)

        Returns:
            True if update was successful, False if jackpot not found

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_jackpot_exists(jackpot_id)

        # Validate update data (only check provided fields)
        update_data = {'game_state_id': 1, 'player_id': 1, 'jackpot_type': 'dummy', 'payout_amount': 100, 'qualifying_cards': ['As', 'Ks']}  # dummy values
        update_data.update(updates)
        self._validate_jackpot_data(update_data)

        try:
            with self.connection.session_scope() as session:
                jackpot = session.query(Jackpot).filter(Jackpot.id == jackpot_id).first()

                if not jackpot:
                    return False

                # Update allowed fields
                allowed_fields = {'jackpot_type', 'payout_amount', 'qualifying_cards'}
                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(jackpot, field, value)

                session.commit()
                logger.info(f"Updated jackpot {jackpot_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to update jackpot {jackpot_id}: {e}")
            raise DatabaseConnectionError(f"Failed to update jackpot: {e}") from e

    def delete_jackpot(self, jackpot_id: int) -> bool:
        """
        Delete a jackpot.

        Args:
            jackpot_id: Jackpot ID to delete

        Returns:
            True if deletion was successful, False if jackpot not found

        Raises:
            DataIntegrityError: If validation fails
            DatabaseConnectionError: If database operation fails
        """
        self._validate_jackpot_exists(jackpot_id)

        try:
            with self.connection.session_scope() as session:
                jackpot = session.query(Jackpot).filter(Jackpot.id == jackpot_id).first()

                if not jackpot:
                    return False

                # Delete the jackpot
                session.delete(jackpot)
                session.commit()

                logger.info(f"Deleted jackpot {jackpot_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete jackpot {jackpot_id}: {e}")
            raise DatabaseConnectionError(f"Failed to delete jackpot: {e}") from e

    # ===== BULK INSERTION OPTIMIZATION =====

    def bulk_insert_game_states(self, game_states_data: List[Dict[str, Any]], batch_size: int = 1000) -> List[int]:
        """
        High-performance bulk insertion of game states.

        Args:
            game_states_data: List of game state data dictionaries
            batch_size: Number of records to insert per transaction (default 1000)

        Returns:
            List of created game state IDs in the same order as input

        Raises:
            DatabaseConnectionError: If database operation fails (all insertions rolled back)
        """
        if not game_states_data:
            return []

        try:
            all_ids = []

            # Process in batches for memory efficiency and performance
            for i in range(0, len(game_states_data), batch_size):
                batch = game_states_data[i:i + batch_size]
                batch_ids = self._bulk_insert_game_states_batch(batch)
                all_ids.extend(batch_ids)

            logger.info(f"Bulk inserted {len(all_ids)} game states in {len(game_states_data) // batch_size + 1} batches")
            return all_ids

        except Exception as e:
            logger.error(f"Failed bulk insert of game states: {e}")
            raise DatabaseConnectionError(f"Failed bulk insert of game states: {e}") from e

    def _bulk_insert_game_states_batch(self, game_states_data: List[Dict[str, Any]]) -> List[int]:
        """Internal method for batch insertion of game states."""
        try:
            with self.connection.session_scope() as session:
                game_state_objects = []

                for game_state_data in game_states_data:
                    board_cards_str = self._resolve_board_cards_str(game_state_data)
                    game_state = GameState(
                        timestamp=game_state_data.get('timestamp', datetime.now(timezone.utc)),
                        round=game_state_data.get('round', 'preflop'),
                        pot_size=game_state_data['pot_size'],
                        board_cards_str=board_cards_str,
                        outcome=game_state_data.get('outcome')
                    )
                    game_state_objects.append(game_state)
                    session.add(game_state)

                # Flush to get IDs without committing yet
                session.flush()
                ids = [gs.id for gs in game_state_objects]

                # Commit the batch
                session.commit()
                return ids

        except Exception as e:
            # Rollback will happen automatically due to context manager
            raise e

    def bulk_insert_players(self, players_data: List[Dict[str, Any]], batch_size: int = 1000) -> List[int]:
        """
        High-performance bulk insertion of players.

        Args:
            players_data: List of player data dictionaries
            batch_size: Number of records to insert per transaction (default 1000)

        Returns:
            List of created player IDs in the same order as input

        Raises:
            DatabaseConnectionError: If database operation fails (all insertions rolled back)
        """
        if not players_data:
            return []

        try:
            all_ids = []

            # Process in batches
            for i in range(0, len(players_data), batch_size):
                batch = players_data[i:i + batch_size]
                batch_ids = self._bulk_insert_players_batch(batch)
                all_ids.extend(batch_ids)

            logger.info(f"Bulk inserted {len(all_ids)} players in {len(players_data) // batch_size + 1} batches")
            return all_ids

        except Exception as e:
            logger.error(f"Failed bulk insert of players: {e}")
            raise DatabaseConnectionError(f"Failed bulk insert of players: {e}") from e

    def _bulk_insert_players_batch(self, players_data: List[Dict[str, Any]]) -> List[int]:
        """Internal method for batch insertion of players."""
        try:
            with self.connection.session_scope() as session:
                player_objects = []

                for player_data in players_data:
                    player = Player(
                        game_state_id=player_data['game_state_id'],
                        position=player_data['position'],
                        hole_cards=player_data['hole_cards'],
                        stack_size=player_data['stack_size'],
                        is_hero=player_data.get('is_hero', False)
                    )
                    player_objects.append(player)
                    session.add(player)

                session.flush()
                ids = [p.id for p in player_objects]
                session.commit()
                return ids

        except Exception as e:
            raise e

    def bulk_insert_bets(self, bets_data: List[Dict[str, Any]], batch_size: int = 1000) -> List[int]:
        """
        High-performance bulk insertion of bets.

        Args:
            bets_data: List of bet data dictionaries
            batch_size: Number of records to insert per transaction (default 1000)

        Returns:
            List of created bet IDs in the same order as input

        Raises:
            DatabaseConnectionError: If database operation fails (all insertions rolled back)
        """
        if not bets_data:
            return []

        try:
            all_ids = []

            # Process in batches
            for i in range(0, len(bets_data), batch_size):
                batch = bets_data[i:i + batch_size]
                batch_ids = self._bulk_insert_bets_batch(batch)
                all_ids.extend(batch_ids)

            logger.info(f"Bulk inserted {len(all_ids)} bets in {len(bets_data) // batch_size + 1} batches")
            return all_ids

        except Exception as e:
            logger.error(f"Failed bulk insert of bets: {e}")
            raise DatabaseConnectionError(f"Failed bulk insert of bets: {e}") from e

    def _bulk_insert_bets_batch(self, bets_data: List[Dict[str, Any]]) -> List[int]:
        """Internal method for batch insertion of bets."""
        try:
            with self.connection.session_scope() as session:
                bet_objects = []

                for bet_data in bets_data:
                    bet = Bet(
                        game_state_id=bet_data['game_state_id'],
                        player_id=bet_data['player_id'],
                        amount=bet_data['amount'],
                        action_type=bet_data.get('action_type', 'raise'),
                        round=bet_data.get('round', 'preflop')
                    )
                    bet_objects.append(bet)
                    session.add(bet)

                session.flush()
                ids = [b.id for b in bet_objects]
                session.commit()
                return ids

        except Exception as e:
            raise e

    def bulk_insert_jackpots(self, jackpots_data: List[Dict[str, Any]], batch_size: int = 1000) -> List[int]:
        """
        High-performance bulk insertion of jackpots.

        Args:
            jackpots_data: List of jackpot data dictionaries
            batch_size: Number of records to insert per transaction (default 1000)

        Returns:
            List of created jackpot IDs in the same order as input

        Raises:
            DatabaseConnectionError: If database operation fails (all insertions rolled back)
        """
        if not jackpots_data:
            return []

        try:
            all_ids = []

            # Process in batches
            for i in range(0, len(jackpots_data), batch_size):
                batch = jackpots_data[i:i + batch_size]
                batch_ids = self._bulk_insert_jackpots_batch(batch)
                all_ids.extend(batch_ids)

            logger.info(f"Bulk inserted {len(all_ids)} jackpots in {len(jackpots_data) // batch_size + 1} batches")
            return all_ids

        except Exception as e:
            logger.error(f"Failed bulk insert of jackpots: {e}")
            raise DatabaseConnectionError(f"Failed bulk insert of jackpots: {e}") from e

    def _bulk_insert_jackpots_batch(self, jackpots_data: List[Dict[str, Any]]) -> List[int]:
        """Internal method for batch insertion of jackpots."""
        try:
            with self.connection.session_scope() as session:
                jackpot_objects = []

                for jackpot_data in jackpots_data:
                    jackpot = Jackpot(
                        game_state_id=jackpot_data['game_state_id'],
                        player_id=jackpot_data['player_id'],
                        jackpot_type=jackpot_data['jackpot_type'],
                        payout_amount=jackpot_data['payout_amount'],
                        qualifying_cards=jackpot_data['qualifying_cards']
                    )
                    jackpot_objects.append(jackpot)
                    session.add(jackpot)

                session.flush()
                ids = [j.id for j in jackpot_objects]
                session.commit()
                return ids

        except Exception as e:
            raise e

    def bulk_insert_simulation_data(self, simulation_data: Dict[str, Any]) -> Dict[str, List[int]]:
        """
        High-performance bulk insertion of complete simulation data.

        This method handles the complex relationships between GameStates, Players, Bets, and Jackpots
        in a single optimized transaction, ensuring data consistency.

        Args:
            simulation_data: Dictionary containing:
                - 'game_states': List of game state data
                - 'players': List of player data
                - 'bets': List of bet data
                - 'jackpots': List of jackpot data

        Returns:
            Dictionary with IDs for each entity type

        Raises:
            DatabaseConnectionError: If database operation fails (all insertions rolled back)
        """
        try:
            with self.connection.session_scope() as session:
                result_ids = {
                    'game_states': [],
                    'players': [],
                    'bets': [],
                    'jackpots': []
                }

                # Insert game states first
                if 'game_states' in simulation_data:
                    game_state_objects = []
                    for gs_data in simulation_data['game_states']:
                        board_cards_str = self._resolve_board_cards_str(gs_data)
                        gs = GameState(
                            timestamp=gs_data.get('timestamp', datetime.now(timezone.utc)),
                            round=gs_data.get('round', 'preflop'),
                            pot_size=gs_data['pot_size'],
                            board_cards_str=board_cards_str,
                            outcome=gs_data.get('outcome')
                        )
                        game_state_objects.append(gs)
                        session.add(gs)

                    session.flush()
                    result_ids['game_states'] = [gs.id for gs in game_state_objects]

                # Insert players
                if 'players' in simulation_data:
                    player_objects = []
                    for p_data in simulation_data['players']:
                        p = Player(
                            game_state_id=p_data['game_state_id'],
                            position=p_data['position'],
                            hole_cards=p_data['hole_cards'],
                            stack_size=p_data['stack_size'],
                            is_hero=p_data.get('is_hero', False)
                        )
                        player_objects.append(p)
                        session.add(p)

                    session.flush()
                    result_ids['players'] = [p.id for p in player_objects]

                # Insert bets
                if 'bets' in simulation_data:
                    bet_objects = []
                    for b_data in simulation_data['bets']:
                        b = Bet(
                            game_state_id=b_data['game_state_id'],
                            player_id=b_data['player_id'],
                            amount=b_data['amount'],
                            action_type=b_data.get('action_type', 'raise'),
                            round=b_data.get('round', 'preflop')
                        )
                        bet_objects.append(b)
                        session.add(b)

                    session.flush()
                    result_ids['bets'] = [b.id for b in bet_objects]

                # Insert jackpots
                if 'jackpots' in simulation_data:
                    jackpot_objects = []
                    for j_data in simulation_data['jackpots']:
                        j = Jackpot(
                            game_state_id=j_data['game_state_id'],
                            player_id=j_data['player_id'],
                            jackpot_type=j_data['jackpot_type'],
                            payout_amount=j_data['payout_amount'],
                            qualifying_cards=j_data['qualifying_cards']
                        )
                        jackpot_objects.append(j)
                        session.add(j)

                    session.flush()
                    result_ids['jackpots'] = [j.id for j in jackpot_objects]

                # Commit all changes
                session.commit()

                total_records = sum(len(ids) for ids in result_ids.values())
                logger.info(f"Bulk inserted complete simulation data: {total_records} total records")
                return result_ids

        except Exception as e:
            logger.error(f"Failed bulk insert of simulation data: {e}")
            raise DatabaseConnectionError(f"Failed bulk insert of simulation data: {e}") from e
