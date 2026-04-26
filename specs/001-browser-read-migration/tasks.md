# Tasks: Browser Read-Path Migration

**Input**: Design documents from `/specs/001-browser-read-migration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: This feature explicitly requires payload-behavior coverage against real persisted data, so test tasks are included for each user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and verified independently.

## Phase 1: Setup (Shared Design Alignment)

**Purpose**: Remove design ambiguity before code changes begin.

- [x] T001 Align browser metric mapping semantics in `specs/001-browser-read-migration/data-model.md`
- [x] T002 Align scenario-read result semantics in `specs/001-browser-read-migration/contracts/browser-scenario-read-contract.md`
- [x] T003 [P] Align provider payload fallback semantics in `specs/001-browser-read-migration/contracts/browser-matrix-payload-contract.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core read-path infrastructure that MUST be complete before any user story work begins.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [x] T004 Extend canonical browser scenario normalization and validation for read-path lookup in `python/hopilot/gto/matrix_sweep_contract.py`
- [x] T005 Implement deterministic aggregated-run lookup and filtered summary retrieval in `python/hopilot/gto/database_repository.py`
- [x] T006 [P] Add shared SQLite browser-scenario fixtures for aggregated run seeding in `tests/conftest.py`

**Checkpoint**: Deterministic scenario normalization, current-run lookup, and reusable test fixtures are ready.

---

## Phase 3: User Story 1 - Load the Current Scenario Matrix (Priority: P1) 🎯 MVP

**Goal**: Return the correct 169-cell payload for a scenario that already has an aggregated run.

**Independent Test**: Seed multiple aggregated scenarios, request one browser scenario, and verify that the payload comes from the selected run only, preserves the GUI shape, and switches metrics without changing scenario resolution.

### Tests for User Story 1

- [x] T007 [P] [US1] Add available-scenario payload contract coverage in `tests/test_browser_database_provider.py`
- [x] T008 [P] [US1] Add SQLite-backed scenario-read and metric-switching coverage in `tests/test_browser_database_provider_persistence.py`
- [x] T009 [P] [US1] Add persisted scenario-to-run resolution coverage in `tests/test_matrix_sweep_pipeline.py`

### Implementation for User Story 1

- [x] T010 [US1] Refactor `get_matrix_payload` to delegate available-scenario reads through the aggregated run path in `python/hopilot/gto/browser_database_provider.py`
- [x] T011 [US1] Implement run-scoped metric extraction and 169-cell summary mapping for the selected run in `python/hopilot/gto/database_repository.py`
- [x] T012 [US1] Update provider context construction to emit the canonical scenario contract for repository lookup in `python/hopilot/gto/browser_database_provider.py`

**Checkpoint**: User Story 1 returns deterministic payloads for existing aggregated scenarios and is independently testable.

---

## Phase 4: User Story 2 - Show a Deterministic Missing Scenario State (Priority: P2)

**Goal**: Return a stable read-only missing payload instead of legacy loading or compute behavior when no aggregated run is available.

**Independent Test**: Request a scenario with no aggregated run and verify that the payload still contains 169 canonical cells, explicit missing status, and no persistence side effects.

### Tests for User Story 2

- [x] T013 [P] [US2] Add missing-scenario and missing-HandMatrix coverage in `tests/test_browser_database_provider_persistence.py`
- [x] T014 [P] [US2] Add explicit missing-status integration coverage for browser reads in `tests/integration/test_browser_database_provider_integration.py`

### Implementation for User Story 2

- [x] T015 [US2] Replace the legacy `LOADING` and `Computing...` fallback with the explicit missing payload in `python/hopilot/gto/browser_database_provider.py`
- [x] T016 [US2] Treat matched simulations without aggregated matrices and cells without requested metric data as deterministic missing-read cases in `python/hopilot/gto/database_repository.py`

**Checkpoint**: User Story 2 returns the correct missing-state payload without writes and without background-compute messaging.

---

## Phase 5: User Story 3 - Prefer the Current Historical Run Deterministically (Priority: P3)

**Goal**: Always choose the same current run for repeated requests against historical reruns of the same scenario.

**Independent Test**: Seed multiple aggregated runs for the same canonical scenario contract and verify that repeated reads always pick the latest completion timestamp, then highest simulation ID when timestamps tie or are absent.

### Tests for User Story 3

- [x] T017 [P] [US3] Add deterministic historical-run ordering coverage in `tests/test_matrix_sweep_pipeline.py`
- [x] T018 [P] [US3] Add provider integration coverage for latest-run and tie-break selection in `tests/integration/test_browser_database_provider_integration.py`

### Implementation for User Story 3

- [x] T019 [US3] Finalize repository ordering rules for aggregated historical runs in `python/hopilot/gto/database_repository.py`
- [x] T020 [US3] Surface selected-run success messaging without cross-run merge behavior in `python/hopilot/gto/browser_database_provider.py`

**Checkpoint**: Historical reruns resolve deterministically and remain independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, verification, and performance validation across stories.

- [x] T021 [P] Remove stale mock-only browser-provider expectations that conflict with the new read path in `tests/test_browser_database_provider.py`
- [x] T022 [P] Update the browser read-path verification steps and expected assertions in `specs/001-browser-read-migration/quickstart.md`
- [x] T023 Add warm-read latency validation for one scenario payload read in `tests/test_browser_database_provider_persistence.py`
- [x] T024 Run the feature verification command and record the outcome in `specs/001-browser-read-migration/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup**: No dependencies.
- **Phase 2: Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3: User Story 1**: Depends on Phase 2 and delivers the MVP.
- **Phase 4: User Story 2**: Depends on Phase 2 and can proceed after or alongside US1 once the foundation is in place.
- **Phase 5: User Story 3**: Depends on Phase 2 and can proceed after or alongside US1 once deterministic lookup exists.
- **Phase 6: Polish**: Depends on the completion of the desired user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other user stories once foundational work is complete.
- **US2 (P2)**: Depends on the shared read path from Phase 2 but remains independently testable.
- **US3 (P3)**: Depends on the shared run-selection path from Phase 2 but remains independently testable.

### Within Each User Story

- Tests must be written and fail before the implementation tasks for that story.
- Repository selection and normalization behavior must land before provider formatting changes depend on it.
- Each story should be revalidated independently before moving to the next phase.

## Parallel Opportunities

- **Setup**: T003 can run in parallel with T001-T002.
- **Foundational**: T006 can run in parallel with T004-T005.
- **US1**: T007-T009 can run in parallel; T010-T012 can be split between provider and repository work after T005.
- **US2**: T013-T014 can run in parallel; T015 and T016 can proceed in parallel after the failing tests exist.
- **US3**: T017-T018 can run in parallel; T019 and T020 can proceed in parallel after deterministic ordering expectations are locked.
- **Polish**: T021-T022 can run in parallel; T023 should finish before T024 records the final verification result.

## Parallel Example: User Story 1

```bash
# Write the story-specific failing tests together:
Task: "Add available-scenario payload contract coverage in tests/test_browser_database_provider.py"
Task: "Add SQLite-backed scenario-read and metric-switching coverage in tests/test_browser_database_provider_persistence.py"
Task: "Add persisted scenario-to-run resolution coverage in tests/test_matrix_sweep_pipeline.py"

# Then split implementation by ownership boundary:
Task: "Implement run-scoped metric extraction and 169-cell summary mapping for the selected run in python/hopilot/gto/database_repository.py"
Task: "Refactor get_matrix_payload to delegate available-scenario reads through the aggregated run path in python/hopilot/gto/browser_database_provider.py"
```

## Parallel Example: User Story 2

```bash
# Run the missing-state tests together:
Task: "Add missing-scenario and missing-HandMatrix coverage in tests/test_browser_database_provider_persistence.py"
Task: "Add explicit missing-status integration coverage for browser reads in tests/integration/test_browser_database_provider_integration.py"

# Then implement the read-only missing path split by layer:
Task: "Treat matched simulations without aggregated matrices and cells without requested metric data as deterministic missing-read cases in python/hopilot/gto/database_repository.py"
Task: "Replace the legacy LOADING and Computing... fallback with the explicit missing payload in python/hopilot/gto/browser_database_provider.py"
```

## Parallel Example: User Story 3

```bash
# Define deterministic current-run behavior in tests first:
Task: "Add deterministic historical-run ordering coverage in tests/test_matrix_sweep_pipeline.py"
Task: "Add provider integration coverage for latest-run and tie-break selection in tests/integration/test_browser_database_provider_integration.py"

# Then land the repository and provider changes:
Task: "Finalize repository ordering rules for aggregated historical runs in python/hopilot/gto/database_repository.py"
Task: "Surface selected-run success messaging without cross-run merge behavior in python/hopilot/gto/browser_database_provider.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1.
2. Complete Phase 2.
3. Complete Phase 3.
4. Validate the existing-scenario read path with the targeted pytest command from `specs/001-browser-read-migration/quickstart.md`.

### Incremental Delivery

1. Deliver US1 for existing aggregated scenarios.
2. Add US2 missing-scenario behavior without changing the entry point.
3. Add US3 deterministic historical-run selection.
4. Finish with latency validation and quickstart evidence.

### Suggested MVP Scope

- **MVP**: Phase 1, Phase 2, and Phase 3 (User Story 1 only).
- **Why**: That is the minimum slice that replaces the legacy browser read path for persisted aggregated scenarios while preserving the GUI-facing entry point.
