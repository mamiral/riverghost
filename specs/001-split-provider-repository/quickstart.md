# Quickstart: Provider/Repository Responsibility Split

## Objective

Implement and verify provider and persistence responsibility separation with mandatory deterministic reconciliation/finalization, without changing external precompute or browser behavior.

## Prerequisites

- Branch checked out: 001-split-provider-repository
- Virtual environment active
- Dependencies installed from requirements.txt

## Implementation Sequence

1. Enforce provider contract split in gto modules.
2. Restrict orchestration call paths to direct context contract only.
3. Keep browser read paths on payload contract only.
4. Split raw persistence and tracking persistence into separate transaction scopes.
5. Add mandatory reconciliation/finalization pass before terminal run completion.
6. Preserve failure boundary semantics and external outputs.

## Verification Commands

Run targeted suites first:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_aof_precompute_runner.py -q --maxfail=1
.venv\Scripts\python.exe -m pytest tests/test_precompute_runner_regression.py -q --maxfail=1
.venv\Scripts\python.exe -m pytest tests/test_matrix_sweep_precompute_runner.py -q --maxfail=1
.venv\Scripts\python.exe -m pytest tests/integration/test_precompute_runner_integration.py -q --maxfail=1
```

Run full regression:

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q --maxfail=1
```

## Expected Outcomes

- Orchestration tests prove no payload-contract calls in orchestration flow.
- Browser payload tests prove read path independence from orchestration logic.
- Reconciliation/finalization resolves all split-write mismatch scenarios deterministically.
- Final counters satisfy completed plus failed equals attempted for each run.
- External behavior remains backward-compatible.

## Compatibility Notes

- The feature preserves failure boundary semantics in scenario links and terminal job state values.
- Browser payload responses continue to return `AVAILABLE`, `MISSING`, and `NO_CONTEST` states consistently.
- The reconciliation pass is deterministic for identical inputs and repairs only job/session accounting, not raw matrix data.

## Troubleshooting Focus

- If orchestration tests fail, inspect provider call paths for payload fallback usage.
- If reconciliation tests fail, compare raw outcomes against scenario-link status transitions and counter recomputation.
- If regression appears, validate failure boundary values and terminal run_state derivation.

## Phase 6 Audit Notes

- The final audit checks that provider contract separation and job/session tracking
  remain isolated from raw sweep persistence.
- The reconciliation pass is intentionally mandatory and deterministic for identical
  persisted inputs.
- Run the full suite after final review to verify end-to-end behavior.
