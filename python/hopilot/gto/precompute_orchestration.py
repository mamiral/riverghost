from __future__ import annotations

from typing import Any

from hopilot.logging_config import get_logger


class PrecomputeOrchestrationService:
    def __init__(self, provider: Any, database_repository: Any, logger: Any | None = None):
        self.provider = provider
        self.database_repository = database_repository
        self.logger = logger or get_logger(__name__)

    def resolve_scenario_context(self, scenario: dict[str, Any]) -> dict[str, Any]:
        if self.provider is None or not hasattr(self.provider, "_build_context"):
            raise ValueError("Provider does not support direct context construction")

        context = self.provider._build_context(
            position=scenario["position"],
            metric=scenario["metric"],
            position_actions=scenario["position_actions"],
            strict_current_action=scenario["strict_current_action"],
        )

        if not self._is_valid_context(context):
            raise ValueError("Failed to build scenario context from provider")

        return context

    def build_matrix_sweep_contract(
        self,
        *,
        context: dict[str, Any],
        profile: Any,
        job_session_id: int | None = None,
        scenario_key: str | None = None,
    ) -> dict[str, Any]:
        position_actions = dict(context.get("position_actions", {}))
        active_players = [pos for pos, action in position_actions.items() if action == "ALL_IN"]
        if not active_players and context.get("position"):
            active_players = [context["position"]]

        sims_per_combo = int(profile.simulations_per_cell)
        contract: dict[str, Any] = {
            "selected_position": str(context["position"]),
            "hero_action": str(context["action"]),
            "position_actions": position_actions,
            "active_players": active_players,
            "num_opponents": max(1, len(active_players) - 1),
            "pot_size": float(context.get("pot_size", 0.0)),
            "bet_amount": float(context.get("bet_amount", 0.0)),
            "sims_per_combo": sims_per_combo,
            "num_simulations": sims_per_combo,
            "matrix_size": "13x13",
            "game_type": str(context.get("game_type", "nlhe")),
            "run_kind": "matrix_sweep",
        }
        if job_session_id is not None:
            contract["precompute_job_session_id"] = job_session_id
        if scenario_key is not None:
            contract["scenario_key"] = scenario_key
        return contract

    def record_orchestration_failure(
        self,
        scenario_link_id: int,
        job_session_id: int,
        failure_reason: str,
        completed: int,
        failed: int,
    ) -> None:
        self.database_repository.update_scenario_run_link(
            scenario_link_id,
            status="FAILED",
            failure_boundary="orchestration",
            failure_reason=failure_reason,
        )
        self.database_repository.update_precompute_job_session(
            job_session_id,
            completed_scenarios=completed,
            failed_scenarios=failed,
        )

    @staticmethod
    def _is_valid_context(context: Any) -> bool:
        return (
            isinstance(context, dict)
            and "action" in context
            and "position_actions" in context
        )
