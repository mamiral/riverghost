# Phase 0 Research: Offline AoF Matrix Precomputation and SQLite Scenario Cache

## Decision 1: Use SQLite + SQLAlchemy for persistent scenario cache
- Decision: Persist matrix payloads in SQLite via SQLAlchemy data-access layer.
- Rationale: Meets explicit constraints, supports local desktop runtime, enables indexed lookups and controlled schema evolution.
- Alternatives considered: JSON file cache, in-memory cache only, direct sqlite3 without SQLAlchemy.

## Decision 2: Runtime flow is cache-first with deterministic fallback compute
- Decision: Runtime provider will query persistent cache first; on miss or stale entry it computes, returns deterministic payload, and writes back successful results.
- Rationale: Delivers fast repeated retrieval while preserving functional correctness for uncached scenarios.
- Alternatives considered: compute-only runtime, cache-only runtime with no fallback.

## Decision 3: Versioned invalidation signature
- Decision: Cache validity will require matching schema version, solver signature, and runtime policy signature.
- Rationale: Prevents serving stale payloads after solver or policy changes.
- Alternatives considered: TTL-only expiration, manual cache purge only.

## Decision 4: Offline precompute as resumable, idempotent batch job
- Decision: Offline job tracks run metadata and per-scenario write outcomes so interrupted runs can resume without redoing completed current entries.
- Rationale: Addresses operational interruptions and large scenario sets safely.
- Alternatives considered: one-shot non-resumable batch processing.

## Decision 5: Persistent record stores full UI payload contract
- Decision: Persist `context`, `cells[169]`, and `status_message` as canonical record payload, along with metadata.
- Rationale: Maintains renderer compatibility and minimizes translation logic at read time.
- Alternatives considered: storing only raw solver vectors and rebuilding payload at runtime.

## Decision 6: Deterministic degraded behavior and observability
- Decision: TIMEOUT/ERROR/MISSING/NO_CONTEST statuses remain deterministic; cache path emits structured logs for hit/miss/stale/fallback/write-back.
- Rationale: Preserves trust and supports diagnostics in production-like usage.
- Alternatives considered: silent retries and non-deterministic partial payload fallback.
