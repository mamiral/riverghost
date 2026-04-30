import abc
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from hopilot.gto.data_model import ActionContext, PositionContext
from hopilot.models import GameState, PrecomputeJobSession, ScenarioRunLink, Simulation


class RepositoryInterface(abc.ABC):
    """Base interface for repository boundaries."""


class GameStateRepositoryInterface(RepositoryInterface):
    """Interface for raw game-state persistence operations."""

    @abc.abstractmethod
    def create_game_state(self, game_state_data: Dict[str, Any]) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def update_game_state(self, game_state_id: int, updates: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_game_state(self, game_state_id: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    def bulk_insert_game_states(self, game_states: List[Dict[str, Any]]) -> List[int]:
        raise NotImplementedError

    @abc.abstractmethod
    def create_player(self, player_data: Dict[str, Any]) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def create_bet(self, bet_data: Dict[str, Any]) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def create_jackpot(self, jackpot_data: Dict[str, Any]) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def get_run_raw_projection(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> List[Dict[str, Any]]:
        raise NotImplementedError


class SimulationRepositoryInterface(RepositoryInterface):
    """Interface for simulation and matrix metadata persistence."""

    @abc.abstractmethod
    def create_simulation(self, parameters: Dict[str, Any]) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def create_hand_matrix(self, simulation_id: int, matrix_size: str = "13x13") -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def create_matrix_sweep_simulation(
        self,
        parameters: Dict[str, Any],
        *,
        name: Optional[str] = None,
        start_timestamp: Optional[datetime] = None,
    ) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def update_matrix_sweep_simulation(
        self,
        simulation_id: int,
        *,
        parameters: Optional[Dict[str, Any]] = None,
        end_timestamp: Optional[datetime] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_latest_game_state_id(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def get_max_simulation_id(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def get_max_matrix_id(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def get_session(self) -> Session:
        raise NotImplementedError

    @abc.abstractmethod
    def get_run_raw_counts(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> Dict[str, int]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_simulation_record(self, simulation_id: int) -> Optional[Simulation]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_simulation_for_hand_matrix(self, hand_matrix_id: int) -> Optional[Simulation]:
        raise NotImplementedError

    @abc.abstractmethod
    def upsert_matrix_cell(
        self,
        matrix_id: int,
        row_idx: int,
        col_idx: int,
        hand_key: str,
        metrics: Dict[str, float],
        status: str,
    ) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def find_matrix_sweep_run_by_contract(self, scenario_contract: Dict[str, Any]) -> Optional[Simulation]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_matrix_sweep_runs_by_contract(self, scenario_contract: Dict[str, Any]) -> List[Simulation]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete_matrix_summaries(self, matrix_id: int) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_run_game_states(self, raw_game_state_id_start: int, raw_game_state_id_end: int) -> List[GameState]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_create_hand_matrix_for_simulation(self, simulation_id: int, *, matrix_size: str = "13x13") -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def get_matrix_sweep_summary(self, simulation_id: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_cross_run_matrix_summary(self, scenario_contract: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class PrecomputeJobRepositoryInterface(RepositoryInterface):
    """Interface for precompute job/session lifecycle persistence."""

    @abc.abstractmethod
    def create_precompute_job_session(self, scenario_fingerprint: str, requested_scenarios: int) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def update_precompute_job_session(self, job_session_id: int, **updates: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_precompute_job_session(self, job_session_id: int) -> Optional[PrecomputeJobSession]:
        raise NotImplementedError

    @abc.abstractmethod
    def create_scenario_run_link(
        self,
        job_session_id: int,
        scenario_index: int,
        scenario_key: str,
        scenario_contract: Dict[str, Any],
        status: str = "PENDING",
    ) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def update_scenario_run_link(self, scenario_link_id: int, **updates: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_scenario_run_links_for_job(self, job_session_id: int) -> List[ScenarioRunLink]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_scenario_run_link(self, scenario_link_id: int) -> Optional[ScenarioRunLink]:
        raise NotImplementedError


class AnalyticsRepositoryInterface(RepositoryInterface):
    """Interface for read-only analytics queries."""

    @abc.abstractmethod
    def get_simulation_summary(
        self,
        position: Optional[PositionContext] = None,
        action: Optional[ActionContext] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_hand_performance_comparison(
        self,
        hand_keys: List[str],
        position: Optional[PositionContext] = None,
        action: Optional[ActionContext] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_strategy_matrix(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: Any,
    ) -> Dict[str, Dict[str, float]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_hand_metric(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: Any,
        hand_key: str,
    ) -> Optional[float]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_convergence_data(
        self,
        position: PositionContext,
        action: ActionContext,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_matrix_statistics(
        self,
        position: PositionContext,
        action: ActionContext,
    ) -> Dict[str, Any]:
        raise NotImplementedError
