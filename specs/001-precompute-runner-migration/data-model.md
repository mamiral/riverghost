# Data Model: Precompute Runner Sweep Delegation

## Overview

This feature keeps production sweep persistence (`Simulation`, `HandMatrix`, `MatrixCell`, `AggregatedMetric`) and introduces durable job-orchestration linkage records so UI precompute jobs can be traced to delegated sweep outputs. The precompute runner no longer writes cell-coupled raw artifacts directly.

## Entities

### PrecomputeJobSession

**Purpose**: Represents one UI-triggered precompute run lifecycle.

**Fields**

- `job_session_id: int`
- `scenario_fingerprint: str`
- `run_state: enum(IDLE, RUNNING, PAUSED, STOPPING, COMPLETED, FAILED)`
- `requested_scenarios: int`
- `completed_scenarios: int`
- `failed_scenarios: int`
- `started_at: datetime | null`
- `finished_at: datetime | null`
- `elapsed_active_ms: int`

**Validation rules**

- `completed_scenarios + failed_scenarios <= requested_scenarios`
- terminal states require `finished_at`
- lifecycle transitions must follow existing transition map

### ScenarioRunLink

**Purpose**: Durable mapping from one requested scenario to one delegated sweep run result.

**Fields**

- `scenario_link_id: int`
- `job_session_id: int`
- `scenario_index: int`
- `scenario_key: str`
- `scenario_contract: dict`
- `simulation_id: int | null`
- `matrix_id: int | null`
- `status: enum(PENDING, RUNNING, COMPLETED, FAILED, CANCELED)`
- `failure_boundary: enum(orchestration, solver_write, aggregation) | null`
- `failure_reason: str | null`
- `created_at: datetime`
- `updated_at: datetime`

**Validation rules**

- `simulation_id` required when status is `COMPLETED`
- `failure_boundary` required when status is `FAILED`
- one unique (`job_session_id`, `scenario_index`) row

### ScenarioPhaseProgress

**Purpose**: Snapshot payload exposed to GUI and logs during delegated execution.

**Fields**

- `job_session_id: int`
- `run_state: str`
- `active_scenario_index: int | null`
- `active_scenario_key: str | null`
- `phase: enum(orchestration, solver_write, aggregation, finalizing)`
- `completed_scenarios: int`
- `total_scenarios: int`
- `failure_count: int`
- `elapsed_seconds: float`
- `eta_seconds: float | null`
- `last_update_at: datetime`

**Validation rules**

- state names remain backward compatible with current GUI expectations
- phase field may extend, but existing lifecycle semantics must not regress

## Relationships

- `PrecomputeJobSession 1 -> N ScenarioRunLink`
- `ScenarioRunLink 0..1 -> 1 Simulation` (null until delegated run is created)
- `Simulation 1 -> 1 HandMatrix` (via existing sweep pipeline)
- `HandMatrix 1 -> 169 MatrixCell`
- `MatrixCell 1 -> 1 AggregatedMetric` (as produced by aggregation)

## Derived Values

### Scenario Fingerprint

- Derived from normalized scenario inputs and orchestration mode fields.
- Used to detect resume compatibility and job continuity.

### Progress ETA

- Derived from `completed_scenarios`, elapsed active time, and total scenarios.
- Undefined (`null`) until enough throughput history exists.

### Failure Boundary

- Derived from the execution stage where failure occurred:
  - orchestration: validation/delegation setup
  - solver_write: raw run execution
  - aggregation: post-processing to matrix outputs

## Failure Cases

- Delegation never starts: create `ScenarioRunLink` failed at `orchestration` boundary.
- Raw sweep fails after simulation creation: record `simulation_id` if known and classify as `solver_write`.
- Aggregation fails after raw writes: classify as `aggregation`; preserve raw run evidence.
- Job canceled during active scenario: no new scenarios dispatched; in-flight scenario reaches terminal status before session cancellation finalizes.
