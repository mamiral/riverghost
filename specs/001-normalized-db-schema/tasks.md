# Tasks: Normalized Relational Database Schema

**Input**: Design documents from `/specs/001-normalized-db-schema/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `python/hopilot/`, `tests/` at repository root
- Paths shown below follow the project structure from plan.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create models directory structure in python/hopilot/models/
- [x] T002 Install SQLAlchemy dependency via pip install sqlalchemy
- [x] T003 [P] Configure pytest for database testing in tests/test_models.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core database infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create database connection module in python/hopilot/database.py
- [x] T005 Create base model class in python/hopilot/models/base.py
- [x] T006 Create schema creation utilities in python/hopilot/schema.py
- [x] T007 [P] Setup database session management and transaction handling
- [x] T008 Configure SQLite WAL mode and connection pooling

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Run Poker Simulations with Full Data Persistence (Priority: P1) 🎯 MVP

**Goal**: Enable running Monte Carlo simulations for all-in-or-fold games with complete data storage for analysis and replay

**Independent Test**: Can be fully tested by running a simulation, verifying data is stored in Simulations, HandMatrices, MatrixCells, GameStates, Players, Bets, and BoardCards tables with proper relationships, and querying historical convergence data.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US1] Unit tests for model creation and relationships in tests/test_models.py
- [ ] T010 [P] [US1] Integration test for simulation data persistence in tests/test_database.py

### Implementation for User Story 1

- [x] T011 [P] [US1] Create Simulation model in python/hopilot/models/simulation.py
- [x] T012 [P] [US1] Create HandMatrix model in python/hopilot/models/hand_matrix.py
- [x] T013 [P] [US1] Create MatrixCell model in python/hopilot/models/matrix_cell.py
- [x] T014 [P] [US1] Create GameState model in python/hopilot/models/game_state.py
- [x] T015 [P] [US1] Create Player model in python/hopilot/models/player.py
- [x] T016 [P] [US1] Create Bet model in python/hopilot/models/bet.py
- [x] T017 [P] [US1] Create BoardCard model in python/hopilot/models/board_card.py
- [x] T018 [US1] Implement bulk game state insertion in database.py (depends on all models)
- [x] T019 [US1] Add foreign key constraints and relationships between all US1 models
- [x] T020 [US1] Create database indexes for performance on frequently queried columns

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Analyze Jackpot Frequencies and EV Impact (Priority: P2)

**Goal**: Track jackpot events during simulations and calculate how they affect expected value calculations

**Independent Test**: Can be fully tested by simulating games with jackpot triggers, verifying jackpot events are recorded in Jackpots table, and confirming EV calculations in AggregatedMetrics include jackpot payouts.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T021 [P] [US2] Unit tests for jackpot event recording in tests/test_models.py
- [ ] T022 [P] [US2] Integration test for EV calculations with jackpots in tests/test_database.py

### Implementation for User Story 2

- [x] T023 [P] [US2] Create Jackpot model in python/hopilot/models/jackpot.py
- [x] T024 [P] [US2] Create AggregatedMetric model in python/hopilot/models/aggregated_metric.py
- [x] T025 [US2] Implement jackpot event detection and recording logic
- [x] T026 [US2] Add jackpot-adjusted EV calculation functions
- [x] T027 [US2] Create aggregated metrics computation and updating system
- [ ] T028 [US2] Add database triggers or scheduled jobs for metrics recalculation

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Query and Extend Database Schema (Priority: P3) 🎯 CURRENT PHASE

**Goal**: Perform complex queries across the normalized schema and easily add new tables for future game features

**Independent Test**: Can be fully tested by executing the provided query examples from spec.md and successfully adding a new table with foreign key relationships.

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T029 [P] [US3] Unit tests for query functions in tests/test_queries.py
- [ ] T030 [P] [US3] Integration test for schema extension in tests/test_database.py

### Implementation for User Story 3

- [x] T031 [P] [US3] Create query service module in python/hopilot/queries.py
- [x] T032 [US3] Implement complex analytical queries (equity analysis, jackpot statistics, game replay)
- [x] T033 [US3] Add schema extension utilities for adding new tables
- [x] T034 [US3] Implement query optimization and performance monitoring
- [x] T035 [US3] Create database migration support for schema evolution

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns 🎯 CURRENT PHASE

**Purpose**: Improvements that affect multiple user stories

- [x] T036 [P] Documentation updates in docs/ and code docstrings
- [x] T037 Code cleanup and SQLAlchemy best practices implementation
- [x] T038 Performance optimization across all database operations
- [x] T039 [P] Additional unit tests for edge cases in tests/
- [x] T040 Security hardening and input validation
- [x] T041 Run quickstart.md validation and update examples

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
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
# Launch all models for User Story 1 together:
Task: "Create Simulation model in python/hopilot/models/simulation.py"
Task: "Create HandMatrix model in python/hopilot/models/hand_matrix.py"
Task: "Create MatrixCell model in python/hopilot/models/matrix_cell.py"
Task: "Create GameState model in python/hopilot/models/game_state.py"
Task: "Create Player model in python/hopilot/models/player.py"
Task: "Create Bet model in python/hopilot/models/bet.py"
Task: "Create BoardCard model in python/hopilot/models/board_card.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
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
<parameter name="filePath">C:\Users\U446541\sandbox\riverghost\specs\001-normalized-db-schema\tasks.md