# Quickstart: Precompute Orchestration Refactor

## Objective

Implement and verify the orchestration refactor for `AoFPrecomputeRunner` while preserving external behavior.

## Prerequisites

- Feature branch checked out: `001-refactor-precompute-runner`
- Virtual environment active
- Dependencies installed from project `requirements.txt`

## Implementation Steps

1. Create collaborator modules in `python/hopilot/gto/`:
   - `precompute_orchestration.py`
   - `precompute_job_persistence.py`
2. Move orchestration concerns out of `aof_precompute_runner.py`:
   - context resolution (direct-only policy)
   - scenario orchestration and contract creation
   - sweep result/failure recording
   - job progress update and finalization
3. Keep `AoFPrecomputeRunner.run()` as a thin coordinator that delegates.
4. Preserve existing failure boundary names and final-state logic.
5. Update tests only where expectations reflect collaborator boundaries, not behavior changes.

## Verification Commands

Run targeted suites:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_aof_precompute_runner.py -q --maxfail=1
.venv\Scripts\python.exe -m pytest tests/test_precompute_runner_regression.py -q --maxfail=1
.venv\Scripts\python.exe -m pytest tests/test_matrix_sweep_precompute_runner.py -q --maxfail=1
.venv\Scripts\python.exe -m pytest tests/integration/test_precompute_runner_integration.py -q --maxfail=1
```

Optional broader confidence run:

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q --maxfail=1
```

## Expected Outcomes

- No behavior regressions in targeted suites.
- Scenario status records and failure boundaries unchanged in semantics.
- Completed/failed counters and final run state remain consistent.
- No payload fallback use during scenario context resolution.

## Rollback Guidance

If behavioral regressions appear:
1. Compare scenario link lifecycle transitions against baseline tests.
2. Validate direct context resolution path for malformed provider context.
3. Temporarily route orchestration through existing runner methods to isolate collaborator defects.
