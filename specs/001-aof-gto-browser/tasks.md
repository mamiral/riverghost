# Tasks: Standalone AoF GTO Solution Browser

**Input**: Design documents from `/specs/001-aof-gto-browser/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included because the specification requires simulator regression protection (SC-005) and independently testable user stories.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create standalone AoF browser scaffolding and test harness.

- [X] T001 Create standalone AoF app entry module in python/hopilot/aof_gto_browser_gui.py
- [X] T002 [P] Create AoF browser panel scaffold in python/hopilot/gui_components/aof_browser_panel.py
- [X] T003 [P] Create AoF browser GUI test scaffold in tests/test_aof_gto_browser_gui.py
- [X] T004 [P] Add deterministic AoF browser fixture dataset in tests/data/aof_browser_fixture.yaml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Remove simulator coupling and establish shared AoF browser data/state infrastructure.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Remove GTO navigation and panel wiring from simulator in python/hopilot/poker_simulator_gui.py
- [X] T006 Remove simulator run_gto event path and analysis hook in python/hopilot/poker_simulator_gui.py
- [X] T007 Remove AoF controls/results coupling from simulation panel in python/hopilot/gui_components/simulation_panel.py
- [X] T008 [P] Implement AoF browser view-state model in python/hopilot/gto/aof_browser_state.py
- [X] T009 [P] Implement canonical 13x13 hand-matrix topology utilities in python/hopilot/gto/aof_hand_matrix.py
- [X] T010 Implement context-based matrix data provider in python/hopilot/gto/aof_browser_data_provider.py
- [X] T011 Update simulator regression tests for decoupled GUI behavior in tests/test_poker_simulator_gui.py
- [X] T012 Update simulation panel regression tests after AoF removal in tests/test_simulation_panel.py

**Checkpoint**: Foundation complete, standalone AoF stories can now be implemented.

---

## Phase 3: User Story 1 - Browse Position-Specific Preflop Strategy (Priority: P1) MVP

**Goal**: User can open standalone AoF app, select UTG/BTN/SB/BB, and see matrix updates.

**Independent Test**: Launch standalone AoF app and switch all four positions to verify matrix refreshes per selection.

### Tests for User Story 1

- [X] T013 [P] [US1] Add position-selector interaction tests in tests/test_aof_gto_browser_gui.py
- [X] T014 [P] [US1] Add matrix refresh integration test for position changes in tests/test_gto_gui_integration.py

### Implementation for User Story 1

- [X] T015 [P] [US1] Implement four-position selector component (UTG/BTN/SB/BB) in python/hopilot/gui_components/aof_position_selector.py
- [X] T016 [P] [US1] Implement matrix rendering panel baseline in python/hopilot/gui_components/aof_hand_matrix_panel.py
- [X] T017 [US1] Implement AoF browser panel composition and state binding in python/hopilot/gui_components/aof_browser_panel.py
- [X] T018 [US1] Wire standalone AoF app event loop and lower-middle matrix layout in python/hopilot/aof_gto_browser_gui.py
- [X] T019 [US1] Add position-change data fetch and redraw flow in python/hopilot/gto/aof_browser_data_provider.py

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Explore Action Outcomes by Position (Priority: P2)

**Goal**: User can toggle fold/all-in for a selected position and compare matrix outcomes.

**Independent Test**: Keep one position selected, toggle fold/all-in, and confirm matrix values change accordingly.

### Tests for User Story 2

- [X] T020 [P] [US2] Add action-toggle behavior tests in tests/test_aof_gto_browser_gui.py
- [X] T021 [P] [US2] Add fold-vs-all-in matrix value change test in tests/test_gto_gui_integration.py

### Implementation for User Story 2

- [X] T022 [P] [US2] Implement fold/all-in action selector component in python/hopilot/gui_components/aof_action_selector.py
- [X] T023 [US2] Extend AoF browser state to include selected action context in python/hopilot/gto/aof_browser_state.py
- [X] T024 [US2] Implement action-aware matrix dataset lookup in python/hopilot/gto/aof_browser_data_provider.py
- [X] T025 [US2] Integrate action selector events into browser panel refresh flow in python/hopilot/gui_components/aof_browser_panel.py
- [X] T026 [US2] Render active action context and per-cell action output in python/hopilot/gui_components/aof_hand_matrix_panel.py

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Compare Different Matrix Metrics (Priority: P3)

**Goal**: User can switch metric dropdown between win/lose probability, EV, equity, and EQR.

**Independent Test**: With fixed position/action, switch all four metrics and verify matrix semantics update without stale values.

### Tests for User Story 3

- [X] T027 [P] [US3] Add metric dropdown option and selection tests in tests/test_aof_gto_browser_gui.py
- [X] T028 [P] [US3] Add matrix metric-switch integration test in tests/test_gto_gui_integration.py

### Implementation for User Story 3

- [X] T029 [P] [US3] Implement metric dropdown component with four required options in python/hopilot/gui_components/aof_metric_dropdown.py
- [X] T030 [US3] Add metric-type mapping and formatting rules in python/hopilot/gto/aof_hand_matrix.py
- [X] T031 [US3] Implement metric-aware dataset selection in python/hopilot/gto/aof_browser_data_provider.py
- [X] T032 [US3] Integrate metric dropdown events into browser panel state transitions in python/hopilot/gui_components/aof_browser_panel.py
- [X] T033 [US3] Implement missing/invalid data placeholder rendering in python/hopilot/gui_components/aof_hand_matrix_panel.py

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, documentation, and verification.

- [X] T034 [P] Update standalone AoF run and verification instructions in specs/001-aof-gto-browser/quickstart.md
- [X] T035 Remove dead imports and stale simulator references after decoupling in python/hopilot/poker_simulator_gui.py
- [X] T036 [P] Add rapid-switching and empty-state regression tests in tests/test_aof_gto_browser_gui.py
- [X] T037 [P] Document standalone AoF usage and simulator separation in docs/initial_design/USAGE_GUIDE_WIN.md
- [X] T038 Run full feature validation command list and record results in specs/001-aof-gto-browser/quickstart.md
- [ ] T039 [P] Run UAT for control discoverability (minimum 10 participants) and record pass rate for identifying position, action, and metric in specs/001-aof-gto-browser/quickstart.md
- [X] T040 [P] Add UAT execution checklist and result template in specs/001-aof-gto-browser/checklists/usability-uat.md
- [X] T041 [P] Add startup time measurement test (target <=30s) in tests/test_aof_gto_browser_gui.py
- [X] T042 [P] Add position-switch latency benchmark assertions (target <=1s p95) in tests/test_gto_gui_integration.py
- [X] T043 [P] Add action-switch latency benchmark assertions (target <=1s p95) in tests/test_gto_gui_integration.py
- [X] T044 [P] Add metric-switch latency benchmark assertions (target <=1s p95) in tests/test_gto_gui_integration.py
- [X] T045 Record benchmark method, environment, and results in specs/001-aof-gto-browser/quickstart.md
- [X] T046 [P] Add combined active-state highlighting test for position, action, and metric in tests/test_aof_gto_browser_gui.py

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 (Setup): no dependencies
- Phase 2 (Foundational): depends on Phase 1 and blocks all user stories
- Phase 3 (US1): depends on Phase 2
- Phase 4 (US2): depends on Phase 2 and uses US1 UI composition
- Phase 5 (US3): depends on Phase 2 and uses US1 UI composition
- Phase 6 (Polish): depends on completion of selected user stories and closes with UAT/performance evidence capture

### User Story Dependencies

- US1 (P1): starts after foundational phase; no dependency on other stories
- US2 (P2): starts after foundational phase; independently testable once shared browser scaffolding from setup/foundation exists
- US3 (P3): starts after foundational phase; independently testable once shared browser scaffolding from setup/foundation exists

### Within Each User Story

- Tests first and confirm they fail before implementation changes
- Components/models before panel integration
- Data provider updates before final redraw wiring
- Story validation must pass before closing story checkpoint

## Parallel Opportunities

- Setup: T002, T003, and T004 can run in parallel after T001
- Foundational: T008 and T009 can run in parallel, then T010
- US1: T013/T014 parallel; T015/T016 parallel; then T017/T018/T019 sequence
- US2: T020/T021 parallel; then T022 and T023; then T024/T025/T026
- US3: T027/T028 parallel; then T029/T030; then T031/T032/T033
- Polish: T034, T036, T037, T039, T040, T041, T042, T043, T044, and T046 can run in parallel; T038 and T045 close phase

---

## Parallel Example: User Story 1

```bash
# Tests in parallel
Task T013 in tests/test_aof_gto_browser_gui.py
Task T014 in tests/test_gto_gui_integration.py

# Components in parallel
Task T015 in python/hopilot/gui_components/aof_position_selector.py
Task T016 in python/hopilot/gui_components/aof_hand_matrix_panel.py
```

## Parallel Example: User Story 2

```bash
# Tests in parallel
Task T020 in tests/test_aof_gto_browser_gui.py
Task T021 in tests/test_gto_gui_integration.py

# Independent implementation kickoff
Task T022 in python/hopilot/gui_components/aof_action_selector.py
Task T023 in python/hopilot/gto/aof_browser_state.py
```

## Parallel Example: User Story 3

```bash
# Tests in parallel
Task T027 in tests/test_aof_gto_browser_gui.py
Task T028 in tests/test_gto_gui_integration.py

# Independent implementation kickoff
Task T029 in python/hopilot/gui_components/aof_metric_dropdown.py
Task T030 in python/hopilot/gto/aof_hand_matrix.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 (Phase 3).
3. Validate independent test for US1.
4. Demo standalone position-based browsing.

### Incremental Delivery

1. Deliver MVP with US1.
2. Add US2 action switching and validate independently.
3. Add US3 metric switching and validate independently.
4. Finish polish and regression verification.

### Parallel Team Strategy

1. Team aligns on Setup + Foundational.
2. After foundational completion:
   - Developer A: US1 panel and app shell
   - Developer B: US2 action flow
   - Developer C: US3 metric flow
3. Merge on shared browser panel contracts and run full regression suite.

---

## Notes

- [P] tasks are file-isolated and can run in parallel safely.
- Story labels map every implementation task back to user-facing value.
- Keep simulator pristine during implementation to satisfy FR-002.
- Preserve centralized logging and pytest coverage per constitution requirements.
