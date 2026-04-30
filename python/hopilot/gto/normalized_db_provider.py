"""
Normalized database provider for AoF GTO browser.

Provides data access layer that bridges the browser's data model
with the normalized database schema via DatabaseRepository.
"""

from typing import Any, Callable, Dict, List, Optional
import asyncio

from hopilot.gto.repository_errors import DatabaseConnectionError, InvalidContextError
from hopilot.gto.data_model import PositionContext, ActionContext, MetricType
from hopilot.gto.aof_hand_matrix import format_metric_value
from hopilot.gto.analytics_repository import AnalyticsRepository
from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger


logger = get_logger(__name__)


class NormalizedDatabaseProvider:
    """
    Provider that retrieves GTO data from the normalized database.

    Implements the same interface as AoFBrowserDataProvider but uses
    DatabaseRepository for data access instead of cache/solver.
    """

    def __init__(self, database_url: str):
        """
        Initialize provider with database connection.

        Args:
            database_url: SQLAlchemy database URL for the normalized database
        """
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.db_connection.create_tables()
        self.repository = AnalyticsRepository(self.db_connection)
        logger.info(f"NormalizedDatabaseProvider initialized with: {database_url}")

    def get_matrix_payload(
        self,
        position: str,
        metric: str,
        position_actions: Dict[str, str] | None = None,
        pot_size: float = 20.0,
        bet_amount: float = 10.0,
        strict_current_action: bool = False,
        allow_compute: bool = True,
        on_cell_complete: Callable[[Dict[str, Any]], None] | None = None,
    ) -> Dict[str, Any]:
        """
        Retrieve matrix payload for given browser context.

        This method maintains the same interface as AoFBrowserDataProvider
        but retrieves data from the normalized database.

        Args:
            position: Player position (UTG, BTN, SB, BB)
            metric: Display metric (EQUITY, EV, WIN_LOSE_PROBABILITY, EQR)
            position_actions: Dict mapping positions to actions (FOLD, ALL_IN)
            pot_size: Pot size (not used in database queries)
            bet_amount: Bet amount (not used in database queries)
            strict_current_action: Whether to use strict action filtering
            allow_compute: Whether to allow computation (not applicable for DB)
            on_cell_complete: Callback for cell completion (not used for DB)

        Returns:
            Dictionary with context, cells, and status_message
        """
        try:
            # Convert browser context to database context objects
            position_ctx = PositionContext.from_id(position)
            action_ctx = self._determine_action_context(position, position_actions)
            metric_ctx = MetricType.from_id(metric)

            # Build context dictionary for compatibility
            context = self._build_context_dict(
                position, metric, position_actions, pot_size, bet_amount, strict_current_action
            )

            # Get matrix data from database
            matrix_data = asyncio.run(
                self.repository.get_strategy_matrix(position_ctx, action_ctx, metric_ctx)
            )

            # Convert to browser-compatible cell format
            cells = self._build_cells_from_matrix_data(matrix_data, metric)

            return {
                "context": context,
                "cells": cells,
                "status_message": None
            }

        except InvalidContextError as e:
            logger.warning(f"Invalid context for database query: {e}")
            context = self._build_context_dict(
                position, metric, position_actions, pot_size, bet_amount, strict_current_action
            )
            return self._build_error_payload(context, "MISSING", f"No data available: {e}")

        except DatabaseConnectionError as e:
            logger.error(f"Database connection error: {e}")
            context = self._build_context_dict(
                position, metric, position_actions, pot_size, bet_amount, strict_current_action
            )
            return self._build_error_payload(context, "ERROR", f"Database unavailable: {e}")

    def get_convergence_data(
        self,
        position: str,
        position_actions: Dict[str, str] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve convergence analysis data for position/action.

        Args:
            position: Player position (UTG, BTN, SB, BB)
            position_actions: Dict mapping positions to actions (FOLD, ALL_IN)

        Returns:
            List of convergence data points with num_simulations, average_equity, timestamp
        """
        try:
            # Convert browser context to database context objects
            position_ctx = PositionContext.from_id(position)
            action_ctx = self._determine_action_context(position, position_actions)

            # Get convergence data from database
            convergence_points = asyncio.run(
                self.repository.get_convergence_data(position_ctx, action_ctx)
            )

            # Convert to browser-compatible format
            return [
                {
                    "num_simulations": point.num_simulations,
                    "average_equity": point.average_equity,
                    "timestamp": point.timestamp.isoformat() if point.timestamp else None,
                }
                for point in convergence_points
            ]

        except (InvalidContextError, DatabaseConnectionError) as e:
            logger.warning(f"Failed to retrieve convergence data: {e}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error in database provider: {e}")
            context = self._build_context_dict(
                position, metric, position_actions, pot_size, bet_amount, strict_current_action
            )
            return self._build_error_payload(context, "ERROR", f"Unexpected error: {e}")

    async def get_strategy_matrix(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: MetricType
    ) -> Dict[str, Dict[str, float]]:
        """
        Retrieve complete 13x13 strategy matrix for given context.

        This provides direct access to repository data without browser formatting.

        Args:
            position: Player position context
            action: Decision action context
            metric: Display metric type

        Returns:
            Dictionary mapping hand keys to metric values

        Raises:
            DatabaseConnectionError: If database is unavailable
            InvalidContextError: If position/action/metric combination invalid
        """
        return await self.repository.get_strategy_matrix(position, action, metric)

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
            hand_key: Specific hand identifier

        Returns:
            Metric value for the hand, or None if not found

        Raises:
            DatabaseConnectionError: If database is unavailable
            InvalidContextError: If hand_key is invalid
        """
        result = await self.repository.get_hand_metric(position, action, metric, hand_key)
        return result.value if result else None

    def _determine_action_context(self, position: str, position_actions: Dict[str, str] | None) -> ActionContext:
        """
        Determine the action context from position actions.

        For database queries, we need to determine what action the hero is taking.
        This is derived from the position_actions dict for the given position.
        """
        if position_actions and position in position_actions:
            action_str = position_actions[position]
            if action_str == "ALL_IN":
                return ActionContext.ALL_IN()
            elif action_str == "FOLD":
                return ActionContext.FOLD()
            else:
                raise InvalidContextError(f"Unsupported action: {action_str}")

        # Default to ALL_IN if no position_actions provided
        return ActionContext.ALL_IN()

    def _build_context_dict(
        self,
        position: str,
        metric: str,
        position_actions: Dict[str, str] | None,
        pot_size: float,
        bet_amount: float,
        strict_current_action: bool
    ) -> Dict[str, Any]:
        """Build context dictionary for browser compatibility."""
        actions = position_actions or {}
        active_players = sum(1 for action in actions.values() if action == "ALL_IN")

        return {
            "position": position,
            "metric": metric,
            "position_actions": actions,
            "active_players": active_players,
            "pot_size": pot_size,
            "bet_amount": bet_amount,
            "effective_mode": "strict-current-action" if strict_current_action else "analysis",
            "num_simulations": 0,  # Not applicable for DB queries
            "timeout_ms": 0,  # Not applicable for DB queries
        }

    def _build_cells_from_matrix_data(
        self,
        matrix_data: Dict[str, Dict[str, float]],
        requested_metric: str
    ) -> list[Dict[str, Any]]:
        """
        Convert matrix data from repository to browser cell format.

        Args:
            matrix_data: Dict mapping hand_key -> {metric: value}
            requested_metric: The metric that was requested

        Returns:
            List of cell dictionaries compatible with browser
        """
        cells = []

        # Generate all possible hand coordinates (13x13 matrix)
        for row_idx in range(13):
            for col_idx in range(13):
                hand_key = self._matrix_coords_to_hand_key(row_idx, col_idx)

                # Get value for this hand and metric
                hand_data = matrix_data.get(hand_key, {})
                value = hand_data.get(requested_metric)

                # Build metrics dict (only include the requested metric)
                metrics = {}
                if value is not None:
                    metrics[requested_metric] = value

                # Determine status
                if value is not None:
                    status = "AVAILABLE"
                    display = format_metric_value(requested_metric, value)
                else:
                    status = "MISSING"
                    display = "N/A"

                cell = {
                    "row": row_idx,
                    "col": col_idx,
                    "hand_key": hand_key,
                    "metrics": metrics,
                    "value": value,
                    "status": status,
                    "display": display,
                }

                cells.append(cell)

        return cells

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

    def _build_error_payload(self, context: Dict[str, Any], status: str, message: str) -> Dict[str, Any]:
        """Build error payload for browser compatibility."""
        return {
            "context": context,
            "cells": [],
            "status_message": message
        }