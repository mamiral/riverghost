from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore
from hopilot.logging_config import get_logger


@dataclass
class PrecomputeProfile:
    positions: tuple[str, ...] = ("UTG", "BTN", "SB", "BB")
    metrics: tuple[str, ...] = ("WIN_LOSE_PROBABILITY", "EV", "EQUITY", "EQR")
    strict_modes: tuple[bool, ...] = (False, True)


class AoFPrecomputeRunner:
    def __init__(self, provider: AoFBrowserDataProvider, store: AoFScenarioCacheStore):
        self.logger = get_logger(__name__)
        self.provider = provider
        self.store = store

    def enumerate_scenarios(self, profile: PrecomputeProfile) -> list[dict[str, Any]]:
        scenarios: list[dict[str, Any]] = []
        for position in profile.positions:
            for metric in profile.metrics:
                for strict_mode in profile.strict_modes:
                    for actions in product(("FOLD", "ALL_IN"), repeat=4):
                        position_actions = {
                            "UTG": actions[0],
                            "BTN": actions[1],
                            "SB": actions[2],
                            "BB": actions[3],
                        }
                        scenarios.append(
                            {
                                "position": position,
                                "metric": metric,
                                "position_actions": position_actions,
                                "strict_current_action": strict_mode,
                            }
                        )
        return scenarios

    def run(
        self,
        profile: PrecomputeProfile | None = None,
        *,
        run_id: int | None = None,
        max_scenarios: int | None = None,
    ) -> int:
        profile = profile or PrecomputeProfile()
        scenarios = self.enumerate_scenarios(profile)
        if max_scenarios is not None:
            scenarios = scenarios[: int(max_scenarios)]

        if run_id is None:
            run_id = self.store.begin_run(total_scenarios=len(scenarios))
            resume_idx = 0
        else:
            previous = self.store.get_run(run_id)
            resume_idx = int(previous.resume_cursor or 0) if previous else 0

        completed = 0
        failed = 0
        for idx in range(resume_idx, len(scenarios)):
            scenario = scenarios[idx]
            context = self.provider._build_context(  # pylint: disable=protected-access
                position=scenario["position"],
                metric=scenario["metric"],
                position_actions=scenario["position_actions"],
                strict_current_action=scenario["strict_current_action"],
            )
            key = self.provider._build_solver_equivalence_key(context)  # pylint: disable=protected-access
            runtime_signature = self.provider._runtime_signature(context)  # pylint: disable=protected-access

            if self.store.has_current(key, runtime_signature):
                self.store.record_write_result(run_id=run_id, scenario_key_hash=key, outcome="SKIPPED_CURRENT")
                completed += 1
                self.store.update_run_progress(run_id, completed=completed, failed=failed, resume_cursor=idx + 1)
                continue

            try:
                payload = self.provider.get_matrix_payload(
                    position=scenario["position"],
                    metric=scenario["metric"],
                    position_actions=scenario["position_actions"],
                    strict_current_action=scenario["strict_current_action"],
                )
                statuses = {cell.get("status") for cell in payload.get("cells", [])}
                if "TIMEOUT" in statuses or "ERROR" in statuses:
                    failed += 1
                    self.store.record_write_result(run_id=run_id, scenario_key_hash=key, outcome="FAILED", error_message="degraded_status")
                else:
                    completed += 1
                    self.store.record_write_result(run_id=run_id, scenario_key_hash=key, outcome="UPDATED")
            except Exception as exc:  # pragma: no cover - defensive path for precompute jobs
                failed += 1
                self.store.record_write_result(run_id=run_id, scenario_key_hash=key, outcome="FAILED", error_message=str(exc))

            self.store.update_run_progress(run_id, completed=completed, failed=failed, resume_cursor=idx + 1)

        status = "FAILED" if failed > 0 else "COMPLETED"
        self.store.finalize_run(run_id, status=status)
        self.logger.info("AoF precompute run complete run_id=%s completed=%s failed=%s", run_id, completed, failed)
        return run_id
