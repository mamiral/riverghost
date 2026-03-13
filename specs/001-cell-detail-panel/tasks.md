# Tasks: Cell Detail Middle Panel

**Input**: Design documents from /specs/001-cell-detail-panel/
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are required by the specification (FR-012), so story-specific test tasks are included.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the feature scaffolding and layout placeholders needed before selection/detail logic.

- [X] T001 Create middle panel component scaffold in python/hopilot/gui_components/aof_cell_detail_panel.py
- [X] T002 [P] Add middle-panel layout placeholders and bounds wiring in python/hopilot/gui_components/aof_browser_panel.py
- [X] T003 [P] Add initial middle-panel import/export wiring in python/hopilot/gui_components/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared selection and view-model foundations that all user stories depend on.

**CRITICAL**: No user story work starts until this phase is complete.

- [X] T004 Add selected-cell state fields and mutators in python/hopilot/gto/aof_browser_state.py
- [X] T005 Add matrix cell hit-detection helper for click mapping in python/hopilot/gui_components/aof_hand_matrix_panel.py
- [X] T006 Wire matrix click events to selected-cell updates in python/hopilot/gui_components/aof_browser_panel.py
- [X] T007 Build selected-cell detail view-model mapping method in python/hopilot/gui_components/aof_browser_panel.py
- [X] T008 Implement status-to-fallback mapping utility in python/hopilot/gui_components/aof_cell_detail_panel.py

**Checkpoint**: Selection + detail-model foundation is ready.

---

## Phase 3: User Story 1 - Inspect Selected Cell Details (Priority: P1) MVP

**Goal**: Show a dedicated middle detail panel that reflects selected matrix cells and empty-state when nothing is selected.

**Independent Test**: Open the browser, select multiple cells, and verify panel updates each time; verify empty-state when no cell is selected.

### Tests for User Story 1

- [X] T009 [P] [US1] Add no-selection empty-state rendering test in tests/test_aof_gto_browser_gui.py
- [X] T010 [P] [US1] Add selected-cell change update test in tests/test_aof_gto_browser_gui.py

### Implementation for User Story 1

- [X] T011 [US1] Implement detail panel empty-state and base frame rendering in python/hopilot/gui_components/aof_cell_detail_panel.py
- [X] T012 [US1] Instantiate and draw middle detail panel in python/hopilot/gui_components/aof_browser_panel.py
- [X] T013 [US1] Feed selected-cell view model into panel draw pipeline in python/hopilot/gui_components/aof_browser_panel.py
- [X] T014 [US1] Handle selection invalidation on payload/context refresh in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Metric-Aware Detail Visualization (Priority: P2)

**Goal**: Provide metric-specific visual detail for selected cells, including stacked win/tie/loss and status-aware fallbacks.

**Independent Test**: With a selected cell, switch metrics and verify visual/value changes; verify fallback views for non-available statuses.

### Tests for User Story 2

- [X] T015 [P] [US2] Add WIN_LOSE_PROBABILITY segment composition test in tests/test_aof_gto_browser_gui.py
- [X] T016 [P] [US2] Add metric-switch detail update regression test in tests/test_gto_gui_integration.py
- [X] T017 [P] [US2] Add fallback-status rendering tests for MISSING/TIMEOUT/ERROR/NO_CONTEST in tests/test_aof_gto_browser_gui.py
- [X] T029 [P] [US2] Add scenario-context refresh regression test (position/action-state change with same selected cell) in tests/test_gto_gui_integration.py

### Implementation for User Story 2

- [X] T018 [US2] Implement vertical stacked win/tie/loss rendering and labels in python/hopilot/gui_components/aof_cell_detail_panel.py
- [X] T019 [US2] Implement scalar metric rendering for EV/EQUITY/EQR in python/hopilot/gui_components/aof_cell_detail_panel.py
- [X] T020 [US2] Map payload metrics/status into panel segments and display values in python/hopilot/gui_components/aof_browser_panel.py
- [X] T021 [US2] Implement explicit status fallback copy and styles in python/hopilot/gui_components/aof_cell_detail_panel.py

**Checkpoint**: User Story 2 is independently functional and testable.

---

## Phase 5: User Story 3 - Preserve Compact Layout and Existing Controls (Priority: P3)

**Goal**: Keep the 3-column layout compact and maintain existing right-side control behavior.

**Independent Test**: Verify matrix/middle/right columns remain visible and controls behave the same with the new panel present.

### Tests for User Story 3

- [X] T022 [P] [US3] Add layout non-overlap/visibility assertions for matrix-detail-right columns in tests/test_gto_gui_integration.py
- [X] T023 [P] [US3] Add right-side precompute control regression test with middle panel active in tests/test_gto_gui_integration.py

### Implementation for User Story 3

- [X] T024 [US3] Finalize compact width budgeting and reflow math for 3-column layout in python/hopilot/gui_components/aof_browser_panel.py
- [X] T025 [US3] Ensure event routing preserves right-control interactions after middle panel integration in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: User Story 3 is independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup across stories.

- [X] T026 [P] Update feature validation steps and expected outcomes in specs/001-cell-detail-panel/quickstart.md
- [X] T027 Run targeted GUI test suites and record final verification notes in specs/001-cell-detail-panel/quickstart.md
- [X] T028 [P] Refine panel readability styles and concise comments in python/hopilot/gui_components/aof_cell_detail_panel.py

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): starts immediately.
- Foundational (Phase 2): depends on Setup completion and blocks all stories.
- User Story phases (3-5): depend on Foundational completion.
- Polish (Phase 6): depends on all targeted stories being complete.

### User Story Dependencies

- US1 (P1): starts after Phase 2; no dependency on other stories.
- US2 (P2): starts after Phase 2; can reuse US1 selection plumbing but must remain independently testable.
- US3 (P3): starts after Phase 2; validates layout/interaction regression with US1/US2 integrated.

### Within Each User Story

- Write tests first and ensure they fail before implementation.
- Implement rendering/model logic after test scaffolds exist.
- Verify each story independently before moving on.

## Parallel Opportunities

- Phase 1: T002 and T003 can run in parallel after T001.
- Phase 2: T005 can run in parallel with T004; T007 and T008 can proceed in parallel once T006 is complete.
- US1: T009 and T010 can run in parallel; T012 and T013 can run in parallel after T011.
- US2: T015, T016, T017, and T029 can run in parallel; T018 and T019 can run in parallel before T020/T021 integration.
- US3: T022 and T023 can run in parallel.

## Parallel Example: User Story 1

- Run T009 and T010 together in tests/test_aof_gto_browser_gui.py
- Run T012 and T013 together in python/hopilot/gui_components/aof_browser_panel.py and python/hopilot/gui_components/aof_cell_detail_panel.py

## Parallel Example: User Story 2

- Run T015, T016, T017, and T029 together in tests/test_aof_gto_browser_gui.py and tests/test_gto_gui_integration.py
- Run T018 and T019 together in python/hopilot/gui_components/aof_cell_detail_panel.py

## Parallel Example: User Story 3

- Run T022 and T023 together in tests/test_gto_gui_integration.py

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 (Phase 3).
3. Validate US1 independently using its test tasks.
4. Demo/ship MVP behavior if desired.

### Incremental Delivery

1. Ship US1 for selected-cell detail baseline.
2. Add US2 for metric-aware visuals and fallbacks.
3. Add US3 for compact layout guarantees and control regression protection.

### Team Parallel Strategy

1. One engineer handles selection/layout plumbing (Phase 2 + US3 integration).
2. One engineer handles detail rendering component (US1/US2 implementation tasks).
3. One engineer handles tests (US1/US2/US3 test tasks) in parallel after foundational hooks exist.
