# Feature Specification: Legacy Schema Cleanup

**Feature Branch**: `001-legacy-schema-cleanup`  
**Created**: 2026-04-27  
**Status**: Completed  
**Input**: User description: "Create a feature specification for removing or retiring stale HoPilot code paths that still depend on old schema assumptions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Dead Read/Write Paths (Priority: P1)

As a maintainer, I need stale production paths that require `GameState.cell_id`, `board_cards_id`, or `BoardCard` joins to be removed or rewritten so the active runtime path is consistent with GameStates-first design.

**Why this priority**: Dead schema paths are an active regression risk and currently mislead development decisions.

**Independent Test**: Can be fully tested by running cleanup-targeted production-path tests and static reference checks showing no active production reads/writes require legacy fields.

**Acceptance Scenarios**:

1. **Given** a production module currently reading or writing through `GameState.cell_id` or `board_cards_id`, **When** cleanup is applied, **Then** the module is either removed or rewritten to operate via raw `GameState` + `Player` + simulation run boundaries.
2. **Given** legacy replay/query modules that still describe `BoardCard`-based behavior, **When** cleanup is applied, **Then** only schema-correct replay/query entry points remain active.

---

### User Story 2 - Retire Obsolete Test Coverage (Priority: P2)

As a maintainer, I need tests that validate dead-schema behavior removed or rewritten so test failures represent real regressions in the active architecture.

**Why this priority**: Legacy tests currently encode invalid assumptions and block confident refactoring.

**Independent Test**: Can be tested by running the retained test suites and confirming no remaining test asserts or fixtures depend on removed schema fields.

**Acceptance Scenarios**:

1. **Given** tests that create or assert `cell_id`-linked GameStates or `board_cards_id` joins, **When** cleanup is complete, **Then** those tests are deleted or rewritten to validate GameStates-first behavior.
2. **Given** migration and replay tests that already validate the new path, **When** cleanup is complete, **Then** they remain passing and become the canonical safety net.

---

### User Story 3 - Enforce Safe Cleanup Sequencing (Priority: P3)

As a maintainer, I need explicit sequencing gates so cleanup does not remove behavior before the replacement path is proven stable.

**Why this priority**: Cleanup without dependency order can break production behavior and hide data-path regressions.

**Independent Test**: Can be tested by executing sequencing gates in order and verifying each gate passes before the next cleanup group begins.

**Acceptance Scenarios**:

1. **Given** replacement replay/raw-query and matrix-sweep run paths are already validated, **When** cleanup starts, **Then** deletion tasks are allowed only for modules with proven replacement coverage.
2. **Given** a module has no validated replacement coverage, **When** cleanup planning is performed, **Then** that module is marked rewrite/deprecate and not deleted in the same phase.

### Edge Cases

- A module mixes both valid GameStates-first logic and legacy schema logic; cleanup must preserve valid logic while removing only stale sections.
- A test file contains both obsolete and still-valid assertions; cleanup must rewrite in place so canonical coverage stays in the existing file path.
- A module appears unused but is still imported by a runtime entrypoint; cleanup must reclassify from delete to deprecate/rewrite until imports are removed.
- Cleanup ordering conflicts with active release work; cleanup must be staged so replacement verification remains continuously green.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The cleanup plan MUST classify stale-schema production modules into `DELETE`, `REWRITE`, `DEPRECATE`, or `KEEP` with a decision rationale.
- **FR-002**: The cleanup plan MUST classify stale-schema test files into `DELETE`, `REWRITE`, or `KEEP` with a decision rationale.
- **FR-003**: Production code paths that require `GameState.cell_id`, `board_cards_id`, or `BoardCard` joins MUST be removed or rewritten when a validated replacement path already exists.
- **FR-004**: No cleanup task MAY delete a module before its replacement path is verified through existing passing tests.
- **FR-005**: The feature MUST define sequencing gates covering: replacement-proof gate, test cleanup gate, production cleanup gate, and final regression gate.
- **FR-006**: Replay and raw-query behavior MUST remain centered on raw `GameState` and related `Player` records with run-boundary selection semantics.
- **FR-007**: Aggregation behavior MUST remain post-processing over stored raw rows, not direct solver-side aggregation writes.
- **FR-008**: Cleanup tasks MUST explicitly identify obsolete interfaces and remove or deprecate them to prevent new usages.
- **FR-009**: The final state MUST include no active production dependency on legacy matrix-cell-linked `GameState` write flows.
- **FR-010**: Documentation for cleanup execution MUST state which modules/tests were removed, rewritten, deprecated, and kept.
- **FR-015**: `DELETE`-classified modules MUST NOT be removed until all direct imports are removed from active runtime entrypoints.
- **FR-016**: `DEPRECATE`-classified modules MUST be removed within one release cycle.
- **FR-017**: Mixed legacy/current test files MUST be rewritten in place rather than split into new files.

### Cleanup Classification

#### Production Modules

- **DELETE**:
  - `python/hopilot/queries.py` (legacy query facade centered on `GameState.cell_id` and legacy replay shape)
  - `python/hopilot/database/aggregation.py` (legacy aggregation path directly keyed by matrix cell)
  - `python/hopilot/models/board_card.py` and BoardCard exports in `python/hopilot/models/__init__.py` (immediate hard removal)
- **REWRITE**:
  - `python/hopilot/gto/database_repository.py` (remove legacy `create_game_state`/`BoardCard` CRUD sections while preserving new run-scoped helpers)
  - `python/hopilot/gto/aof_precompute_runner.py` (remove `board_cards_id` and legacy GameState write assumptions)
  - `python/hopilot/gto/convergence_analysis_queries.py` (replace `GameState.cell_id` filters with run-scoped raw derivation)
  - `python/hopilot/gto/jackpot_frequency_queries.py` (replace `MatrixCell`↔`GameState.cell_id` joins with schema-correct path)
  - `python/hopilot/gto/aggregation_engine.py` and `python/hopilot/gto/incremental_aggregation.py` (align to GameStates-first raw-row derivation)
  - `python/hopilot/models/game_state.py` (remove legacy conversion/representation paths tied to `BoardCard` and `cell_id`)
- **DEPRECATE**:
  - `python/hopilot/gto/game_replay_queries.py` (retain temporary wrapper only if still required by callers; route entirely to truthful replay service)
  - `python/hopilot/database.py` (legacy helper surface that still exposes cell-linked query/write behavior)
- **KEEP**:
  - `python/hopilot/gto/replay_query_service.py` (canonical truthful replay and raw-run query path)
  - `python/hopilot/gto/query_builder.py` run-scoped raw-query integration paths
  - Matrix-sweep run + aggregation services already aligned with run-boundary model

#### Test Modules

- **DELETE**:
  - `tests/test_database_repository_crud.py`
  - `tests/test_matrix_aggregation.py`
  - `tests/test_incremental_aggregation.py`
- **REWRITE**:
  - `tests/test_aggregation_engine_comprehensive.py`
  - `tests/test_aggregation.py`
  - Any remaining repository/analytical tests asserting `board_cards_id`/`cell_id` behavior
- **KEEP**:
  - `tests/test_game_replay_queries.py`
  - `tests/integration/test_replay_query_migration.py`
  - Run-boundary and matrix-sweep tests validating GameStates-first architecture

### Sequencing Requirements

- **FR-011**: Phase A (Proof Gate) MUST confirm replacement-path tests are passing before any deletion tasks begin.
- **FR-012**: Phase B (Test Cleanup) MUST remove/rewrite obsolete tests first so production cleanup can be validated against correct expectations.
- **FR-013**: Phase C (Production Cleanup) MUST execute module actions in this order: deprecate wrappers, rewrite mixed modules, then delete dead modules.
- **FR-014**: Phase D (Regression Gate) MUST validate replay migration tests, run-boundary analytical tests, and matrix-sweep aggregation tests after cleanup.

### Key Entities *(include if feature involves data)*

- **Cleanup Inventory Item**: Represents a production module or test file with attributes: target path, classification (`DELETE`/`REWRITE`/`DEPRECATE`/`KEEP`), rationale, and sequencing phase.
- **Sequencing Gate**: Represents a required checkpoint with attributes: gate name, prerequisite evidence, pass/fail decision, and allowed next actions.
- **Legacy Dependency Signal**: Represents each stale dependency type (`GameState.cell_id`, `board_cards_id`, `BoardCard` join, cell-linked write flow) and where it appears.

### Final Cleanup Summary

- The cleanup achieved the intended GameStates-first transition by removing `python/hopilot/queries.py`, `python/hopilot/database/aggregation.py`, and `python/hopilot/models/board_card.py`.
- All retained production code now depends on raw `GameState` rows and related `Player` data rather than legacy `board_cards_id` or `GameState.cell_id` paths.
- Obsolete test modules were deleted and mixed test suites were rewritten in place with explicit GameStates-first assertions.
- Sequencing gates were satisfied with proof, test cleanup, production cleanup, and final regression evidence recorded in the feature documentation.

### Assumptions

- Existing replacement paths for truthful replay and run-scoped raw query behavior are stable and already covered by passing tests.
- Cleanup work targets active production/test modules under `python/hopilot/` and `tests/`, not prototyping artifacts.
- Temporary deprecation is acceptable only for callers not yet migrated; permanent compatibility shims are out of scope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of production modules classified as `DELETE` are removed from active imports and runtime entry points.
- **SC-002**: 100% of production modules classified as `REWRITE` no longer require `GameState.cell_id`, `board_cards_id`, or `BoardCard` joins for active behavior.
- **SC-003**: 100% of tests classified as obsolete are deleted or rewritten, and no retained test validates dead-schema assumptions.
- **SC-004**: Replacement-path regression suite (replay + raw-run query + aggregation post-processing) passes after cleanup with no critical failures.
- **SC-005**: Engineering reviewers can trace every cleanup action to a sequencing gate and classification rationale without ambiguity.
- **SC-006**: The codebase contains no active production path that reintroduces legacy matrix-cell-linked `GameState` write flow semantics.
