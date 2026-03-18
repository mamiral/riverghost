from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hopilot.logging_config import get_logger

try:
    from sqlalchemy import create_engine
    from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
    from sqlalchemy.orm import Session, sessionmaker

    from hopilot.gto.aof_scenario_cache_models import (
        Base,
        CacheMetadataModel,
        OfflinePrecomputeRunModel,
        ScenarioPayloadModel,
        ScenarioWriteResultModel,
    )
    from hopilot.gto.aof_aggregation_models import (
        ScenarioModel,
        RunModel,
        SimulationOutcomeModel,
    )
    from hopilot.gto.aof_aggregation_math import aggregate_run_data, calculate_confidence_score
except Exception:  # pragma: no cover - optional dependency guard for environments not yet provisioned
    create_engine = None
    SQLAlchemyError = Exception
    Session = Any
    sessionmaker = None
    Base = None
    CacheMetadataModel = Any
    OfflinePrecomputeRunModel = Any
    ScenarioPayloadModel = Any
    ScenarioWriteResultModel = Any


@dataclass
class CacheSignatures:
    schema_version: str
    solver_signature: str
    policy_signature: str
    runtime_signature: str


class AoFScenarioCacheStore:
    def __init__(
        self,
        db_path: str,
        signatures: CacheSignatures,
    ):
        self.logger = get_logger(__name__)
        if create_engine is None or sessionmaker is None or Base is None:
            raise RuntimeError("SQLAlchemy is unavailable in current environment")

        self.signatures = signatures
        self._lock_retry_attempts = 3
        self._lock_retry_delay_seconds = 0.02
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        self.bootstrap_schema()

    def bootstrap_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    @staticmethod
    def build_scenario_key(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _json_dumps(value: Any) -> str:
        return json.dumps(value, sort_keys=True)

    @staticmethod
    def _json_loads(value: str) -> Any:
        return json.loads(value)

    def _log_event(self, event: str, **fields: Any) -> None:
        self.logger.info("AoF cache event=%s fields=%s", event, fields)

    def _runtime_signature(self, context: dict[str, Any], runtime: dict[str, Any]) -> str:
        encoded = json.dumps({"context": context, "runtime": runtime}, sort_keys=True)
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()

    def get_payload(
        self,
        scenario_key_hash: str,
        expected_runtime_signature: str,
    ) -> dict[str, Any] | None:
        def _op() -> dict[str, Any] | None:
            with self._session_factory() as session:
                payload = session.get(ScenarioPayloadModel, scenario_key_hash)
                if payload is None:
                    self._log_event("cache_miss", scenario_key_hash=scenario_key_hash)
                    return None

                meta = payload.metadata_row
                if meta is None:
                    self._mark_stale(session, payload, reason="missing_metadata")
                    self._log_event("cache_stale", scenario_key_hash=scenario_key_hash, reason="missing_metadata")
                    return None

                if not self._is_current(meta, expected_runtime_signature):
                    reason = meta.stale_reason or "signature_mismatch"
                    self._mark_stale(session, payload, reason=reason)
                    self._log_event("cache_stale", scenario_key_hash=scenario_key_hash, reason=reason)
                    return None

                try:
                    context = self._json_loads(payload.context_json)
                    cells = self._json_loads(payload.cells_json)
                except Exception:
                    self._mark_stale(session, payload, reason="corrupt_payload")
                    self._log_event("cache_corrupt", scenario_key_hash=scenario_key_hash)
                    return None

                self._log_event("cache_hit", scenario_key_hash=scenario_key_hash)
                return {
                    "context": context,
                    "cells": cells,
                    "status_message": payload.status_message,
                }

        return self._with_lock_retry(_op, operation="get_payload")

    def has_current(self, scenario_key_hash: str, expected_runtime_signature: str) -> bool:
        return self.get_payload(scenario_key_hash, expected_runtime_signature) is not None

    def upsert_payload(
        self,
        scenario_key_hash: str,
        payload: dict[str, Any],
        runtime_signature: str,
        skip_if_current: bool = False,
    ) -> str:
        def _op() -> str:
            with self._session_factory() as session:
                current = session.get(ScenarioPayloadModel, scenario_key_hash)
                if current is not None and current.metadata_row is not None and self._is_current(current.metadata_row, runtime_signature):
                    if skip_if_current:
                        return "SKIPPED_CURRENT"

                if current is None:
                    current = ScenarioPayloadModel(
                        scenario_key_hash=scenario_key_hash,
                        context_json=self._json_dumps(payload["context"]),
                        cells_json=self._json_dumps(payload["cells"]),
                        status_message=payload.get("status_message"),
                    )
                    current.metadata_row = CacheMetadataModel(
                        scenario_key_hash=scenario_key_hash,
                        schema_version=self.signatures.schema_version,
                        solver_signature=self.signatures.solver_signature,
                        policy_signature=self.signatures.policy_signature,
                        runtime_signature=runtime_signature,
                        is_stale=False,
                        stale_reason=None,
                    )
                    session.add(current)
                    outcome = "INSERTED"
                else:
                    current.context_json = self._json_dumps(payload["context"])
                    current.cells_json = self._json_dumps(payload["cells"])
                    current.status_message = payload.get("status_message")
                    current.updated_at = datetime.now(UTC)
                    if current.metadata_row is None:
                        current.metadata_row = CacheMetadataModel(
                            scenario_key_hash=scenario_key_hash,
                            schema_version=self.signatures.schema_version,
                            solver_signature=self.signatures.solver_signature,
                            policy_signature=self.signatures.policy_signature,
                            runtime_signature=runtime_signature,
                            is_stale=False,
                            stale_reason=None,
                        )
                    else:
                        current.metadata_row.schema_version = self.signatures.schema_version
                        current.metadata_row.solver_signature = self.signatures.solver_signature
                        current.metadata_row.policy_signature = self.signatures.policy_signature
                        current.metadata_row.runtime_signature = runtime_signature
                        current.metadata_row.is_stale = False
                        current.metadata_row.stale_reason = None
                    outcome = "UPDATED"

                session.commit()
                self._log_event("write_back_inserted_or_updated", scenario_key_hash=scenario_key_hash, outcome=outcome)
                return outcome

        return self._with_lock_retry(_op, operation="upsert_payload")

    def begin_run(self, total_scenarios: int) -> int:
        with self._session_factory() as session:
            run = OfflinePrecomputeRunModel(
                status="RUNNING",
                total_scenarios=int(total_scenarios),
                completed_scenarios=0,
                failed_scenarios=0,
                resume_cursor=0,
            )
            session.add(run)
            session.commit()
            return int(run.run_id)

    def get_run(self, run_id: int) -> OfflinePrecomputeRunModel | None:
        with self._session_factory() as session:
            return session.get(OfflinePrecomputeRunModel, int(run_id))

    def get_latest_run_id(self, statuses: tuple[str, ...] | None = None) -> int | None:
        with self._session_factory() as session:
            query = session.query(OfflinePrecomputeRunModel)
            if statuses:
                query = query.filter(OfflinePrecomputeRunModel.status.in_(tuple(statuses)))
            run = query.order_by(OfflinePrecomputeRunModel.run_id.desc()).first()
            if run is None:
                return None
            return int(run.run_id)

    def update_run_progress(self, run_id: int, *, completed: int, failed: int, resume_cursor: int) -> None:
        with self._session_factory() as session:
            run = session.get(OfflinePrecomputeRunModel, int(run_id))
            if run is None:
                return
            run.completed_scenarios = int(completed)
            run.failed_scenarios = int(failed)
            run.resume_cursor = int(resume_cursor)
            session.commit()

    def persist_gui_checkpoint(
        self,
        run_id: int,
        *,
        resume_cursor: int,
        completed_cells: int,
        failed_cells: int,
        status: str,
    ) -> None:
        with self._session_factory() as session:
            run = session.get(OfflinePrecomputeRunModel, int(run_id))
            if run is None:
                return
            run.resume_cursor = int(resume_cursor)
            run.completed_scenarios = int(completed_cells)
            run.failed_scenarios = int(failed_cells)
            run.status = str(status)
            session.commit()

    def get_gui_checkpoint_cursor(self, run_id: int) -> dict[str, int | str] | None:
        with self._session_factory() as session:
            run = session.get(OfflinePrecomputeRunModel, int(run_id))
            if run is None:
                return None
            return {
                "run_id": int(run.run_id),
                "resume_cursor": int(run.resume_cursor or 0),
                "completed_cells": int(run.completed_scenarios or 0),
                "failed_cells": int(run.failed_scenarios or 0),
                "status": str(run.status),
            }

    def finalize_run(self, run_id: int, status: str) -> None:
        with self._session_factory() as session:
            run = session.get(OfflinePrecomputeRunModel, int(run_id))
            if run is None:
                return
            run.status = status
            run.finished_at = datetime.now(UTC)
            session.commit()

    def record_write_result(
        self,
        *,
        run_id: int | None,
        scenario_key_hash: str,
        outcome: str,
        error_message: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            record = ScenarioWriteResultModel(
                run_id=run_id,
                scenario_key_hash=scenario_key_hash,
                outcome=outcome,
                error_message=error_message,
            )
            session.add(record)
            session.commit()

    def _is_current(self, metadata: CacheMetadataModel, expected_runtime_signature: str) -> bool:
        if metadata.is_stale:
            return False
        if metadata.schema_version != self.signatures.schema_version:
            metadata.stale_reason = "schema_version_mismatch"
            return False
        if metadata.solver_signature != self.signatures.solver_signature:
            metadata.stale_reason = "solver_signature_mismatch"
            return False
        if metadata.policy_signature != self.signatures.policy_signature:
            metadata.stale_reason = "policy_signature_mismatch"
            return False
        if metadata.runtime_signature != expected_runtime_signature:
            metadata.stale_reason = "runtime_signature_mismatch"
            return False
        return True

    def _mark_stale(self, session: Session, payload: ScenarioPayloadModel, reason: str) -> None:
        if payload.metadata_row is None:
            return
        payload.metadata_row.is_stale = True
        payload.metadata_row.stale_reason = reason
        session.commit()

    def _with_lock_retry(self, fn: Any, *, operation: str) -> Any:
        for attempt in range(1, self._lock_retry_attempts + 1):
            try:
                return fn()
            except SQLAlchemyError as exc:
                if attempt >= self._lock_retry_attempts or not self._is_retryable_db_error(exc):
                    raise
                self._log_event(
                    "cache_retry",
                    operation=operation,
                    attempt=attempt,
                    max_attempts=self._lock_retry_attempts,
                )
                time.sleep(self._lock_retry_delay_seconds * attempt)

    def migrate_legacy_payloads_to_aggregation(
        self,
        aggregation_store: "AoFAggregationCacheStore",  # type: ignore
        scenario_key_builder: Callable[[dict[str, Any]], str],
    ) -> dict[str, str]:
        """Migrate existing snapshot payloads to aggregation format.
        
        Returns dict of scenario_key -> migration_status
        """
        results = {}
        
        def _migrate() -> None:
            with self._session_factory() as session:
                # Get all current payloads
                payloads = session.query(ScenarioPayloadModel).all()
                
                for payload in payloads:
                    try:
                        # Parse payload data
                        context = self._json_loads(payload.context_json)
                        cells = self._json_loads(payload.cells_json)
                        
                        # Build scenario key (excluding runtime)
                        scenario_key = scenario_key_builder(context)
                        
                        # Create run data from legacy payload - convert aggregated results to synthetic outcomes
                        # Note: This creates one synthetic outcome per hand representing the aggregated result
                        synthetic_outcomes = []
                        for hand, metrics in cells.items():
                            # Create a synthetic outcome representing the aggregated result
                            # We use a dummy villain hand since we don't have individual matchups
                            equity = metrics.get('EQUITY', metrics.get('WIN_LOSE_PROBABILITY', 0.5))
                            ev = metrics.get('EV', 0.0)
                            
                            outcome = SimulationOutcome(
                                hero_hand=hand,
                                villain_hand='SYNTHETIC',  # Placeholder
                                outcome='WIN' if equity > 0.5 else 'LOSS' if equity < 0.5 else 'TIE',
                                hero_equity=equity,
                                ev_chips=ev,
                                board_cards=''
                            )
                            synthetic_outcomes.append(outcome)
                        
                        run_data = RunData(
                            timestamp=payload.created_at,
                            sim_count=context.get("runtime", {}).get("num_simulations", len(synthetic_outcomes)),
                            combo_samples=context.get("runtime", {}).get("combo_samples", 4),
                            timeout=context.get("runtime", {}).get("timeout_ms", 900) / 1000.0,
                            seed=context.get("runtime", {}).get("seed", 42),
                            outcomes=synthetic_outcomes
                        )
                        
                        # Store in aggregation
                        aggregation_store.store_run(scenario_key, run_data)
                        
                        results[scenario_key] = "MIGRATED"
                        
                    except Exception as exc:
                        self.logger.warning("Failed to migrate payload %s: %s", payload.scenario_key_hash, exc)
                        results[payload.scenario_key_hash] = f"FAILED: {exc}"
        
        try:
            _migrate()
        except Exception as exc:
            self.logger.error("Migration failed: %s", exc)
            results["MIGRATION_ERROR"] = str(exc)
        
        return results

    @staticmethod
    def _is_retryable_db_error(exc: SQLAlchemyError) -> bool:
        if isinstance(exc, IntegrityError):
            message = str(exc).lower()
            return "unique constraint failed" in message
        if isinstance(exc, OperationalError):
            message = str(exc).lower()
            return "database is locked" in message or "database is busy" in message
        return False


@dataclass
class SimulationOutcome:
    """Individual simulation outcome data."""
    hero_hand: str  # treys format
    villain_hand: str  # treys format
    outcome: str  # 'WIN', 'LOSS', 'TIE'
    hero_equity: float  # 1.0 for win, 0.0 for loss, 0.5 for tie
    ev_chips: float  # EV in chips for this simulation
    board_cards: str = ""  # Optional: final board cards


@dataclass
class RunData:
    timestamp: datetime
    sim_count: int
    combo_samples: int
    timeout: float
    seed: int
    outcomes: list[SimulationOutcome] | None = None
    results: dict[str, dict[str, float]] | None = None  # For backward compatibility  # Individual simulation outcomes


@dataclass
class AggregatedResults:
    scenario_key: str
    statistics: dict[str, dict[str, Statistic]]  # hand -> metric -> stats


@dataclass
class Statistic:
    value: float
    sample_count: int
    confidence: float


class AggregationService:
    """Service for aggregating AoF run statistics across multiple executions."""

    def __init__(self, db_path: str, cache_size: int = 100):
        self.logger = get_logger(__name__)
        if create_engine is None or sessionmaker is None or Base is None:
            raise RuntimeError("SQLAlchemy is unavailable in current environment")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        
        # Simple LRU cache for aggregated results
        self._cache: dict[str, tuple[AggregatedResults, datetime]] = {}
        self._cache_size = cache_size
        self._cache_order: list[str] = []  # For LRU tracking
        
        self.bootstrap_schema()

    def bootstrap_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def _get_cached_result(self, scenario_key: str) -> AggregatedResults | None:
        """Get cached result if available and not stale."""
        if scenario_key in self._cache:
            result, cached_time = self._cache[scenario_key]
            # Cache for 5 minutes
            if (datetime.now(UTC) - cached_time).total_seconds() < 300:
                # Move to end of LRU order
                if scenario_key in self._cache_order:
                    self._cache_order.remove(scenario_key)
                self._cache_order.append(scenario_key)
                return result
            else:
                # Remove stale cache entry
                del self._cache[scenario_key]
                if scenario_key in self._cache_order:
                    self._cache_order.remove(scenario_key)
        return None

    def _cache_result(self, scenario_key: str, result: AggregatedResults) -> None:
        """Cache an aggregated result."""
        self._cache[scenario_key] = (result, datetime.now(UTC))
        
        # Maintain LRU order
        if scenario_key in self._cache_order:
            self._cache_order.remove(scenario_key)
        self._cache_order.append(scenario_key)
        
        # Evict oldest if cache is full
        if len(self._cache) > self._cache_size:
            oldest_key = self._cache_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]

    def clear_cache(self) -> None:
        """Clear the aggregation cache."""
        self._cache.clear()
        self._cache_order.clear()

    def store_run(self, scenario_key: str, run_data: RunData) -> None:
        """Store a new run with individual simulation outcomes for aggregation."""
        def _op() -> None:
            with self._session_factory() as session:
                # Get or create scenario
                scenario = session.query(ScenarioModel).filter_by(scenario_key=scenario_key).first()
                if scenario is None:
                    scenario = ScenarioModel(scenario_key=scenario_key)
                    session.add(scenario)
                    session.flush()  # Ensure scenario exists

                # Create run record
                run = RunModel(
                    scenario_key=scenario_key,
                    timestamp=run_data.timestamp,
                    sim_count=run_data.sim_count,
                    combo_samples=run_data.combo_samples,
                    timeout=run_data.timeout,
                    seed=run_data.seed,
                )
                session.add(run)
                session.flush()  # Get run_id

                # Store individual simulation outcomes
                outcome_objects = []
                for outcome in run_data.outcomes:
                    outcome_obj = SimulationOutcomeModel(
                        run_id=run.run_id,
                        hero_hand=outcome.hero_hand,
                        villain_hand=outcome.villain_hand,
                        outcome=outcome.outcome,
                        hero_equity=outcome.hero_equity,
                        ev_chips=outcome.ev_chips,
                        board_cards=outcome.board_cards,
                    )
                    outcome_objects.append(outcome_obj)

                session.add_all(outcome_objects)
                session.commit()
                
                self.logger.info("Stored run %d for scenario %s with %d simulation outcomes", 
                               run.run_id, scenario_key, len(run_data.outcomes))
                
                # Clear cache for this scenario since we have new data
                if scenario_key in self._cache:
                    del self._cache[scenario_key]
                    if scenario_key in self._cache_order:
                        self._cache_order.remove(scenario_key)

        try:
            _op()
        except Exception as exc:
            self.logger.error("Failed to store run for scenario %s: %s", scenario_key, exc)
            raise

    def get_aggregated_stats(self, scenario_key: str) -> AggregatedResults:
        """Retrieve aggregated statistics for a scenario by querying individual simulation outcomes."""
        # Check cache first
        cached_result = self._get_cached_result(scenario_key)
        if cached_result is not None:
            self.logger.debug("Returning cached result for scenario %s", scenario_key)
            return cached_result
        
        def _op() -> AggregatedResults:
            with self._session_factory() as session:
                # Get scenario
                scenario = session.query(ScenarioModel).filter_by(scenario_key=scenario_key).first()
                if scenario is None:
                    result = AggregatedResults(scenario_key=scenario_key, statistics={})
                    self._cache_result(scenario_key, result)
                    return result

                # Get all runs for this scenario to get total sim_count
                runs = session.query(RunModel).filter(RunModel.scenario_key == scenario_key).all()
                
                # Get all simulation outcomes for this scenario
                outcomes = session.query(SimulationOutcomeModel).join(RunModel).filter(
                    RunModel.scenario_key == scenario_key
                ).all()
                
                # Calculate total sim_count only from runs that have outcomes
                run_ids_with_outcomes = {outcome.run_id for outcome in outcomes}
                total_sim_count = sum(run.sim_count for run in runs if run.run_id in run_ids_with_outcomes)
                
                self.logger.debug("Found %d simulation outcomes for scenario %s", len(outcomes), scenario_key)
                
                if not outcomes:
                    result = AggregatedResults(scenario_key=scenario_key, statistics={})
                    self._cache_result(scenario_key, result)
                    return result
                
                # Aggregate outcomes by hero hand
                hand_stats = {}
                for outcome in outcomes:
                    hero_hand = outcome.hero_hand
                    
                    if hero_hand not in hand_stats:
                        hand_stats[hero_hand] = {
                            'equity_sum': 0.0,
                            'ev_sum': 0.0,
                            'count': 0
                        }
                    
                    hand_stats[hero_hand]['equity_sum'] += outcome.hero_equity
                    hand_stats[hero_hand]['ev_sum'] += outcome.ev_chips
                    hand_stats[hero_hand]['count'] += 1
                
                # Calculate final statistics
                statistics = {}
                for hero_hand, stats in hand_stats.items():
                    count = stats['count']
                    avg_equity = stats['equity_sum'] / count
                    avg_ev = stats['ev_sum'] / count
                    
                    # Calculate confidence based on sample size
                    confidence = min(1.0, count / 1000.0)  # Simple confidence calculation
                    
                    statistics[hero_hand] = {
                        'EQUITY': Statistic(
                            value=avg_equity,
                            sample_count=total_sim_count,
                            confidence=calculate_confidence_score(total_sim_count)
                        ),
                        'WIN_LOSE_PROBABILITY': Statistic(
                            value=avg_equity,
                            sample_count=total_sim_count,
                            confidence=calculate_confidence_score(total_sim_count)
                        ),
                        'EV': Statistic(
                            value=avg_ev,
                            sample_count=total_sim_count,
                            confidence=calculate_confidence_score(total_sim_count)
                        )
                    }
                
                self.logger.info("Aggregated %d simulation outcomes for scenario %s into %d hands", 
                               len(outcomes), scenario_key, len(statistics))
                
                result = AggregatedResults(scenario_key=scenario_key, statistics=statistics)
                self._cache_result(scenario_key, result)
                return result

        try:
            return _op()
        except Exception as exc:
            self.logger.error("Failed to get aggregated stats for scenario %s: %s", scenario_key, exc)
            raise
