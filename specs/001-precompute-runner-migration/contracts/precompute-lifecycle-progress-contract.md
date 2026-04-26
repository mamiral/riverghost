# Contract: Precompute Lifecycle and Progress

## Purpose

Define the lifecycle and progress guarantees that must remain stable for GUI/job orchestration consumers after migration to sweep-based execution.

## Lifecycle States

- `IDLE`
- `RUNNING`
- `PAUSED`
- `STOPPING`
- `COMPLETED`
- `FAILED`

## Compatibility Requirement

- State names and terminal semantics MUST remain backward compatible.
- Progress payload fields MAY evolve as long as state-driven consumer behavior remains valid.

## Progress Snapshot Shape

- `run_state`
- `completed_scenarios`
- `total_scenarios`
- `active_scenario` (index/key, nullable)
- `phase` (`orchestration`, `solver_write`, `aggregation`, `finalizing`)
- `elapsed_seconds`
- `eta_seconds` (nullable)
- `failure_count`

## Progress Semantics

- Snapshot updates MUST be monotonic for completed/failed counts.
- `phase` reflects active delegated boundary, not per-cell internals.
- `eta_seconds` may be null early in runs or when insufficient throughput history exists.

## Terminal Behavior

- `COMPLETED`: all scenarios terminal with no unresolved failures.
- `FAILED`: at least one non-recoverable orchestration-level job failure prevents run completion.
- `STOPPING` then canceled terminal outcome: cancellation requested and no new scenarios dispatched.

## Failure Classification Exposure

Each failed scenario MUST expose:

- `failure_boundary`
- `failure_reason`
- `simulation_id` when available

This metadata is required for manual retry and post-run diagnosis.
