# Data Model: Provider/Repository Responsibility Split

## Purpose

Define behavioral entities, boundaries, and lifecycle transitions required to split provider/repository responsibilities while preserving existing behavior. This feature does not introduce new database tables.

## Entities

### 1. ProviderContextContract

Orchestration-facing provider contract used to resolve validated scenario context for sweep execution.

- Fields:
  - position
  - metric
  - action
  - position_actions
  - pot_size
  - bet_amount
  - strict_current_action
  - optional game_type and derived fields
- Validation rules:
  - Required keys must be present and semantically valid
  - Invalid context yields orchestration-classified failure
- Invariants:
  - Orchestration consumers must not call payload retrieval API

### 2. ProviderPayloadContract

Browser-facing provider contract used to return matrix payload for UI/read paths.

- Fields:
  - context (position, metric, action, position_actions, active_players, optional matrix_id)
  - cells (169 matrix cells with hand_key, value, status, display)
  - status and status_message
- Validation rules:
  - Context must remain browser-consumable even for missing data
  - Payload contract cannot require orchestration-only fields
- Invariants:
  - Payload reads remain independent of orchestration execution flow

### 3. RawSweepPersistenceRecord

Represents persisted raw sweep outcome for one scenario execution.

- Fields:
  - simulation_id
  - matrix_id
  - raw_game_states_written
  - raw_players_written
  - execution status details
- Validation rules:
  - Successful raw outcome requires valid simulation and matrix identifiers
  - Raw write failures must persist diagnostic boundary data
- Invariants:
  - Written in raw persistence transaction scope only

### 4. JobTrackingRecord

Represents job/session plus scenario-link lifecycle state.

- Fields:
  - job_session_id
  - scenario_index
  - scenario_key
  - status (PENDING, RUNNING, COMPLETED, FAILED)
  - failure_boundary
  - failure_reason
  - simulation_id
  - matrix_id
  - completed_scenarios
  - failed_scenarios
  - run_state
- Validation rules:
  - FAILED records require failure_boundary and failure_reason
  - COMPLETED records require simulation_id and matrix_id
  - completed plus failed must reconcile to attempted in final state
- Invariants:
  - Written in job-tracking transaction scope only

### 5. ReconciliationFinalizationRecord

Behavioral entity representing deterministic mismatch detection and correction after split transactions.

- Fields:
  - job_session_id
  - attempted_scenarios
  - tracked_completed
  - tracked_failed
  - raw_success_count
  - raw_failure_count
  - mismatch_count
  - final_run_state
  - reconciliation_actions
- Validation rules:
  - Reconciliation must run exactly once per run finalization path
  - For identical persisted inputs, produced actions and final state must be identical
- Invariants:
  - Mandatory execution before run completion is considered final

## Relationships

- ProviderContextContract 1:1 Sweep execution request for each scenario.
- ProviderPayloadContract 1:N browser reads for equivalent scenario context.
- RawSweepPersistenceRecord 1:1 Scenario execution attempt.
- JobTrackingRecord 1:1 Scenario run link with aggregate 1:N to job session.
- ReconciliationFinalizationRecord 1:1 per finalized job session over all scenario records.

## State Transitions

### Scenario link lifecycle

PENDING -> RUNNING -> COMPLETED | FAILED

- Orchestration validation failure: RUNNING -> FAILED with boundary orchestration.
- Aggregation failure: RUNNING -> FAILED with boundary aggregation.
- Execution/persistence failure: RUNNING -> FAILED with boundary solver_write.

### Job session lifecycle

RUNNING -> COMPLETED | FAILED | CANCELED

- COMPLETED: all attempted scenarios reconciled as completed, none failed.
- FAILED: one or more reconciled failed scenarios and not canceled.
- CANCELED: cancellation requested and run stops dispatch.

### Reconciliation/finalization lifecycle

PENDING_RECONCILIATION -> RECONCILING -> FINALIZED

- Entry condition: split transactions may have produced mismatched raw/tracking states.
- Exit condition: mismatch count is zero after deterministic corrections.

## Transaction Boundaries

- Raw transaction scope: writes raw sweep artifacts only.
- Tracking transaction scope: writes scenario-link and job progress only.
- Finalization scope: reads persisted state from both scopes and performs deterministic reconciliation updates.

No cross-scope transaction is permitted for this feature.
