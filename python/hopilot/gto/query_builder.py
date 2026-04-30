"""
Query builder for dynamic filtering of poker analysis data.

Provides a flexible query builder that allows dynamic construction of complex
database queries with multiple filtering options and aggregation capabilities.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy import select, and_, or_, func, text, desc, asc
from sqlalchemy.orm import Session

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger
from hopilot.models import (
    AggregatedMetric,
    MatrixCell,
    Simulation,
    HandMatrix,
    GameState,
    Bet,
    Jackpot
)
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.replay_query_service import ReplayQueryService
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.data_model import PositionContext, ActionContext, MetricType

logger = get_logger(__name__)


@dataclass
class QueryFilter:
    """Represents a single query filter condition."""
    field: str
    operator: str  # 'eq', 'ne', 'gt', 'lt', 'gte', 'lte', 'like', 'in', 'between'
    value: Any
    table_alias: Optional[str] = None


@dataclass
class QuerySort:
    """Represents a sorting specification."""
    field: str
    direction: str  # 'asc', 'desc'
    table_alias: Optional[str] = None


@dataclass
class QueryAggregation:
    """Represents an aggregation specification."""
    function: str  # 'count', 'sum', 'avg', 'min', 'max'
    field: str
    alias: str
    table_alias: Optional[str] = None


class PokerQueryBuilder:
    """
    Flexible query builder for poker analysis data with dynamic filtering.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.filters: List[QueryFilter] = []
        self.sorts: List[QuerySort] = []
        self.aggregations: List[QueryAggregation] = []
        self.group_by_fields: List[str] = []
        self.limit_count: Optional[int] = None
        self.offset_count: Optional[int] = None

    def add_filter(self, field: str, operator: str, value: Any,
                   table_alias: Optional[str] = None) -> 'PokerQueryBuilder':
        """Add a filter condition to the query."""
        self.filters.append(QueryFilter(field, operator, value, table_alias))
        return self

    def add_sort(self, field: str, direction: str = 'asc',
                 table_alias: Optional[str] = None) -> 'PokerQueryBuilder':
        """Add a sorting specification to the query."""
        self.sorts.append(QuerySort(field, direction, table_alias))
        return self

    def add_aggregation(self, function: str, field: str, alias: str,
                       table_alias: Optional[str] = None) -> 'PokerQueryBuilder':
        """Add an aggregation function to the query."""
        self.aggregations.append(QueryAggregation(function, field, alias, table_alias))
        return self

    def group_by(self, *fields: str) -> 'PokerQueryBuilder':
        """Add GROUP BY fields to the query."""
        self.group_by_fields.extend(fields)
        return self

    def limit(self, count: int) -> 'PokerQueryBuilder':
        """Set LIMIT for the query."""
        self.limit_count = count
        return self

    def offset(self, count: int) -> 'PokerQueryBuilder':
        """Set OFFSET for the query."""
        self.offset_count = count
        return self

    def _build_where_clause(self) -> Optional[Any]:
        """Build the WHERE clause from filters."""
        if not self.filters:
            return None

        conditions = []
        for filter_obj in self.filters:
            field_ref = self._get_field_reference(filter_obj.field, filter_obj.table_alias)

            if filter_obj.operator == 'eq':
                conditions.append(field_ref == filter_obj.value)
            elif filter_obj.operator == 'ne':
                conditions.append(field_ref != filter_obj.value)
            elif filter_obj.operator == 'gt':
                conditions.append(field_ref > filter_obj.value)
            elif filter_obj.operator == 'lt':
                conditions.append(field_ref < filter_obj.value)
            elif filter_obj.operator == 'gte':
                conditions.append(field_ref >= filter_obj.value)
            elif filter_obj.operator == 'lte':
                conditions.append(field_ref <= filter_obj.value)
            elif filter_obj.operator == 'like':
                conditions.append(field_ref.like(filter_obj.value))
            elif filter_obj.operator == 'in':
                conditions.append(field_ref.in_(filter_obj.value))
            elif filter_obj.operator == 'between':
                conditions.append(field_ref.between(filter_obj.value[0], filter_obj.value[1]))

        return and_(*conditions) if len(conditions) > 1 else conditions[0] if conditions else None

    def _get_field_reference(self, field: str, table_alias: Optional[str] = None):
        """Get the appropriate field reference for a given field name."""
        # Map field names to model attributes
        field_mappings = {
            # Simulation fields
            'simulation_id': Simulation.id,
            'simulation_parameters': Simulation.parameters,
            'simulation_created_at': Simulation.created_at,

            # MatrixCell fields
            'hand_key': MatrixCell.hand_key,
            'row_index': MatrixCell.row_index,
            'col_index': MatrixCell.col_index,

            # AggregatedMetric fields
            'equity': AggregatedMetric.equity,
            'jackpot_adjusted_ev': AggregatedMetric.jackpot_adjusted_ev,
            'convergence_status': AggregatedMetric.convergence_status,
            'last_updated': AggregatedMetric.last_updated,

            # HandMatrix fields
            'matrix_id': HandMatrix.id,

            # GameState fields
            'game_state_id': GameState.id,
            'pot_size': GameState.pot_size,

            # Jackpot fields
            'jackpot_type': Jackpot.jackpot_type,
            'jackpot_payout': Jackpot.payout_amount,
        }

        if field in field_mappings:
            return field_mappings[field]

        # For dynamic fields, try to access as attribute
        # This is a fallback for extension fields
        raise ValueError(f"Unknown field: {field}")

    def _build_select_columns(self):
        """Build the SELECT columns including aggregations."""
        if self.aggregations:
            columns = []
            for agg in self.aggregations:
                field_ref = self._get_field_reference(agg.field, agg.table_alias)

                if agg.function == 'count':
                    columns.append(func.count(field_ref).label(agg.alias))
                elif agg.function == 'sum':
                    columns.append(func.sum(field_ref).label(agg.alias))
                elif agg.function == 'avg':
                    columns.append(func.avg(field_ref).label(agg.alias))
                elif agg.function == 'min':
                    columns.append(func.min(field_ref).label(agg.alias))
                elif agg.function == 'max':
                    columns.append(func.max(field_ref).label(agg.alias))

            return columns
        else:
            # Default columns for non-aggregated queries
            return [
                Simulation.id.label('simulation_id'),
                Simulation.parameters.label('simulation_parameters'),
                MatrixCell.hand_key,
                AggregatedMetric.equity,
                AggregatedMetric.jackpot_adjusted_ev,
                AggregatedMetric.convergence_status,
                AggregatedMetric.last_updated
            ]

    def _build_order_by(self):
        """Build the ORDER BY clause."""
        if not self.sorts:
            return None

        order_clauses = []
        for sort_obj in self.sorts:
            field_ref = self._get_field_reference(sort_obj.field, sort_obj.table_alias)

            if sort_obj.direction == 'desc':
                order_clauses.append(desc(field_ref))
            else:
                order_clauses.append(asc(field_ref))

        return order_clauses

    async def execute(self) -> List[Dict[str, Any]]:
        """
        Execute the built query and return results.

        Returns:
            List of dictionaries containing the query results
        """
        def _execute_query() -> List[Dict[str, Any]]:
            try:
                # Build the base query with joins
                query = select(*self._build_select_columns()).select_from(
                    Simulation
                    .join(HandMatrix, Simulation.id == HandMatrix.simulation_id)
                    .join(MatrixCell, HandMatrix.id == MatrixCell.matrix_id)
                    .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
                )

                # Add WHERE clause
                where_clause = self._build_where_clause()
                if where_clause is not None:
                    query = query.where(where_clause)

                # Add GROUP BY
                if self.group_by_fields:
                    group_refs = [self._get_field_reference(field) for field in self.group_by_fields]
                    query = query.group_by(*group_refs)

                # Add ORDER BY
                order_by = self._build_order_by()
                if order_by:
                    query = query.order_by(*order_by)

                # Add LIMIT/OFFSET
                if self.limit_count:
                    query = query.limit(self.limit_count)
                if self.offset_count:
                    query = query.offset(self.offset_count)

                with self.db_connection.session() as session:
                    results = session.execute(query).fetchall()

                    # Convert to dictionaries
                    result_dicts = []
                    for row in results:
                        result_dicts.append(dict(row._mapping))

                    return result_dicts

            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise e

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute_query)

    def reset(self) -> 'PokerQueryBuilder':
        """Reset the query builder to initial state."""
        self.filters.clear()
        self.sorts.clear()
        self.aggregations.clear()
        self.group_by_fields.clear()
        self.limit_count = None
        self.offset_count = None
        return self


class PredefinedQueries:
    """
    Collection of commonly used query patterns.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url

    async def get_top_performing_hands(self, position: str, action: str,
                                      limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing hands for a given position/action."""
        builder = PokerQueryBuilder(self.database_url)
        return await (
            builder
            .add_filter('simulation_parameters', 'like', f'%position:{position}%')
            .add_filter('simulation_parameters', 'like', f'%action:{action}%')
            .add_sort('jackpot_adjusted_ev', 'desc')
            .limit(limit)
            .execute()
        )

    async def get_convergence_summary(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get convergence summary for recent simulations."""
        since_time = datetime.now() - timedelta(hours=hours_back)

        builder = PokerQueryBuilder(self.database_url)
        return await (
            builder
            .add_filter('simulation_created_at', 'gte', since_time)
            .add_aggregation('count', 'simulation_id', 'total_simulations')
            .add_aggregation('avg', 'equity', 'avg_equity')
            .add_aggregation('count', 'convergence_status', 'converged_count',
                           lambda x: x == 'CONVERGED')
            .group_by('simulation_parameters')
            .execute()
        )

    async def get_hand_range_analysis(self, hand_keys: List[str]) -> List[Dict[str, Any]]:
        """Analyze performance across different hand ranges."""
        builder = PokerQueryBuilder(self.database_url)
        return await (
            builder
            .add_filter('hand_key', 'in', hand_keys)
            .add_aggregation('avg', 'equity', 'avg_equity')
            .add_aggregation('avg', 'jackpot_adjusted_ev', 'avg_jackpot_ev')
            .add_aggregation('min', 'equity', 'min_equity')
            .add_aggregation('max', 'equity', 'max_equity')
            .group_by('hand_key')
            .add_sort('avg_jackpot_ev', 'desc')
            .execute()
        )

    async def get_run_scoped_raw_game_states(
        self,
        scenario_contract: Optional[Dict[str, Any]] = None,
        explicit_run_id: Optional[int] = None,
        simulation_id: Optional[int] = None,
        hand_matrix_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return raw GameState projections for a persisted run scope."""
        db_connection = DatabaseConnection(self.database_url)
        service = ReplayQueryService(
            db_connection=db_connection,
            simulation_repository=SimulationRepository(db_connection),
            game_state_repository=GameStateRepository(db_connection),
        )
        result = service.query_raw_run(
            scenario_contract=scenario_contract,
            explicit_run_id=explicit_run_id,
            simulation_id=simulation_id,
            hand_matrix_id=hand_matrix_id,
        )
        return result.get("game_states", [])
