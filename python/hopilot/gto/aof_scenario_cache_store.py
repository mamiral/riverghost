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

    def update_run_progress(self, run_id: int, *, completed: int, failed: int, resume_cursor: int) -> None:
        with self._session_factory() as session:
            run = session.get(OfflinePrecomputeRunModel, int(run_id))
            if run is None:
                return
            run.completed_scenarios = int(completed)
            run.failed_scenarios = int(failed)
            run.resume_cursor = int(resume_cursor)
            session.commit()

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

    @staticmethod
    def _is_retryable_db_error(exc: SQLAlchemyError) -> bool:
        if isinstance(exc, IntegrityError):
            message = str(exc).lower()
            return "unique constraint failed" in message
        if isinstance(exc, OperationalError):
            message = str(exc).lower()
            return "database is locked" in message or "database is busy" in message
        return False
