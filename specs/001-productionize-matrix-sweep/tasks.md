# Tasks: Productionize Matrix Sweep

**Input**: Design documents from `/specs/001-productionize-matrix-sweep/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: This feature explicitly requires real persistence acceptance coverage (FR-016), so test tasks are included and sequenced before implementation in each user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story-phase tasks only
- Every task includes an explicit file target

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish production sweep scaffolding and test harness entry points.

- [X] T001 Create production sweep module scaffold in `python/hopilot/gto/matrix_sweep_service.py`
- [X] T002 [P] Create aggregation module scaffold in `python/hopilot/gto/matrix_sweep_aggregation_service.py`
- [X] T003 [P] Create matrix sweep contract helper scaffold in `python/hopilot/gto/matrix_sweep_contract.py`
- [X] T004 [P] Create matrix sweep integration DB fixture helper in `tests/integration/matrix_sweep_db_utils.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared primitives that all stories depend on.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [X] T005 Implement scenario contract normalization/validation (required fields + compatibility alias `num_simulations`) in `python/hopilot/gto/matrix_sweep_contract.py`
- [X] T006 Implement run-boundary metadata helpers (`raw_game_state_id_start/end`, counters, status updates) in `python/hopilot/gto/matrix_sweep_contract.py`
- [X] T007 [P] Add canonical reverse-mapping helper from hero hole cards to matrix coordinates in `python/hopilot/gto/aof_hand_matrix.py`
- [X] T008 [P] Add canonical 169-cell iterator helper for deterministic aggregation coverage in `python/hopilot/gto/aof_hand_matrix.py`
- [X] T009 [P] Update matrix cell validation to accept canonical cell labels (without requiring `'vs'`) in `python/hopilot/models/matrix_cell.py`
- [X] T010 [P] Update simulation parameter validation to support matrix-sweep required contract fields while preserving compatibility checks in `python/hopilot/models/simulation.py`
- [X] T011 Add repository/session helper methods for run-scoped simulation + hand-matrix creation and retrieval in `python/hopilot/gto/database_repository.py`
- [X] T012 Add architecture guard utility to block production imports from `prototyping/` in `tests/integration/test_architecture_boundaries.py`

**Checkpoint**: Shared contract, mapping, model constraints, and boundary utilities are ready.

---

## Phase 3: User Story 1 - Run a Fixed Scenario Sweep (Priority: P1) 🎯 MVP

**Goal**: Execute one fixed-scenario full sweep that writes raw records first, then aggregates into one run boundary with idempotent aggregation rerun semantics.

**Independent Test**: Run one fixed scenario; verify raw writes precede summaries, then verify one `Simulation`, one `HandMatrix`, 169 `MatrixCell`, and 169 `AggregatedMetric`; rerun aggregation and verify only summaries inside that run are replaced.

### Tests for User Story 1 (write first, fail first)

- [X] T013 [P] [US1] Add integration test for raw-only sweep phase (no summary writes before aggregation) in `tests/test_matrix_sweep_service.py`
- [X] T014 [P] [US1] Add integration test for full aggregation counts (1 simulation, 1 matrix, 169 cells, 169 metrics) in `tests/test_matrix_sweep_aggregation_service.py`
- [X] T015 [P] [US1] Add integration test for aggregation rerun idempotency (delete/recreate summaries only; raw rows unchanged) in `tests/test_matrix_sweep_aggregation_service.py`
- [X] T016 [P] [US1] Add edge-case test for unmappable hero hole cards being excluded and counted (without aborting run) in `tests/test_matrix_sweep_aggregation_service.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement `MatrixSweepAggregationService.aggregate_run(simulation_id)` with run-boundary raw filtering in `python/hopilot/gto/matrix_sweep_aggregation_service.py`
- [X] T018 [US1] Implement canonical 169-cell summary creation and per-cell aggregated metric write in `python/hopilot/gto/matrix_sweep_aggregation_service.py`
- [X] T019 [US1] Implement `MatrixSweepAggregationService.rerun_aggregation(simulation_id)` to delete/recreate only selected run summaries in `python/hopilot/gto/matrix_sweep_aggregation_service.py`
- [X] T020 [US1] Implement `MatrixSweepService.run_sweep(scenario_contract)` orchestration (create simulation, execute combos, persist boundary metadata) in `python/hopilot/gto/matrix_sweep_service.py`
- [X] T021 [US1] Integrate `PokerAnalyzer.calculate_odds_random_opponents(..., persistence=...)` to enforce raw GameState/Player writes only during sweep in `python/hopilot/gto/matrix_sweep_service.py`
- [X] T022 [US1] Implement run result contract fields (`simulation_id`, `matrix_id`, counts, failed combinations, unmapped records, status) in `python/hopilot/gto/matrix_sweep_service.py`
- [X] T023 [US1] Export production services for consumption by precompute/CLI layers in `python/hopilot/gto/__init__.py`

**Checkpoint**: US1 delivers a complete MVP matrix sweep and rerunnable aggregation with run-local idempotency.

---

## Phase 4: User Story 2 - Query a Completed Run Cleanly (Priority: P2)

**Goal**: Query one selected run using canonical scenario contract metadata and return only that run's summarized results.

**Independent Test**: Create two runs with different contracts, query one run, and verify no matrix/metric leakage from the other run.

### Tests for User Story 2 (write first, fail first)

- [X] T024 [P] [US2] Add integration test for run selection by scenario contract and summary isolation in `tests/test_matrix_sweep_pipeline.py`
- [X] T025 [P] [US2] Add integration test verifying required persisted contract fields in `Simulation.parameters` for completed runs in `tests/test_matrix_sweep_pipeline.py`

### Implementation for User Story 2

- [X] T026 [US2] Implement run query helpers (`find_run_by_contract`, `get_run_summary`) scoped to a single simulation boundary in `python/hopilot/gto/matrix_sweep_service.py`
- [X] T027 [US2] Add read-path projection for run-scoped matrix summaries (`HandMatrix`, `MatrixCell`, `AggregatedMetric`) in `python/hopilot/gto/database_repository.py`
- [X] T028 [US2] Wire run query surface into browser-facing provider without cross-run joins in `python/hopilot/gto/browser_database_provider.py`

**Checkpoint**: US2 provides deterministic run lookup and run-local summary retrieval.

---

## Phase 5: User Story 3 - Preserve Historical Runs and Architectural Boundaries (Priority: P3)

**Goal**: Ensure new production sweep appends historical runs safely and preserves GameStates-first and prototype-reference-only boundaries.

**Independent Test**: Execute a new run in a DB containing prior runs; verify prior runs unchanged and no solver-side summary coupling is reintroduced.

### Tests for User Story 3 (write first, fail first)

- [X] T029 [P] [US3] Add integration test verifying new run appends new simulation/matrix and keeps existing runs unchanged in `tests/test_matrix_sweep_pipeline.py`
- [X] T030 [P] [US3] Add architecture regression test ensuring sweep path does not create summaries during solver execution in `tests/test_matrix_sweep_service.py`
- [X] T031 [P] [US3] Add architecture regression test preventing production imports from `prototyping/` modules in `tests/integration/test_architecture_boundaries.py`

### Implementation for User Story 3

- [X] T032 [US3] Route precompute runner matrix sweep execution through `MatrixSweepService` (not prototype script paths) in `python/hopilot/gto/aof_precompute_runner.py`
- [X] T033 [US3] Remove/guard stale cell-coupled sweep entrypoints that pass `matrix_cell_id` through production sweep orchestration in `python/hopilot/all_in_fold_gto.py`
- [X] T034 [US3] Add explicit run-boundary append semantics and historical-run immutability checks in production flow logging/guards in `python/hopilot/gto/matrix_sweep_service.py`

**Checkpoint**: US3 confirms historical-run safety and architecture integrity.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize documentation, verification commands, and consistency checks.

- [X] T035 [P] Update feature quickstart with finalized commands and expected assertions in `specs/001-productionize-matrix-sweep/quickstart.md`
- [X] T036 [P] Update storage/reference documentation with run-boundary and rerun-idempotency semantics in `docs/multi_scenario_storage.md`
- [X] T037 Execute targeted test suite and record pass/fail evidence in `specs/001-productionize-matrix-sweep/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all story work.
- **Phase 3 (US1)**: Depends on Phase 2; delivers MVP.
- **Phase 4 (US2)**: Depends on US1 data flow and run metadata behavior.
- **Phase 5 (US3)**: Depends on US1 implementation; validates architecture and historical safety around completed pipeline.
- **Phase 6 (Polish)**: Depends on completion of desired stories.

### User Story Dependencies

- **US1 (P1)**: Starts after foundational completion; no dependency on US2/US3.
- **US2 (P2)**: Depends on US1 because run querying targets completed runs created by the production orchestrator.
- **US3 (P3)**: Depends on US1 pipeline completion; can run in parallel with late US2 refinements after foundational + core US1 behavior is stable.

### Within-Story Ordering Rules

- Test tasks for each story must be implemented before story implementation tasks.
- Service contract and mapping helpers must be in place before aggregation and orchestration implementation.
- Aggregation rerun idempotency behavior must be implemented before story completion signoff.

---

## Parallel Execution Examples

## Parallel Example: User Story 1

```bash
# Tests in parallel
T013, T014, T015, T016

# After tests exist, implementation parallelization
T017 and T020 can start in parallel, then converge for T021/T022
```

## Parallel Example: User Story 2

```bash
# Tests in parallel
T024, T025

# Implementation split
T026 and T027 in parallel, then integrate in T028
```

## Parallel Example: User Story 3

```bash
# Tests in parallel
T029, T030, T031

# Implementation split
T032 and T033 in parallel, then finalize safeguards in T034
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2.
2. Complete US1 tests and implementation (Phase 3).
3. Validate one fixed-scenario end-to-end run and aggregation rerun idempotency.
4. Demo/deploy MVP once US1 acceptance checks pass.

### Incremental Delivery

1. Deliver US1 (core pipeline).
2. Add US2 (run query isolation using contract metadata).
3. Add US3 (historical immutability + architecture boundary hardening).
4. Finish polish/documentation and rerun quickstart verification.

### Definition of Done for this Feature

- Production sweep writes raw `GameState`/`Player` only during simulation.
- Aggregation is post-sweep and creates exactly 169 cell summaries and 169 metrics per completed run.
- Aggregation rerun replaces only selected run summaries and leaves raw rows plus other runs untouched.
- No production code imports from `prototyping/`.
- Tests validate real persisted behavior, not mocked persistence.
