from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable

import yaml

from hopilot.gto.aof_browser_state import METRICS, POSITIONS, build_browser_context, normalize_position_actions
from hopilot.gto.aof_hand_matrix import build_matrix_keys, format_metric_value
from hopilot.gto.aof_scenario_cache_store import AoFScenarioCacheStore, CacheSignatures, AggregationService, RunData, AggregatedResults
from hopilot.gto.aof_solver_adapter import AoFSolverAdapter, SolverRuntimeConfig
from hopilot.logging_config import get_logger

STATUS_AVAILABLE = "AVAILABLE"
STATUS_MISSING = "MISSING"
STATUS_NO_CONTEST = "NO_CONTEST"
STATUS_TIMEOUT = "TIMEOUT"
STATUS_ERROR = "ERROR"

SOLVER_SIGNATURE = "aof-solver-v1"


class AoFBrowserDataProvider:
    def __init__(
        self,
        fixture_path: str | None = None,
        cache_enabled: bool | None = None,
        cache_db_path: str | None = None,
        persist_degraded_payloads: bool | None = None,
        database_url: str | None = None,
    ):
        self.logger = get_logger(__name__)
        self._matrix_keys = build_matrix_keys()
        self._fixture_data: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_store: AoFScenarioCacheStore | None = None
        self._aggregation_service: AggregationService | None = None
        self._database_provider: NormalizedDatabaseProvider | None = None
        self._runtime = self._load_runtime_config()
        self._cache_cfg = self._load_cache_config()
        self._aggregation_cfg = self._load_aggregation_config()
        if persist_degraded_payloads is None:
            self._persist_degraded_payloads = bool(self._cache_cfg.get("persist_degraded_payloads", True))
        else:
            self._persist_degraded_payloads = bool(persist_degraded_payloads)
        self._solver = AoFSolverAdapter(runtime=self._runtime)
        self._baseline_equity_cache: dict[str, float] = {}

        # Initialize database provider if URL provided
        if database_url:
            try:
                from hopilot.gto.normalized_db_provider import NormalizedDatabaseProvider
                self._database_provider = NormalizedDatabaseProvider(database_url)
                self.logger.info("Database provider initialized for AoF browser")
            except Exception as exc:
                self.logger.warning("Failed to initialize database provider: %s", exc)
                self._database_provider = None

        enabled = bool(self._cache_cfg.get("enabled", False)) if cache_enabled is None else bool(cache_enabled)
        # Keep legacy tests isolated from persistent cache unless explicitly enabled.
        if os.getenv("PYTEST_CURRENT_TEST"):
            enabled = bool(cache_enabled)

        if enabled:
            try:
                db_path_raw = cache_db_path or str(self._cache_cfg.get("db_path", "python/hopilot/cache/aof_scenario_cache.sqlite3"))
                db_path = self._resolve_cache_db_path(db_path_raw)
                schema_version = str(self._cache_cfg.get("schema_version", "1"))
                policy_signature = str(self._cache_cfg.get("policy_signature", "aof-cache-policy-v1"))
                self._cache_store = AoFScenarioCacheStore(
                    db_path=db_path,
                    signatures=CacheSignatures(
                        schema_version=schema_version,
                        solver_signature=SOLVER_SIGNATURE,
                        policy_signature=policy_signature,
                        runtime_signature=self._runtime_signature_base(),
                    ),
                )
            except Exception as exc:
                self.logger.warning("Failed to initialize AoF persistent cache store: %s", exc)
                self._cache_store = None

        # Initialize aggregation service if enabled
        aggregation_enabled = bool(self._aggregation_cfg.get("enabled", False))
        if aggregation_enabled:
            try:
                db_path_raw = str(self._aggregation_cfg.get("db_path", "python/hopilot/cache/aof_aggregation.sqlite3"))
                db_path = self._resolve_cache_db_path(db_path_raw)
                self._aggregation_service = AggregationService(db_path=db_path)
            except Exception as exc:
                self.logger.warning("Failed to initialize aggregation service: %s", exc)
                self._aggregation_service = None

        if fixture_path and Path(fixture_path).exists():
            with open(fixture_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            self._fixture_data = loaded.get("data", {})

    def _resolve_cache_db_path(self, configured_path: str) -> str:
        path_obj = Path(configured_path)
        if path_obj.is_absolute():
            return str(path_obj)

        repo_root = Path(__file__).resolve().parents[3]
        canonical = (repo_root / path_obj).resolve()
        return str(canonical)

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

    def _load_cache_config(self) -> dict[str, Any]:
        cfg_path = Path(__file__).resolve().parents[3] / "config" / "gto_defaults.yaml"
        if not cfg_path.exists():
            return {
                "enabled": False,
                "db_path": "python/hopilot/cache/aof_scenario_cache.sqlite3",
                "schema_version": "1",
                "policy_signature": "aof-cache-policy-v1",
                "persist_degraded_payloads": True,
            }
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            return loaded.get("aof_browser_cache", {})
        except Exception as exc:
            self.logger.warning("Failed to load AoF cache config: %s", exc)
            return {"enabled": False}

    def _load_aggregation_config(self) -> dict[str, Any]:
        cfg_path = Path(__file__).resolve().parents[3] / "config" / "gto_defaults.yaml"
        if not cfg_path.exists():
            return {
                "enabled": False,
                "migration_mode": "coexist",
                "db_path": "python/hopilot/cache/aof_aggregation.sqlite3",
                "schema_version": "1",
                "min_runs_for_aggregation": 3,
                "confidence_threshold": 0.8,
            }
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            return loaded.get("aggregation", {})
        except Exception as exc:
            self.logger.warning("Failed to load aggregation config: %s", exc)
            return {"enabled": False}

    def _runtime_signature_base(self) -> str:
        payload = {
            "num_simulations": self._runtime.num_simulations,
            "combo_samples": self._runtime.combo_samples,
            "timeout_ms": self._runtime.timeout_ms,
            "seed": self._runtime.seed,
            "fixture_enabled": bool(self._fixture_data),
        }
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _runtime_signature(self, context: dict[str, Any]) -> str:
        canonical = self._canonical_solver_payload(context)
        payload = {
            "runtime": self._runtime_signature_base(),
            "selected_action": canonical["selected_action"],
            "active_players": canonical["active_players"],
            "num_opponents": canonical["num_opponents"],
            "pot_size": canonical["pot_size"],
            "bet_amount": canonical["bet_amount"],
            "effective_mode": canonical["effective_mode"],
        }
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _legacy_runtime_signature(self, context: dict[str, Any]) -> str:
        canonical = self._legacy_canonical_solver_payload(context)
        payload = {
            "runtime": self._runtime_signature_base(),
            "metric": canonical["metric"],
            "selected_action": canonical["selected_action"],
            "active_players": canonical["active_players"],
            "num_opponents": canonical["num_opponents"],
            "pot_size": canonical["pot_size"],
            "bet_amount": canonical["bet_amount"],
            "effective_mode": canonical["effective_mode"],
        }
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _canonical_solver_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        selected_action = str(context["action"])
        active_players = int(context["active_players"])
        num_opponents = int(self._resolve_num_opponents(selected_action, context["position_actions"]))
        return {
            "solver_signature": SOLVER_SIGNATURE,
            "selected_action": selected_action,
            "active_players": active_players,
            "num_opponents": num_opponents,
            "pot_size": float(context["pot_size"]),
            "bet_amount": float(context["bet_amount"]),
            "effective_mode": context.get("effective_mode"),
            "runtime": {
                "num_simulations": self._runtime.num_simulations,
                "combo_samples": self._runtime.combo_samples,
                "timeout_ms": self._runtime.timeout_ms,
                "seed": self._runtime.seed,
            },
            "fixture_enabled": bool(self._fixture_data),
        }

    def _legacy_canonical_solver_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        payload = self._canonical_solver_payload(context)
        payload["metric"] = str(context["metric"])
        return payload

    def _build_scenario_equivalence_key(self, context: dict[str, Any]) -> str:
        """Build scenario key excluding runtime parameters for aggregation.
        
        This allows merging results across different runtime configurations.
        """
        selected_action = str(context["action"])
        active_players = int(context["active_players"])
        num_opponents = int(self._resolve_num_opponents(selected_action, context["position_actions"]))
        payload = {
            "solver_signature": SOLVER_SIGNATURE,
            "selected_action": selected_action,
            "active_players": active_players,
            "num_opponents": num_opponents,
            "pot_size": float(context["pot_size"]),
            "bet_amount": float(context["bet_amount"]),
            "effective_mode": context.get("effective_mode"),
            "fixture_enabled": bool(self._fixture_data),
        }
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _build_legacy_solver_equivalence_key(self, context: dict[str, Any]) -> str:
        payload = self._legacy_canonical_solver_payload(context)
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _build_context(
        self,
        *,
        position: str,
        metric: str,
        position_actions: dict[str, str] | None,
        pot_size: float = 20.0,
        bet_amount: float = 10.0,
        strict_current_action: bool = False,
    ) -> dict[str, Any]:
        return build_browser_context(
            selected_position=position,
            metric=metric,
            position_actions=position_actions,
            pot_size=pot_size,
            bet_amount=bet_amount,
            num_simulations=self._runtime.num_simulations,
            timeout_ms=self._runtime.timeout_ms,
            strict_current_action=strict_current_action,
        )

    def _log_event(self, event: str, **fields: Any) -> None:
        self.logger.info("AoF provider event=%s fields=%s", event, fields)

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

    @staticmethod
    def _metric_template() -> dict[str, float | None]:
        return {
            "WIN_LOSE_PROBABILITY": None,
            "EQUITY": None,
            "EV": None,
            "EQR": None,
        }

    def _project_cells_for_metric(
        self,
        cells: list[dict[str, Any]],
        metric: str,
        stored_metric: str | None,
    ) -> list[dict[str, Any]] | None:
        projected: list[dict[str, Any]] = []
        has_metric_bundle = any(isinstance(cell.get("metrics"), dict) for cell in cells)
        if not has_metric_bundle and stored_metric is not None and stored_metric != metric:
            return None

        for cell in cells:
            entry = dict(cell)
            bundle = entry.get("metrics")
            if isinstance(bundle, dict):
                value = bundle.get(metric)
                entry["value"] = value
                entry["display"] = format_metric_value(metric, value)
            elif stored_metric == metric:
                metrics = self._metric_template()
                metrics[metric] = entry.get("value")
                entry["metrics"] = metrics
                entry["display"] = format_metric_value(metric, entry.get("value"))
            else:
                return None
            projected.append(entry)
        return projected

    def _load_legacy_persistent_payload(
        self,
        context: dict[str, Any],
        metric: str,
        request_key: str,
        current_solver_key: str,
        current_runtime_signature: str,
    ) -> dict[str, Any] | None:
        if self._cache_store is None:
            return None

        legacy_context = dict(context)
        legacy_context["metric"] = metric
        legacy_key = self._build_legacy_solver_equivalence_key(legacy_context)
        legacy_signature = self._legacy_runtime_signature(legacy_context)
        legacy_payload = self._cache_store.get_payload(legacy_key, legacy_signature)
        if legacy_payload is None:
            return None

        projected = self._project_cells_for_metric(
            legacy_payload.get("cells", []),
            metric,
            str(legacy_payload.get("context", {}).get("metric")) if isinstance(legacy_payload.get("context"), dict) else None,
        )
        if projected is None:
            return None

        migrated_payload = {
            "context": dict(context),
            "cells": projected,
            "status_message": legacy_payload.get("status_message"),
        }
        try:
            self._cache_store.upsert_payload(current_solver_key, migrated_payload, current_runtime_signature)
            self._log_event("cache_migrated", source="legacy_metric_key", scenario_key_hash=current_solver_key)
        except Exception as exc:
            self.logger.warning("AoF provider legacy cache migration failed key=%s error=%s", current_solver_key, exc)

        hydrated = {
            "context": context,
            "cells": projected,
            "status_message": legacy_payload.get("status_message"),
        }
        self._cache[request_key] = hydrated
        self._log_event("cache_hit", source="persistent_legacy", scenario_key_hash=legacy_key)
        return hydrated

    def get_matrix_payload(
        self,
        position: str,
        metric: str,
        position_actions: dict[str, str] | None = None,
        pot_size: float = 20.0,
        bet_amount: float = 10.0,
        strict_current_action: bool = False,
        allow_compute: bool = True,
        on_cell_complete: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        # Check if database provider is available and use it for data retrieval
        if self._database_provider is not None:
            try:
                return self._database_provider.get_matrix_payload(
                    position=position,
                    metric=metric,
                    position_actions=position_actions,
                    pot_size=pot_size,
                    bet_amount=bet_amount,
                    strict_current_action=strict_current_action,
                    allow_compute=allow_compute,
                    on_cell_complete=on_cell_complete,
                )
            except Exception as exc:
                self.logger.warning("Database provider failed, falling back to cache/solver: %s", exc)
                # Fall through to existing cache/solver logic

        try:
            context = self._build_context(
                position=position,
                metric=metric,
                position_actions=position_actions,
                pot_size=pot_size,
                bet_amount=bet_amount,
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

        request_key = self._build_cache_key(context)
        cached = self._cache.get(request_key)
        if cached:
            return cached

        # Check for aggregated data if enabled
        if self._aggregation_service is not None:
            scenario_key = self._build_scenario_equivalence_key(context)
            try:
                aggregated = self._aggregation_service.get_aggregated_stats(scenario_key)
                if aggregated.statistics:  # Only use if we have aggregated data
                    payload = self._build_payload_from_aggregated_data(context, aggregated, metric)
                    if payload is not None:
                        self._cache[request_key] = payload  # Cache the result
                        self._log_event("aggregation_hit", scenario_key=scenario_key, hands_count=len(aggregated.statistics))
                        return payload
            except Exception as exc:
                self.logger.warning("Failed to retrieve aggregated data for scenario %s: %s", scenario_key, exc)

        selected_action = context["action"]
        active_players = context["active_players"]
        if active_players == 0:
            payload = self._build_status_payload(context, STATUS_NO_CONTEST, "All positions are folded")
            self._cache[request_key] = payload
            return payload

        if selected_action == "FOLD" and context["effective_mode"] == "strict-current-action":
            payload = self._build_status_payload(
                context,
                STATUS_NO_CONTEST,
                "Selected position is folded in strict-current-action mode",
            )
            self._cache[request_key] = payload
            return payload

        solver_key = self._build_solver_equivalence_key(context)
        runtime_signature = self._runtime_signature(context)
        if self._cache_store is not None:
            store_payload = self._cache_store.get_payload(solver_key, runtime_signature)
            if store_payload is not None:
                projected = self._project_cells_for_metric(
                    store_payload["cells"],
                    metric,
                    str(store_payload.get("context", {}).get("metric")) if isinstance(store_payload.get("context"), dict) else None,
                )
                if projected is None:
                    self._log_event("cache_miss", source="persistent_metric_incompatible", scenario_key_hash=solver_key)
                else:
                    hydrated = {
                        "context": context,
                        "cells": projected,
                        "status_message": store_payload.get("status_message"),
                    }
                    self._log_event("cache_hit", source="persistent", scenario_key_hash=solver_key)
                    self._cache[request_key] = hydrated
                    return hydrated
            migrated = self._load_legacy_persistent_payload(
                context=context,
                metric=metric,
                request_key=request_key,
                current_solver_key=solver_key,
                current_runtime_signature=runtime_signature,
            )
            if migrated is not None:
                return migrated
            self._log_event("cache_miss", source="persistent", scenario_key_hash=solver_key)

        if not allow_compute:
            payload = self._build_status_payload(context, STATUS_MISSING, "No cached result for selected scenario")
            return payload

        cells: list[dict[str, Any]] = []
        request_start = time.perf_counter()
        timeout_budget_ms = int(context["timeout_ms"])
        self._log_event("fallback_compute_started", scenario_key_hash=solver_key, timeout_ms=timeout_budget_ms)
        for row in range(13):
            for col in range(13):
                key = self._matrix_keys[row][col]
                elapsed_ms = int((time.perf_counter() - request_start) * 1000)
                remaining_ms = max(0, timeout_budget_ms - elapsed_ms)
                if remaining_ms == 0:
                    metric_bundle = self._metric_template()
                    value, status, status_message = (None, STATUS_TIMEOUT, "Solver timeout")
                else:
                    metric_bundle, status, status_message = self._metrics_for_hand(context, key, remaining_ms)
                    value = metric_bundle.get(metric)
                cells.append(
                    {
                        "row": row,
                        "col": col,
                        "hand_key": key,
                        "metrics": metric_bundle,
                        "value": value,
                        "status": status,
                        "display": format_metric_value(metric, value),
                    }
                )
                if on_cell_complete is not None:
                    try:
                        on_cell_complete(cells[-1])
                    except Exception as exc:
                        self.logger.warning("AoF provider cell callback failed for %s: %s", key, exc)
                if status_message:
                    context["status_message"] = status_message

        payload = {
            "context": context,
            "cells": cells,
            "status_message": context.get("status_message"),
        }
        self._cache[request_key] = payload

        if self._cache_store is not None:
            statuses = {cell.get("status") for cell in cells}
            degraded = STATUS_TIMEOUT in statuses or STATUS_ERROR in statuses
            if degraded and STATUS_TIMEOUT in statuses:
                self._log_event("fallback_compute_timeout", scenario_key_hash=solver_key)
            if degraded and STATUS_ERROR in statuses:
                self._log_event("fallback_compute_error", scenario_key_hash=solver_key)

            if degraded and not self._persist_degraded_payloads:
                self._log_event("write_back_skipped", reason="degraded_status", scenario_key_hash=solver_key)
            else:
                try:
                    self._cache_store.upsert_payload(solver_key, payload, runtime_signature)
                    if degraded:
                        self._log_event("write_back_persisted", reason="degraded_status", scenario_key_hash=solver_key)
                except Exception as exc:
                    self.logger.warning("AoF provider write-back failed key=%s error=%s", solver_key, exc)

        # Store aggregation data if enabled
        if self._aggregation_service is not None and allow_compute:
            try:
                scenario_key = self._build_scenario_equivalence_key(context)
                # Extract results from computed cells
                results = {}
                for cell in cells:
                    hand_key = cell["hand_key"]
                    metrics = cell["metrics"]
                    if metrics:  # Only include cells with computed metrics
                        results[hand_key] = metrics
                
                if results:  # Only store if we have results
                    run_data = RunData(
                        timestamp=datetime.now(UTC),
                        sim_count=context.get("num_simulations", self._runtime.num_simulations),
                        combo_samples=self._runtime.combo_samples,
                        timeout=context.get("timeout_ms", self._runtime.timeout_ms) / 1000.0,  # Convert to seconds
                        seed=self._runtime.seed,
                        results=results
                    )
                    self._aggregation_service.store_run(scenario_key, run_data)
                    self._log_event("aggregation_stored", scenario_key=scenario_key, hands_count=len(results))
            except Exception as exc:
                self.logger.warning("AoF provider aggregation storage failed: %s", exc)

        return payload

    def _canonical_solver_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        selected_action = str(context["action"])
        active_players = int(context["active_players"])
        num_opponents = int(self._resolve_num_opponents(selected_action, context["position_actions"]))
        return {
            "solver_signature": SOLVER_SIGNATURE,
            "selected_action": selected_action,
            "active_players": active_players,
            "num_opponents": num_opponents,
            "pot_size": float(context["pot_size"]),
            "bet_amount": float(context["bet_amount"]),
            "effective_mode": str(context["effective_mode"]),
            "runtime": {
                "num_simulations": self._runtime.num_simulations,
                "combo_samples": self._runtime.combo_samples,
                "timeout_ms": self._runtime.timeout_ms,
                "seed": self._runtime.seed,
            },
            "fixture_enabled": bool(self._fixture_data),
        }

    def _build_solver_equivalence_key(self, context: dict[str, Any]) -> str:
        payload = self._canonical_solver_payload(context)
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _runtime_signature_base(self) -> str:
        payload = {
            "num_simulations": self._runtime.num_simulations,
            "combo_samples": self._runtime.combo_samples,
            "timeout_ms": self._runtime.timeout_ms,
            "seed": self._runtime.seed,
            "fixture_enabled": bool(self._fixture_data),
        }
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _runtime_signature(self, context: dict[str, Any]) -> str:
        canonical = self._canonical_solver_payload(context)
        payload = {
            "runtime": self._runtime_signature_base(),
            "selected_action": canonical["selected_action"],
            "active_players": canonical["active_players"],
            "num_opponents": canonical["num_opponents"],
            "pot_size": canonical["pot_size"],
            "bet_amount": canonical["bet_amount"],
            "effective_mode": canonical["effective_mode"],
        }
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _build_scenario_equivalence_key(self, context: dict[str, Any]) -> str:
        """Build scenario key for aggregation (excluding runtime parameters)."""
        # Use the same canonical payload but exclude runtime-specific fields
        canonical = self._canonical_solver_payload(context)
        
        # Remove runtime-specific fields that shouldn't affect scenario equivalence
        scenario_payload = {k: v for k, v in canonical.items() 
                          if k not in ['runtime', 'fixture_enabled']}
        
        encoded = json.dumps(scenario_payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def _build_payload_from_aggregated_data(
        self, 
        context: dict[str, Any], 
        aggregated: "AggregatedResults", 
        target_metric: str
    ) -> dict[str, Any] | None:
        """Build payload from aggregated statistics data."""
        cells = []
        
        for hand_key, metrics in aggregated.statistics.items():
            if target_metric in metrics:
                stat = metrics[target_metric]
                cells.append({
                    "row": 0,  # Will be set by matrix building logic
                    "col": 0,  # Will be set by matrix building logic  
                    "hand_key": hand_key,
                    "metrics": {target_metric: stat.value},  # Only include the target metric
                    "value": stat.value,
                    "status": STATUS_AVAILABLE,
                    "sample_count": stat.sample_count,
                    "confidence": stat.confidence
                })
            else:
                # Hand exists in aggregation but not for this metric
                cells.append({
                    "row": 0,
                    "col": 0,
                    "hand_key": hand_key,
                    "metrics": {},
                    "value": None,
                    "status": STATUS_MISSING,
                    "sample_count": 0,
                    "confidence": 0.0
                })
        
        if not cells:
            return None
            
        # Build the matrix from cells (reuse existing logic)
        matrix_keys = build_matrix_keys()
        matrix = [[None for _ in range(13)] for _ in range(13)]
        
        for cell in cells:
            hand_key = cell["hand_key"]
            if hand_key in matrix_keys:
                row, col = matrix_keys[hand_key]
                cell["row"] = row
                cell["col"] = col
                matrix[row][col] = cell
        
        return {
            "context": context,
            "cells": cells,
            "matrix": matrix,
            "status_message": f"Aggregated from {len(aggregated.statistics)} hands"
        }

    def _metrics_for_hand(
        self,
        context: dict[str, Any],
        hand_key: str,
        remaining_timeout_ms: int,
    ) -> tuple[dict[str, float | None], str, str | None]:
        action = context["action"]
        active_players = int(context["active_players"])
        pot_size = float(context["pot_size"])
        bet_amount = float(context["bet_amount"])

        fixture_metrics = self._metric_template()
        has_fixture = False
        for fixture_metric in tuple(fixture_metrics.keys()):
            fixture_context = dict(context)
            fixture_context["metric"] = fixture_metric
            fixture_value = self._fixture_value(fixture_context, hand_key)
            if fixture_value is not None:
                fixture_metrics[fixture_metric] = round(float(fixture_value), 4)
                has_fixture = True
        if has_fixture:
            return fixture_metrics, STATUS_AVAILABLE, None

        # Selected all-in with no opponents is an uncontested capture.
        if action == "ALL_IN" and active_players == 1:
            return {
                "WIN_LOSE_PROBABILITY": 1.0,
                "EQUITY": 1.0,
                "EV": round(pot_size, 4),
                "EQR": 1.0,
            }, STATUS_AVAILABLE, "Uncontested all-in capture"

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
            return self._metric_template(), mapped, msg

        combo_results = solved.get("combo_results")
        if isinstance(combo_results, list):
            valid_records = [record for record in combo_results if bool(record.get("is_valid", True))]
            if not valid_records:
                return self._metric_template(), STATUS_MISSING, "No valid combos for current hand/context"
            win_prob = sum(float(record.get("win_probability", 0.0)) for record in valid_records) / len(valid_records)
            equity = sum(float(record.get("equity", 0.0)) for record in valid_records) / len(valid_records)
            ev = sum(float(record.get("ev", 0.0)) for record in valid_records) / len(valid_records)
        else:
            equity = float(solved["equity"])
            win_prob = float(solved["win_probability"])
            ev = float(solved["ev"])

        baseline_equity = self._baseline_equity(hand_key)
        eqr = max(0.0, min(1.0, equity / max(1e-6, baseline_equity)))

        return {
            "WIN_LOSE_PROBABILITY": round(win_prob, 4),
            "EQUITY": round(equity, 4),
            "EV": round(ev, 4),
            "EQR": round(eqr, 4),
        }, STATUS_AVAILABLE, None

    def _value_for_hand(
        self,
        context: dict[str, Any],
        hand_key: str,
        remaining_timeout_ms: int,
    ) -> tuple[float | None, str, str | None]:
        metric = context["metric"]
        metric_bundle, status, status_message = self._metrics_for_hand(context, hand_key, remaining_timeout_ms)
        return metric_bundle.get(metric), status, status_message

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
                metrics = self._metric_template()
                cells.append(
                    {
                        "row": row,
                        "col": col,
                        "hand_key": key,
                        "metrics": metrics,
                        "value": metrics.get(metric),
                        "status": status,
                        "display": format_metric_value(metric, metrics.get(metric)),
                    }
                )
        return {"context": context, "cells": cells, "status_message": message}
