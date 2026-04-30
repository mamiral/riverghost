# Tasks: Database Repository Refactor

**Input**: Design documents from `/specs/001-refactor-database-repository/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Regression gates are required by spec (FR-015): targeted suites per migration step and full suite before merge.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare repository scaffolding and migration guardrails.

- [X] T001 Create repository split module stubs in `python/hopilot/gto/game_state_repository.py`, `python/hopilot/gto/simulation_repository.py`, `python/hopilot/gto/precompute_job_repository.py`, and `python/hopilot/gto/analytics_repository.py`
- [X] T002 Create shared unit-of-work helper in `python/hopilot/gto/unit_of_work.py`
- [X] T003 [P] Add repository boundary notes and migration assumptions to `specs/001-refactor-database-repository/contracts/repository-boundaries.md`
- [X] T004 [P] Add migration test command set to `specs/001-refactor-database-repository/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish core cross-story infrastructure required before user-story migrations.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [X] T005 Implement sync-only repository base protocol/interfaces in `python/hopilot/gto/repository_interfaces.py`
- [X] T006 Implement shared session orchestration in `python/hopilot/gto/unit_of_work.py` with context-managed transaction behavior
- [X] T007 Implement domain validation helpers in `python/hopilot/gto/repository_validation.py` replacing dummy payload update-validation pattern
- [X] T008 [P] Add unit tests for shared unit-of-work behavior in `tests/test_repository_unit_of_work.py`
- [X] T009 [P] Add unit tests for validation helpers in `tests/test_repository_validation.py`
- [X] T010 Fix `self.db_connection` usage defects in `python/hopilot/gto/database_repository.py` to use one consistent connection path

**Checkpoint**: Shared transaction, validation, and interface foundations are in place.

---

## Phase 3: User Story 1 - Isolate Persistence Domains (Priority: P1) 🎯 MVP

**Goal**: Split monolithic repository ownership into domain repositories while preserving behavior.

**Independent Test**: Domain repositories can execute core write/tracking/query paths with unchanged outputs against existing fixtures.

### Tests for User Story 1

- [X] T011 [P] [US1] Add domain split write regression tests in `tests/test_database_repository_domain_split.py`
- [X] T012 [P] [US1] Add precompute job tracking repository tests in `tests/test_precompute_job_repository.py`
- [X] T013 [P] [US1] Add simulation/matrix repository tests in `tests/test_simulation_repository.py`
- [X] T014 [P] [US1] Add analytics repository query equivalence tests in `tests/test_analytics_repository.py`

### Implementation for User Story 1

- [X] T015 [US1] Implement `GameStateRepository` in `python/hopilot/gto/game_state_repository.py` by moving raw game-state/player/bet/jackpot CRUD and bulk-write logic
- [X] T016 [US1] Implement `SimulationRepository` in `python/hopilot/gto/simulation_repository.py` by moving simulation/matrix persistence and contract-run lookup logic
- [X] T017 [US1] Implement `PrecomputeJobRepository` in `python/hopilot/gto/precompute_job_repository.py` by moving precompute session/scenario-link lifecycle logic
- [X] T018 [US1] Implement `AnalyticsRepository` in `python/hopilot/gto/analytics_repository.py` by moving matrix/query projection logic
- [X] T019 [US1] Refactor `python/hopilot/gto/database_repository.py` into delegating compatibility facade over new repositories
- [X] T020 [US1] Update `python/hopilot/gto/precompute_job_persistence.py` to consume `PrecomputeJobRepository` and shared unit-of-work
- [X] T021 [US1] Update `python/hopilot/gto/aof_precompute_runner.py` to consume `SimulationRepository`/`PrecomputeJobRepository` through sync interfaces
- [X] T022 [US1] Run targeted gate suite for US1 scope in `tests/test_database_repository.py`, `tests/test_database_repository_writes.py`, `tests/test_precompute_job_persistence.py`, and `tests/test_precompute_runner_regression.py`

**Checkpoint**: Domain split exists, trigger consumers migrated, behavior preserved in targeted tests.

---

## Phase 4: User Story 2 - Preserve Consumer Compatibility During Migration (Priority: P2)

**Goal**: Migrate remaining key consumers safely and remove compatibility facade at the required trigger point.

**Independent Test**: Migrated and remaining consumers continue to pass integration/contract tests through migration.

### Tests for User Story 2

- [X] T023 [P] [US2] Add provider compatibility migration tests in `tests/test_browser_database_provider_migration.py`
- [X] T024 [P] [US2] Extend integration coverage for mixed-consumer migration in `tests/integration/test_browser_database_provider_integration.py`
- [X] T025 [P] [US2] Extend contract coverage for repository boundary split in `tests/contract/test_provider_contract_split.py`

### Implementation for User Story 2

- [X] T026 [US2] Update `python/hopilot/gto/browser_database_provider.py` to consume split repositories/services without async repository calls
- [X] T027 [US2] Update `python/hopilot/gto/normalized_db_provider.py` and `python/hopilot/gto/game_replay_queries.py` to use new domain boundaries
- [X] T028 [US2] Update `python/hopilot/gto/matrix_cells_derivation.py` and `python/hopilot/gto/incremental_aggregation.py` to consume domain repositories
- [X] T029 [US2] Remove compatibility facade implementation from `python/hopilot/gto/database_repository.py` once trigger migration (`aof_precompute_runner.py` + `precompute_job_persistence.py`) is confirmed complete
- [X] T030 [US2] Update imports/call sites referencing `DatabaseRepository` in runtime modules under `python/hopilot/gto/`
- [X] T031 [US2] Run targeted gate suite for US2 scope in `tests/contract/test_precompute_runner_contracts.py`, `tests/contract/test_provider_contract_split.py`, `tests/integration/test_precompute_runner_integration.py`, and `tests/integration/test_browser_database_provider_integration.py`

**Checkpoint**: Consumers migrated and compatibility facade removed per FR-012/FR-013.

---

## Phase 5: User Story 3 - Improve Testability and Defect Isolation (Priority: P3)

**Goal**: Ensure failures are localized per domain and regression diagnostics remain explicit.

**Independent Test**: Intentionally breaking one repository domain fails only that domain’s tests while others remain green.

### Tests for User Story 3

- [X] T032 [P] [US3] Add failure-localization tests for domain boundaries in `tests/test_repository_failure_isolation.py`
- [X] T033 [P] [US3] Add transaction atomicity tests for coupled write paths in `tests/test_repository_transaction_atomicity.py`
- [X] T034 [P] [US3] Add diagnostics attribution tests in `tests/test_repository_diagnostics.py`

### Implementation for User Story 3

- [X] T035 [US3] Add explicit domain-scoped exception mapping/logging in `python/hopilot/gto/game_state_repository.py`, `python/hopilot/gto/simulation_repository.py`, `python/hopilot/gto/precompute_job_repository.py`, and `python/hopilot/gto/analytics_repository.py`
- [X] T036 [US3] Remove dead transitional code and stale adapter paths in `python/hopilot/gto/database_repository.py` and `python/hopilot/gto/repository_interfaces.py`
- [X] T037 [US3] Update developer-facing migration notes in `specs/001-refactor-database-repository/quickstart.md` and `specs/001-refactor-database-repository/contracts/repository-boundaries.md`
- [X] T038 [US3] Run targeted gate suite for US3 scope in `tests/test_repository_unit_of_work.py`, `tests/test_repository_validation.py`, and new US3 test files

**Checkpoint**: Domain isolation and diagnostics requirements are verifiably satisfied.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening and merge gate validation.

- [X] T039 [P] Run final full regression gate with `pytest tests/` from repository root
- [X] T040 [P] Validate quickstart commands and update any command drift in `specs/001-refactor-database-repository/quickstart.md`
- [X] T041 Remove obsolete repository references from docs in `plans/database_repository_refactor_plan.md` and `specs/001-refactor-database-repository/plan.md`
- [X] T042 Produce final migration summary in `specs/001-refactor-database-repository/research.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories
- **Phase 3 (US1)**: Depends on Phase 2; forms MVP
- **Phase 4 (US2)**: Depends on Phase 3 trigger migration for facade removal
- **Phase 5 (US3)**: Depends on Phases 3 and 4 domain boundary completion
- **Phase 6 (Polish)**: Depends on all user story phases

### User Story Dependencies

- **US1 (P1)**: Starts after foundational phase; no dependency on other stories
- **US2 (P2)**: Starts after US1 because facade removal trigger is defined by US1 migration tasks
- **US3 (P3)**: Starts after US1/US2 to validate final boundary behavior and diagnostics

### Within Each User Story

- Write/enable tests first for story scope
- Implement domain/module changes
- Run targeted regression gate for that story
- Mark checkpoint complete before next story

### Parallel Opportunities

- Phase 1: T003, T004 can run in parallel after T001/T002
- Phase 2: T008 and T009 can run in parallel after T005-T007
- US1: T011-T014 can run in parallel; T015-T018 can run in parallel by repository file
- US2: T023-T025 can run in parallel; T027 and T028 can run in parallel
- US3: T032-T034 can run in parallel
- Polish: T039 and T040 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Parallel tests
Task: T011 tests/test_database_repository_domain_split.py
Task: T012 tests/test_precompute_job_repository.py
Task: T013 tests/test_simulation_repository.py
Task: T014 tests/test_analytics_repository.py

# Parallel repository implementations
Task: T015 python/hopilot/gto/game_state_repository.py
Task: T016 python/hopilot/gto/simulation_repository.py
Task: T017 python/hopilot/gto/precompute_job_repository.py
Task: T018 python/hopilot/gto/analytics_repository.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (US1)
3. Validate with targeted US1 regression gate
4. Stop and verify boundary split + trigger consumer migration

### Incremental Delivery

1. Deliver US1 split and trigger migration
2. Deliver US2 downstream consumer migration + facade removal
3. Deliver US3 isolation/diagnostics hardening
4. Run full-suite gate before merge

### Parallel Team Strategy

1. One engineer on foundational infra (Phase 2)
2. After foundation:
   - Engineer A: Raw + simulation repositories (US1)
   - Engineer B: Tracking + analytics repositories (US1)
   - Engineer C: Test scaffolding and regression gates
3. Re-converge for US2 consumer migrations and facade removal

---

## Notes

- `[P]` tasks touch different files and have no unmet dependencies.
- Every story phase contains independent validation criteria and targeted test gates.
- Regression policy from spec is enforced: targeted suites during migration, full suite before merge.
- Task IDs are execution ordered; dependencies may prevent some later IDs from starting immediately.
