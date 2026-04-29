# Tasks: Precompute Orchestration Refactor

**Feature**: `001-refactor-precompute-runner`  
**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/orchestration-contract.md](contracts/orchestration-contract.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to (US1, US2, US3)
- File paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm baseline and create collaborator module stubs that all user stories depend on.

- [x] T001 Verify baseline targeted test suites pass: `tests/test_aof_precompute_runner.py`, `tests/test_precompute_runner_regression.py`, `tests/test_matrix_sweep_precompute_runner.py`, `tests/integration/test_precompute_runner_integration.py`
- [x] T002 Create `PrecomputeOrchestrationService` class stub in `python/hopilot/gto/precompute_orchestration.py`
- [x] T003 [P] Create `PrecomputeJobPersistenceService` class stub in `python/hopilot/gto/precompute_job_persistence.py`

**Checkpoint**: Both collaborator modules exist and are importable; baseline tests still pass

---

## Phase 2: User Story 1 — Stabilize Precompute Orchestration (Priority: P1) 🎯 MVP

**Goal**: Extract scenario orchestration, context resolution, sweep contract preparation, and failure classification from `AoFPrecomputeRunner.run()` into `PrecomputeOrchestrationService`. Refactor runner into a thin coordinator that delegates to the new collaborator.

**Independent Test**: Run `tests/test_precompute_runner_regression.py` and `tests/test_matrix_sweep_precompute_runner.py` after refactor; all must pass with no behavior changes.

### Tests for User Story 1

- [x] T004 [US1] Add unit tests for `PrecomputeOrchestrationService` scenario loop and context validation in `tests/test_precompute_orchestration.py`
- [x] T005 [P] [US1] Update `tests/test_precompute_runner_regression.py` to assert `PrecomputeOrchestrationService` is delegated to by `AoFPrecomputeRunner.run()`
- [x] T006 [P] [US1] Update `tests/test_matrix_sweep_precompute_runner.py` to assert orchestration collaborator delegation replaces inline runner logic

### Implementation for User Story 1

- [x] T007 [US1] Implement `PrecomputeOrchestrationService.orchestrate_scenarios()` by extracting scenario enumeration and loop logic from `AoFPrecomputeRunner.run()` in `python/hopilot/gto/precompute_orchestration.py`
- [x] T008 [US1] Implement `PrecomputeOrchestrationService.build_sweep_contract()` by extracting sweep contract preparation from `AoFPrecomputeRunner.run()` in `python/hopilot/gto/precompute_orchestration.py`
- [x] T009 [US1] Implement `PrecomputeOrchestrationService.record_scenario_failure()` by extracting failure boundary classification from `AoFPrecomputeRunner._persist_scenario_results()` in `python/hopilot/gto/precompute_orchestration.py`
- [x] T010 [US1] Refactor `AoFPrecomputeRunner.run()` to delegate scenario orchestration, contract preparation, and failure recording to `PrecomputeOrchestrationService` in `python/hopilot/gto/aof_precompute_runner.py`
- [x] T011 [US1] Run targeted tests: `tests/test_aof_precompute_runner.py`, `tests/test_precompute_runner_regression.py`, `tests/test_matrix_sweep_precompute_runner.py`

**Checkpoint**: User Story 1 is complete when all targeted regression and matrix sweep tests pass with orchestration delegated to `PrecomputeOrchestrationService`

---

## Phase 3: User Story 2 — Clarify Provider Context Contract (Priority: P2)

**Goal**: Remove `get_matrix_payload` fallback from scenario context resolution. Enforce direct-context-only policy in `PrecomputeOrchestrationService.resolve_scenario_context()` with explicit orchestration failure classification when direct context is unavailable.

**Independent Test**: Run `tests/test_precompute_runner_regression.py` and `tests/test_matrix_sweep_precompute_runner.py`; confirm `get_matrix_payload` is never called and explicit failure is raised for missing context.

### Tests for User Story 2

- [x] T012 [US2] Add unit test asserting explicit orchestration failure when provider cannot supply direct context (no fallback) in `tests/test_precompute_orchestration.py`
- [x] T013 [P] [US2] Update `tests/test_precompute_runner_regression.py` to assert `get_matrix_payload` is never called during scenario context resolution
- [x] T014 [P] [US2] Verify `tests/test_matrix_sweep_precompute_runner.py` existing `get_matrix_payload.assert_not_called()` assertion passes (no change needed if US1 preserved it)

### Implementation for User Story 2

- [x] T015 [US2] Implement `PrecomputeOrchestrationService.resolve_scenario_context()` with direct-context-only policy and explicit orchestration failure classification in `python/hopilot/gto/precompute_orchestration.py`
- [x] T016 [US2] Remove any remaining `get_matrix_payload` fallback references from `AoFPrecomputeRunner.run()` in `python/hopilot/gto/aof_precompute_runner.py`
- [x] T017 [US2] Run targeted tests: `tests/test_aof_precompute_runner.py`, `tests/test_precompute_runner_regression.py`, `tests/test_matrix_sweep_precompute_runner.py`

**Checkpoint**: User Story 2 is complete when context resolution uses the direct-only path, fallback is absent, and explicit failure is classified and covered by tests

---

## Phase 4: User Story 3 — Separate Persistence Responsibilities (Priority: P3)

**Goal**: Extract job session lifecycle, scenario run link state transitions, and progress counter persistence from `AoFPrecomputeRunner.run()` into `PrecomputeJobPersistenceService`. Refactor runner to delegate all persistence through the new collaborator while preserving existing semantics.

**Independent Test**: Run `tests/integration/test_precompute_runner_integration.py`; confirm completed/failed counters, link states, and terminal job state remain correct after persistence logic moves to dedicated collaborator.

### Tests for User Story 3

- [x] T018 [US3] Add unit tests for `PrecomputeJobPersistenceService` link state transitions (`PENDING→RUNNING→COMPLETED`, `PENDING→RUNNING→FAILED`) and job finalization (`COMPLETED`, `FAILED`, `CANCELED`) in `tests/test_precompute_job_persistence.py`
- [x] T019 [P] [US3] Update `tests/integration/test_precompute_runner_integration.py` to assert persistence collaborator controls all link and job state transitions

### Implementation for User Story 3

- [x] T020 [US3] Implement `PrecomputeJobPersistenceService.create_job_session()` and `update_job_progress()` in `python/hopilot/gto/precompute_job_persistence.py`
- [x] T021 [US3] Implement `PrecomputeJobPersistenceService.create_scenario_link()`, `mark_link_running()`, `mark_link_completed()`, and `mark_link_failed()` with required failure boundary and result ID semantics in `python/hopilot/gto/precompute_job_persistence.py`
- [x] T022 [US3] Implement `PrecomputeJobPersistenceService.finalize_job()` with `COMPLETED`/`FAILED`/`CANCELED` terminal state rules per contract in `python/hopilot/gto/precompute_job_persistence.py`
- [x] T023 [US3] Refactor `AoFPrecomputeRunner.run()` to delegate all persistence operations to `PrecomputeJobPersistenceService` in `python/hopilot/gto/aof_precompute_runner.py`
- [x] T024 [US3] Run targeted tests: `tests/integration/test_precompute_runner_integration.py` and full targeted suite

**Checkpoint**: User Story 3 is complete when all persistence is handled by `PrecomputeJobPersistenceService` and integration tests confirm unchanged behavior

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and thin-coordinator confirmation across all stories.

- [x] T025 [P] Run full targeted test suite confirming all success criteria (SC-001 through SC-005) in `tests/`
- [x] T026 [P] Execute `quickstart.md` verification commands and confirm all expected outcomes pass
- [x] T027 [P] Audit `python/hopilot/gto/aof_precompute_runner.py` to confirm it is a thin coordinator with no inline persistence, context resolution, or scenario orchestration logic

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **User Story 1 (Phase 2)**: Depends on Phase 1 stubs — BLOCKS US2 (US2 extends `resolve_scenario_context()` introduced in US1)
- **User Story 2 (Phase 3)**: Depends on US1 completing `PrecomputeOrchestrationService` skeleton
- **User Story 3 (Phase 4)**: Depends on Phase 1 stubs only; can run concurrently with US2 once US1 runner delegation is in place
- **Polish (Phase 5)**: Depends on all user stories complete

### User Story Dependencies

| Story | Depends On | Can Parallelize With |
|-------|-----------|----------------------|
| US1 (P1) | Phase 1 complete | — |
| US2 (P2) | US1 complete | US3 (Phase 4) |
| US3 (P3) | Phase 1 complete, US1 runner delegation | US2 (Phase 3) |

### Within Each User Story

- Tests written before implementation (T004-T006 before T007-T010; T018-T019 before T020-T023)
- Context resolution before sweep contract (US1: T007 before T008)
- Link creation before finalization (US3: T020-T021 before T022)
- Core implementation before runner delegation (US1: T007-T009 before T010; US3: T020-T022 before T023)

---

## Parallel Execution Examples

### Phase 1

```powershell
# T002 and T003 in parallel (different files)
# Create both stubs simultaneously
```

### User Story 1

```powershell
# T005 and T006 in parallel (different test files)
# T008 and T009 can be developed in parallel (different methods, same file - coordinate)
```

### User Story 2

```powershell
# T013 and T014 in parallel (different test files)
```

### User Story 3

```powershell
# T018 and T019 in parallel (different test files)
# T020, T021, T022 are sequential — session → links → finalization
```

### Polish

```powershell
# T025, T026, T027 fully parallel — independent validation steps
```

---

## Implementation Strategy

**MVP scope**: Complete User Story 1 (Phase 2) — delivers the core decomposition value, produces independently testable `PrecomputeOrchestrationService`, and unblocks US2 and US3.

**Incremental delivery order**:
1. **Phase 1** (T001–T003): Baseline confirmed, module stubs importable
2. **Phase 2 / US1** (T004–T011): Runner delegates orchestration; regression tests pass
3. **Phase 3 / US2** (T012–T017): No payload fallback; explicit failure tested
4. **Phase 4 / US3** (T018–T024): Runner delegates persistence; integration tests pass
5. **Phase 5** (T025–T027): Full suite passes, thin coordinator confirmed

Each phase is verifiable using the commands in [quickstart.md](quickstart.md).

---

## Summary

| Phase | Tasks | User Story | Key Deliverable |
|-------|-------|-----------|----------------|
| Phase 1: Setup | T001–T003 | — | Stubs importable, baseline confirmed |
| Phase 2: US1 | T004–T011 | US1 (P1) | `PrecomputeOrchestrationService` delegates orchestration |
| Phase 3: US2 | T012–T017 | US2 (P2) | Direct-context-only policy enforced |
| Phase 4: US3 | T018–T024 | US3 (P3) | `PrecomputeJobPersistenceService` owns all persistence |
| Phase 5: Polish | T025–T027 | — | All success criteria confirmed |
| **Total** | **27 tasks** | **3 stories** | |
