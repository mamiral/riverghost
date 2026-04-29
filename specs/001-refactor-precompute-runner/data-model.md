# Data Model: Precompute Orchestration Refactor

## Purpose

Define the behavioral entities and interactions used by the refactored orchestration flow. This feature does not introduce new database schema objects; it formalizes orchestration-domain models and collaborator boundaries.

## Entities

### 1. PrecomputeRunRequest

Represents one invocation of precompute execution.

- **Attributes**:
  - `profile`
  - `run_id` (optional)
  - `max_scenarios` (optional)
- **Validation rules**:
  - profile must be present or defaultable
  - `max_scenarios` when provided is positive integer
- **Lifecycle**:
  - created at run start
  - consumed by orchestrator

### 2. ScenarioDescriptor

Represents one enumerated scenario to process.

- **Attributes**:
  - `scenario_key`
  - `position`
  - `metric`
  - `position_actions`
  - `strict_current_action`
- **Validation rules**:
  - `scenario_key` non-empty and unique within run
  - required fields present

### 3. ScenarioContext

Represents validated context used to build a sweep contract.

- **Attributes**:
  - `position`
  - `action`
  - `position_actions`
  - optional runtime parameters (`pot_size`, `bet_amount`, `game_type`, etc.)
- **Validation rules**:
  - direct context construction required
  - malformed/missing core fields result in orchestration failure classification

### 4. SweepContract

Represents normalized matrix-sweep execution contract.

- **Attributes**:
  - selected position/action details
  - active players/opponent count
  - simulation parameters
  - run/scenario linkage identifiers
- **Validation rules**:
  - must be generated from validated `ScenarioContext`
  - must retain existing contract semantics expected by sweep service

### 5. ScenarioRunStatusRecord

Represents persisted status for one scenario run link.

- **Attributes**:
  - `status` (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`)
  - optional `failure_boundary` and `failure_reason`
  - optional `simulation_id` and `matrix_id`
- **Validation rules**:
  - failure boundary required for failed states
  - result IDs required for completed states

### 6. PrecomputeJobProgress

Represents aggregate counters and terminal state for a precompute job.

- **Attributes**:
  - `completed_scenarios`
  - `failed_scenarios`
  - `run_state` terminal value
- **Validation rules**:
  - counts reconcile to attempted scenarios
  - terminal state consistent with cancellation/failure/completion rules

## Relationships

- `PrecomputeRunRequest` 1:N `ScenarioDescriptor`
- `ScenarioDescriptor` 1:1 `ScenarioContext` (resolved before dispatch)
- `ScenarioContext` 1:1 `SweepContract`
- `ScenarioDescriptor` 1:1 `ScenarioRunStatusRecord` (with state transitions over time)
- `PrecomputeJobProgress` aggregates all scenario status outcomes in one run

## State Transitions

### Scenario Run Link

`PENDING -> RUNNING -> COMPLETED | FAILED`

- Orchestration failures transition `RUNNING -> FAILED` with `failure_boundary=orchestration`
- Aggregation failures transition `RUNNING -> FAILED` with `failure_boundary=aggregation`
- Execution/runtime failures transition `RUNNING -> FAILED` with `failure_boundary=solver_write`

### Precompute Job Session

`RUNNING -> COMPLETED | FAILED | CANCELED`

- `CANCELED` if stop requested and respected during dispatch
- `FAILED` if any failed scenarios and not canceled
- `COMPLETED` if all attempted scenarios succeeded and not canceled

## Collaborator Boundaries (Planned)

### PrecomputeOrchestrationService

Responsibilities:
- scenario orchestration
- direct context resolution and validation
- sweep contract preparation
- dispatch coordination

### PrecomputeJobPersistenceService

Responsibilities:
- job session create/update/finalization
- scenario run link create/update
- progress counter persistence
- standardized result/failure recording

These collaborators map to existing persisted entities without schema changes.
