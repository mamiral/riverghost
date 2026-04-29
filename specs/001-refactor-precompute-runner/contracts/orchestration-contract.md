# Orchestration Contract: Precompute Runner Refactor

## Scope

Internal behavioral contract between `AoFPrecomputeRunner` and new orchestration/persistence collaborators.

## Contract 1: Scenario Context Resolution

### Inputs
- `ScenarioDescriptor` (position, metric, position actions, strict mode)
- provider capable of direct context construction

### Rules
- Direct context construction is the only allowed resolution path for precompute orchestration.
- Payload retrieval fallback is not permitted in orchestration flow.
- Missing/invalid core fields (`action`, `position_actions`, required keys) result in orchestration failure classification.

### Outputs
- Valid `ScenarioContext` for contract building
- or classified orchestration failure

## Contract 2: Scenario Run Link Lifecycle

### Required transitions
- `PENDING -> RUNNING -> COMPLETED`
- `PENDING -> RUNNING -> FAILED`

### Required persisted diagnostics
- Failure requires `failure_boundary` and `failure_reason`
- Completion requires `simulation_id` and `matrix_id`

### Failure boundary mapping
- contract/orchestration validation issues -> `orchestration`
- aggregation failures -> `aggregation`
- other sweep execution failures -> `solver_write`

## Contract 3: Job Progress Persistence

### Required behavior
- `completed_scenarios` or `failed_scenarios` updated after every scenario attempt
- counters reconcile with attempted scenario count
- terminal job state set to one of `COMPLETED`, `FAILED`, `CANCELED`

### Terminal state rules
- `CANCELED` when stop requested and run halts dispatch
- `FAILED` when one or more failed scenarios and not canceled
- `COMPLETED` when no failed scenarios and not canceled

## Contract 4: Behavior Preservation

### Non-negotiable outcomes
- `AoFPrecomputeRunner.run()` return semantics remain unchanged
- Existing targeted regression/integration tests continue to pass
- Persisted lifecycle/state semantics remain compatible with current tests and consumers
