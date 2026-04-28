# Contract: Sequencing Gates

## Purpose

Define mandatory ordering and pass criteria for cleanup execution.

## Gate Definitions

### Gate A: Proof Gate

**Must Pass Before**: Any delete action.

**Required Evidence**:
- Replacement-path suites are passing.
- Classified target inventory is complete.
- Evidence is recorded in `specs/001-legacy-schema-cleanup/quickstart.md`.

### Gate B: Test Cleanup Gate

**Must Pass Before**: Production delete phase.

**Required Evidence**:
- Obsolete tests deleted or rewritten.
- Mixed test files rewritten in place.
- No retained test asserts dead-schema behavior.
- Evidence is recorded in `specs/001-legacy-schema-cleanup/quickstart.md`.

### Gate C: Production Cleanup Gate

**Execution Order**:
1. Deprecate wrappers with unresolved callers.
2. Rewrite mixed modules.
3. Delete dead modules after strict delete gate checks.

**Required Evidence**:
- Runtime import graph checks for delete targets.
- Delete-target import-clean precondition checks have been completed.
- Classification contract satisfied per target.
- Runtime-entrypoint checklist is complete in `specs/001-legacy-schema-cleanup/plan.md`.

**Import-Clean Precondition Checks**:
- Confirm no active runtime entrypoint imports `python/hopilot/queries.py`.
- Confirm no active runtime entrypoint imports `python/hopilot/database/aggregation.py`.
- Confirm no active runtime entrypoint imports `python/hopilot/models/board_card.py` or re-exports `BoardCard` from `python/hopilot/models/__init__.py`.
- Confirm all delete-target references are absent from active `python/hopilot/` modules and runtime import graph scans.
- Record `runtime_imports_removed=true` in gate evidence for each delete target once the precondition passes.

### Gate D: Final Regression Gate

**Required Suites**:
- Replay migration tests
- Run-boundary analytical tests
- Matrix-sweep aggregation tests

**Pass Condition**:
- All required suites pass with no critical failures.

## Failure Policy

- If any gate fails, progression to next gate is blocked.
- Failed gates require explicit failure reason and corrective action before retry.
- Failed gate output MUST set `next_gate_allowed=false`.
- A failed Proof Gate blocks all delete actions.

## Output Shape

```json
{
  "gate_name": "proof_gate|test_cleanup_gate|production_cleanup_gate|final_regression_gate",
  "result": "pass|fail",
  "evidence": ["..."],
  "failure_reason": "string|null",
  "runtime_imports_removed": true,
  "next_gate_allowed": true
}
```
