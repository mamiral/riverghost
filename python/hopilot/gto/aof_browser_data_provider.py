from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import yaml

from hopilot.gto.aof_browser_state import METRICS, POSITIONS, build_browser_context, normalize_position_actions
from hopilot.gto.aof_hand_matrix import build_matrix_keys, format_metric_value
from hopilot.gto.aof_solver_adapter import AoFSolverAdapter, SolverRuntimeConfig
from hopilot.logging_config import get_logger

STATUS_AVAILABLE = "AVAILABLE"
STATUS_MISSING = "MISSING"
STATUS_NO_CONTEST = "NO_CONTEST"
STATUS_TIMEOUT = "TIMEOUT"
STATUS_ERROR = "ERROR"

SOLVER_SIGNATURE = "aof-solver-v1"


class AoFBrowserDataProvider:
    def __init__(self, fixture_path: str | None = None):
        self.logger = get_logger(__name__)
        self._matrix_keys = build_matrix_keys()
        self._fixture_data: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
        self._cache: dict[str, dict[str, Any]] = {}
        self._runtime = self._load_runtime_config()
        self._solver = AoFSolverAdapter(runtime=self._runtime)
        self._baseline_equity_cache: dict[str, float] = {}

        if fixture_path and Path(fixture_path).exists():
            with open(fixture_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            self._fixture_data = loaded.get("data", {})

    def _load_runtime_config(self) -> SolverRuntimeConfig:
        cfg_path = Path(__file__).resolve().parents[3] / "config" / "gto_defaults.yaml"
        default = SolverRuntimeConfig()
        if not cfg_path.exists():
            return default

        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
        except Exception as exc:
            self.logger.warning("Failed to load gto_defaults.yaml: %s", exc)
            return default

        runtime_cfg = loaded.get("aof_browser_runtime", {})
        return SolverRuntimeConfig(
            num_simulations=int(runtime_cfg.get("num_simulations", default.num_simulations)),
            combo_samples=int(runtime_cfg.get("combo_samples", default.combo_samples)),
            timeout_ms=int(runtime_cfg.get("timeout_ms", default.timeout_ms)),
            seed=int(runtime_cfg.get("seed", default.seed)),
        )

    def clear_cache(self) -> None:
        self._cache.clear()

    def _build_cache_key(self, context: dict[str, Any]) -> str:
        payload = {
            "solver_signature": SOLVER_SIGNATURE,
            "context": context,
            "runtime": {
                "num_simulations": self._runtime.num_simulations,
                "combo_samples": self._runtime.combo_samples,
                "timeout_ms": self._runtime.timeout_ms,
                "seed": self._runtime.seed,
            },
            "fixture_enabled": bool(self._fixture_data),
        }
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def get_matrix_payload(
        self,
        position: str,
        metric: str,
        position_actions: dict[str, str] | None = None,
        pot_size: float = 20.0,
        bet_amount: float = 10.0,
        strict_current_action: bool = False,
    ) -> dict[str, Any]:
        try:
            context = build_browser_context(
                selected_position=position,
                metric=metric,
                position_actions=position_actions,
                pot_size=pot_size,
                bet_amount=bet_amount,
                num_simulations=self._runtime.num_simulations,
                timeout_ms=self._runtime.timeout_ms,
                strict_current_action=strict_current_action,
            )
        except ValueError:
            # Preserve legacy browser behavior for unsupported metrics by returning a full MISSING payload.
            if metric not in METRICS and position in POSITIONS:
                actions = normalize_position_actions(position_actions)
                active_players = sum(1 for action in actions.values() if action == "ALL_IN")
                fallback_context = {
                    "position": position,
                    "action": actions[position],
                    "metric": metric,
                    "position_actions": actions,
                    "active_players": active_players,
                    "pot_size": float(pot_size),
                    "bet_amount": float(bet_amount),
                    "num_simulations": int(self._runtime.num_simulations),
                    "timeout_ms": int(self._runtime.timeout_ms),
                    "effective_mode": "strict-current-action" if strict_current_action else "analysis",
                }
                return self._build_status_payload(
                    fallback_context,
                    STATUS_MISSING,
                    f"Unsupported metric: {metric}",
                )
            raise

        cache_key = self._build_cache_key(context)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        selected_action = context["action"]
        active_players = context["active_players"]
        if active_players == 0:
            payload = self._build_status_payload(context, STATUS_NO_CONTEST, "All positions are folded")
            self._cache[cache_key] = payload
            return payload

        if selected_action == "FOLD" and context["effective_mode"] == "strict-current-action":
            payload = self._build_status_payload(
                context,
                STATUS_NO_CONTEST,
                "Selected position is folded in strict-current-action mode",
            )
            self._cache[cache_key] = payload
            return payload

        cells: list[dict[str, Any]] = []
        request_start = time.perf_counter()
        timeout_budget_ms = int(context["timeout_ms"])
        for row in range(13):
            for col in range(13):
                key = self._matrix_keys[row][col]
                elapsed_ms = int((time.perf_counter() - request_start) * 1000)
                remaining_ms = max(0, timeout_budget_ms - elapsed_ms)
                if remaining_ms == 0:
                    value, status, status_message = (None, STATUS_TIMEOUT, "Solver timeout")
                else:
                    value, status, status_message = self._value_for_hand(context, key, remaining_ms)
                cells.append(
                    {
                        "row": row,
                        "col": col,
                        "hand_key": key,
                        "value": value,
                        "status": status,
                        "display": format_metric_value(metric, value),
                    }
                )
                if status_message:
                    context["status_message"] = status_message

        payload = {
            "context": context,
            "cells": cells,
            "status_message": context.get("status_message"),
        }
        self._cache[cache_key] = payload
        return payload

    def _value_for_hand(
        self,
        context: dict[str, Any],
        hand_key: str,
        remaining_timeout_ms: int,
    ) -> tuple[float | None, str, str | None]:
        metric = context["metric"]
        action = context["action"]
        active_players = int(context["active_players"])
        pot_size = float(context["pot_size"])
        bet_amount = float(context["bet_amount"])

        fixture_value = self._fixture_value(context, hand_key)
        if fixture_value is not None:
            return fixture_value, STATUS_AVAILABLE, None

        # Selected all-in with no opponents is an uncontested capture.
        if action == "ALL_IN" and active_players == 1:
            if metric == "EV":
                return round(pot_size, 4), STATUS_AVAILABLE, "Uncontested all-in capture"
            if metric in ("WIN_LOSE_PROBABILITY", "EQUITY", "EQR"):
                return 1.0, STATUS_AVAILABLE, "Uncontested all-in capture"

        num_opponents = self._resolve_num_opponents(action, context["position_actions"])
        solved = self._solver.evaluate_hand_key(
            hand_key=hand_key,
            num_opponents=num_opponents,
            pot_size=pot_size,
            bet_amount=bet_amount,
            timeout_ms=max(1, int(remaining_timeout_ms)),
        )
        solved_status = solved.get("status")
        if solved_status != STATUS_AVAILABLE:
            mapped = self._map_solver_status(str(solved_status))
            msg = "Solver timeout" if mapped == STATUS_TIMEOUT else "Solver unavailable for current context"
            if mapped in (STATUS_TIMEOUT, STATUS_ERROR):
                self.logger.warning("AoF provider degraded mode for %s: %s", hand_key, solved)
            return None, mapped, msg

        combo_results = solved.get("combo_results")
        if isinstance(combo_results, list):
            valid_records = [record for record in combo_results if bool(record.get("is_valid", True))]
            if not valid_records:
                return None, STATUS_MISSING, "No valid combos for current hand/context"
            win_prob = sum(float(record.get("win_probability", 0.0)) for record in valid_records) / len(valid_records)
            equity = sum(float(record.get("equity", 0.0)) for record in valid_records) / len(valid_records)
            ev = sum(float(record.get("ev", 0.0)) for record in valid_records) / len(valid_records)
        else:
            equity = float(solved["equity"])
            win_prob = float(solved["win_probability"])
            ev = float(solved["ev"])

        baseline_equity = self._baseline_equity(hand_key)
        eqr = max(0.0, min(1.0, equity / max(1e-6, baseline_equity)))

        if metric == "WIN_LOSE_PROBABILITY":
            return round(win_prob, 4), STATUS_AVAILABLE, None
        if metric == "EQUITY":
            return round(equity, 4), STATUS_AVAILABLE, None
        if metric == "EV":
            return round(ev, 4), STATUS_AVAILABLE, None
        if metric == "EQR":
            return round(eqr, 4), STATUS_AVAILABLE, None
        return None, STATUS_MISSING, "Unknown metric"

    def _baseline_equity(self, hand_key: str) -> float:
        cached = self._baseline_equity_cache.get(hand_key)
        if cached is not None:
            return cached
        solved = self._solver.evaluate_hand_key(
            hand_key=hand_key,
            num_opponents=1,
            pot_size=20.0,
            bet_amount=10.0,
            timeout_ms=self._runtime.timeout_ms,
        )
        if solved.get("status") == STATUS_AVAILABLE:
            eq = float(solved["equity"])
        else:
            eq = 0.5
        self._baseline_equity_cache[hand_key] = eq
        return eq

    def _resolve_num_opponents(self, selected_action: str, position_actions: dict[str, str]) -> int:
        resolver = getattr(self._solver, "resolve_num_opponents", None)
        if callable(resolver):
            return int(resolver(selected_action, position_actions))
        active_players = sum(1 for action in position_actions.values() if action == "ALL_IN")
        if selected_action == "ALL_IN":
            return max(1, active_players - 1)
        return max(1, active_players)

    @staticmethod
    def _map_solver_status(status: str) -> str:
        if status == STATUS_TIMEOUT:
            return STATUS_TIMEOUT
        if status == STATUS_MISSING:
            return STATUS_MISSING
        if status == STATUS_NO_CONTEST:
            return STATUS_NO_CONTEST
        return STATUS_ERROR

    def _fixture_value(self, context: dict[str, Any], hand_key: str) -> float | None:
        position = context["position"]
        action = context["action"]
        metric = context["metric"]
        if position not in self._fixture_data:
            return None
        if action not in self._fixture_data[position]:
            return None
        if metric not in self._fixture_data[position][action]:
            return None
        metric_map = self._fixture_data[position][action][metric]
        if hand_key not in metric_map:
            return None
        return float(metric_map[hand_key])

    def _build_status_payload(self, context: dict[str, Any], status: str, message: str) -> dict[str, Any]:
        cells: list[dict[str, Any]] = []
        metric = context["metric"]
        for row in range(13):
            for col in range(13):
                key = self._matrix_keys[row][col]
                cells.append(
                    {
                        "row": row,
                        "col": col,
                        "hand_key": key,
                        "value": None,
                        "status": status,
                        "display": format_metric_value(metric, None),
                    }
                )
        return {"context": context, "cells": cells, "status_message": message}
