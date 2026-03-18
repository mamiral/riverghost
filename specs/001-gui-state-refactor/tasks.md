# Implementation Tasks: Refactor GuiRunState State Machine Using Transitions Library

**Feature Branch**: `001-gui-state-refactor`
**Created**: March 18, 2026
**Status**: Ready for Implementation
**Spec**: [specs/001-gui-state-refactor/spec.md](specs/001-gui-state-refactor/spec.md)
**Plan**: [specs/001-gui-state-refactor/plan.md](specs/001-gui-state-refactor/plan.md)

## Task Organization

This feature implements a robust state machine using the transitions library to replace the flawed manual GuiRunState logic. Tasks are organized by user story with dependencies clearly marked.

**Total Tasks**: 24
**User Stories**: 4
**Parallel Opportunities**: 8 tasks marked with [P]
**MVP Scope**: User Story 1 (Start Simulation) - 6 core tasks

## Phase 1: Setup (Project Initialization)

- [X] T001 Create feature branch and verify environment setup
- [X] T002 Install transitions==0.9.3 dependency in virtual environment
- [X] T003 Update requirements.txt with transitions dependency
- [X] T004 Verify transitions library import and basic functionality

## Phase 2: Foundational (Shared Infrastructure)

- [X] T005 [P] Create state machine configuration module in `python/hopilot/`
- [X] T006 [P] Define state and transition constants for type safety
- [X] T007 [P] Implement base state machine error handling utilities
- [X] T008 [P] Create state machine logging integration with existing logger

## Phase 3: User Story 1 - Start Precompute Simulation

**Goal**: Enable users to start precompute simulations with proper state management
**Independent Test**: Start button works, simulation begins, UI updates correctly
**Dependencies**: Phase 1, Phase 2

- [X] T009 Implement LockedMachine initialization in GuiApplication.__init__
- [X] T010 Define state definitions (idle, running, paused, stopping, completed, failed)
- [X] T011 Define start_simulation transition with validation conditions
- [X] T012 Implement on_enter_running callback for ThreadPoolExecutor creation
- [X] T013 Implement prepare_simulation callback for scenario validation
- [X] T014 Update UI button enablement logic using may_start_simulation()

## Phase 4: User Story 2 - Pause and Resume Simulation

**Goal**: Allow users to pause and resume simulations with context validation
**Independent Test**: Pause/resume buttons work, processing stops/starts correctly
**Dependencies**: Phase 3

- [X] T015 Define pause_simulation transition from running to paused
- [X] T016 Implement on_enter_paused callback for future cancellation
- [X] T017 Define resume_simulation transition with context validation
- [X] T018 Implement context_matches condition for resume validation
- [X] T019 Implement on_exit_paused callback for executor recreation
- [X] T020 Update UI button states for pause/resume enablement

## Phase 5: User Story 3 - Stop Simulation

**Goal**: Provide graceful simulation stopping with proper cleanup
**Independent Test**: Stop button works, all resources cleaned up
**Dependencies**: Phase 4

- [X] T021 Define stop_simulation transition from running/paused to stopping
- [X] T022 Implement on_enter_stopping callback for graceful shutdown
- [X] T023 Define transitions from stopping to completed/failed
- [X] T024 Implement on_exit_running callback for executor cleanup
- [X] T025 Update UI button states for stop enablement

## Phase 6: User Story 4 - Handle Simulation Errors Gracefully

**Goal**: Provide robust error handling and recovery mechanisms
**Independent Test**: Errors transition to failed state, recovery works
**Dependencies**: Phase 5

- [X] T026 Implement on_exception callback for global error handling
- [X] T027 Define fail_simulation transition for error scenarios
- [X] T028 Implement finalize_event callback for guaranteed cleanup
- [X] T029 Define reset_simulation transition from failed/completed to idle
- [X] T030 Add error state UI feedback and recovery options

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Ensure production readiness with testing, documentation, and optimization
**Dependencies**: All user story phases

- [X] T031 [P] Create comprehensive unit tests for state machine behavior
- [X] T032 [P] Implement integration tests for GUI state machine interaction
- [X] T033 [P] Add state machine performance monitoring and metrics
- [X] T034 [P] Update existing checkpoint functionality for state machine compatibility
- [X] T035 [P] Add state machine debugging and logging capabilities
- [X] T036 [P] Create state machine documentation and usage examples
- [X] T037 [P] Perform thread safety testing with concurrent operations
- [X] T038 [P] Optimize state transition performance for real-time responsiveness

## Dependencies Graph

```
Setup (T001-T004)
    ↓
Foundational (T005-T008)
    ↓
US1: Start Simulation (T009-T014)
    ↓
US2: Pause/Resume (T015-T020)
    ↓
US3: Stop Simulation (T021-T025)
    ↓
US4: Error Handling (T026-T030)
    ↓
Polish (T031-T038)
```

## Parallel Execution Opportunities

**Setup Phase**: All tasks can run in parallel
**Foundational Phase**: All tasks marked [P] can run in parallel
**User Story Phases**: Sequential due to dependencies
**Polish Phase**: All tasks marked [P] can run in parallel

## Implementation Strategy

**MVP First**: Implement User Story 1 first for basic start functionality
**Incremental Delivery**: Each user story delivers independently testable value
**Risk Mitigation**: Start with core state machine, add error handling last
**Testing Approach**: Unit tests for state logic, integration tests for GUI interaction

## Success Criteria Validation

- [ ] All 24 tasks completed successfully
- [ ] Each user story independently testable
- [ ] State machine behavior matches simulation_control_logic_analysis.md
- [ ] Thread safety verified through testing
- [ ] Backward compatibility maintained
- [ ] Performance requirements met
- [ ] Code maintainability improved

## Task Format Validation

- [ ] All tasks follow strict checklist format: `- [ ] T### [P] [US#] Description with file path`
- [ ] Sequential task IDs (T001-T038)
- [ ] Parallel tasks marked with [P]
- [ ] User story tasks marked with [US#]
- [ ] Clear file paths for implementation
- [ ] Actionable descriptions for LLM execution