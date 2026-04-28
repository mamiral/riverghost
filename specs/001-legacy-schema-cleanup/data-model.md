# Data Model: Legacy Schema Cleanup

## Overview

This feature manages cleanup planning artifacts rather than introducing new runtime schema. The entities below define how cleanup scope, ordering, and validation are tracked.

## Entities

### 1. Cleanup Inventory Item

Represents one production module or test target selected for cleanup.

**Fields**:

- `target_path` (string): Repository-relative path to module or test file.
- `target_kind` (enum): `production_module` or `test_module`.
- `classification` (enum): `DELETE`, `REWRITE`, `DEPRECATE`, `KEEP`.
- `legacy_signals` (list[string]): Any of `GameState.cell_id`, `board_cards_id`, `BoardCard_join`, `cell_linked_raw_write`.
- `rationale` (string): Why the classification is correct.
- `phase` (enum): `proof_gate`, `test_cleanup`, `production_rewrite`, `production_delete`, `regression_gate`.
- `status` (enum): `pending`, `in_progress`, `done`, `blocked`.

**Validation Rules**:

- `DELETE` is invalid if runtime entrypoint imports still reference `target_path`.
- `DEPRECATE` items must include a one-release-cycle removal deadline.
- `REWRITE` must preserve active behavior under GameStates-first architecture.

### Cleanup Inventory Tracker (Phase 2 Baseline)

Use this tracker to record per-target execution status during cleanup.

| target_path | target_kind | classification | legacy_signals | phase | status | proof_gate_ref |
|-------------|-------------|----------------|----------------|-------|--------|----------------|
| python/hopilot/queries.py | production_module | DELETE | GameState.cell_id, BoardCard_join | production_delete | pending | quickstart Proof Gate Evidence |
| python/hopilot/database/aggregation.py | production_module | DELETE | GameState.cell_id | production_delete | pending | quickstart Proof Gate Evidence |
| python/hopilot/models/board_card.py | production_module | DELETE | BoardCard_join | production_delete | pending | quickstart Proof Gate Evidence |
| tests/test_database_repository_crud.py | test_module | DELETE | board_cards_id, BoardCard_join | test_cleanup | pending | quickstart Proof Gate Evidence |

### 2. Sequencing Gate

Represents a mandatory checkpoint controlling progression.

**Fields**:

- `gate_name` (enum): `proof_gate`, `test_cleanup_gate`, `production_cleanup_gate`, `final_regression_gate`.
- `prerequisites` (list[string]): Required evidence before gate can pass.
- `required_suites` (list[string]): Required tests for gate validation.
- `result` (enum): `pass`, `fail`.
- `failure_reason` (string, optional): Required when `result=fail`.

**Validation Rules**:

- `proof_gate` must pass before any `DELETE` action.
- `test_cleanup_gate` must pass before production-module deletion.
- `final_regression_gate` must include replay migration, run-boundary analytical, and matrix-sweep aggregation suites.

### 3. Cleanup Decision Record

Represents traceable decisions made for each target.

**Fields**:

- `target_path` (string): Associated inventory item.
- `decision` (enum): `retain`, `rewrite`, `deprecate`, `delete`.
- `decision_basis` (string): Evidence summary from code and tests.
- `approved_at` (datetime string).
- `approved_by` (string).

**Validation Rules**:

- Every `DELETE` and `REWRITE` target requires one decision record before execution.
- Decision basis must reference at least one legacy dependency signal.
## Per-Target Cleanup Decision Records

Decision records capture the exact cleanup rationale and current phase status for each target.

| target_path | decision | rationale | phase | status | approved_by | approved_at |
|-------------|----------|-----------|-------|--------|-------------|-------------|
| `python/hopilot/queries.py` | `delete` | Legacy query facade removed after replacement-path validation and active import cleanup. | `production_delete` | `done` | `cleanup-team` | `2026-04-28` |
| `python/hopilot/database/aggregation.py` | `delete` | Dead aggregation module removed after GameStates-first aggregation rewrite and import verification. | `production_delete` | `done` | `cleanup-team` | `2026-04-28` |
| `python/hopilot/models/board_card.py` | `delete` | BoardCard model retired; GameStates-first storage is active and no runtime references remain. | `production_delete` | `done` | `cleanup-team` | `2026-04-28` |
| `python/hopilot/database/persistence/database.py::store_board_cards` | `deprecate` | Legacy persistence wrapper retained for one release cycle while callers converge away from BoardCard storage. | `production_rewrite` | `pending` | `cleanup-team` | `2026-04-28` |

Decision basis must explicitly cite the legacy signal(s) that motivated the target classification and the phase at which the decision was approved.
