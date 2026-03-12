# Tasks: GTO Analysis Integration in Poker Simulator

**Input**: Design documents from `/specs/002-gto-simulator-integration/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included for key integration points to ensure the enhanced simulator works correctly.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- Source code: `python/hopilot/` (existing structure)
- GUI components: `python/hopilot/gui_components/`
- Tests: `tests/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create any needed backup files for existing simulator components
- [x] T002 Verify all existing simulator tests still pass before integration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Add AllInFoldGTOSolver import and instance to poker_simulator_gui.py
- [x] T004 [P] Update SimulationPanel constructor to accept GTO solver reference
- [x] T005 Setup GTO result storage in simulation panel

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - GTO Analysis in Poker Simulator (Priority: P1) 🎯 MVP

**Goal**: Enable GTO analysis directly within the poker simulator interface

**Independent Test**: Can be fully tested by running the simulator, configuring a scenario, and verifying GTO results appear alongside equity results

### Implementation for User Story 1

- [x] T006 [US1] Add "Run GTO" button to SimulationPanel in python/hopilot/gui_components/simulation_panel.py
- [x] T007 [US1] Add GTO results display area in SimulationPanel
- [x] T008 [US1] Implement run_gto_analysis() method in poker_simulator_gui.py

**Checkpoint**: At this point, User Story 1 should be fully functional and independently testable

---

## Phase 4: User Story 2 - Integrated GTO Configuration (Priority: P2)

**Goal**: Enable configuration of GTO parameters within the simulator interface

**Independent Test**: Can be fully tested by modifying bonus payouts and GTO parameters in the simulator and verifying they affect analysis results

### Implementation for User Story 2

- [x] T009 [US2] Add bonus payout input fields to SimulationPanel
- [x] T010 [US2] Add GTO pot size and bet amount input fields to SimulationPanel
- [x] T011 [US2] Implement bonus payout validation in SimulationPanel
- [x] T012 [US2] Connect GTO parameter inputs to analysis calculations
- [x] T013 [US2] Add preset bonus configurations for common tournament types

**Checkpoint**: All user stories should now be independently functional

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T014 [P] Update poker simulator title/caption to reflect GTO capabilities
- [ ] T015 Update quickstart documentation for enhanced simulator
- [ ] T016 Add GTO analysis tooltips and help text in simulator
- [ ] T017 Performance optimization for GTO result caching
- [ ] T018 [P] Integration tests for combined equity + GTO analysis
- [ ] T019 Security validation for GTO parameter inputs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-4)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Phase 5)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of other stories

### Within Each User Story

- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, both user stories can start in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Stories

```bash
# Launch both user stories in parallel:
Task: "Add GTO analysis button and results display in SimulationPanel"
Task: "Add bonus payout configuration inputs to SimulationPanel"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently with enhanced simulator
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (GTO Analysis Integration)
   - Developer B: User Story 2 (GTO Configuration)
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
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\002-gto-simulator-integration\tasks.md