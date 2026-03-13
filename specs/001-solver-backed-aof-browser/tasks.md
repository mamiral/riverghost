# Tasks: Solver-Backed AoF Browser Data

**Input**: Design documents from `/specs/001-solver-backed-aof-browser/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare solver-backed provider scaffolding and deterministic test assets

- [X] T001 Create solver adapter module skeleton in python/hopilot/gto/aof_solver_adapter.py
- [X] T002 Add provider status constants and shared helpers in python/hopilot/gto/aof_browser_data_provider.py
- [X] T003 [P] Add deterministic solver runtime defaults in config/gto_defaults.yaml
- [X] T004 [P] Add solver-backed fixture scaffolding for edge contexts in tests/data/aof_solver_backed_fixture.yaml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core context validation, cache primitives, timeout wrapper, and status mapping used by all stories

**CRITICAL**: No user story implementation starts before this phase completes

- [X] T005 Implement BrowserContext normalization and validation helpers in python/hopilot/gto/aof_browser_state.py
- [X] T006 Implement stable cache-key builder for full context in python/hopilot/gto/aof_browser_data_provider.py
- [X] T007 [P] Implement cache entry metadata and invalidation hooks in python/hopilot/gto/aof_browser_data_provider.py
- [X] T008 Implement timeout wrapper for solver calls in python/hopilot/gto/aof_solver_adapter.py
- [X] T009 [P] Add degraded-mode logging hooks via centralized logger in python/hopilot/gto/aof_browser_data_provider.py
- [X] T010 Implement status mapping contract (AVAILABLE, MISSING, NO_CONTEST, TIMEOUT, ERROR) in python/hopilot/gto/aof_browser_data_provider.py

**Checkpoint**: Foundation complete; user story work can begin

---

## Phase 3: User Story 1 - Trustworthy Matrix Decisions (Priority: P1) 🎯 MVP

**Goal**: Replace heuristic matrix values with real solver-backed values across all metrics

**Independent Test**: Load AoF browser for fixed context and verify 169-cell payload values are solver-backed and metric-consistent

### Tests for User Story 1

- [X] T011 [P] [US1] Add payload contract tests for context and 169-cell matrix shape in tests/test_aof_solver_provider_contract.py
- [X] T012 [P] [US1] Add provenance tests that fail if heuristic generation is used in normal path in tests/test_aof_solver_provider_contract.py
- [X] T013 [P] [US1] Add metric semantic tests for WIN_LOSE_PROBABILITY, EV, EQUITY, and EQR in tests/test_aof_solver_provider_metrics.py

### Implementation for User Story 1

- [X] T014 [US1] Implement per-hand solver evaluation adapter using existing solver modules in python/hopilot/gto/aof_solver_adapter.py
- [X] T015 [US1] Integrate solver adapter as default provider execution path in python/hopilot/gto/aof_browser_data_provider.py
- [X] T016 [US1] Implement combo expansion and aggregation into per-hand matrix cell values in python/hopilot/gto/aof_browser_data_provider.py
- [X] T017 [US1] Align metric formatting and display semantics with solver outputs in python/hopilot/gto/aof_hand_matrix.py
- [X] T018 [US1] Wire provider status_message into panel refresh flow in python/hopilot/gui_components/aof_browser_panel.py
- [X] T019 [US1] Update matrix renderer handling for non-available statuses in python/hopilot/gui_components/aof_hand_matrix_panel.py

**Checkpoint**: US1 delivers solver-backed matrix values and is independently testable

---

## Phase 4: User Story 2 - Correct Context Across Position Actions (Priority: P2)

**Goal**: Ensure full per-position action map deterministically changes effective solver context and outputs

**Independent Test**: Toggle position actions through edge and normal states and verify deterministic context-driven payload changes

### Tests for User Story 2

- [X] T020 [P] [US2] Add per-position context transition tests in tests/test_aof_solver_provider_context.py
- [X] T021 [P] [US2] Add edge-case tests for all-fold, single-all-in, uncontested-win, and multiway-all-in in tests/test_aof_solver_provider_edge_cases.py
- [X] T022 [P] [US2] Add invalid-combo and null-value mapping tests in tests/test_aof_solver_provider_edge_cases.py

### Implementation for User Story 2

- [X] T023 [US2] Implement effective-opponent resolution from position_actions in python/hopilot/gto/aof_solver_adapter.py
- [X] T024 [US2] Implement deterministic edge-case resolver table in python/hopilot/gto/aof_browser_data_provider.py
- [X] T025 [US2] Implement selected-position fold and no-contest semantics in python/hopilot/gto/aof_browser_data_provider.py
- [X] T026 [US2] Implement invalid combo filtering and MISSING cell status mapping in python/hopilot/gto/aof_browser_data_provider.py
- [X] T027 [US2] Populate derived context summary fields (action, active_players, effective_mode) in python/hopilot/gto/aof_browser_data_provider.py
- [X] T028 [US2] Surface edge-case status messages in panel summary area in python/hopilot/gui_components/aof_browser_panel.py

**Checkpoint**: US2 delivers deterministic context semantics and edge-case behavior without ambiguity

---

## Phase 5: User Story 3 - Stable Performance and Failure Transparency (Priority: P3)

**Goal**: Add robust caching, timeout handling, and clear degraded-mode behavior with latency safeguards

**Independent Test**: Repeated context toggles show cache acceleration; timeout/failure paths return deterministic statuses and no crash

### Tests for User Story 3

- [X] T029 [P] [US3] Add cache hit, miss, and invalidation tests in tests/test_aof_solver_provider_cache.py
- [X] T030 [P] [US3] Add timeout and solver-failure resilience tests in tests/test_aof_solver_provider_resilience.py
- [X] T031 [P] [US3] Add latency regression tests for context and metric switches in tests/test_gto_gui_integration.py
- [X] T044 [US3] Add p95 latency harness (n=200 switches) and pass/fail assertion for <= 1.0s in tests/test_gto_gui_integration.py

### Implementation for User Story 3

- [X] T032 [US3] Implement context-keyed payload cache retrieval and storage in python/hopilot/gto/aof_browser_data_provider.py
- [X] T033 [US3] Implement timeout-to-TIMEOUT payload translation in python/hopilot/gto/aof_solver_adapter.py
- [X] T034 [US3] Implement solver-failure degraded-mode payload with ERROR status and messaging in python/hopilot/gto/aof_browser_data_provider.py
- [X] T035 [US3] Add deterministic seed controls for test mode execution in python/hopilot/gto/aof_solver_adapter.py
- [X] T036 [US3] Add configurable simulation and timeout knobs in provider initialization in python/hopilot/gto/aof_browser_data_provider.py

**Checkpoint**: US3 delivers responsive toggles and transparent failure handling

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, verification, and regression hardening

- [X] T037 [P] Update feature quickstart with solver-backed validation workflow in specs/001-solver-backed-aof-browser/quickstart.md
- [X] T038 [P] Update AoF browser usage guidance and limitations in docs/initial_design/USAGE_GUIDE_WIN.md
- [X] T039 [P] Update contract details for final status and metric semantics in specs/001-solver-backed-aof-browser/contracts/aof-solver-provider-contract.md
- [X] T040 [P] Record final design and policy decisions in specs/001-solver-backed-aof-browser/research.md
- [X] T041 Run and document targeted AoF/provider test evidence in specs/001-solver-backed-aof-browser/quickstart.md
- [X] T042 Add simulator-decoupling regression assertion in tests/test_poker_simulator_gui.py
- [X] T043 Perform final logging and cleanup pass in python/hopilot/gto/aof_browser_data_provider.py

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies
- Foundational (Phase 2): Depends on Setup and blocks all user stories
- User Story phases: Begin only after Foundational checkpoint
- Polish (Phase 6): Depends on completion of desired user stories

### User Story Dependencies

- US1 (P1): Starts after Phase 2 and establishes solver-backed baseline
- US2 (P2): Depends on US1 solver-backed baseline and extends context semantics
- US3 (P3): Depends on US1 baseline and US2 context semantics for resilient performance behavior

### Within Each User Story

- Tests are created before implementation and should fail before code changes
- Adapter and provider core logic precede UI summary/messaging updates
- Story checkpoint must pass before moving to next priority

### Parallel Opportunities

- Phase 1 tasks T003 and T004 can run in parallel
- Phase 2 tasks T007 and T009 can run in parallel
- US1 test tasks T011 to T013 can run in parallel
- US2 test tasks T020 to T022 can run in parallel
- US3 test tasks T029 to T031 can run in parallel
- Polish doc tasks T037 to T040 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Run these in parallel:
T011 tests/test_aof_solver_provider_contract.py
T012 tests/test_aof_solver_provider_contract.py
T013 tests/test_aof_solver_provider_metrics.py
```

## Parallel Example: User Story 2

```bash
# Run these in parallel:
T020 tests/test_aof_solver_provider_context.py
T021 tests/test_aof_solver_provider_edge_cases.py
T022 tests/test_aof_solver_provider_edge_cases.py
```

## Parallel Example: User Story 3

```bash
# Run these in parallel:
T029 tests/test_aof_solver_provider_cache.py
T030 tests/test_aof_solver_provider_resilience.py
T031 tests/test_gto_gui_integration.py
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2
2. Complete US1 (Phase 3)
3. Validate solver-backed payload correctness
4. Demo MVP with real data provenance

### Incremental Delivery

1. Deliver US1 solver-backed baseline
2. Deliver US2 deterministic context and edge-case semantics
3. Deliver US3 performance and resilience guarantees
4. Complete Phase 6 polish and documentation

### Team Parallelization Strategy

1. One contributor focuses on adapter/provider core logic
2. One contributor builds provider and integration tests in parallel once interfaces stabilize
3. One contributor updates contracts/docs and validates quickstart evidence during polish
