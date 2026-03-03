# Tasks: All-In-or-Fold GTO Solver with Bonus Payouts

**Input**: Design documents from `/specs/001-all-in-fold-gto/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included as requested in the feature specification for comprehensive validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- Source code: `python/hopilot/` (existing structure)
- New GTO components: `python/hopilot/gto/`
- GUI components: `python/hopilot/gui_components/`
- Tests: `tests/`
- Config: `config/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create GTO subdirectory structure in python/hopilot/gto/
- [x] T002 Create GUI component directories in python/hopilot/gui_components/
- [x] T003 [P] Configure default bonus payout configuration in config/gto_defaults.yaml
- [x] T004 [P] Update requirements.txt with any new dependencies (if needed)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Extend AllInFoldGTOSolver class in python/hopilot/all_in_fold_gto.py with bonus payout support
- [x] T006 [P] Create PokerRange Pydantic model in python/hopilot/hand_range.py
- [x] T007 [P] Create GTOParameters and GTOResult models in python/hopilot/gto/gto_models.py
- [x] T008 [P] Create RangeManager class in python/hopilot/gto/range_manager.py
- [x] T009 [P] Create base GTOOptimizer class in python/hopilot/gto/gto_optimizer.py
- [x] T010 Setup logging configuration for GTO components using existing logging_config

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic GTO Threshold Analysis (Priority: P1) 🎯 MVP

**Goal**: Enable calculation of GTO equity thresholds for all-in-or-fold games with bonus payouts

**Independent Test**: Can be fully tested by running the solver with specific parameters and verifying threshold calculation matches expected GTO theory

### Tests for User Story 1 ⚠️

- [x] T011 [P] [US1] Unit tests for GTO threshold calculation in tests/test_all_in_fold_gto.py
- [x] T012 [P] [US1] Contract tests for AllInFoldGTOSolver API in tests/test_gto_solver_contract.py

### Implementation for User Story 1

- [x] T013 [US1] Implement bonus payout integration in AllInFoldGTOSolver._calculate_ev_with_bonus()
- [x] T014 [US1] Implement find_gto_threshold() method with Monte Carlo simulation
- [x] T015 [US1] Add parameter validation for GTO calculations
- [x] T016 [US1] Add progress tracking and cancellation support
- [x] T017 [US1] Add result caching for performance optimization

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Range Management and Persistence (Priority: P2)

**Goal**: Enable creation, saving, and loading of poker hand ranges in YAML format

**Independent Test**: Can be fully tested by creating ranges, saving to YAML, loading them back, and verifying data integrity

### Tests for User Story 2 ⚠️

- [x] T018 [P] [US2] Unit tests for RangeManager in tests/test_range_manager.py
- [x] T019 [P] [US2] YAML validation tests in tests/test_range_format.py

### Implementation for User Story 2

- [x] T020 [P] [US2] Implement PokerRange model validation in python/hopilot/hand_range.py
- [x] T021 [P] [US2] Implement RangeManager.save_range() method
- [x] T022 [P] [US2] Implement RangeManager.load_range() method
- [x] T023 [US2] Implement range listing and deletion methods
- [x] T024 [US2] Add YAML schema validation for range files
- [x] T025 [US2] Add error handling for invalid range files

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Interactive Strategy Visualization (Priority: P3)

**Goal**: Provide visual representation of GTO results with color-coded strategy recommendations

**Independent Test**: Can be fully tested by generating strategy data and verifying correct visual representation

### Tests for User Story 3 ⚠️

- [x] T026 [P] [US3] Unit tests for strategy visualization logic in tests/test_strategy_visualizer.py
- [x] T027 [P] [US3] GUI component tests for StrategyVisualizer in tests/test_strategy_visualizer_gui.py

### Implementation for User Story 3

- [x] T028 [P] [US3] Create StrategyVisualizer GUI component in python/hopilot/gui_components/strategy_visualizer.py
- [x] T029 [P] [US3] Implement hand grid display with color coding
- [x] T030 [P] [US3] Implement EV breakdown on hand selection
- [x] T031 [US3] Add result export functionality
- [x] T032 [US3] Integrate with existing GUI event handling patterns

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: User Story 4 - Range vs Range Optimization ✅ COMPLETED (Priority: P4)

**Goal**: Enable optimization of opening ranges against opponent ranges using Nash equilibrium

**Independent Test**: Can be fully tested by providing two ranges and verifying Nash equilibrium solutions are found

### Tests for User Story 4 ⚠️

- [x] T033 [P] [US4] Unit tests for range optimization in tests/test_gto_optimizer.py
- [x] T034 [P] [US4] Integration tests for hero vs villain analysis in tests/test_range_vs_range.py

### Implementation for User Story 4

- [x] T035 [US4] Implement push-fold Nash equilibrium algorithm using dynamic programming in GTOOptimizer
- [x] T036 [US4] Add range vs range equity calculation methods for shove/fold matchups
- [x] T037 [US4] Implement optimal shove frequency calculation for each hand using indifference points
- [x] T038 [US4] Add support for asymmetric stack sizes with ICM considerations
- [x] T039 [US4] Add convergence checking for Nash equilibrium solutions using best response validation

---

## Phase 7: User Story 5 - GUI Integration (Priority: P5)

**Goal**: Integrate GTO solver into main HoPilot GUI with simple form-based interface

**Independent Test**: Can be fully tested by interacting with GUI elements and verifying correct solver integration

### Tests for User Story 5 ⚠️

- [x] T040 [P] [US5] GUI integration tests in tests/test_gto_solver_panel.py
- [x] T041 [P] [US5] End-to-end GUI workflow tests in tests/test_gto_gui_integration.py

### Implementation for User Story 5

- [x] T042 [P] [US5] Create GTOSolverPanel GUI component in python/hopilot/gui_components/gto_solver_panel.py
- [x] T043 [P] [US5] Implement parameter input form (opponents, pot size, bet amount, bonuses)
- [x] T044 [P] [US5] Add range file picker integration
- [x] T045 [US5] Implement calculate button and result display
- [x] T046 [US5] Add progress indicators for long-running calculations
- [x] T047 [US5] Integrate panel into main HoPilot GUI navigation

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T048 [P] Documentation updates in docs/ for GTO solver features
- [ ] T049 Code cleanup and refactoring across GTO components
- [ ] T050 Performance optimization for simulation caching
- [ ] T051 [P] Additional unit tests for edge cases in tests/
- [ ] T052 Security validation for YAML file handling
- [ ] T053 Run quickstart.md validation and update examples

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of other stories
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May use US1 results but independently testable
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Builds on US1/US2 but independently testable
- **User Story 5 (P5)**: Can start after Foundational (Phase 2) - Integrates all stories but can be tested independently

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Core logic before GUI integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for GTO threshold calculation in tests/test_all_in_fold_gto.py"
Task: "Contract tests for AllInFoldGTOSolver API in tests/test_gto_solver_contract.py"

# Launch core implementation tasks:
Task: "Implement bonus payout integration in AllInFoldGTOSolver._calculate_ev_with_bonus()"
Task: "Implement find_gto_threshold() method with Monte Carlo simulation"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently with command-line interface
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Add User Story 5 → Test independently → Deploy/Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Core GTO Logic)
   - Developer B: User Story 2 (Range Management)
   - Developer C: User Stories 3-5 (GUI & Advanced Features)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-all-in-fold-gto\tasks.md