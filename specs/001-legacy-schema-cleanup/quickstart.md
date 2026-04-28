# Quickstart: Legacy Schema Cleanup

## Goal

Execute stale-schema cleanup in safe phases while preserving GameStates-first production behavior.

## Prerequisites

1. Activate the project environment.
2. Run commands from repository root.
3. Ensure feature branch is `001-legacy-schema-cleanup`.

## Gate Policies

- Strict delete gate: no `DELETE`-classified module may be removed until runtime entrypoint imports are removed and verified.
- Deprecation window: any `DEPRECATE`-classified module must be removed within one release cycle.
- Test cleanup gate: no production deletion may proceed until obsolete tests are removed and mixed tests are rewritten in place.

## Gate Execution Notes

- Gate A: `proof_gate` must pass before any delete action.
- Gate B: `test_cleanup_gate` must pass before production cleanup deletion.
- Gate C: `production_cleanup_gate` requires runtime import clean checks for delete targets and classification contract approval.
- Gate D: `final_regression_gate` requires replay migration, analytical run-boundary, and matrix-sweep aggregation suites to pass.

## Runtime Delete Target Verification

- Delete target: `python/hopilot/queries.py` -> `runtime_imports_removed=true`
- Delete target: `python/hopilot/database/aggregation.py` -> `runtime_imports_removed=true`
- Delete target: `python/hopilot/models/board_card.py` -> `runtime_imports_removed=true`

## Phase Execution Flow

1. Run proof-gate regression checks before any deletion.

```powershell
.venv\Scripts\Activate.ps1
python -m pytest tests/test_game_replay_queries.py tests/integration/test_replay_query_migration.py -q
python -m pytest tests/test_analytical_query_integration.py -q
python -m pytest tests/test_matrix_sweep_aggregation_service.py tests/test_matrix_sweep_pipeline.py -q
```

Expected outcome:

- Active replacement path suites pass.
- Cleanup scope can proceed.

### Proof Gate Evidence (2026-04-28)

- `python -m pytest tests/test_game_replay_queries.py tests/integration/test_replay_query_migration.py -q`
	- Result: PASS (`7 passed`)
- `python -m pytest tests/test_analytical_query_integration.py -q`
	- Result: PASS
- `python -m pytest tests/test_matrix_sweep_aggregation_service.py tests/test_matrix_sweep_pipeline.py -q`
	- Result: PASS
- Runtime import scan for delete targets in `python/hopilot/` modules returned no active references to `python/hopilot/queries.py`, `python/hopilot/database/aggregation.py`, or `python/hopilot/models/board_card.py`.

Proof Gate verdict:
- `result=pass`
- `next_gate_allowed=true`
- Delete-phase actions are allowed after test cleanup gate verification.

### Test Cleanup Gate Evidence (2026-04-28)

- Deleted obsolete tests:
  - `tests/test_database_repository_crud.py`
  - `tests/test_matrix_aggregation.py`
  - `tests/test_incremental_aggregation.py`
- Rewrote mixed test coverage in place:
  - `tests/test_aggregation_engine_comprehensive.py`
  - `tests/test_aggregation.py`
  - `tests/test_analytical_query_integration.py`
- Validation: targeted test runs passed and guard assertions verify no maintained raw-state assertions depend on `board_cards_id` or `cell_id`.

Test Cleanup Gate verdict:
- `result=pass`
- `next_gate_allowed=true`

2. Perform test cleanup (delete obsolete files, rewrite mixed files in place).

Expected outcome:

- No retained test asserts `GameState.cell_id`, `board_cards_id`, or `BoardCard` joins as active behavior.

3. Perform production cleanup sequencing.

### Final Regression Gate Evidence (2026-04-28)

- `pytest -q tests/test_game_replay_queries.py tests/integration/test_replay_query_migration.py tests/test_analytical_query_integration.py tests/test_matrix_sweep_aggregation_service.py tests/test_matrix_sweep_pipeline.py`
	- Result: PASS (`26 passed`)

Final Regression Gate verdict:
- `result=pass`
- `next_gate_allowed=true`

Expected outcome:

- Deprecation actions applied only where callers remain.
- Mixed modules rewritten to schema-correct behavior.
- Delete targets removed only after import graph is clean.

4. Run final regression gate.

```powershell
python -m pytest tests/test_game_replay_queries.py tests/integration/test_replay_query_migration.py -q
python -m pytest tests/test_analytical_query_integration.py -q
python -m pytest tests/test_matrix_sweep_aggregation_service.py tests/test_matrix_sweep_pipeline.py -q
```

Expected outcome:

- Replay migration tests pass.
- Run-boundary analytical tests pass.
- Matrix-sweep aggregation tests pass.

## Completion Criteria

- All cleanup targets have final classification outcomes.
- No active production path depends on dead-schema fields.
- Deprecated modules have one-release-cycle removal deadlines recorded in tasks.
