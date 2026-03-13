# Contract: AoF Browser In-GUI Precompute Runner

## Purpose
Define the contract between AoF browser UI controls, GUI precompute orchestration, and persistent cache/checkpoint behavior.

## Control Interface Contract
Input actions:
- `start(simulations_per_cell, scenario_context)`
- `pause()`
- `resume()`
- `stop()`
- `reset()`

State transitions:
1. `start` from IDLE initializes run session and sets state RUNNING.
2. `pause` from RUNNING sets pause request and transitions to PAUSED at next cooperative boundary.
3. `resume` from PAUSED restarts from checkpoint `next_cell_index`.
4. `stop` from RUNNING/PAUSED transitions through STOPPING and persists checkpoint.
5. `reset` from PAUSED/COMPLETED/FAILED clears in-memory session and optional checkpoint.

Invalid calls (no-op with warning log):
- `pause` from IDLE/COMPLETED/FAILED
- `resume` when no checkpoint exists
- `start` while RUNNING unless user confirms stop-and-restart

## Scenario Guard Contract
- While state in {RUNNING, STOPPING}, scenario-defining controls (position/actions/metric/strict-mode) are locked.
- If user attempts scenario change during active run, UI MUST present confirmation:
  - confirm stop-and-restart: stop current run, apply change, reset counters, start new run
  - cancel change: keep current run and controls unchanged

## Progress + Telemetry Contract
Required telemetry payload for UI panel refresh:
```json
{
  "run_state": "RUNNING",
  "completed_cells": 37,
  "total_cells": 169,
  "current_cell": {"index": 38, "hand_key": "KQo"},
  "elapsed_seconds": 42.3,
  "eta_seconds": 151.0,
  "failure_count": 2
}
```

Rules:
1. `completed_cells` increments only when a cell reaches terminal status.
2. `current_cell` reflects the cell currently being processed; null when paused/completed.
3. `eta_seconds` may be null until timing sample count is sufficient.

## Cell Update Contract
For each completed cell, matrix payload entry MUST be updated immediately with deterministic status semantics:
- AVAILABLE
- MISSING
- NO_CONTEST
- TIMEOUT
- ERROR

Continuation rules:
1. TIMEOUT/ERROR on one cell increments `failure_count` and processing continues.
2. Runner-level unhandled exception transitions run to FAILED and preserves checkpoint.

## Checkpoint + Resume Contract
Checkpoint persistence requirements:
1. Persist progress at least after each cell completion and on pause/stop transition.
2. Persist run lifecycle metadata using existing run tables (`aof_precompute_run`, `aof_precompute_write_result`).
3. Resume MUST skip already completed cells for the same scenario fingerprint and canonical key.

Recovery requirements:
1. On app restart, runner may restore latest RUNNING/PAUSED checkpoint and expose Resume action.
2. If checkpoint scenario does not match active scenario context, resume is blocked until user selects matching scenario or resets checkpoint.

## Canonical Dedup + Context Hydration Contract
- Persistent writes and reads use canonical solver-equivalence keying.
- Returned payload in GUI MUST hydrate request-local context for the currently selected scenario.
- Cell values/status may come from canonical cache hit, but UI context cannot leak canonical seat labeling.

## Responsiveness Contract
- Cooperative execution chunk cadence MUST target pause/stop acknowledgement <= 1 second under reference workload.
- Main UI loop remains interactive during run; no intentional blocking solve loop on render thread.

## Observability Contract
Emit structured lifecycle events via standard logger:
- `gui_precompute_started`
- `gui_precompute_paused`
- `gui_precompute_resumed`
- `gui_precompute_stopping`
- `gui_precompute_completed`
- `gui_precompute_failed`
- `gui_precompute_checkpoint_saved`
- `gui_precompute_checkpoint_restored`
- existing provider/cache events for cache hit/miss/stale/timeout/error
