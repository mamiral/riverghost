# Contract: Precompute Run Orchestration

## Purpose

Define the required orchestration behavior between `AoFPrecomputeRunner` and production `MatrixSweepService` for each requested scenario in a precompute job.

## Inputs

- `job_session_id`
- ordered `scenario_requests[]`
  - `scenario_index`
  - `scenario_key`
  - normalized `scenario_contract`

## Delegation Behavior

1. Runner validates scenario request and records a `ScenarioRunLink` with `PENDING` status.
2. Runner transitions link to `RUNNING` and delegates scenario to `MatrixSweepService.run_sweep(scenario_contract)`.
3. On success, runner stores returned identifiers and marks link `COMPLETED`.
4. On failure, runner marks link `FAILED` with boundary classification and reason.

## Required Success Output Per Scenario

- `simulation_id` (required)
- `matrix_id` (required)
- `status` (`COMPLETED`)
- any sweep-reported summary fields may be stored for diagnostics

## Required Failure Output Per Scenario

- `status` (`FAILED`)
- `failure_boundary` one of: `orchestration`, `solver_write`, `aggregation`
- `failure_reason` non-empty text
- `simulation_id` optional when failure occurs after simulation creation

## Orchestration Constraints

- Runner MUST NOT write `GameState` rows with `cell_id`.
- Runner MUST NOT create board-card, bet, or jackpot rows for this feature path.
- Runner MUST delegate directly to production sweep service.
- Automatic retries are out of scope and MUST NOT be added.

## Cancellation Semantics

- Cancellation is cooperative.
- After cancellation request, runner MUST stop dispatching new scenarios.
- In-flight delegated scenario is allowed to complete to terminal status.
- Job session ends with canceled terminal lifecycle outcome.
