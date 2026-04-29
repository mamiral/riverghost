# Tasks: Provider and Repository Responsibility Split

**Input**: Design documents from `/specs/001-split-provider-repository/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: This feature requires automated verification per spec success criteria (SC-001 through SC-006).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature-specific modules and baseline test scaffolding.

- [X] T001 Create reconciliation module scaffold in `python/hopilot/gto/precompute_reconciliation.py`
- [X] T002 [P] Create provider contract split test scaffold in `tests/test_provider_contract_split.py`
- [X] T003 [P] Create reconciliation unit test scaffold in `tests/test_precompute_reconciliation.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared boundaries and primitives required by all user stories.

- [X] T004 Define reconciliation input/output types and deterministic result model in `python/hopilot/gto/precompute_reconciliation.py`
- [X] T005 [P] Add shared orchestration-vs-payload contract guard helpers in `python/hopilot/gto/precompute_orchestration.py`
- [X] T006 [P] Add tracking/raw persistence boundary helper methods in `python/hopilot/gto/precompute_job_persistence.py`
- [X] T007 Add runner integration seam for mandatory final reconciliation pass in `python/hopilot/gto/aof_precompute_runner.py`

**Checkpoint**: Foundation complete - user stories can proceed.

---

## Phase 3: User Story 1 - Separate Provider Contracts (Priority: P1) 🎯 MVP

**Goal**: Enforce explicit provider contract split so orchestration uses direct context only and browser paths use payload contract only.

**Independent Test**: Run provider and orchestration contract tests to prove call-site separation and unchanged payload behavior.

### Tests for User Story 1

- [X] T008 [P] [US1] Add orchestration contract tests ensuring no payload retrieval call path in `tests/test_provider_contract_split.py`
- [X] T009 [P] [US1] Add browser payload contract tests ensuring payload path independence in `tests/test_provider_contract_split.py`
- [X] T010 [US1] Add regression assertion that precompute orchestration never calls payload retrieval in `tests/test_precompute_runner_regression.py`

### Implementation for User Story 1

- [X] T011 [US1] Refactor orchestration context resolution to direct-context contract only in `python/hopilot/gto/precompute_orchestration.py`
- [X] T012 [US1] Enforce browser payload contract boundary in `python/hopilot/gto/browser_database_provider.py`
- [X] T013 [US1] Add call-site enforcement wiring for runner and browser modules in `python/hopilot/gto/aof_precompute_runner.py`
- [X] T014 [US1] Validate US1 targeted suites in `tests/test_provider_contract_split.py` and `tests/test_precompute_runner_regression.py`

**Checkpoint**: Provider contracts are split and independently testable.

---

## Phase 4: User Story 2 - Isolate Job Tracking Persistence (Priority: P2)

**Goal**: Split tracking and raw persistence transaction responsibilities and implement mandatory deterministic reconciliation/finalization.

**Independent Test**: Run reconciliation and integration tests proving split transactions resolve mismatches deterministically.

### Tests for User Story 2

- [X] T015 [P] [US2] Add reconciliation unit tests for raw-only success, tracking-only success, and mismatch correction in `tests/test_precompute_reconciliation.py`
- [X] T016 [P] [US2] Add reconciliation determinism tests for identical persisted inputs in `tests/test_precompute_reconciliation.py`
- [X] T017 [US2] Add integration tests for mandatory finalization pass and counter recomputation in `tests/integration/test_precompute_runner_integration.py`

### Implementation for User Story 2

- [X] T018 [US2] Implement deterministic reconciliation engine and stable precedence rules in `python/hopilot/gto/precompute_reconciliation.py`
- [X] T019 [US2] Implement separate-transaction tracking helpers and mismatch-repair updates in `python/hopilot/gto/precompute_job_persistence.py`
- [X] T020 [US2] Integrate mandatory reconciliation/finalization call into run completion path in `python/hopilot/gto/aof_precompute_runner.py`
- [X] T021 [US2] Ensure raw persistence paths remain isolated from tracking updates in `python/hopilot/gto/database_repository.py`
- [X] T022 [US2] Validate US2 targeted suites in `tests/test_precompute_reconciliation.py` and `tests/integration/test_precompute_runner_integration.py`

**Checkpoint**: Split transactions plus mandatory deterministic reconciliation are working.

---

## Phase 5: User Story 3 - Preserve Backward-Compatible Behavior (Priority: P3)

**Goal**: Preserve external precompute and browser behavior while introducing provider/repository boundary split.

**Independent Test**: Run full targeted regression suites and confirm behavior parity in outputs, failure semantics, and run lifecycle outcomes.

### Tests for User Story 3

- [X] T023 [P] [US3] Add compatibility assertions for failure boundary semantics and terminal states in `tests/integration/test_precompute_runner_integration.py`
- [X] T024 [P] [US3] Add browser payload compatibility assertions for AVAILABLE/MISSING/NO_CONTEST behavior in `tests/integration/test_browser_database_provider_integration.py`

### Implementation for User Story 3

- [X] T025 [US3] Preserve run return and lifecycle semantics after reconciliation integration in `python/hopilot/gto/aof_precompute_runner.py`
- [X] T026 [US3] Preserve browser payload response semantics under contract split in `python/hopilot/gto/browser_database_provider.py`
- [X] T027 [US3] Validate all targeted compatibility suites in `tests/test_aof_precompute_runner.py`, `tests/test_matrix_sweep_precompute_runner.py`, and `tests/integration/test_browser_database_provider_integration.py`

**Checkpoint**: External behavior remains backward-compatible.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality verification and documentation consistency.

- [X] T028 [P] Update split-boundary implementation notes in `specs/001-split-provider-repository/quickstart.md`
- [X] T029 [P] Run full regression suite and verify SC-001 through SC-006 in `tests/`
- [X] T030 [P] Perform final code audit for contract and transaction-boundary separation in `python/hopilot/gto/aof_precompute_runner.py`, `python/hopilot/gto/precompute_orchestration.py`, `python/hopilot/gto/precompute_job_persistence.py`, and `python/hopilot/gto/precompute_reconciliation.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion.
- **User Story 2 (Phase 4)**: Depends on Foundational completion and US1 contract seam enforcement.
- **User Story 3 (Phase 5)**: Depends on US1 and US2 completion.
- **Polish (Phase 6)**: Depends on all user stories complete.

### User Story Dependencies

- **US1 (P1)**: First deliverable and MVP.
- **US2 (P2)**: Requires US1 contract boundaries to avoid cross-path coupling during reconciliation integration.
- **US3 (P3)**: Validates backward compatibility after US1 + US2 changes.

### Within Each User Story

- Write tests first, confirm they fail, then implement.
- Provider/repository boundary enforcement before compatibility hardening.
- Reconciliation engine before finalization integration.
- Run targeted suite before moving to next story.

### Parallel Opportunities

- Phase 1 test scaffolds (T002, T003) in parallel.
- Foundational helper additions (T005, T006) in parallel.
- US1 contract tests (T008, T009) in parallel.
- US2 reconciliation tests (T015, T016) in parallel.
- US3 compatibility test additions (T023, T024) in parallel.
- Polish tasks (T028, T029, T030) in parallel.

---

## Parallel Example: User Story 2

```bash
# Parallel test work
Task: "Add reconciliation unit tests in tests/test_precompute_reconciliation.py"
Task: "Add reconciliation determinism tests in tests/test_precompute_reconciliation.py"

# Then implement core behavior
Task: "Implement deterministic reconciliation engine in python/hopilot/gto/precompute_reconciliation.py"
Task: "Integrate mandatory reconciliation into python/hopilot/gto/aof_precompute_runner.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate contract split behavior via targeted tests

### Incremental Delivery

1. Setup + Foundational
2. Deliver US1 provider contract split (MVP)
3. Deliver US2 persistence split + deterministic reconciliation
4. Deliver US3 compatibility hardening
5. Polish with full-suite verification and final audits

### Parallel Team Strategy

1. Team completes Setup + Foundational together.
2. US1 lead: provider contract boundaries.
3. US2 lead: persistence split and reconciliation logic.
4. US3 lead: compatibility assertions and regression hardening.

---

## Notes

- [P] tasks are file-isolated and dependency-safe for parallel execution.
- Every task includes an explicit file path.
- User story phases are independently testable increments.
- This task plan assumes no schema redesign and preserves existing external behavior.
