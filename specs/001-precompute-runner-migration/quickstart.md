# Quickstart: Verify Precompute Runner Sweep Delegation

## Assumptions

- Work from `C:\Users\U446541\sandbox\riverghost`
- Use existing project virtual environment
- Run tests against temporary SQLite DB fixtures, not production database file

## Verification Flow

1. Activate the project environment.
2. Run runner unit tests that validate delegation behavior and lifecycle compatibility.
3. Run pipeline/integration tests proving delegated sweep execution creates real persisted outputs.
4. Validate failure-boundary and cancellation behavior with targeted tests.

## Verification Commands

```powershell
.venv\Scripts\Activate.ps1
python -m pytest tests/test_aof_precompute_runner.py tests/test_matrix_sweep_precompute_runner.py tests/test_aof_precompute_cli.py tests/contract/test_precompute_runner_contracts.py tests/integration/test_precompute_runner_integration.py -q
```

## Expected Assertions

- precompute runner delegates scenario execution to matrix sweep service
- runner no longer writes `GameState` with `cell_id` in migrated path
- runner no longer creates board-card, bet, or jackpot artifacts in migrated path
- successful delegated runs persist `Simulation` and `HandMatrix` outputs
- each requested scenario can be traced to persisted simulation identifiers
- lifecycle states remain backward compatible for GUI consumers
- progress snapshots expose scenario counts and current phase
- failures are classified by `orchestration`, `solver_write`, or `aggregation`
- cancellation is cooperative: no new scenarios after cancellation request

## Manual Inspection Targets

- inspect runner code path for removal of direct dead-schema write calls in delegated execution flow
- inspect persisted linkage rows tying job/scenario identity to `simulation_id`
- inspect logs/telemetry for phase-aware progress updates and boundary-classified failures
