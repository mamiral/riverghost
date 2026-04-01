# Tasks: Test Suite Cleanup

**Input**: Design documents from `/specs/001-test-suite-cleanup/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Ensure pytest environment is configured in tests/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Remove Placeholder Tests (Priority: P1) 🎯 MVP

**Goal**: Identify and remove tests that contain only placeholder code to establish a clean baseline for test coverage.

**Independent Test**: Run the test suite and verify that removed tests no longer appear in test output, and that no new failures are introduced in remaining tests.

### Implementation for User Story 1

- [x] T002 [US1] Remove placeholder test_table_creation from tests/test_models.py that contains only pass
- [x] T003 [US1] Remove or rewrite tests with TODO comments in tests/test_aof_gui_precompute_runner_canonical_dedup.py indicating incomplete implementation
- [x] T004 [US1] Remove or rewrite test_find_gto_threshold_basic_functionality in tests/test_all_in_fold_gto.py that mocks internal methods with placeholder comments

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Rewrite Meaningless Assertions (Priority: P2)

**Goal**: Replace trivial assert True statements with meaningful assertions that validate actual functionality.

**Independent Test**: Run individual test methods and verify they fail when expected conditions are not met, and pass when functionality works correctly.

### Implementation for User Story 2

- [x] T005 [P] [US2] Replace assert True at line 175 in tests/test_db_browser_integration.py with meaningful database integration validation
- [x] T006 [P] [US2] Replace assert True at line 211 in tests/test_db_browser_integration.py with meaningful database integration validation
- [x] T007 [P] [US2] Replace assert True at line 340 in tests/test_db_browser_integration.py with meaningful database integration validation
- [x] T008 [P] [US2] Replace assert True at line 370 in tests/test_db_browser_integration.py with meaningful database integration validation
- [x] T009 [P] [US2] Replace assert True at line 399 in tests/test_db_browser_integration.py with meaningful database integration validation
- [x] T010 [P] [US2] Replace assert True at line 593 in tests/test_db_browser_integration.py with meaningful database integration validation
- [x] T011 [P] [US2] Replace assert True at line 662 in tests/test_db_browser_integration.py with meaningful database integration validation
- [x] T012 [US2] Replace assert True at line 157 in tests/test_incremental_aggregation.py with meaningful incremental aggregation logic validation

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Fix Tests Expecting Deterministic Results from Random Behavior (Priority: P2)

**Goal**: Rewrite tests to properly handle non-deterministic behavior rather than expecting fixed results.

**Independent Test**: Run the test multiple times and verify it passes consistently, while still validating the underlying logic.

### Implementation for User Story 3

- [x] T013 [US3] Rewrite test_calculate_cell_equity in tests/test_jackpot_metrics.py to handle random win determination without expecting fixed 0.6 equity

**Checkpoint**: At this point, User Stories 1, 2 AND 3 should all work independently

---

## Phase 6: User Story 4 - Enhance Existence-Only Tests (Priority: P3)

**Goal**: Enhance tests to validate actual content and functionality rather than just checking object existence.

**Independent Test**: Modify the underlying implementation to return invalid data and verify the tests fail appropriately.

### Implementation for User Story 4

- [x] T014 [US4] Enhance tests in tests/test_aof_browser_panel_database_integration.py to validate actual payload content instead of only checking panel.payload is not None
- [x] T015 [US4] Replace assert result is not None checks in tests/test_aggregation_engine_comprehensive.py with content validation of aggregation results
- [x] T016 [US4] Complete assertions in tests/test_browser_database_provider_persistence.py to validate persistence behavior comprehensively

**Checkpoint**: At this point, User Stories 1, 2, 3 AND 4 should all work independently

---

## Phase 7: User Story 5 - Remove Mock-Heavy Tests (Priority: P3)

**Goal**: Rewrite tests to validate real implementation rather than mocked interactions.

**Independent Test**: Run tests against actual implementations and verify they exercise real code paths.

### Implementation for User Story 5

- [x] T017 [US5] Rewrite tests in tests/test_aof_gui_precompute_runner_canonical_dedup.py to test actual deduplication implementation instead of using mocks
- [x] T018 [US5] Rewrite test_find_gto_threshold_basic_functionality in tests/test_all_in_fold_gto.py to validate real GTO threshold finding logic instead of mocking internal methods

**Checkpoint**: All user stories should now be independently functional

---

## Phase 9: Integration Tests for Mock-Heavy Tests

**Purpose**: Replace mock-testing tests with proper integration tests

- [x] T021 Create integration test for AOF browser panel database integration (replaces mock call count test)
- [x] T022 Create integration test for browser database provider (replaces mock called assertions)
- [x] T023 Create integration test for dashboard commands (replaces mock logger called assertion)
- [x] T024 Create integration test for precompute runner (replaces mock called assertion)
- [x] T025 Create integration test for state machine controller (replaces mock call count assertion)

**Checkpoint**: All mock-heavy tests have been replaced with proper integration tests

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
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tasks for a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 2

```bash
# Run all US2 tasks in parallel
pytest tests/test_db_browser_integration.py::test_method_at_line_175 -v &
pytest tests/test_db_browser_integration.py::test_method_at_line_211 -v &
pytest tests/test_db_browser_integration.py::test_method_at_line_340 -v &
pytest tests/test_db_browser_integration.py::test_method_at_line_370 -v &
pytest tests/test_db_browser_integration.py::test_method_at_line_399 -v &
pytest tests/test_db_browser_integration.py::test_method_at_line_593 -v &
pytest tests/test_db_browser_integration.py::test_method_at_line_662 -v &
pytest tests/test_incremental_aggregation.py::test_method_at_line_157 -v &
wait
```

---

## Implementation Strategy

**MVP Scope**: User Story 1 (P1) - Establish clean baseline by removing placeholder tests.

**Incremental Delivery**: Complete each user story in priority order, ensuring tests fail initially (red phase) until implementation is added in subsequent features.

**Task Completeness Validation**: Each task includes specific file paths and line numbers where possible, ensuring LLM can execute without additional context.

**Final Cleanup Pass**: Removed meaningless tests including:
- `test_base_model_exists` (only checked Base class existence)
- `test_connection_creation` (only checked db_connection is not None)  
- `test_session_creation` (only checked session is not None)