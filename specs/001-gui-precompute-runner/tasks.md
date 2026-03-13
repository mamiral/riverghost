# Tasks: In-GUI AoF Precompute Runner

**Input**: Design documents from `/specs/001-gui-precompute-runner/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Automated tests are required by FR-018 and are included per user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare project scaffolding and test placeholders for GUI precompute runner work.

- [X] T001 Create GUI runner test module skeleton in tests/test_aof_gui_precompute_runner_state.py
- [X] T002 [P] Create resume/recovery test module skeleton in tests/test_aof_gui_precompute_runner_resume.py
- [X] T003 [P] Create responsiveness test module skeleton in tests/test_aof_gui_precompute_runner_responsiveness.py
- [X] T004 [P] Create canonical dedup GUI test module skeleton in tests/test_aof_gui_precompute_runner_canonical_dedup.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared runner primitives and persistence interfaces required by all user stories.

**⚠️ CRITICAL**: No user story implementation should begin before these tasks complete.

- [X] T005 Define GUI run-state enums and transition guards in python/hopilot/gto/aof_precompute_runner.py
- [X] T006 Implement `GuiPrecomputeRunSession` dataclass and validation helpers in python/hopilot/gto/aof_precompute_runner.py
- [X] T007 [P] Add checkpoint read/write cursor helpers for GUI runs in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T008 [P] Add persistence model fields/constants for GUI checkpoint lifecycle in python/hopilot/gto/aof_scenario_cache_models.py
- [X] T009 Implement telemetry snapshot builder and ETA calculation utility in python/hopilot/gto/aof_precompute_runner.py
- [X] T010 Add structured GUI lifecycle logging events in python/hopilot/gto/aof_precompute_runner.py
- [X] T011 Wire provider-facing incremental cell update callback contract in python/hopilot/gto/aof_browser_data_provider.py
- [X] T012 Add foundational unit tests for run-state transition validation in tests/test_aof_precompute_runner.py

**Checkpoint**: Shared run-state, checkpoint, and telemetry infrastructure is ready.

---

## Phase 3: User Story 1 - Run Precompute In Browser (Priority: P1) 🎯 MVP

**Goal**: Start precompute from AoF browser UI and process all 169 cells sequentially with immediate matrix updates.

**Independent Test**: Launch browser, start run for active scenario, observe incremental per-cell updates through Completed without CLI.

### Tests for User Story 1

- [X] T013 [P] [US1] Add panel control rendering/state-enable tests in tests/test_gto_gui_integration.py
- [X] T014 [P] [US1] Add sequential 169-cell progression test with per-cell callback assertions in tests/test_aof_gui_precompute_runner_state.py
- [X] T015 [US1] Add matrix immediate-update integration test for completed cells in tests/test_aof_gui_precompute_runner_state.py

### Implementation for User Story 1

- [X] T016 [P] [US1] Add precompute runner panel UI section and controls in python/hopilot/gui_components/aof_browser_panel.py
- [X] T017 [US1] Implement Start action wiring from panel to runner controller in python/hopilot/gui_components/aof_browser_panel.py
- [X] T018 [US1] Implement sequential cell execution loop with fixed matrix order in python/hopilot/gto/aof_precompute_runner.py
- [X] T019 [US1] Connect cell-complete callback to matrix cell refresh in python/hopilot/gto/aof_browser_data_provider.py
- [X] T020 [US1] Expose run-state and progress snapshot getters for UI polling in python/hopilot/gto/aof_precompute_runner.py
- [X] T021 [US1] Map terminal run completion to Completed panel state in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: User can run precompute fully inside AoF browser and see live matrix updates.

---

## Phase 4: User Story 2 - Interrupt and Resume Safely (Priority: P2)

**Goal**: Support pause/resume/stop with quick cooperative interruption and checkpoint-based resume.

**Independent Test**: Start run, pause and resume mid-way, stop, restart app, resume from checkpoint without recomputing completed cells.

### Tests for User Story 2

- [X] T022 [P] [US2] Add pause/resume state transition timing tests (<=1s target) in tests/test_aof_gui_precompute_runner_responsiveness.py
- [X] T023 [P] [US2] Add stop/checkpoint persistence and restart recovery tests in tests/test_aof_gui_precompute_runner_resume.py
- [X] T024 [US2] Add scenario-change guard confirmation flow tests in tests/test_gto_gui_integration.py

### Implementation for User Story 2

- [X] T025 [US2] Implement cooperative chunk boundary checks for pause/stop requests in python/hopilot/gto/aof_precompute_runner.py
- [X] T026 [US2] Implement Pause/Resume/Stop/Reset handlers and legal transition enforcement in python/hopilot/gto/aof_precompute_runner.py
- [X] T027 [US2] Persist per-cell checkpoint after completion and on stop/pause transitions in python/hopilot/gto/aof_scenario_cache_store.py
- [X] T028 [US2] Restore latest matching checkpoint on panel initialization/app restart in python/hopilot/gto/aof_precompute_runner.py
- [X] T029 [US2] Add scenario-defining control lock and stop-confirm-restart modal flow in python/hopilot/gui_components/aof_browser_panel.py
- [X] T030 [US2] Block resume when scenario fingerprint mismatch is detected in python/hopilot/gto/aof_precompute_runner.py

**Checkpoint**: Long-running jobs can be safely interrupted and resumed without losing completed work.

---

## Phase 5: User Story 3 - Trustworthy Progress and Determinism (Priority: P3)

**Goal**: Provide reliable telemetry and deterministic status handling while preserving canonical dedup/context hydration.

**Independent Test**: During active run, telemetry updates accurately, timeout/error cells continue flow deterministically, canonical equivalents reuse cache without UI context leakage.

### Tests for User Story 3

- [X] T031 [P] [US3] Add telemetry accuracy tests for counters/current-cell/elapsed/ETA/failures in tests/test_aof_gui_precompute_runner_state.py
- [X] T032 [P] [US3] Add deterministic timeout/error continuation tests in tests/test_aof_gui_precompute_runner_state.py
- [X] T033 [US3] Add canonical dedup with request-local context hydration tests in tests/test_aof_gui_precompute_runner_canonical_dedup.py

### Implementation for User Story 3

- [X] T034 [US3] Implement authoritative telemetry snapshot updates from session counters in python/hopilot/gto/aof_precompute_runner.py
- [X] T035 [US3] Ensure per-cell TIMEOUT/ERROR handling increments failures and continues run in python/hopilot/gto/aof_precompute_runner.py
- [X] T036 [US3] Ensure deterministic status mapping remains AVAILABLE/MISSING/NO_CONTEST/TIMEOUT/ERROR in python/hopilot/gto/aof_browser_data_provider.py
- [X] T037 [US3] Preserve canonical solver-equivalence cache reuse with request-local context hydration in python/hopilot/gto/aof_browser_data_provider.py
- [X] T038 [US3] Surface telemetry and failure indicators in browser panel progress widgets in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: Telemetry and deterministic behavior are trustworthy across normal and failure paths.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality, documentation, and end-to-end validation across stories.

- [X] T039 [P] Document GUI precompute runner usage and guard behavior in docs/initial_design/USAGE_GUIDE_WIN.md
- [X] T040 [P] Update feature quickstart verification notes in specs/001-gui-precompute-runner/quickstart.md
- [X] T041 Run targeted regression suite for runner/provider/gui integration in tests/test_aof_precompute_runner.py
- [X] T042 Run targeted regression suite for GUI precompute new tests in tests/test_aof_gui_precompute_runner_state.py
- [X] T043 Run targeted regression suite for resume/responsiveness/dedup tests in tests/test_aof_gui_precompute_runner_resume.py
- [X] T044 Run targeted regression suite for canonical dedup and panel integration in tests/test_aof_gui_precompute_runner_canonical_dedup.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; delivers MVP.
- **Phase 4 (US2)**: Depends on Phase 2 and integrates with US1 runner flow.
- **Phase 5 (US3)**: Depends on Phase 2 and integrates with US1/US2 execution data.
- **Phase 6 (Polish)**: Depends on completion of selected user stories.

### User Story Dependencies

- **US1 (P1)**: Can start immediately after Foundational completion.
- **US2 (P2)**: Requires foundational run-state/checkpoint primitives; builds on US1 panel runner wiring.
- **US3 (P3)**: Requires foundational telemetry/checkpoint structure; uses runner/provider behavior from US1 and interruption lifecycle from US2.

### Within Each User Story

- Tests should be authored before implementation tasks and fail initially.
- Runner control/state implementation precedes panel wiring that consumes those states.
- Persistence/checkpoint tasks precede resume/recovery UI exposure.

---

## Parallel Opportunities

- **Setup**: T002-T004 can run in parallel after T001.
- **Foundational**: T007 and T008 can run in parallel; T005/T006/T009/T010 can be split once state model skeleton exists.
- **US1**: T013 and T014 can run in parallel; T016 and T018 can proceed in parallel before wiring tasks.
- **US2**: T022 and T023 can run in parallel; T027 and T029 can run in parallel once transition handlers exist.
- **US3**: T031 and T032 can run in parallel; T036 and T038 can run in parallel after telemetry core is ready.

### Parallel Example: User Story 2

```text
Parallel block A:
- T022 [US2] responsiveness timing tests
- T023 [US2] resume/recovery tests

Parallel block B (after T026):
- T027 [US2] checkpoint persistence updates
- T029 [US2] scenario guard UI flow
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) end-to-end.
3. Validate independent test for in-browser sequential precompute completion.

### Incremental Delivery

1. Add US2 interruption and resume safety on top of MVP.
2. Add US3 telemetry/determinism/canonical dedup assurances.
3. Finish with Phase 6 regression and docs polish.

### Validation Gates

1. Gate A: Foundational run-state and checkpoint primitives stable.
2. Gate B: US1 MVP functional in browser without CLI.
3. Gate C: Pause/Resume/Stop and restart-resume behavior validated.
4. Gate D: Deterministic statuses and canonical dedup tests pass.

---

## Notes

- All tasks follow the strict checklist format: checkbox, Task ID, optional `[P]`, required `[USx]` in story phases, actionable description with file path.
- Keep standalone AoF browser decoupled from simulator workflows while extending existing provider/cache modules.
- Preserve deterministic status semantics and canonical solver-equivalence dedup behavior throughout implementation.
