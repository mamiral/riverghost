# Contract: Persistence Split and Deterministic Reconciliation

## Scope

Behavioral contract for isolating raw sweep persistence from job/session tracking persistence using separate transactions with mandatory reconciliation/finalization.

## Contract A: Raw Sweep Persistence Transaction

### Responsibilities

- Persist simulation/matrix/game-state raw outputs for each scenario attempt.
- Return raw outcome identifiers and counts needed for linkage.

### Rules

- Executes in its own transaction scope.
- Must not write job/session progress counters or run-link status transitions.
- On failure, records sufficient diagnostics for reconciliation.

## Contract B: Job/Session Tracking Transaction

### Responsibilities

- Persist scenario link state transitions and job/session counters.
- Persist failure boundary and reason semantics.

### Rules

- Executes in a separate transaction scope from raw persistence.
- Must not perform raw sweep table writes.
- On failure, leaves a state that reconciliation can deterministically repair.

## Contract C: Mandatory Reconciliation/Finalization Pass

### Trigger

- Runs after scenario execution loop and before final run state is considered complete.
- Runs even when no immediate mismatch is expected.

### Inputs

- Persisted raw sweep outcomes for attempted scenarios.
- Persisted job/session link records and counters.

### Deterministic resolution rules

- For each attempted scenario:
  - If raw success exists and link is non-completed, set link to COMPLETED with identifiers.
  - If link is COMPLETED but raw success is missing, set link to FAILED with deterministic boundary/reason.
  - If both exist and conflict, apply stable precedence and normalize to one final state.
- For job counters:
  - recompute completed and failed from reconciled links
  - enforce completed plus failed equals attempted
- For terminal run_state:
  - CANCELED if cancellation requested and dispatch stopped
  - else FAILED if any reconciled link failed
  - else COMPLETED

### Non-optional guarantees

- Pass is mandatory for every run finalization path.
- Same persisted inputs always produce identical reconciliation actions and final state.
- No manual intervention is required for split-write mismatch scenarios in test scope.

## Observability and Diagnostics

- Reconciliation emits structured diagnostics for mismatch count and applied corrections.
- Failure boundary semantics remain unchanged in meaning for existing consumers.

## Verification

- Targeted tests cover raw-only success, tracking-only success, dual success, dual failure, and mixed mismatch scenarios.
- Full regression confirms no external behavior changes.
