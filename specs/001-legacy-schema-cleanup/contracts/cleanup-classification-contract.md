# Contract: Cleanup Classification

## Purpose

Define required behavior for classifying production and test targets as `DELETE`, `REWRITE`, `DEPRECATE`, or `KEEP`.

## Required Inputs

- Target path
- Target kind (`production_module` or `test_module`)
- Detected legacy dependency signals
- Replacement path evidence status
- Runtime import reference status

## Classification Rules

1. `DELETE`
- Allowed only when replacement path exists and is validated.
- Runtime entrypoint imports must be removed first.
- No fallback shim may be introduced unless explicit migration exception is approved.

2. `REWRITE`
- Required when module contains mixed valid and stale logic.
- Rewritten module must preserve active GameStates-first behavior.
- Legacy dependency signals must be removed from active code path.

3. `DEPRECATE`
- Allowed only when immediate removal is unsafe due to unresolved callers.
- Must include explicit one-release-cycle removal deadline.
- New callsites must be blocked.

4. `KEEP`
- Allowed only when module is aligned with active architecture and contains no legacy dependency signal in active path.

## Output Shape

```json
{
  "target_path": "string",
  "target_kind": "production_module|test_module",
  "classification": "DELETE|REWRITE|DEPRECATE|KEEP",
  "legacy_signals": ["..."],
  "replacement_proven": true,
  "runtime_imports_removed": true,
  "decision_rationale": "string"
}
```

## Acceptance Conditions

- Every target in cleanup scope has exactly one classification record.
- No `DELETE` record may pass with `runtime_imports_removed=false`.
- Any `DEPRECATE` record must include a one-release-cycle deadline in plan/tasks artifacts.

## Acceptance Semantics

- `PASS`: Classification record is complete, evidence is present, and all classification rules are satisfied.
- `BLOCKED`: Classification record exists but required evidence is missing or an explicit rule is violated.

### Required PASS Evidence

1. `DELETE`
- `replacement_proven=true`
- `runtime_imports_removed=true`
- Decision rationale references at least one legacy dependency signal

2. `REWRITE`
- Rewrite scope is explicitly documented
- Active behavior preservation is documented against GameStates-first architecture

3. `DEPRECATE`
- Remaining callers are identified
- One-release-cycle removal deadline is recorded in plan/tasks artifacts

4. `KEEP`
- No active-path legacy dependency signal remains
- Decision rationale explains why module remains in active architecture
