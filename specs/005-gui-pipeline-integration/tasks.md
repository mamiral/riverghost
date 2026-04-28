# Tasks: GUI Integration and UX Hardening on the GameStates-First Pipeline

**Input**: Design documents from `/specs/005-gui-pipeline-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/panel-state-machine.md, quickstart.md

**Tests**: Include targeted pytest coverage for state transitions and cross-run aggregation, plus manual end-to-end validation required by FR-020/FR-021.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature workspace and test scaffolding.

- [X] T001 Create feature task tracking checklist in specs/005-gui-pipeline-integration/tasks.md
- [X] T002 Validate baseline test entrypoints in pytest.ini and tests/
- [X] T003 [P] Add feature test module stub in tests/test_cross_run_aggregation.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data and API prerequisites required before user story implementation.

**CRITICAL**: No user story work starts until this phase is complete.

- [X] T004 Add `sample_count` column to ORM model in python/hopilot/models/aggregated_metric.py
- [X] T005 Persist per-cell `sample_count` during run aggregation in python/hopilot/gto/matrix_sweep_aggregation_service.py
- [X] T006 Implement cross-run matrix merge query method in python/hopilot/gto/database_repository.py
- [X] T007 Switch browser read path to cross-run payload source in python/hopilot/gto/browser_database_provider.py
- [X] T008 [P] Add repository-level tests for cross-run weighted merge in tests/test_cross_run_aggregation.py

**Checkpoint**: Cross-run aggregation and sample-count persistence are functional and test-backed.

---

## Phase 3: User Story 1 - View Precomputed Matrix for Current Scenario (Priority: P1) 🎯 MVP

**Goal**: Render honest panel states for scenario fetches and prevent stale scenario leakage.

**Independent Test**: Selecting a scenario with data shows AVAILABLE; selecting one without data shows MISSING; changing scenario never leaves old scenario values visible.

### Tests for User Story 1

- [X] T009 [P] [US1] Add panel state derivation tests for LOADING/AVAILABLE/MISSING/NO_CONTEST in tests/test_aof_browser_panel_database_integration.py
- [X] T010 [P] [US1] Add stale-data prevention integration test for scenario switch in tests/integration/test_aof_browser_panel_integration.py

### Implementation for User Story 1

- [X] T011 [US1] Introduce `PanelState` enum and computed `panel_state` property in python/hopilot/gui_components/aof_browser_panel.py
- [X] T012 [US1] Route panel rendering decisions through `panel_state` in python/hopilot/gui_components/aof_browser_panel.py
- [X] T013 [US1] Ensure async fetch success maps to AVAILABLE/MISSING/NO_CONTEST states in python/hopilot/gui_components/aof_browser_panel.py
- [X] T014 [US1] Ensure async fetch failure sets `_last_error` and ERROR state in python/hopilot/gui_components/aof_browser_panel.py
- [X] T015 [US1] Display active scenario context (position + metric) in panel header in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: US1 is independently functional and trust-safe for read-only browsing.

---

## Phase 4: User Story 2 - Trigger Precompute for a Missing Scenario (Priority: P1)

**Goal**: Start precompute from MISSING/NO_CONTEST/ERROR/AVAILABLE and auto-refresh to new aggregated results.

**Independent Test**: Empty scenario transitions MISSING -> COMPUTING -> AVAILABLE after run completion without manual refresh.

### Tests for User Story 2

- [X] T016 [P] [US2] Add Start-button enablement tests across panel states in tests/test_aof_browser_panel_database_integration.py
- [X] T017 [P] [US2] Add rerun-from-AVAILABLE overlay behavior test in tests/integration/test_aof_browser_panel_integration.py
- [X] T018 [P] [US2] Add auto-refresh-after-completion test in tests/test_aof_browser_panel_database_integration.py

### Implementation for User Story 2

- [X] T019 [US2] Add `_rerun_in_progress` flag lifecycle to panel in python/hopilot/gui_components/aof_browser_panel.py
- [X] T020 [US2] Update `_start_precompute()` to preserve payload when starting from AVAILABLE in python/hopilot/gui_components/aof_browser_panel.py
- [X] T021 [US2] Implement Start/Pause/Resume/Stop button gating by `panel_state` in python/hopilot/gui_components/aof_browser_panel.py
- [X] T022 [US2] Trigger `_refresh()` after COMPLETED run state when futures drain in python/hopilot/gui_components/aof_browser_panel.py
- [X] T023 [US2] Show COMPUTING overlay while AVAILABLE rerun is active in python/hopilot/gui_components/aof_browser_panel.py
- [X] T024 [US2] Surface `sample_count` into payload/cell details for AVAILABLE cells in python/hopilot/gto/browser_database_provider.py

**Checkpoint**: US2 supports complete compute-and-refresh workflow including rerun accumulation.

---

## Phase 5: User Story 3 - Handle Precompute Failure Gracefully (Priority: P2)

**Goal**: Failures move panel to ERROR with user-visible messaging and retry behavior.

**Independent Test**: Simulated fetch or run failure shows ERROR; clicking Start from ERROR clears error and retries.

### Tests for User Story 3

- [X] T025 [P] [US3] Add fetch-failure to ERROR transition test in tests/test_aof_browser_panel_database_integration.py
- [X] T026 [P] [US3] Add precompute-failure to ERROR + retry test in tests/integration/test_aof_browser_panel_integration.py

### Implementation for User Story 3

- [X] T027 [US3] Set and clear `_last_error` consistently in async refresh and precompute callbacks in python/hopilot/gui_components/aof_browser_panel.py
- [X] T028 [US3] Render user-visible ERROR message and disable invalid actions in python/hopilot/gui_components/aof_browser_panel.py
- [X] T029 [US3] Ensure Start from ERROR clears error state before launching new run in python/hopilot/gui_components/aof_browser_panel.py
- [X] T030 [US3] Prevent incomplete partial state from being shown as fully AVAILABLE after failures in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: US3 recovers cleanly from operational failures.

---

## Phase 6: User Story 4 - Context Change Invalidates Current Matrix (Priority: P2)

**Goal**: Position/metric changes immediately invalidate current matrix and safely restart fetch lifecycle.

**Independent Test**: Change position or metric while viewing AVAILABLE; old scenario cells disappear immediately and never reappear for the new context.

### Tests for User Story 4

- [X] T031 [P] [US4] Add context-change invalidation tests for position and metric in tests/test_aof_browser_panel_database_integration.py
- [X] T032 [P] [US4] Add in-flight fetch result discard test for context mismatch in tests/integration/test_aof_browser_panel_integration.py

### Implementation for User Story 4

- [X] T033 [US4] Set existing payload cells to LOADING and clear context at `_refresh()` start in python/hopilot/gui_components/aof_browser_panel.py
- [X] T034 [US4] Stop or detach in-flight precompute session when context changes in python/hopilot/gui_components/aof_browser_panel.py
- [X] T035 [US4] Discard stale async fetch results that do not match active scenario context in python/hopilot/gui_components/aof_browser_panel.py
- [X] T036 [US4] Add partial cell-count indicator (`x / 169`) for AVAILABLE-with-partial-cells in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: US4 ensures strict scenario-context integrity.

---

## Phase 7: User Story 5 - Cancel or Pause a Running Precompute Job (Priority: P3)

**Goal**: Pause/resume/stop controls operate deterministically without ambiguous panel behavior.

**Independent Test**: RUNNING job can pause/resume/stop; panel and buttons reflect true session state; partial completion remains honest.

### Tests for User Story 5

- [X] T037 [P] [US5] Add pause/resume/stop button-state transition tests in tests/test_aof_browser_panel_database_integration.py
- [X] T038 [P] [US5] Add stop-with-partial-results integration test in tests/integration/test_aof_browser_panel_integration.py

### Implementation for User Story 5

- [X] T039 [US5] Wire Pause control to `GuiRunState.PAUSED` transitions in python/hopilot/gui_components/aof_browser_panel.py
- [X] T040 [US5] Wire Resume control to paused session restart path in python/hopilot/gui_components/aof_browser_panel.py
- [X] T041 [US5] Wire Stop control to terminate session and trigger partial-result refresh in python/hopilot/gui_components/aof_browser_panel.py
- [X] T042 [US5] Ensure partial post-stop matrix is represented as AVAILABLE-partial or MISSING honestly in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: US5 gives users full control over long-running jobs.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final quality pass, end-to-end checks, and documentation sync.

- [X] T043 [P] Update feature behavior notes and caveats in specs/005-gui-pipeline-integration/quickstart.md
- [X] T044 Run targeted pytest suite for touched modules in tests/
- [X] T045 Run full pytest regression in tests/
- [ ] T046 Execute manual SC-005 workflow against real DB and record results in specs/005-gui-pipeline-integration/quickstart.md
- [X] T047 Verify Constitution re-check outcomes for sample_count/cross-run changes in specs/005-gui-pipeline-integration/plan.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 -> Phase 2
- Phase 2 blocks all user story phases
- Phase 3 (US1) and Phase 4 (US2) are both P1 and should execute in order because US2 depends on state-machine behavior from US1
- Phase 5 (US3) depends on US2 lifecycle hooks
- Phase 6 (US4) depends on US1 fetch/state baseline
- Phase 7 (US5) depends on US2 precompute lifecycle wiring
- Phase 8 depends on all selected stories being complete

### User Story Dependencies

- **US1 (P1)**: Starts immediately after Phase 2
- **US2 (P1)**: Depends on US1 panel-state foundation
- **US3 (P2)**: Depends on US2 completion/failure pathways
- **US4 (P2)**: Depends on US1 and can run in parallel with late US3 work
- **US5 (P3)**: Depends on US2 pause/resume/stop pipeline

### Within Each User Story

- Tests first (where listed)
- State/model primitives before button/render wiring
- Async lifecycle handling before integration assertions
- Story checkpoint validation before moving to next priority

---

## Parallel Opportunities

- T003 can run in parallel with T001-T002
- T008 can run in parallel after T004-T007 interfaces are stable
- In US1: T009 and T010 run in parallel
- In US2: T016, T017, and T018 run in parallel
- In US3: T025 and T026 run in parallel
- In US4: T031 and T032 run in parallel
- In US5: T037 and T038 run in parallel
- In Polish: T043 can run in parallel with T044

---

## Parallel Example: User Story 2

```bash
# Run US2 test authoring in parallel:
Task T016: tests/test_aof_browser_panel_database_integration.py
Task T017: tests/integration/test_aof_browser_panel_integration.py
Task T018: tests/test_aof_browser_panel_database_integration.py

# After tests are in place, implement independent code paths in parallel:
Task T019: _rerun_in_progress lifecycle in python/hopilot/gui_components/aof_browser_panel.py
Task T024: sample_count mapping in python/hopilot/gto/browser_database_provider.py
```

## Parallel Example: User Story 4

```bash
# Parallel test tasks:
Task T031: position/metric invalidation tests in tests/test_aof_browser_panel_database_integration.py
Task T032: stale async result discard test in tests/integration/test_aof_browser_panel_integration.py

# Then implement independent behavior slices:
Task T033: LOADING invalidation in python/hopilot/gui_components/aof_browser_panel.py
Task T036: partial count indicator in python/hopilot/gui_components/aof_browser_panel.py
```

## Parallel Example: User Story 5

```bash
# Parallel tests:
Task T037: pause/resume/stop transitions in tests/test_aof_browser_panel_database_integration.py
Task T038: stop-with-partial-results integration in tests/integration/test_aof_browser_panel_integration.py

# Parallel implementation slices after lifecycle hooks exist:
Task T040: resume handling in python/hopilot/gui_components/aof_browser_panel.py
Task T041: stop handling + refresh in python/hopilot/gui_components/aof_browser_panel.py
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Setup (Phase 1)
2. Complete Foundational (Phase 2)
3. Complete US1 (Phase 3)
4. Validate US1 independently before continuing

### Incremental Delivery

1. Deliver US1 for trustworthy stateful viewing
2. Deliver US2 for compute-and-refresh workflow
3. Deliver US3 and US4 for resilience and context integrity
4. Deliver US5 for advanced run control
5. Finish with Polish phase and full/manual validation

### Suggested MVP Scope

- **MVP**: Phases 1-3 (through US1)
- **First production-ready increment**: Phases 1-4 (US1 + US2)
