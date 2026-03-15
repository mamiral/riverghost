# Tasks: Aggregated AoF Run Statistics Database

**Input**: Design documents from `/specs/001-aggregated-aof-stats/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included as requested in the feature specification for comprehensive validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `python/hopilot/`, `tests/` at repository root
- Paths adjusted based on plan.md structure for desktop GUI application

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database schema and configuration setup for aggregation feature

- [x] T001 Create SQLAlchemy models for Scenario, Run, Statistics entities in python/hopilot/gto/aof_aggregation_models.py
- [x] T002 [P] Add aggregation configuration flags to config/gto_defaults.yaml
- [x] T003 Initialize aggregation database tables in python/hopilot/gto/aof_scenario_cache_store.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core aggregation logic that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement weighted average aggregation math functions in python/hopilot/gto/aof_aggregation_math.py
- [x] T005 [P] Implement confidence score calculation from sample counts in python/hopilot/gto/aof_aggregation_math.py
- [x] T006 [P] Implement scenario keying policy (merge runtime params) in python/hopilot/gto/aof_browser_data_provider.py
- [x] T007 Implement migration logic from snapshot to aggregation tables in python/hopilot/gto/aof_scenario_cache_store.py
- [x] T008 [P] Implement degraded status aggregation rules in python/hopilot/gto/aof_aggregation_math.py
- [x] T009 Add feature flag support for aggregation/coexistence mode in python/hopilot/gto/aof_browser_data_provider.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Cumulative Evidence Aggregation (Priority: P1) 🎯 MVP

**Goal**: Enable appending new simulation evidence to existing scenario data for improved accuracy

**Independent Test**: Run same scenario multiple times and verify sample counts increase, metrics converge

### Tests for User Story 1 ⚠️

- [x] T010 [P] [US1] Unit test for aggregation math functions in tests/test_aggregation.py
- [x] T011 [P] [US1] Unit test for confidence calculation in tests/test_aggregation.py
- [x] T012 [US1] Integration test for repeated scenario runs increasing sample counts in tests/test_gto_gui_integration.py

### Implementation for User Story 1

- [x] T013 [US1] Implement store_run method in AggregationService contract in python/hopilot/gto/aof_scenario_cache_store.py
- [x] T014 [US1] Implement aggregation computation on run storage in python/hopilot/gto/aof_scenario_cache_store.py
- [x] T015 [US1] Update precompute runner to use aggregation storage in python/hopilot/gto/aof_browser_data_provider.py
- [x] T016 [US1] Add logging for aggregation operations in python/hopilot/gto/aof_scenario_cache_store.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Aggregated Scenario Loading (Priority: P1)

**Goal**: Load scenarios with results computed from all historical runs instead of single snapshots

**Independent Test**: Load scenario after multiple runs and verify aggregated results display correctly

### Tests for User Story 2 ⚠️

- [x] T017 [P] [US2] Unit test for get_aggregated_stats method in tests/test_aggregation.py
- [x] T018 [US2] Integration test for scenario loading with aggregated data in tests/test_gto_gui_integration.py

### Implementation for User Story 2

- [x] T019 [US2] Implement get_aggregated_stats method in AggregationService contract in python/hopilot/gto/aof_scenario_cache_store.py
- [x] T020 [US2] Update data provider to retrieve aggregated statistics in python/hopilot/gto/aof_browser_data_provider.py
- [x] T021 [US2] Update browser state to handle aggregated data structure in python/hopilot/gto/aof_browser_state.py
- [x] T022 [US2] Integrate with existing matrix loading flow in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Confidence Metadata Display (Priority: P2)

**Goal**: Show sample counts and confidence indicators in UI to indicate estimate reliability

**Independent Test**: Select cells and verify sample counts and confidence scores display in detail panel

### Tests for User Story 3 ⚠️

- [x] T023 [P] [US3] Unit test for confidence score display logic in tests/test_aof_gto_browser_gui.py
- [x] T024 [US3] GUI integration test for confidence metadata in cell detail panel in tests/test_gto_gui_integration.py

### Implementation for User Story 3

- [x] T025 [US3] Add confidence_score field to browser state data structures in python/hopilot/gto/aof_browser_state.py
- [x] T026 [US3] Update cell detail panel to display sample count and confidence in python/hopilot/gui_components/aof_cell_detail_panel.py
- [x] T027 [US3] Update browser panel to pass confidence data to detail view in python/hopilot/gui_components/aof_browser_panel.py
- [x] T028 [US3] Add visual indicators for confidence levels in python/hopilot/gui_components/aof_cell_detail_panel.py

**Checkpoint**: User Stories 1, 2, and 3 should now be independently functional

---

## Phase 6: User Story 4 - UI Flow Compatibility (Priority: P3)

**Goal**: Ensure existing matrix view, precompute runner, and metric switching work with aggregation

**Independent Test**: Run existing GUI tests and verify no regressions in UI flows

### Tests for User Story 4 ⚠️

- [x] T029 [US4] Regression test for metric switching with aggregated data in tests/test_gto_gui_integration.py
- [x] T030 [US4] Regression test for matrix view layout with confidence metadata in tests/test_aof_gto_browser_gui.py
- [x] T031 [US4] Regression test for precompute runner compatibility in tests/test_gto_gui_integration.py

### Implementation for User Story 4

- [x] T032 [US4] Ensure metric switching updates aggregated data display in python/hopilot/gui_components/aof_browser_panel.py
- [x] T033 [US4] Verify matrix layout accommodates confidence indicators in python/hopilot/gui_components/aof_browser_panel.py
- [x] T034 [US4] Confirm precompute runner works with aggregation storage in python/hopilot/gto/aof_browser_data_provider.py
- [x] T035 [US4] Test degraded status handling in UI flows in python/hopilot/gui_components/aof_cell_detail_panel.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and validation

- [x] T036 [P] Add comprehensive unit tests for edge cases in tests/test_aggregation.py
- [x] T037 [P] Add migration validation tests in tests/test_aggregation.py
- [x] T038 Update documentation with aggregation behavior in docs/
- [x] T039 Performance optimization for aggregation queries in python/hopilot/gto/aof_scenario_cache_store.py
- [x] T040 [P] Run quickstart.md validation and update if needed
- [x] T041 Final integration testing across all user stories in tests/test_gto_gui_integration.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Integrates with US1 but independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Depends on US1/US2 for data but independently testable
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Depends on US1/US2/US3 but focuses on compatibility

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Core aggregation before UI integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel
- All tests for a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Developer A: Tests
pytest tests/test_aggregation.py::test_weighted_average -xvs
pytest tests/test_aggregation.py::test_confidence_calculation -xvs

# Developer B: Core implementation  
python -c "from python.hopilot.gto.aof_scenario_cache_store import AggregationService; # test store_run"

# Developer C: Integration
pytest tests/test_gto_gui_integration.py::test_cumulative_evidence -xvs
```

---

## Implementation Strategy

**MVP First**: Start with US1 (cumulative aggregation) as it delivers core value immediately.

**Incremental Delivery**: Each user story provides independent value:
- US1: Better accuracy through repetition
- US2: Proper aggregated display  
- US3: Transparency about reliability
- US4: No breaking changes

**Risk Mitigation**: Feature flags allow rollback, coexistence mode preserves compatibility.

**Success Metrics**: All SC-001 through SC-004 from spec.md must pass before completion.