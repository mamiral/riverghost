from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from hopilot.database import DatabaseConnection
from hopilot.gto.matrix_sweep_contract import normalize_scenario_contract
from hopilot.gto.repository_errors import SimulationRepositoryError
from hopilot.gto.repository_interfaces import SimulationRepositoryInterface
from hopilot.logging_config import get_logger
from hopilot.models import AggregatedMetric, GameState, HandMatrix, MatrixCell, Player, Simulation


class DataIntegrityError(Exception):
    pass


logger = get_logger(__name__)


class SimulationRepository(SimulationRepositoryInterface):
    def __init__(self, db_connection: DatabaseConnection, session: Optional[Session] = None):
        self.db_connection = db_connection
        self.session = session

    @contextmanager
    def _session_scope(self) -> Session:
        if self.session is not None:
            yield self.session
            return
        with self.db_connection.session_scope() as session:
            yield session

    def _raise_domain_error(self, operation: str, exc: Exception) -> None:
        logger.error("SimulationRepository.%s failed: %s", operation, exc, exc_info=True)
        raise SimulationRepositoryError(f"SimulationRepository {operation} failed: {exc}") from exc

    def create_simulation(self, parameters: Dict[str, Any]) -> int:
        try:
            with self._session_scope() as session:
                simulation = Simulation(
                    parameters=parameters,
                    name=f"simulation_{datetime.now().isoformat()}",
                    start_timestamp=datetime.now(),
                )
                session.add(simulation)
                session.flush()
                return simulation.id
        except Exception as exc:
            self._raise_domain_error("create_simulation", exc)

    def create_hand_matrix(self, simulation_id: int, matrix_size: str = "13x13") -> int:
        try:
            with self._session_scope() as session:
                hand_matrix = HandMatrix(simulation_id=simulation_id, matrix_size=matrix_size)
                session.add(hand_matrix)
                session.flush()
                return hand_matrix.id
        except Exception as exc:
            self._raise_domain_error("create_hand_matrix", exc)

    def create_matrix_sweep_simulation(
        self,
        parameters: Dict[str, Any],
        *,
        name: Optional[str] = None,
        start_timestamp: Optional[datetime] = None,
    ) -> int:
        try:
            with self._session_scope() as session:
                simulation = Simulation(
                    parameters=dict(parameters),
                    name=name or f"matrix_sweep_{datetime.now().isoformat()}",
                    start_timestamp=start_timestamp or datetime.now(),
                )
                session.add(simulation)
                session.flush()
                return simulation.id
        except Exception as exc:
            self._raise_domain_error("create_matrix_sweep_simulation", exc)

    def update_matrix_sweep_simulation(
        self,
        simulation_id: int,
        *,
        parameters: Optional[Dict[str, Any]] = None,
        end_timestamp: Optional[datetime] = None,
    ) -> None:
        try:
            with self._session_scope() as session:
                simulation = session.get(Simulation, simulation_id)
                if simulation is None:
                    raise DataIntegrityError(f"Simulation with ID {simulation_id} does not exist")
                if parameters is not None:
                    simulation.parameters = dict(parameters)
                if end_timestamp is not None:
                    simulation.end_timestamp = end_timestamp
        except DataIntegrityError:
            raise
        except Exception as exc:
            self._raise_domain_error("update_matrix_sweep_simulation", exc)

    def get_latest_game_state_id(self) -> int:
        with self._session_scope() as session:
            latest_id = session.query(func.max(GameState.id)).scalar()
            return int(latest_id or 0)

    def get_max_simulation_id(self) -> int:
        with self._session_scope() as session:
            latest_id = session.query(func.max(Simulation.id)).scalar()
            return int(latest_id or 0)

    def get_max_matrix_id(self) -> int:
        with self._session_scope() as session:
            latest_id = session.query(func.max(HandMatrix.id)).scalar()
            return int(latest_id or 0)

    def get_session(self) -> Session:
        return self.db_connection.get_session()

    def get_run_raw_counts(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> Dict[str, int]:
        with self._session_scope() as session:
            raw_game_states = session.query(func.count(GameState.id)).filter(
                GameState.id >= raw_game_state_id_start,
                GameState.id <= raw_game_state_id_end,
            ).scalar()
            raw_players = session.query(func.count(Player.id)).join(Player.game_state).filter(
                GameState.id >= raw_game_state_id_start,
                GameState.id <= raw_game_state_id_end,
            ).scalar()
            return {
                "raw_game_states": int(raw_game_states or 0),
                "raw_players": int(raw_players or 0),
            }

    def get_simulation_record(self, simulation_id: int) -> Optional[Simulation]:
        with self._session_scope() as session:
            return session.get(Simulation, simulation_id)

    def get_simulation_for_hand_matrix(self, hand_matrix_id: int) -> Optional[Simulation]:
        with self._session_scope() as session:
            matrix = session.query(HandMatrix).filter(HandMatrix.id == hand_matrix_id).first()
            return matrix.simulation if matrix is not None else None

    def upsert_matrix_cell(
        self,
        matrix_id: int,
        row_idx: int,
        col_idx: int,
        hand_key: str,
        metrics: Dict[str, float],
        status: str,
    ) -> int:
        try:
            with self._session_scope() as session:
                existing_cell = session.query(MatrixCell).filter(
                    MatrixCell.matrix_id == matrix_id,
                    MatrixCell.row_index == row_idx,
                    MatrixCell.col_index == col_idx,
                ).first()

                if existing_cell:
                    cell_id = existing_cell.id
                    existing_cell.hand_combination = hand_key
                else:
                    cell = MatrixCell(
                        matrix_id=matrix_id,
                        row_index=row_idx,
                        col_index=col_idx,
                        hand_combination=hand_key,
                    )
                    session.add(cell)
                    session.flush()
                    cell_id = cell.id

                existing_metric = session.query(AggregatedMetric).filter_by(cell_id=cell_id).first()
                equity = metrics.get("equity", 0.5)
                win_probability = metrics.get("win_probability")
                ev = metrics.get("ev")
                jackpot_adjusted_ev = metrics.get("jackpot_adjusted_ev")
                jackpot_frequency = metrics.get("jackpot_frequency")
                avg_jackpot_payout = metrics.get("avg_jackpot_payout")
                sample_count = metrics.get("sample_count")

                if existing_metric:
                    existing_metric.equity = equity
                    existing_metric.win_probability = win_probability
                    existing_metric.ev = ev
                    existing_metric.jackpot_adjusted_ev = jackpot_adjusted_ev
                    existing_metric.jackpot_frequency = jackpot_frequency
                    existing_metric.avg_jackpot_payout = avg_jackpot_payout
                    existing_metric.sample_count = sample_count
                    existing_metric.convergence_status = status
                    existing_metric.last_updated = datetime.now()
                else:
                    metric_record = AggregatedMetric(
                        cell_id=cell_id,
                        equity=equity,
                        win_probability=win_probability,
                        ev=ev,
                        jackpot_adjusted_ev=jackpot_adjusted_ev,
                        jackpot_frequency=jackpot_frequency,
                        avg_jackpot_payout=avg_jackpot_payout,
                        sample_count=sample_count,
                        convergence_status=status,
                        last_updated=datetime.now(),
                    )
                    session.add(metric_record)

                if self.session is None:
                    session.commit()
                return cell_id
        except Exception as exc:
            self._raise_domain_error("upsert_matrix_cell", exc)

    def find_matrix_sweep_run_by_contract(self, scenario_contract: Dict[str, Any]) -> Optional[Simulation]:
        with self._session_scope() as session:
            runs = (
                session.query(Simulation)
                .order_by(Simulation.end_timestamp.desc(), Simulation.id.desc())
                .all()
            )
            return next(
                (run for run in runs if self._matches_scenario_contract(run.parameters, scenario_contract)),
                None,
            )

    def _compare_contract_values(self, saved_value: Any, query_value: Any, key: str) -> bool:
        if key == "active_players":
            if isinstance(saved_value, list) and isinstance(query_value, list):
                return sorted(saved_value) == sorted(query_value)
            if isinstance(saved_value, list) and isinstance(query_value, int):
                return len(saved_value) == query_value
            if isinstance(saved_value, int) and isinstance(query_value, list):
                return saved_value == len(query_value)
            if isinstance(saved_value, int) and isinstance(query_value, int):
                return saved_value == query_value
            return False

        if key in ("raw_game_state_id_start", "raw_game_state_id_end"):
            # A persisted run may not yet have completed raw writes, so None should still match
            if query_value is None:
                return True
            if saved_value is None:
                return key == "raw_game_state_id_end"
            return saved_value == query_value

        return saved_value == query_value

    def _matches_scenario_contract(self, saved_contract: Dict[str, Any], query_contract: Dict[str, Any]) -> bool:
        saved_normalized = normalize_scenario_contract(saved_contract)
        query_normalized = normalize_scenario_contract(query_contract)

        for key, query_value in query_normalized.items():
            saved_value = saved_normalized.get(key)
            if not self._compare_contract_values(saved_value, query_value, key):
                return False
        return True

    def list_matrix_sweep_runs_by_contract(self, scenario_contract: Dict[str, Any]) -> List[Simulation]:
        with self._session_scope() as session:
            runs = session.query(Simulation).all()
            return [run for run in runs if self._matches_scenario_contract(run.parameters, scenario_contract)]

    def get_run_game_states(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> List[GameState]:
        with self._session_scope() as session:
            return (
                session.query(GameState)
                .options(selectinload(GameState.players))
                .filter(
                    GameState.id >= raw_game_state_id_start,
                    GameState.id <= raw_game_state_id_end,
                )
                .order_by(GameState.id.asc())
                .all()
            )

    def get_or_create_hand_matrix_for_simulation(
        self,
        simulation_id: int,
        *,
        matrix_size: str = "13x13",
    ) -> int:
        with self._session_scope() as session:
            matrix = session.query(HandMatrix).filter(HandMatrix.simulation_id == simulation_id).first()
            if matrix is None:
                matrix = HandMatrix(simulation_id=simulation_id, matrix_size=matrix_size)
                session.add(matrix)
                session.flush()
            return matrix.id

    def delete_matrix_summaries(self, matrix_id: int) -> None:
        with self._session_scope() as session:
            cells = session.query(MatrixCell).filter(MatrixCell.matrix_id == matrix_id).all()
            for cell in cells:
                session.delete(cell)

    def get_matrix_sweep_summary(self, simulation_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self._session_scope() as session:
                simulation = session.get(Simulation, simulation_id)
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
                aggregated_metrics = [cell.aggregated_metric for cell in matrix_cells if cell.aggregated_metric is not None]
                return {
                    "simulation": simulation,
                    "hand_matrix": matrix,
                    "matrix_cells": matrix_cells,
                    "aggregated_metrics": aggregated_metrics,
                }
        except Exception as exc:
            self._raise_domain_error("get_matrix_sweep_summary", exc)

    def get_cross_run_matrix_summary(self, scenario_contract: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
                    if getattr(metric, "sample_count", None) is not None:
                        sample_count = int(metric.sample_count)
                    else:
                        sample_count = 1

                if sample_count <= 0:
                    continue

                data = merged_cells[coord]
                if metric is not None:
                    if getattr(metric, "equity", None) is not None:
                        data["equity_sum"] += float(metric.equity) * sample_count
                    if getattr(metric, "win_probability", None) is not None:
                        data["win_probability_sum"] += float(metric.win_probability) * sample_count
                    if getattr(metric, "ev", None) is not None:
                        data["ev_sum"] += float(metric.ev) * sample_count
                    if getattr(metric, "jackpot_adjusted_ev", None) is not None:
                        data["jackpot_adjusted_ev_sum"] += float(metric.jackpot_adjusted_ev) * sample_count
                    data["sample_count_sum"] += sample_count
                    if getattr(metric, "last_updated", None):
                        if data["latest_updated"] is None or metric.last_updated > data["latest_updated"]:
                            data["latest_updated"] = metric.last_updated
                    if getattr(metric, "convergence_status", None):
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
