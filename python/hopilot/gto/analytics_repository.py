from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from hopilot.database import DatabaseConnection
from hopilot.gto.data_model import ActionContext, ConvergencePoint, PositionContext
from hopilot.gto.repository_errors import AnalyticsRepositoryError
from hopilot.gto.repository_interfaces import AnalyticsRepositoryInterface
from hopilot.logging_config import get_logger
from hopilot.models import AggregatedMetric, HandMatrix, MatrixCell, Simulation


logger = get_logger(__name__)


class AnalyticsRepository(AnalyticsRepositoryInterface):
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection

    def _raise_domain_error(self, operation: str, exc: Exception) -> None:
        logger.error("AnalyticsRepository.%s failed: %s", operation, exc, exc_info=True)
        raise AnalyticsRepositoryError(f"AnalyticsRepository {operation} failed") from exc

    def get_simulation_summary(
        self,
        position: Optional[PositionContext] = None,
        action: Optional[ActionContext] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            select(
                Simulation.id.label("simulation_id"),
                Simulation.parameters,
                Simulation.created_at,
                func.count(MatrixCell.id).label("total_cells"),
                func.avg(AggregatedMetric.equity).label("avg_equity"),
                func.avg(AggregatedMetric.jackpot_adjusted_ev).label("avg_jackpot_ev"),
                func.count(func.distinct(AggregatedMetric.id)).filter(
                    AggregatedMetric.convergence_status == "CONVERGED"
                ).label("converged_cells"),
                func.max(AggregatedMetric.last_updated).label("last_updated"),
            )
            .select_from(Simulation)
            .join(HandMatrix, Simulation.id == HandMatrix.simulation_id)
            .join(MatrixCell, HandMatrix.id == MatrixCell.matrix_id)
            .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
            .group_by(Simulation.id, Simulation.parameters, Simulation.created_at)
        )

        if position:
            query = query.where(Simulation.parameters.like(f"%position:{position.id}%"))
        if action:
            query = query.where(Simulation.parameters.like(f"%action:{action.id}%"))

        query = query.order_by(Simulation.created_at.desc())

        try:
            with self.db_connection.session_scope() as session:
                rows = session.execute(query).fetchall()
                return [
                    {
                        "simulation_id": row.simulation_id,
                        "parameters": row.parameters,
                        "created_at": row.created_at,
                        "total_cells": row.total_cells,
                        "avg_equity": float(row.avg_equity) if row.avg_equity is not None else None,
                        "avg_jackpot_ev": float(row.avg_jackpot_ev) if row.avg_jackpot_ev is not None else None,
                        "converged_cells": row.converged_cells,
                        "convergence_rate": row.converged_cells / row.total_cells if row.total_cells else 0,
                        "last_updated": row.last_updated,
                    }
                    for row in rows
                ]
        except Exception as exc:
            self._raise_domain_error("get_simulation_summary", exc)

    def _get_metric_column(self, metric: Any):
        column_map = {
            'WIN_LOSE_PROBABILITY': AggregatedMetric.equity,
            'EV': AggregatedMetric.jackpot_adjusted_ev,
            'EQUITY': AggregatedMetric.equity,
            'EQR': AggregatedMetric.jackpot_adjusted_ev,
        }
        return column_map.get(metric.id, AggregatedMetric.equity)

    def get_strategy_matrix(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: Any,
    ) -> Dict[str, Dict[str, float]]:
        metric_column = self._get_metric_column(metric)
        query = (
            select(
                MatrixCell.hand_combination.label('hand_key'),
                metric_column,
                Simulation.parameters,
            )
            .select_from(MatrixCell)
            .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
            .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
            .join(Simulation, HandMatrix.simulation_id == Simulation.id)
            .where(MatrixCell.hand_combination.isnot(None))
            .order_by(MatrixCell.hand_combination)
        )

        def _matches_context(parameters: Any) -> bool:
            if not isinstance(parameters, dict):
                return True
            if position is not None:
                stored_position = parameters.get("selected_position", parameters.get("position"))
                if stored_position != position.id:
                    return False
            if action is not None:
                stored_action = parameters.get("hero_action", parameters.get("action"))
                if stored_action != action.id:
                    return False
            return True

        try:
            with self.db_connection.session_scope() as session:
                rows = session.execute(query).fetchall()
                matrix_data: Dict[str, Dict[str, float]] = {}
                for row in rows:
                    if not _matches_context(row[2]):
                        continue
                    if row[1] is not None:
                        matrix_data[row[0]] = {metric.id: float(row[1])}
                return matrix_data
        except Exception as exc:
            self._raise_domain_error("get_strategy_matrix", exc)

    def get_hand_metric(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: Any,
        hand_key: str,
    ) -> Optional[float]:
        metric_column = self._get_metric_column(metric)
        query = (
            select(metric_column)
            .select_from(MatrixCell)
            .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
            .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
            .join(Simulation, HandMatrix.simulation_id == Simulation.id)
            .where(MatrixCell.hand_combination == hand_key)
        )

        if position:
            query = query.where(Simulation.parameters.like(f"%position:{position.id}%"))
        if action:
            query = query.where(Simulation.parameters.like(f"%action:{action.id}%"))

        try:
            with self.db_connection.session_scope() as session:
                row = session.execute(query).first()
                return float(row[0]) if row and row[0] is not None else None
        except Exception as exc:
            self._raise_domain_error("get_hand_metric", exc)

    def get_convergence_data(
        self,
        position: PositionContext,
        action: ActionContext,
    ) -> List[Dict[str, Any]]:
        stats_query = (
            select(
                func.count(AggregatedMetric.id).label('simulation_count'),
                func.avg(AggregatedMetric.equity).label('average_equity'),
            )
            .select_from(MatrixCell)
            .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
            .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
            .join(Simulation, HandMatrix.simulation_id == Simulation.id)
            .where(Simulation.parameters.like(f"%position:{position.id}%"))
            .where(Simulation.parameters.like(f"%action:{action.id}%"))
            .where(AggregatedMetric.convergence_status == 'CONVERGED')
            .group_by(Simulation.id)
            .order_by(func.count(AggregatedMetric.id))
            .limit(20)
        )

        try:
            with self.db_connection.session_scope() as session:
                results = session.execute(stats_query).fetchall()
                points: List[Dict[str, Any]] = []
                cumulative_count = 0
                for row in results:
                    cumulative_count += int(row.simulation_count or 0)
                    points.append({
                        'num_simulations': cumulative_count,
                        'average_equity': float(row.average_equity) if row.average_equity is not None else 0.0,
                        'timestamp': None,
                    })
                return points
        except Exception as exc:
            self._raise_domain_error("get_convergence_data", exc)

    def get_hand_performance_comparison(
        self,
        hand_keys: List[str],
        position: Optional[PositionContext] = None,
        action: Optional[ActionContext] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            select(
                MatrixCell.hand_combination.label('hand_key'),
                Simulation.parameters,
                AggregatedMetric.equity,
                AggregatedMetric.jackpot_adjusted_ev,
                AggregatedMetric.convergence_status,
                AggregatedMetric.last_updated,
            )
            .select_from(MatrixCell)
            .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
            .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
            .join(Simulation, HandMatrix.simulation_id == Simulation.id)
            .where(MatrixCell.hand_combination.in_(hand_keys))
            .order_by(MatrixCell.hand_combination, Simulation.created_at.desc())
        )

        if position:
            query = query.where(Simulation.parameters.like(f"%position:{position.id}%"))
        if action:
            query = query.where(Simulation.parameters.like(f"%action:{action.id}%"))

        with self.db_connection.session_scope() as session:
            rows = session.execute(query).fetchall()
            return [
                {
                    "hand_key": row.hand_key,
                    "simulation_params": row.parameters,
                    "equity": float(row.equity) if row.equity is not None else None,
                    "jackpot_adjusted_ev": float(row.jackpot_adjusted_ev) if row.jackpot_adjusted_ev is not None else None,
                    "convergence_status": row.convergence_status,
                    "last_updated": row.last_updated,
                }
                for row in rows
            ]

    def get_matrix_statistics(
        self,
        position: PositionContext,
        action: ActionContext,
    ) -> Dict[str, Any]:
        stats_query = (
            select(
                func.count(MatrixCell.id).label("total_cells"),
                func.count(AggregatedMetric.id).filter(
                    AggregatedMetric.convergence_status == "CONVERGED"
                ).label("converged_cells"),
                func.avg(AggregatedMetric.equity).label("avg_equity"),
                func.min(AggregatedMetric.equity).label("min_equity"),
                func.max(AggregatedMetric.equity).label("max_equity"),
                func.stddev(AggregatedMetric.equity).label("equity_stddev"),
                func.avg(AggregatedMetric.jackpot_adjusted_ev).label("avg_jackpot_ev"),
                func.min(AggregatedMetric.jackpot_adjusted_ev).label("min_jackpot_ev"),
                func.max(AggregatedMetric.jackpot_adjusted_ev).label("max_jackpot_ev"),
                func.stddev(AggregatedMetric.jackpot_adjusted_ev).label("jackpot_ev_stddev"),
            )
            .select_from(MatrixCell)
            .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
            .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
            .join(Simulation, HandMatrix.simulation_id == Simulation.id)
            .where(Simulation.parameters.like(f"%position:{position.id}%"))
            .where(Simulation.parameters.like(f"%action:{action.id}%"))
        )

        equity_dist_query = (
            select(
                func.floor(AggregatedMetric.equity * 10).label("equity_bucket"),
                func.count(AggregatedMetric.id).label("count"),
            )
            .select_from(MatrixCell)
            .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
            .join(HandMatrix, MatrixCell.matrix_id == HandMatrix.id)
            .join(Simulation, HandMatrix.simulation_id == Simulation.id)
            .where(Simulation.parameters.like(f"%position:{position.id}%"))
            .where(Simulation.parameters.like(f"%action:{action.id}%"))
            .where(AggregatedMetric.equity.isnot(None))
            .group_by(func.floor(AggregatedMetric.equity * 10))
            .order_by(func.floor(AggregatedMetric.equity * 10))
        )

        with self.db_connection.session_scope() as session:
            stats_result = session.execute(stats_query).first()
            equity_dist = session.execute(equity_dist_query).fetchall()
            if not stats_result:
                return {
                    "total_cells": 0,
                    "converged_cells": 0,
                    "convergence_rate": 0,
                    "equity_stats": {},
                    "jackpot_ev_stats": {},
                    "equity_distribution": [],
                }

            distribution = [
                {
                    "equity_range": f"{row.equity_bucket / 10:.1f}-{(row.equity_bucket + 1) / 10:.1f}",
                    "count": row.count,
                }
                for row in equity_dist
            ]

            return {
                "total_cells": stats_result.total_cells,
                "converged_cells": stats_result.converged_cells,
                "convergence_rate": stats_result.converged_cells / stats_result.total_cells if stats_result.total_cells else 0,
                "equity_stats": {
                    "average": float(stats_result.avg_equity) if stats_result.avg_equity is not None else None,
                    "minimum": float(stats_result.min_equity) if stats_result.min_equity is not None else None,
                    "maximum": float(stats_result.max_equity) if stats_result.max_equity is not None else None,
                },
                "jackpot_ev_stats": {
                    "average": float(stats_result.avg_jackpot_ev) if stats_result.avg_jackpot_ev is not None else None,
                    "minimum": float(stats_result.min_jackpot_ev) if stats_result.min_jackpot_ev is not None else None,
                    "maximum": float(stats_result.max_jackpot_ev) if stats_result.max_jackpot_ev is not None else None,
                },
                "equity_distribution": distribution,
            }
