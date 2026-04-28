# Tasks: Legacy Schema Cleanup

**Input**: Design documents from `/specs/001-legacy-schema-cleanup/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: This feature explicitly requires proof-gate and final regression-gate validation, so fail-first and gate-validation test tasks are included per user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story-phase tasks only
- Every task includes an explicit file target

## Phase 1: Setup (Shared Alignment)

**Purpose**: Lock cleanup scope, sequencing, and validation artifacts before code changes.

- [x] T001 Align cleanup classification rules and acceptance semantics in `specs/001-legacy-schema-cleanup/contracts/cleanup-classification-contract.md`
- [x] T002 [P] Align sequencing gate evidence and failure policy in `specs/001-legacy-schema-cleanup/contracts/sequencing-gate-contract.md`
- [x] T003 [P] Record strict delete-gate and one-release deprecation window in `specs/001-legacy-schema-cleanup/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish proof-gate checks and inventory tracking required by all stories.

**CRITICAL**: No user story implementation should start until this phase is complete.

- [x] T004 Create cleanup inventory tracker (`target_path`, classification, legacy signals, gate status) in `specs/001-legacy-schema-cleanup/data-model.md`
- [x] T005 [P] Add repository-wide legacy dependency scan baseline (`GameState.cell_id`, `board_cards_id`, `BoardCard`) to `specs/001-legacy-schema-cleanup/research.md`
- [x] T006 [P] Add runtime-entrypoint import verification checklist for delete targets in `specs/001-legacy-schema-cleanup/plan.md`
- [x] T007 Execute proof-gate replacement suites and record pass evidence in `specs/001-legacy-schema-cleanup/quickstart.md`

**Checkpoint**: Proof gate is documented and passing, and cleanup inventory/gate criteria are ready.

---

## Phase 3: User Story 1 - Remove Dead Read/Write Paths (Priority: P1) 🎯 MVP

**Goal**: Remove or rewrite stale production schema paths while preserving GameStates-first runtime behavior.

**Independent Test**: Run proof/final replay and run-boundary suites, then verify no active production path requires `GameState.cell_id`, `board_cards_id`, or `BoardCard` joins.

### Tests for User Story 1 (write first, fail first)

- [x] T008 [P] [US1] Add/refresh regression assertions for truthful replay delegation and no legacy board-card dependence in `tests/test_game_replay_queries.py`
- [x] T009 [P] [US1] Add/refresh run-boundary raw-query assertions that reject legacy cell-linked assumptions in `tests/test_analytical_query_integration.py`
- [x] T010 [P] [US1] Add matrix-sweep aggregation regression assertions ensuring post-processing over raw rows only in `tests/test_matrix_sweep_aggregation_service.py`

### Implementation for User Story 1

- [x] T011 [US1] Rewrite legacy `create_game_state`/`board_cards` repository paths to schema-correct behavior in `python/hopilot/gto/database_repository.py`
- [x] T012 [US1] Rewrite legacy precompute write flow that requires `board_cards_id` in `python/hopilot/gto/aof_precompute_runner.py`
- [x] T013 [US1] Rewrite legacy convergence queries that depend on `GameState.cell_id` in `python/hopilot/gto/convergence_analysis_queries.py`
- [x] T014 [US1] Rewrite legacy jackpot-frequency joins keyed on `GameState.cell_id` in `python/hopilot/gto/jackpot_frequency_queries.py`
- [x] T015 [US1] Rewrite aggregation engine to derive from GameStates-first scope rather than cell-linked raw ownership in `python/hopilot/gto/aggregation_engine.py`
- [x] T016 [US1] Rewrite incremental aggregation path to remove direct `GameState.cell_id` dependence in `python/hopilot/gto/incremental_aggregation.py`
- [x] T017 [US1] Rewrite legacy conversion/representation paths tied to BoardCard/cell_id in `python/hopilot/models/game_state.py`
- [x] T018 [US1] Remove dead legacy query facade in `python/hopilot/queries.py`
- [x] T019 [US1] Remove dead legacy aggregation module in `python/hopilot/database/aggregation.py`
- [x] T020 [US1] Remove BoardCard model and stale exports in `python/hopilot/models/board_card.py` and `python/hopilot/models/__init__.py`
- [x] T021 [US1] Apply deprecation-only wrappers (one release cycle) where unresolved callers remain in `python/hopilot/gto/game_replay_queries.py` and `python/hopilot/database.py`

**Checkpoint**: US1 leaves only schema-correct production paths active with delete gate honored.

---

## Phase 4: User Story 2 - Retire Obsolete Test Coverage (Priority: P2)

**Goal**: Remove obsolete tests and rewrite mixed tests in place so retained suites validate only active architecture.

**Independent Test**: Run retained suite slices and verify no passing test asserts dead-schema behavior.

### Tests for User Story 2 (write first, fail first)

- [x] T022 [P] [US2] Add guard assertion that retained tests must not reference legacy schema fields in `tests/test_game_replay_queries.py`
- [x] T023 [P] [US2] Add guard assertion for run-boundary analytical behavior in `tests/test_analytical_query_integration.py`

### Implementation for User Story 2

- [x] T024 [US2] Delete obsolete CRUD test file tied to `cell_id`/`board_cards_id` behavior: `tests/test_database_repository_crud.py`
- [x] T025 [US2] Delete obsolete matrix aggregation integration test file: `tests/test_matrix_aggregation.py`
- [x] T026 [US2] Delete obsolete incremental aggregation test file: `tests/test_incremental_aggregation.py`
- [x] T027 [US2] Rewrite mixed aggregation comprehensive tests in place to GameStates-first behavior in `tests/test_aggregation_engine_comprehensive.py`
- [x] T028 [US2] Rewrite mixed aggregation unit/integration tests in place to GameStates-first behavior in `tests/test_aggregation.py`
- [x] T029 [US2] Rewrite any remaining analytical/repository tests asserting `board_cards_id` or `cell_id` in place in `tests/test_analytical_query_integration.py` and `tests/test_database_repository.py`

**Checkpoint**: US2 leaves test suite aligned to active architecture with no dead-schema assertions.

---

## Phase 5: User Story 3 - Enforce Safe Cleanup Sequencing (Priority: P3)

**Goal**: Make sequencing gates and import-clean checks explicit so cleanup cannot bypass safety rules.

**Independent Test**: Confirm each gate has evidence, failed gates block progression, and final required suites pass.

### Tests for User Story 3 (write first, fail first)

- [x] T030 [P] [US3] Add sequencing-gate execution verification notes and expected failure behavior in `specs/001-legacy-schema-cleanup/quickstart.md`
- [x] T031 [P] [US3] Add import-clean precondition checks for delete targets in `specs/001-legacy-schema-cleanup/contracts/sequencing-gate-contract.md`

### Implementation for User Story 3

- [x] T032 [US3] Record per-target cleanup decisions (delete/rewrite/deprecate/keep) with rationale and phase status in `specs/001-legacy-schema-cleanup/data-model.md`
- [x] T033 [US3] Add strict delete-gate completion log (`runtime_imports_removed=true` for delete targets) in `specs/001-legacy-schema-cleanup/quickstart.md`
- [x] T034 [US3] Add one-release-cycle deprecation removal deadline entries for deprecate targets in `specs/001-legacy-schema-cleanup/plan.md`
- [x] T035 [US3] Execute final regression gate suites and record outcomes in `specs/001-legacy-schema-cleanup/quickstart.md`

**Checkpoint**: US3 enforces sequencing and produces auditable gate evidence.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency pass across docs, imports, and regression evidence.

- [x] T036 [P] Update cleanup summary and final module classification status in `specs/001-legacy-schema-cleanup/spec.md`
- [x] T037 [P] Update implementation outcomes and residual risks in `specs/001-legacy-schema-cleanup/plan.md`
- [x] T038 Run targeted validation commands from quickstart and record final pass status in `specs/001-legacy-schema-cleanup/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2 and delivers the MVP cleanup slice.
- **Phase 4 (US2)**: Depends on Phase 2 and should follow US1 production rewrites for stable test migration.
- **Phase 5 (US3)**: Depends on US1 and US2 outputs to enforce gates with real cleanup outcomes.
- **Phase 6 (Polish)**: Depends on completion of desired stories.

### User Story Dependencies

- **US1 (P1)**: Starts after foundational proof gate.
- **US2 (P2)**: Depends on established replacement-path behavior and active production rewrites.
- **US3 (P3)**: Depends on completed cleanup actions to validate sequencing evidence.

### Within-Story Ordering Rules

- Tests for each story must be written/updated before implementation tasks.
- For delete targets, runtime import cleanup must be verified before deletion.
- Mixed-module rewrites must complete before final removal of dead modules.
- Final regression gate must run after all cleanup actions are complete.

---

## Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel after T001 starts.
- **Foundational**: T005 and T006 can run in parallel before T007 proof-gate capture.
- **US1**: T008-T010 can run in parallel; T013/T014/T015/T016 can run in parallel after T011 starts.
- **US2**: T024-T026 deletions can run in parallel; T027-T029 rewrites can run in parallel by file.
- **US3**: T030 and T031 can run in parallel; T033 and T034 can run in parallel before T035.
- **Polish**: T036 and T037 can run in parallel before T038.

## Parallel Example: User Story 1

```bash
# Write failing/updated guards together
Task: "Add replay no-legacy-dependency regression assertions in tests/test_game_replay_queries.py"
Task: "Add run-boundary no-cell-linked-path assertions in tests/test_analytical_query_integration.py"
Task: "Add post-processing-only aggregation assertions in tests/test_matrix_sweep_aggregation_service.py"

# Rewrite independent production modules in parallel
Task: "Rewrite convergence legacy cell_id queries in python/hopilot/gto/convergence_analysis_queries.py"
Task: "Rewrite jackpot_frequency legacy joins in python/hopilot/gto/jackpot_frequency_queries.py"
Task: "Rewrite incremental aggregation legacy dependence in python/hopilot/gto/incremental_aggregation.py"
```

## Parallel Example: User Story 2

```bash
# Remove obsolete test files together
Task: "Delete tests/test_database_repository_crud.py"
Task: "Delete tests/test_matrix_aggregation.py"
Task: "Delete tests/test_incremental_aggregation.py"

# Rewrite mixed test files in place
Task: "Rewrite tests/test_aggregation_engine_comprehensive.py to GameStates-first assertions"
Task: "Rewrite tests/test_aggregation.py to GameStates-first assertions"
```

## Parallel Example: User Story 3

```bash
# Gate evidence updates in parallel
Task: "Add import-clean preconditions to sequencing gate contract"
Task: "Add gate execution evidence capture to quickstart"

# Then finalize with required regression suite execution
Task: "Run replay migration + run-boundary + matrix-sweep aggregation suites and record outcomes"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1.
2. Complete Phase 2 proof gate.
3. Complete Phase 3 production cleanup and delete-gate checks.
4. Validate US1 independently via replay/run-boundary/matrix-sweep slices.

### Incremental Delivery

1. Deliver US1 production-path cleanup.
2. Deliver US2 test cleanup and in-place rewrites.
3. Deliver US3 sequencing enforcement and gate evidence.
4. Finish with polish and final validation evidence.

### Suggested MVP Scope

- **MVP**: Phase 1, Phase 2, and Phase 3 (US1 only).
- **Why**: This is the smallest safe slice that removes high-risk dead schema production paths while preserving validated replacement behavior.
