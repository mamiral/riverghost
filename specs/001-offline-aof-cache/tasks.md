# Tasks: Offline AoF Matrix Precomputation and SQLite Scenario Cache

**Input**: Design documents from `/specs/001-offline-aof-cache/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare persistence dependencies, module scaffolding, and baseline configuration.

- [X] T001 Add SQLAlchemy dependency in requirements.txt
- [X] T002 Create cache DB module scaffold in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T003 [P] Create cache ORM model scaffold in python/hopilot/gto/aof_scenario_cache_models.py
- [X] T004 [P] Create offline precompute runner scaffold in python/hopilot/gto/aof_precompute_runner.py
- [X] T005 [P] Add cache/runtime signature config defaults in config/gto_defaults.yaml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement core schema, keying, serialization, and lifecycle primitives used by all stories.

**CRITICAL**: No user story implementation starts before this phase completes.

- [X] T006 Implement canonical scenario-key builder in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T007 [P] Implement payload JSON serialization and deserialization helpers in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T008 [P] Implement SQLAlchemy engine/session factory for SQLite in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T009 Implement cache tables (payload, metadata, precompute run, write result) in python/hopilot/gto/aof_scenario_cache_models.py
- [X] T010 [P] Implement schema version bootstrap and validation in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T011 Implement metadata-signature validation helper in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T012 [P] Implement structured cache lifecycle logging helpers in python/hopilot/gto/aof_scenario_cache_store.py

**Checkpoint**: Cache foundation complete; user story work can begin.

---

## Phase 3: User Story 1 - Fast Cached Matrix Loads (Priority: P1) 🎯 MVP

**Goal**: Return matrix payloads from persistent SQLite cache for current scenarios.

**Independent Test**: Precompute a scenario, restart runtime provider, request same scenario, and confirm deterministic payload comes from persistent cache.

### Tests for User Story 1

- [X] T013 [P] [US1] Add cache-hit retrieval tests in tests/test_aof_scenario_cache_runtime.py
- [X] T014 [P] [US1] Add cross-restart persistence tests in tests/test_aof_scenario_cache_runtime.py
- [X] T015 [P] [US1] Add store contract shape tests for context/cells/status_message in tests/test_aof_scenario_cache_store.py

### Implementation for User Story 1

- [X] T016 [US1] Implement cache read API by scenario key in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T017 [US1] Integrate cache-first lookup into provider request path in python/hopilot/gto/aof_browser_data_provider.py
- [X] T018 [US1] Implement payload hydration from stored JSON to runtime payload in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T019 [US1] Emit cache-hit and cache-miss logs in provider flow in python/hopilot/gto/aof_browser_data_provider.py

**Checkpoint**: US1 delivers fast persistent cache retrieval for current entries.

---

## Phase 4: User Story 2 - Reliable Fallback and Write-Back (Priority: P2)

**Goal**: On cache miss, compute deterministically, return payload, and persist successful result.

**Independent Test**: Trigger cache miss, verify fallback compute path and write-back, then confirm subsequent request is cache-hit.

### Tests for User Story 2

- [X] T020 [P] [US2] Add cache-miss fallback compute tests in tests/test_aof_scenario_cache_runtime.py
- [X] T021 [P] [US2] Add write-back success tests for miss->hit transition in tests/test_aof_scenario_cache_runtime.py
- [X] T022 [P] [US2] Add timeout/error no-invalid-write tests in tests/test_aof_scenario_cache_runtime.py
- [X] T051 [P] [US2] Add concurrent read/write same-key stress tests under repeated toggles in tests/test_aof_scenario_cache_concurrency.py
- [X] T052 [P] [US2] Add concurrent writer contention/upsert validity tests in tests/test_aof_scenario_cache_concurrency.py

### Implementation for User Story 2

- [X] T023 [US2] Implement cache write-upsert API for current payload records in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T024 [US2] Add provider write-back after successful fallback compute in python/hopilot/gto/aof_browser_data_provider.py
- [X] T025 [US2] Enforce deterministic TIMEOUT/ERROR return without writing invalid current payload in python/hopilot/gto/aof_browser_data_provider.py
- [X] T026 [US2] Add transactional upsert protection for concurrent same-key writes in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T053 [US2] Implement lock/retry transaction policy for concurrent same-key reads/writes in python/hopilot/gto/aof_scenario_cache_store.py

**Checkpoint**: US2 delivers deterministic miss handling with persistent write-back.

---

## Phase 5: User Story 3 - Safe Versioned Invalidation (Priority: P3)

**Goal**: Prevent stale records from being served when schema/signatures drift.

**Independent Test**: Seed stale metadata for an existing scenario, request it, and verify invalidation plus deterministic refresh behavior.

### Tests for User Story 3

- [X] T027 [P] [US3] Add stale schema/signature invalidation tests in tests/test_aof_scenario_cache_invalidation.py
- [X] T028 [P] [US3] Add corrupt payload deserialization handling tests in tests/test_aof_scenario_cache_invalidation.py
- [X] T029 [P] [US3] Add stale->refresh->current lifecycle tests in tests/test_aof_scenario_cache_invalidation.py

### Implementation for User Story 3

- [X] T030 [US3] Implement stale record detection and stale_reason mapping in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T031 [US3] Integrate stale bypass and refresh path into provider retrieval flow in python/hopilot/gto/aof_browser_data_provider.py
- [X] T032 [US3] Implement corrupt-row guard and deterministic miss fallback behavior in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T033 [US3] Persist and compare runtime_signature/policy_signature/solver_signature metadata in python/hopilot/gto/aof_scenario_cache_store.py

**Checkpoint**: US3 guarantees deterministic invalidation and safe refresh behavior.

---

## Phase 6: User Story 4 - Managed Offline Precompute Operations (Priority: P4)

**Goal**: Provide resumable idempotent offline generation and persistence for scenario sets.

**Independent Test**: Run bounded offline precompute set, interrupt, resume, and verify completed-current scenarios are skipped while remaining scenarios complete.

### Tests for User Story 4

- [X] T034 [P] [US4] Add precompute run lifecycle tests in tests/test_aof_precompute_runner.py
- [X] T035 [P] [US4] Add resume-cursor continuation tests in tests/test_aof_precompute_runner.py
- [X] T036 [P] [US4] Add idempotent SKIPPED_CURRENT behavior tests in tests/test_aof_precompute_runner.py

### Implementation for User Story 4

- [X] T037 [US4] Implement scenario-set enumerator for offline jobs in python/hopilot/gto/aof_precompute_runner.py
- [X] T038 [US4] Implement run metadata persistence (start/progress/finish/failure) in python/hopilot/gto/aof_precompute_runner.py
- [X] T039 [US4] Implement resumable processing with cursor/checkpointing in python/hopilot/gto/aof_precompute_runner.py
- [X] T040 [US4] Implement per-scenario write-result outcomes (INSERTED/UPDATED/SKIPPED_CURRENT/FAILED) in python/hopilot/gto/aof_precompute_runner.py
- [X] T041 [US4] Add offline execution entrypoint for operators in python/hopilot/gto/aof_precompute_cli.py

**Checkpoint**: US4 provides operational offline precompute with resume and idempotency.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, observability validation, and documentation.

- [X] T042 [P] Update quickstart for offline precompute execution and validation evidence in specs/001-offline-aof-cache/quickstart.md
- [X] T043 [P] Update cache contract details after implementation in specs/001-offline-aof-cache/contracts/aof-scenario-cache-contract.md
- [X] T044 [P] Add SQLAlchemy cache usage notes to docs/initial_design/USAGE_GUIDE_WIN.md
- [X] T045 Run and document full target test evidence in specs/001-offline-aof-cache/quickstart.md
- [X] T046 Verify standalone AoF decoupling remains intact in tests/test_poker_simulator_gui.py
- [X] T047 Perform final logging cleanup for cache/precompute observability in python/hopilot/gto/aof_browser_data_provider.py
- [X] T048 [P] Add cached-retrieval performance benchmark (200 repeated requests) with p95 <= 250 ms assertion in tests/test_aof_scenario_cache_performance.py
- [X] T049 [P] Add offline-precomputed load reliability benchmark with timeout-free rate >= 99% in tests/test_aof_scenario_cache_reliability.py
- [X] T050 Record SC-001 and SC-003 benchmark evidence in specs/001-offline-aof-cache/quickstart.md
- [X] T054 [P] Add observability contract tests for required cache lifecycle events and minimum fields in tests/test_aof_scenario_cache_observability.py

### Canonical Solver-Equivalence Optimization

- [X] T055 Implement canonical solver-equivalence persistent key builder in python/hopilot/gto/aof_browser_data_provider.py
- [X] T056 Integrate provider persistent read/write path to use canonical key while preserving request-local context in responses
- [X] T057 [P] Update precompute runner to use canonical keying for deduplicated writes in python/hopilot/gto/aof_precompute_runner.py
- [X] T058 [P] Add runtime test proving seat-label-equivalent contexts reuse persistent cache without recomputation in tests/test_aof_scenario_cache_runtime.py
- [X] T059 Update quickstart/contract validation evidence for canonical dedup behavior in specs/001-offline-aof-cache/quickstart.md and specs/001-offline-aof-cache/contracts/aof-scenario-cache-contract.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 (Setup): no dependencies.
- Phase 2 (Foundational): depends on Phase 1 and blocks all user stories.
- Phases 3-6 (User Stories): start only after Phase 2 checkpoint.
- Phase 7 (Polish): depends on completion of desired user stories.

### User Story Dependencies

- US1 (P1): starts after Foundational and delivers MVP cache retrieval.
- US2 (P2): depends on US1 cache retrieval path and adds miss fallback/write-back.
- US3 (P3): depends on US1/US2 persistence path and adds versioned invalidation safety.
- US4 (P4): depends on foundational persistence primitives and can proceed after US2.

### Within Each User Story

- Tests should be authored first and fail before implementation.
- Store/model updates before provider integration for each story.
- Story checkpoint must pass before moving to the next priority.

### Parallel Opportunities

- Setup: T003, T004, T005 can run in parallel.
- Foundational: T007, T008, T010, T012 can run in parallel.
- US1 tests: T013-T015 can run in parallel.
- US2 tests: T020-T022 can run in parallel.
- US2 tests: T020-T022, T051, T052 can run in parallel.
- US3 tests: T027-T029 can run in parallel.
- US4 tests: T034-T036 can run in parallel.
- Polish docs/perf: T042-T044, T048, T049, T054 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Run these in parallel:
T013 tests/test_aof_scenario_cache_runtime.py
T014 tests/test_aof_scenario_cache_runtime.py
T015 tests/test_aof_scenario_cache_store.py
```

## Parallel Example: User Story 2

```bash
# Run these in parallel:
T020 tests/test_aof_scenario_cache_runtime.py
T021 tests/test_aof_scenario_cache_runtime.py
T022 tests/test_aof_scenario_cache_runtime.py
```

## Parallel Example: User Story 4

```bash
# Run these in parallel:
T034 tests/test_aof_precompute_runner.py
T035 tests/test_aof_precompute_runner.py
T036 tests/test_aof_precompute_runner.py
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 (Phase 3).
3. Validate persistent cache retrieval across restart.
4. Demo MVP with cache-hit observability.

### Incremental Delivery

1. Deliver US1 cache retrieval baseline.
2. Deliver US2 deterministic miss fallback and write-back.
3. Deliver US3 safe invalidation/corruption handling.
4. Deliver US4 offline resumable precompute operations.
5. Finish polish and validation evidence.

### Team Parallelization Strategy

1. One contributor implements SQLAlchemy schema/store foundation.
2. One contributor integrates provider runtime read/write path and invalidation checks.
3. One contributor builds offline precompute runner and operator entrypoint.
4. One contributor leads contract/integration testing and docs evidence.
