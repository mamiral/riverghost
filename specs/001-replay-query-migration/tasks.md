# Tasks: Replay Query Migration

**Input**: Design documents from `/specs/001-replay-query-migration/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: This feature explicitly requires truthful replay/query behavior over real persisted rows (FR-014), so fail-first test tasks are included per user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story-phase tasks only
- Every task includes an explicit file target

## Phase 1: Setup (Shared Alignment)

**Purpose**: Lock interfaces and fixtures to the migrated raw-schema path before implementation.

- [x] T001 Align replay readability semantics in `specs/001-replay-query-migration/contracts/replay-read-contract.md`
- [x] T002 [P] Align run-scope status semantics (`AVAILABLE`, `EMPTY_SCOPE`, `DISAMBIGUATION_REQUIRED`, `NOT_FOUND`) in `specs/001-replay-query-migration/contracts/raw-hand-query-contract.md`
- [x] T003 [P] Add feature test-data fixture helpers for raw GameState/Player seeded runs in `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared read-path primitives that all stories depend on.

**CRITICAL**: No user story implementation should start until this phase is complete.

- [x] T004 Add exact-contract run listing helper (return all matching completed/aggregated runs) in `python/hopilot/gto/database_repository.py`
- [x] T005 Implement explicit-run-selection resolver for scenario-contract queries in `python/hopilot/gto/database_repository.py`
- [x] T006 [P] Add raw-boundary readability guard (`start/end` both valid) and empty-scope result helper in `python/hopilot/gto/database_repository.py`
- [x] T007 [P] Add run-scoped raw-hand projection helper (ascending `GameState.id` ordering + hero-hole extraction) in `python/hopilot/gto/database_repository.py`
- [x] T008 Create truthful replay query service scaffold in `python/hopilot/gto/replay_query_service.py`

**Checkpoint**: Exact run matching, explicit disambiguation, boundary guards, and reusable raw-hand projections are available.

---

## Phase 3: User Story 1 - Replay A Stored Hand Truthfully (Priority: P1) 🎯 MVP

**Goal**: Replay one stored hand from `GameState.board_cards_str` and related `Player` rows without dead-schema dependencies.

**Independent Test**: Persist a real raw hand with players and request replay by `game_state_id`; verify truthful output shape and no fabricated event detail.

### Tests for User Story 1 (write first, fail first)

- [x] T009 [P] [US1] Rewrite replay contract tests for `READABLE` / `UNREADABLE` / `NOT_FOUND` states in `tests/test_game_replay_queries.py`
- [x] T010 [P] [US1] Add regression test for empty `board_cards_str` replay behavior in `tests/test_game_replay_queries.py`
- [x] T011 [P] [US1] Add regression test that replay does not require `GameState.cell_id` or `BoardCard` joins in `tests/test_game_replay_queries.py`

### Implementation for User Story 1

- [x] T012 [US1] Implement replay response builder (`ReplayView`, `ReplayPlayerView`, optional-detail availability) in `python/hopilot/gto/replay_query_service.py`
- [x] T013 [US1] Refactor `GameReplayQueryEngine.replay_game_sequence(...)` to delegate to the truthful replay service and remove legacy `matrix_cell`/`board_cards` assumptions in `python/hopilot/gto/game_replay_queries.py`
- [x] T014 [US1] Implement safe board parsing from `GameState.board_cards_str` only in `python/hopilot/gto/replay_query_service.py`
- [x] T015 [US1] Add explicit unreadable-hand handling for missing required player rows in `python/hopilot/gto/replay_query_service.py`

**Checkpoint**: US1 delivers truthful single-hand replay over the current raw schema.

---

## Phase 4: User Story 2 - Filter Raw Hands By Run Boundary (Priority: P2)

**Goal**: Return raw hands scoped to one simulation run (simulation, hand matrix, or exact scenario contract) with explicit run isolation.

**Independent Test**: Seed multiple runs and verify each scope returns only hands inside the selected run boundary.

### Tests for User Story 2 (write first, fail first)

- [x] T016 [P] [US2] Add simulation-scope boundary filter test coverage in `tests/test_analytical_query_integration.py`
- [x] T017 [P] [US2] Add hand-matrix-to-simulation boundary resolution coverage in `tests/test_analytical_query_integration.py`
- [x] T018 [P] [US2] Add exact scenario-contract scope coverage with unique match in `tests/test_analytical_query_integration.py`
- [x] T019 [P] [US2] Add boundary-missing empty-scope coverage in `tests/test_analytical_query_integration.py`

### Implementation for User Story 2

- [x] T020 [US2] Implement raw-hand query entrypoint supporting `simulation_id`, `hand_matrix_id`, and exact `scenario_contract` scope in `python/hopilot/gto/replay_query_service.py`
- [x] T021 [US2] Wire simulation and hand-matrix scope resolution through repository run-boundary helpers in `python/hopilot/gto/replay_query_service.py`
- [x] T022 [US2] Integrate run-scoped raw projection helper into query flow and enforce ascending raw ID ordering in `python/hopilot/gto/replay_query_service.py`
- [x] T023 [US2] Refactor legacy analytical query touchpoints that depend on `GameState.cell_id` to call the new run-scoped raw query path in `python/hopilot/gto/query_builder.py`

**Checkpoint**: US2 delivers deterministic run-scoped raw-hand filtering without stale joins.

---

## Phase 5: User Story 3 - Explicit Disambiguation And Aggregated Context Linking (Priority: P3)

**Goal**: Enforce explicit run selection when exact scenario matches are ambiguous and support summary-to-raw linking without mutating replay payload semantics.

**Independent Test**: Seed two runs with the same exact scenario contract and verify disambiguation-required status until explicit run selection is provided.

### Tests for User Story 3 (write first, fail first)

- [x] T024 [P] [US3] Add ambiguous exact-contract disambiguation test coverage in `tests/integration/test_replay_query_migration.py`
- [x] T025 [P] [US3] Add explicit-run-selection success-path coverage in `tests/integration/test_replay_query_migration.py`
- [x] T026 [P] [US3] Add summary-to-raw linking regression coverage (no replay payload mutation) in `tests/integration/test_replay_query_migration.py`

### Implementation for User Story 3

- [x] T027 [US3] Implement disambiguation-required response path (`matched_runs` populated, empty `game_states`) in `python/hopilot/gto/replay_query_service.py`
- [x] T028 [US3] Implement explicit-run-selection validation against matched candidates in `python/hopilot/gto/replay_query_service.py`
- [x] T029 [US3] Add helper for aggregated-context-to-run resolution that feeds the raw query path without modifying replay view shape in `python/hopilot/gto/replay_query_service.py`
- [x] T030 [US3] Expose the migrated replay/raw-query read surface for consumers in `python/hopilot/gto/__init__.py`

**Checkpoint**: US3 enforces explicit disambiguation and preserves run isolation under historical reruns.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, documentation sync, and end-to-end verification.

- [x] T031 [P] Remove stale legacy replay/query assertions that codify `cell_id`/`BoardCard` behavior in `tests/test_game_replay_queries.py`
- [x] T032 [P] Update feature verification notes and expected outcomes in `specs/001-replay-query-migration/quickstart.md`
- [x] T033 Run targeted feature verification commands and record outcomes in `specs/001-replay-query-migration/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2 and delivers the MVP.
- **Phase 4 (US2)**: Depends on Phase 2 and can proceed after US1 replay primitives are stable.
- **Phase 5 (US3)**: Depends on Phase 2 and US2 scenario-contract query flow.
- **Phase 6 (Polish)**: Depends on completion of the desired user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories once foundational work is complete.
- **US2 (P2)**: Depends on foundational run-boundary helpers and replay/query read service scaffolding.
- **US3 (P3)**: Depends on US2 scenario-contract query behavior.

### Within-Story Ordering Rules

- Tests for each story must exist and fail before the story implementation tasks.
- Repository run-selection and boundary guards must land before service-level response shaping depends on them.
- Disambiguation logic must land before explicit-run success paths are considered complete.

---

## Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel after T001 starts.
- **Foundational**: T006 and T007 can run in parallel after T004/T005 begin; T008 can proceed in parallel with repository helper work.
- **US1**: T009-T011 can run in parallel; T012 and T014 can run in parallel before T013/T015 integration points.
- **US2**: T016-T019 can run in parallel; T021/T022 can run in parallel once T020 is stubbed.
- **US3**: T024-T026 can run in parallel; T027/T028 can run in parallel before T029/T030 integration.
- **Polish**: T031 and T032 can run in parallel before T033 records final verification.

## Parallel Example: User Story 1

```bash
# Write failing replay tests together
Task: "Rewrite replay contract tests for READABLE/UNREADABLE/NOT_FOUND in tests/test_game_replay_queries.py"
Task: "Add empty board_cards_str replay behavior coverage in tests/test_game_replay_queries.py"
Task: "Add no-cell-id/no-BoardCard dependency coverage in tests/test_game_replay_queries.py"

# Then split implementation by concern
Task: "Implement replay response builder in python/hopilot/gto/replay_query_service.py"
Task: "Implement board parsing from GameState.board_cards_str in python/hopilot/gto/replay_query_service.py"
```

## Parallel Example: User Story 2

```bash
# Write failing run-scope tests together
Task: "Add simulation/hand-matrix/scenario scope boundary tests in tests/test_analytical_query_integration.py"
Task: "Add missing-boundary empty-scope test in tests/test_analytical_query_integration.py"

# Then split implementation by layer
Task: "Implement raw-hand query entrypoint in python/hopilot/gto/replay_query_service.py"
Task: "Refactor query_builder legacy cell_id path to run-scoped raw query in python/hopilot/gto/query_builder.py"
```

## Parallel Example: User Story 3

```bash
# Define disambiguation behavior first
Task: "Add ambiguous exact-contract disambiguation tests in tests/integration/test_replay_query_migration.py"
Task: "Add explicit run selection tests in tests/integration/test_replay_query_migration.py"

# Then implement disambiguation + explicit selection
Task: "Implement DISAMBIGUATION_REQUIRED response in python/hopilot/gto/replay_query_service.py"
Task: "Implement explicit run selection validation in python/hopilot/gto/replay_query_service.py"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1.
2. Complete Phase 2.
3. Complete Phase 3.
4. Validate replay behavior with the targeted pytest command in `quickstart.md`.

### Incremental Delivery

1. Deliver US1 truthful single-hand replay.
2. Add US2 run-scoped raw-hand filtering.
3. Add US3 disambiguation and explicit run-selection semantics.
4. Finish with polish and final verification evidence.

### Suggested MVP Scope

- **MVP**: Phase 1, Phase 2, and Phase 3 (US1 only).
- **Why**: That is the minimum slice that replaces stale replay behavior with truthful raw-schema replay while preserving the existing query entry surface.