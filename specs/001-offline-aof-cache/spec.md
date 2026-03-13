# Feature Specification: Offline AoF Matrix Precomputation and SQLite Scenario Cache

**Feature Branch**: `001-offline-aof-cache`  
**Created**: 2026-03-13  
**Status**: Draft  
**Input**: User description: "Add offline AoF matrix precomputation and persistent SQLite scenario cache with SQLAlchemy so runtime can retrieve, fallback-compute, and write back deterministically."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast Cached Matrix Loads (Priority: P1)

As a user of the standalone AoF browser, I want previously solved scenarios to load from persistent cache so the 13x13 matrix appears quickly during normal browsing.

**Why this priority**: This directly addresses observed timeout pressure and is the primary user-facing value.

**Independent Test**: Precompute one scenario offline, restart the app, request the same context, and verify the matrix returns from persistent cache without triggering scenario recomputation.

**Acceptance Scenarios**:

1. **Given** a scenario that already exists in persistent cache, **When** the same context is requested at runtime, **Then** the system returns the cached 169-cell payload with deterministic status fields.
2. **Given** multiple repeated requests for the same scenario across app restarts, **When** users toggle away and back, **Then** cached retrieval remains fast and stable.

---

### User Story 2 - Reliable Fallback and Write-Back (Priority: P2)

As a user, I want runtime to compute a missing scenario and save it for future use so the first miss is recoverable and later loads are fast.

**Why this priority**: Ensures full coverage of scenario space even when offline jobs have not precomputed every context.

**Independent Test**: Request a cache-miss scenario, verify deterministic fallback compute behavior, and then verify a second request is served from persistent cache.

**Acceptance Scenarios**:

1. **Given** a requested scenario is missing from persistent cache, **When** runtime fallback compute succeeds, **Then** the response is returned and persisted for future requests.
2. **Given** fallback compute exceeds budget or fails, **When** payload is returned, **Then** statuses and messages follow deterministic timeout/error policy and no synthetic silent fallback is used.

---

### User Story 3 - Safe Versioned Invalidation (Priority: P3)

As a maintainer, I want cache entries invalidated when solver semantics or schema versions change so stale or incompatible scenario data is never served.

**Why this priority**: Prevents correctness regressions after solver or data model updates.

**Independent Test**: Insert a cached scenario with outdated version metadata, request the same context under current version metadata, and verify stale entry is invalidated and recomputed.

**Acceptance Scenarios**:

1. **Given** cache entry metadata does not match active solver/config/schema signature, **When** that scenario is requested, **Then** the system bypasses stale data and performs a deterministic refresh path.
2. **Given** refreshed data is successfully computed, **When** stored, **Then** future requests use the new entry with current metadata.

---

### User Story 4 - Managed Offline Precompute Operations (Priority: P4)

As an operator, I want an offline precompute job that can run in batches, resume, and report progress/failures so scenario libraries can be prepared ahead of runtime use.

**Why this priority**: Operational readiness and resilience, while important, comes after runtime correctness and cache behavior.

**Independent Test**: Run offline precompute for a bounded scenario set, interrupt mid-run, resume, and verify idempotent completion with progress/error reporting.

**Acceptance Scenarios**:

1. **Given** a defined precompute scenario set, **When** offline job runs, **Then** it stores deterministic scenario payload records with lifecycle metadata.
2. **Given** an interrupted run, **When** resume is invoked, **Then** completed scenarios are not recomputed unnecessarily and remaining scenarios continue.

### Edge Cases

- Cache entry exists but schema version is stale.
- Cache entry exists but solver signature, runtime knobs, or policy signature differs from request.
- Offline job is interrupted mid-batch after partial writes.
- Cached payload row is corrupt or cannot be deserialized.
- Runtime fallback compute times out and must return deterministic timeout status.
- Concurrent readers/writers target the same scenario key.
- Runtime receives unsupported metric and must preserve deterministic missing semantics.
- Different selected positions map to equivalent solver semantics (same selected action/opponent count) and should reuse cache without context leakage.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support offline generation of full 169-cell AoF matrix payloads for supported browser scenarios.
- **FR-002**: System MUST persist scenario payloads in SQLite using SQLAlchemy-managed persistence.
- **FR-003**: Runtime retrieval MUST check persistent scenario cache before any on-demand computation.
- **FR-004**: If persistent cache has no valid entry, runtime MUST perform fallback compute and write successful results back to persistent cache.
- **FR-005**: Cache keys MUST include full scenario-defining context and policy-signature metadata that can affect output values.
- **FR-006**: System MUST implement deterministic invalidation when schema version, solver signature, or runtime policy signature changes.
- **FR-007**: System MUST preserve existing matrix payload contract consumed by UI (`context`, `cells[169]`, `status_message`).
- **FR-008**: System MUST preserve deterministic status semantics for `AVAILABLE`, `MISSING`, `NO_CONTEST`, `TIMEOUT`, and `ERROR`.
- **FR-009**: System MUST NOT silently substitute synthetic/heuristic payloads in normal operation when exact or cached data is unavailable.
- **FR-010**: Offline precompute workflow MUST support resumable, idempotent operation for partially completed runs.
- **FR-011**: System MUST expose operational visibility for cache hits, misses, stale invalidation, fallback compute, timeout, and failure outcomes.
- **FR-012**: Runtime DB operations MUST safely handle repeated context toggles and concurrent access patterns without data corruption.
- **FR-013**: Standalone AoF browser MUST remain decoupled from simulator workflow.
- **FR-014**: Automated tests MUST cover schema behavior, cache hit/miss, versioned invalidation, corruption handling, timeout/error fallback, and offline resume/idempotency behavior.
- **FR-015**: System MUST support canonical solver-equivalence cache keying so semantically equivalent contexts reuse persisted matrix cells instead of recomputing.
- **FR-016**: Canonical key reuse MUST preserve request-local context in response payloads while keeping cell values/statuses deterministic.

### Key Entities *(include if feature involves data)*

- **Scenario Key**: Canonical identifier derived from selected position, position actions, metric, pot/bet parameters, runtime knobs, and policy signature.
- **Matrix Payload Record**: Persisted representation of UI-consumed `context + 169 cells + status_message` plus storage metadata.
- **Cache Lifecycle Metadata**: Version and validation fields including schema version, solver signature, runtime policy signature, creation/update timestamps, and stale flags.
- **Offline Job Run**: Batch execution record that tracks targeted scenario set, progress counts, resume cursor, and failure details.
- **Scenario Write Result**: Per-scenario outcome record indicating inserted, updated, skipped-as-current, or failed.

## Assumptions

- Supported scenario dimensions for offline precompute are bounded and operationally manageable.
- First-pass offline precompute scope is bounded to: selected_position in {UTG, BTN, SB, BB}; position_actions across all 16 FOLD/ALL_IN combinations; metric in {WIN_LOSE_PROBABILITY, EV, EQUITY, EQR}; strict_current_action in {false, true}; runtime knobs fixed to active defaults unless an explicit alternate precompute profile is requested.
- Persistent storage location and access permissions are available in target runtime environments.
- Existing runtime provider remains the sole matrix access surface for UI integration.
- Deterministic status behavior remains more important than returning partial non-deterministic values on failures.

## Dependencies

- Existing AoF browser provider contract and matrix rendering path.
- Existing solver-backed scenario compute path.
- SQLite runtime availability.
- SQLAlchemy module and migration-safe persistence conventions in project tooling.

## Risks

- **Storage Growth Risk**: Scenario cardinality can increase database size significantly.
- **Version Drift Risk**: Incomplete signature coverage could allow stale payload leakage.
- **Concurrency Risk**: Concurrent writes for identical keys may cause lock contention.
- **Operational Risk**: Offline precompute interruptions may leave partially complete datasets if lifecycle tracking is weak.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For scenarios present in persistent cache, p95 matrix retrieval time is <= 250 ms on reference environment over 200 repeated requests.
- **SC-002**: 100% of stale-version scenario requests are deterministically invalidated and refreshed before being served as current.
- **SC-003**: Offline-precomputed scenarios load without runtime timeout in >= 99% of requests under reference browsing workload.
- **SC-004**: Resume of interrupted offline precompute reprocesses <= 1% already completed scenarios for the same run scope.
- **SC-005**: Automated tests for cache lifecycle, invalidation, corruption handling, timeout/error fallback, and offline resume/idempotency all pass in CI.
