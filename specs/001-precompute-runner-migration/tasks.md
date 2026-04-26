# Tasks: Precompute Runner Sweep Delegation

**Input**: Design documents from `/specs/001-precompute-runner-migration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included because the specification requires automated validation of delegated execution, persisted outputs, lifecycle compatibility, and failure boundaries.

**Organization**: Tasks are grouped by user story so each story can be implemented and verified independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare migration scaffolding and baseline test targets.

- [x] T001 Create migration notes and scope guardrails in specs/001-precompute-runner-migration/quickstart.md
- [x] T002 Add focused test module scaffold for runner migration in tests/integration/test_precompute_runner_migration_integration.py
- [x] T003 [P] Add contract test scaffold for orchestration and lifecycle payloads in tests/contract/test_precompute_runner_contracts.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared persistence and repository primitives required by all user stories.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [x] T004 Add precompute job session ORM model in python/hopilot/models/precompute_job_session.py
- [x] T005 [P] Add scenario run link ORM model with failure-boundary fields in python/hopilot/models/scenario_run_link.py
- [x] T006 Register new ORM models and exports in python/hopilot/models/__init__.py
- [x] T007 Add repository persistence/query methods for job sessions and scenario links in python/hopilot/gto/database_repository.py
- [x] T008 [P] Add migration-safe enum/constants for phase and boundary classification in python/hopilot/gto/matrix_sweep_contract.py
- [x] T009 Add repository integration tests for job-session and scenario-link persistence in tests/test_database_repository.py

**Checkpoint**: Foundation ready. User story implementation can proceed.

---

## Phase 3: User Story 1 - Run Precompute Jobs Through Sweep Pipeline (Priority: P1) 🎯 MVP

**Goal**: Delegate each precompute scenario to production sweep service and persist scenario-to-simulation linkage.

**Independent Test**: Execute a multi-scenario precompute job and verify each scenario delegates to sweep, persists Simulation/HandMatrix output, and stores durable scenario link rows.

### Tests for User Story 1

- [x] T010 [P] [US1] Add unit test for direct scenario delegation to sweep service in tests/test_aof_precompute_runner.py
- [x] T011 [P] [US1] Add integration test validating persisted Simulation/HandMatrix outputs per scenario in tests/integration/test_precompute_runner_migration_integration.py
- [x] T012 [US1] Add contract test verifying required success output fields (simulation_id, matrix_id, status) in tests/contract/test_precompute_runner_contracts.py

### Implementation for User Story 1

- [x] T013 [US1] Refactor precompute execution path to call MatrixSweepService.run_sweep per scenario in python/hopilot/gto/aof_precompute_runner.py
- [x] T014 [US1] Remove dead-schema scenario write path (cell_id GameState, board-card, bet, jackpot artifact creation) from delegated flow in python/hopilot/gto/aof_precompute_runner.py
- [x] T015 [US1] Persist ScenarioRunLink records on pending/running/completed transitions in python/hopilot/gto/aof_precompute_runner.py
- [x] T016 [US1] Persist UI job metadata to Simulation linkage fields via repository calls in python/hopilot/gto/database_repository.py
- [x] T017 [US1] Update precompute CLI result formatting to include scenario-to-simulation mappings in python/hopilot/gto/aof_precompute_cli.py

**Checkpoint**: User Story 1 delivers delegated sweep execution with persisted outputs and durable linkage.

---

## Phase 4: User Story 2 - Preserve Lifecycle and Progress Visibility (Priority: P2)

**Goal**: Keep lifecycle semantics stable while reporting scenario-phase progress for delegated execution.

**Independent Test**: Run a delegated job and verify lifecycle states remain compatible and progress snapshots include scenario counts, active scenario identity, and phase.

### Tests for User Story 2

- [x] T018 [P] [US2] Add unit tests for lifecycle state compatibility during delegated runs in tests/test_aof_precompute_runner.py
- [x] T019 [P] [US2] Add contract tests for progress payload shape and monotonic counters in tests/contract/test_precompute_runner_contracts.py
- [x] T020 [P] [US2] Add integration test validating GUI-facing terminal lifecycle outcomes for delegated jobs in tests/integration/test_precompute_runner_integration.py

### Implementation for User Story 2

- [x] T021 [US2] Implement scenario-phase progress snapshots (orchestration/solver_write/aggregation/finalizing) in python/hopilot/gto/aof_precompute_runner.py
- [x] T022 [US2] Preserve existing GuiRunState transitions while adapting progress internals for scenario sweep execution in python/hopilot/gto/aof_precompute_runner.py
- [x] T023 [US2] Expose progress snapshot fields through runner public status payloads in python/hopilot/gto/aof_precompute_runner.py

**Checkpoint**: User Story 2 preserves state-driven compatibility while improving phase-aware progress visibility.

---

## Phase 5: User Story 3 - Enforce Failure Boundaries and Recovery Behavior (Priority: P3)

**Goal**: Classify failures by execution boundary and enforce cooperative cancellation without automatic retries.

**Independent Test**: Inject orchestration, solver_write, and aggregation failures and verify boundary-classified failure persistence, partial success retention, and cooperative cancellation semantics.

### Tests for User Story 3

- [x] T024 [P] [US3] Add unit tests for boundary classification mapping and no-retry behavior in tests/test_aof_precompute_runner.py
- [x] T025 [P] [US3] Add integration tests for mixed scenario outcomes and partial success persistence in tests/integration/test_precompute_runner_integration.py
- [x] T026 [US3] Add integration test for cooperative cancellation (stop dispatch, allow in-flight completion) in tests/integration/test_precompute_runner_integration.py

### Implementation for User Story 3

- [x] T027 [US3] Implement phase-boundary failure classification and persistence on ScenarioRunLink rows in python/hopilot/gto/aof_precompute_runner.py
- [x] T028 [US3] Enforce cooperative cancellation dispatch gating in delegated execution loop in python/hopilot/gto/aof_precompute_runner.py
- [x] T029 [US3] Ensure no automatic retries are introduced for failed scenarios in python/hopilot/gto/aof_precompute_runner.py
- [x] T030 [US3] Surface boundary-classified diagnostics in runner completion artifacts in python/hopilot/gto/aof_precompute_cli.py

**Checkpoint**: User Story 3 provides deterministic failure boundaries, cancellation semantics, and manual-retry-ready diagnostics.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality and migration hardening across stories.

- [x] T031 [P] Update migration documentation and operational troubleshooting notes in specs/001-precompute-runner-migration/quickstart.md
- [x] T032 Remove obsolete runner helper methods and dead imports created by legacy write-path removal in python/hopilot/gto/aof_precompute_runner.py
- [x] T033 Run full migration verification test suite and capture expected command in specs/001-precompute-runner-migration/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Setup completion and blocks all user stories.
- User Story phases (Phase 3-5): depend on Foundational completion.
- Polish (Phase 6): depends on all targeted user stories complete.

### User Story Dependencies

- US1 (P1): starts immediately after Foundational and is the MVP slice.
- US2 (P2): depends on US1 runner delegation path because lifecycle/progress behavior wraps delegated execution.
- US3 (P3): depends on US1 delegated execution and US2 progress/lifecycle plumbing for boundary visibility.

### Within Each User Story

- Write tests first and confirm they fail before implementation tasks.
- Runner delegation and persistence wiring before CLI/reporting updates.
- Failure/cancellation logic before final diagnostics formatting.

## Parallel Opportunities

- Setup: T003 can run in parallel with T001-T002.
- Foundational: T005 and T008 can run in parallel once T004 starts.
- US1: T010 and T011 can run in parallel; implementation T013/T014 precedes T015-T017.
- US2: T018 and T019 can run in parallel; T021/T022 precede T023.
- US3: T024 and T025 can run in parallel; T027/T028 can be split by team members after tests are in place.
- Polish: T031 and T032 can run in parallel.

## Parallel Example: User Story 1

```bash
# Parallel test authoring
Task: T010 tests/test_aof_precompute_runner.py
Task: T011 tests/integration/test_precompute_runner_migration_integration.py

# Parallel model/repository support after delegation refactor lands
Task: T015 python/hopilot/gto/aof_precompute_runner.py
Task: T016 python/hopilot/gto/database_repository.py
```

## Parallel Example: User Story 2

```bash
# Parallel contract + unit test updates
Task: T018 tests/test_aof_precompute_runner.py
Task: T019 tests/contract/test_precompute_runner_contracts.py
```

## Parallel Example: User Story 3

```bash
# Parallel failure-path coverage
Task: T024 tests/test_aof_precompute_runner.py
Task: T025 tests/integration/test_precompute_runner_migration_integration.py
```

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Setup and Foundational phases.
2. Complete US1 delegation and persistence linkage tasks.
3. Validate US1 independently with T010-T012 and integration assertions.
4. Demo delegated precompute runs producing Simulation/HandMatrix outputs.

### Incremental Delivery

1. Deliver US1 (delegation and persisted mapping).
2. Deliver US2 (lifecycle/progress compatibility).
3. Deliver US3 (failure boundaries and cancellation behavior).
4. Finish with polish and regression suite verification.

### Team Parallelization

1. One engineer owns runner refactor (`aof_precompute_runner.py`) while another owns repository/model support.
2. Test engineer can build contract/integration coverage in parallel once foundational schema/repository tasks are complete.
3. CLI/reporting tasks can run after core execution semantics stabilize.

## Notes

- [P] tasks indicate safe parallel execution when dependencies are satisfied.
- [USx] labels provide strict story traceability.
- Every task includes a concrete file path to keep execution deterministic.
- Story checkpoints define independently testable increments.
