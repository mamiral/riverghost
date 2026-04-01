# Tasks: Fix Database Schema Remediation

**Input**: Design documents from `/specs/001-fix-db-schema-remediation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Integration tests are included as they are required to verify genuine data storage and eliminate fake data generation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure: `python/hopilot/`, `tests/` at repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create persistence strategy directory structure in python/hopilot/database/persistence/
- [x] T002 [P] Update project dependencies for Strategy pattern implementation
- [x] T003 [P] Configure database session management for strategy injection

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create GameStatePersistence abstract base class in python/hopilot/database/persistence/base.py
- [x] T005 [P] Implement DatabasePersistenceStrategy in python/hopilot/database/persistence/database.py
- [x] T006 [P] Implement MockPersistenceStrategy in python/hopilot/database/persistence/mock.py
- [x] T007 [P] Implement InMemoryPersistenceStrategy in python/hopilot/database/persistence/memory.py
- [x] T008 Modify AllInFoldGTOSolver constructor to accept persistence strategy in python/hopilot/poker_analyzer.py
- [x] T009 Update database models to support confirmed schema from specs/001-normalized-db-schema in python/hopilot/database/models.py
- [x] T010 Configure foreign key constraints and data validation in python/hopilot/database/session.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Run Genuine Game State Simulations (Priority: P1) 🎯 MVP

**Goal**: Enable running Monte Carlo simulations that capture and store complete, real game states for every simulation outcome

**Independent Test**: Can be tested by running a simulation with MockPersistenceStrategy, verifying that persistence methods are called with real game state data, not fabricated

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US1] Unit test for solver persistence injection in tests/test_solver_integration.py
- [x] T012 [P] [US1] Integration test for genuine data storage in tests/test_database_remediation.py

### Implementation for User Story 1

- [x] T013 [US1] Modify AllInFoldGTOSolver to call persistence methods during simulation in python/hopilot/poker_analyzer.py
- [x] T014 [US1] Implement game state capture logic in python/hopilot/simulation/game_state.py
- [x] T015 [US1] Add jackpot detection during simulation runs in python/hopilot/simulation/game_state.py
- [x] T016 [US1] Update simulation loop to store complete game states in python/hopilot/simulation/monte_carlo.py
- [x] T017 [US1] Remove AoFSolverAdapter references from solver initialization

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently - simulations store real GameStates, Players, Bets, and Jackpots

---

## Phase 4: User Story 2 - Derive Matrix Cells from Game States (Priority: P2)

**Goal**: Compute MatrixCells and aggregated metrics from stored GameStates data, ensuring equity calculations are based on real simulation outcomes

**Independent Test**: Can be tested by storing GameStates, running aggregation, and verifying MatrixCell values match computed statistics from the stored data

### Tests for User Story 2 ⚠️

- [x] T018 [P] [US2] Unit test for aggregation logic in tests/test_aggregation.py
- [x] T019 [P] [US2] Integration test for MatrixCell derivation in tests/test_matrix_aggregation.py

### Implementation for User Story 2

- [x] T020 [US2] Create aggregation engine to compute MatrixCells from GameStates in python/hopilot/database/aggregation.py
- [x] T021 [US2] Implement AggregatedMetrics calculation with jackpot-adjusted EV in python/hopilot/database/aggregation.py
- [x] T022 [US2] Add convergence tracking from historical GameStates data in python/hopilot/database/aggregation.py
- [x] T023 [US2] Update existing MatrixCell computation to use GameStates-first approach
- [x] T024 [US2] Add database queries for temporal analysis in python/hopilot/database/queries.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - MatrixCells are derived from real GameStates data

---

## Phase 5: User Story 3 - Detect and Store Jackpot Events (Priority: P3)

**Goal**: Detect and store jackpot events during simulations for analysis of bonus event frequencies and EV impact

**Independent Test**: Can be tested by running simulations with jackpot-eligible hands and verifying Jackpots table contains detected events with correct payout amounts

### Tests for User Story 3 ⚠️

- [ ] T025 [P] [US3] Unit test for jackpot detection logic in tests/test_jackpot_detection.py
- [ ] T026 [P] [US3] Integration test for jackpot storage in tests/test_jackpot_storage.py

### Implementation for User Story 3

- [ ] T027 [US3] Implement jackpot detection rules (straight flush, royal flush) in python/hopilot/simulation/jackpot_detector.py
- [ ] T028 [US3] Add jackpot payout calculation logic in python/hopilot/simulation/jackpot_detector.py
- [ ] T029 [US3] Integrate jackpot detection into game state capture in python/hopilot/simulation/game_state.py
- [ ] T030 [US3] Update persistence strategies to store jackpot events in python/hopilot/database/persistence/
- [ ] T031 [US3] Add jackpot frequency analysis queries in python/hopilot/database/queries.py

**Checkpoint**: All user stories should now be independently functional - jackpot events are detected and stored during simulations

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, performance optimization, and quality improvements

- [ ] T032 [P] Add comprehensive error handling and logging throughout persistence layer
- [ ] T033 [P] Implement performance monitoring for simulation processing times
- [ ] T034 [P] Add data integrity validation checks in persistence strategies
- [ ] T035 [P] Create database migration scripts for schema updates - DEFFERED
- [ ] T036 [P] Add configuration management for different persistence strategies
- [ ] T037 [P] Implement cleanup utilities for test data management
- [ ] T038 [P] Add documentation for Strategy pattern usage and extension
- [ ] T039 [P] Performance optimization for large-scale simulation data storage

**Final Checkpoint**: Complete genuine GameStates-first architecture with all requirements satisfied

---

## Dependencies & Parallel Execution

**Story Completion Order:**
- US1 (P1) → US2 (P2) → US3 (P3) → Polish

**Parallel Opportunities:**
- Within each story: Tests can run in parallel with implementation
- Across stories: US2 and US3 can begin once US1 foundation is complete
- Setup tasks: T001-T003 can run in parallel
- Foundation tasks: T004-T010 have some parallel dependencies

**Total Tasks**: 39
**Parallelizable**: 18 tasks (46%)
**Test Tasks**: 8 tasks (21%)
**Suggested MVP**: Complete US1 for genuine simulation data capture