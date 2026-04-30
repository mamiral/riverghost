# Phase 1 Data Model: Database Repository Refactor

## Overview
This feature introduces architectural entities (capability boundaries and contracts) rather than new database tables. Existing SQLAlchemy ORM entities remain unchanged.

## Architectural Entities

### 1. Raw Persistence Domain (`GameStateRepository`)
- Purpose: Own raw simulation/game state writes and CRUD for game-state related records.
- Owned capabilities:
  - GameState CRUD and bulk writes
  - Player/Bet/Jackpot CRUD and bulk writes
  - Raw run projections and counts
- Invariants:
  - Preserves GameStates-first architecture
  - No job/session lifecycle ownership

### 2. Simulation/Matrix Domain (`SimulationRepository`)
- Purpose: Own simulation metadata and matrix persistence/readback.
- Owned capabilities:
  - Simulation and hand matrix lifecycle
  - Matrix cell upsert and summary retrieval
  - Scenario contract run resolution and lookup
- Invariants:
  - No ownership of job/session tracking counters
  - No ownership of raw player/bet/jackpot CRUD

### 3. Tracking Domain (`PrecomputeJobRepository`)
- Purpose: Own durable precompute job and scenario link lifecycle.
- Owned capabilities:
  - Create/update/query `PrecomputeJobSession`
  - Create/update/query `ScenarioRunLink`
- Invariants:
  - Tracking writes must participate in shared unit-of-work for coupled workflow steps
  - No direct ownership of matrix analytics queries

### 4. Analytics/Query Domain (`AnalyticsRepository`)
- Purpose: Own read projections used by browser/replay/query services.
- Owned capabilities:
  - Strategy matrix retrieval
  - Convergence/jackpot/simulation summary queries
  - Cross-run matrix summary projections
- Invariants:
  - Read-oriented; does not own durable job/session state changes

### 5. Compatibility Facade (`DatabaseRepository` transitional)
- Purpose: Transitional delegating entrypoint during migration.
- Lifecycle:
  - Present during staged migration
  - Removed immediately after first consumer migration trigger is satisfied (`aof_precompute_runner.py` + `precompute_job_persistence.py`)

## Existing ORM Data Entities (unchanged schema)
- `Simulation`
- `HandMatrix`
- `MatrixCell`
- `AggregatedMetric`
- `GameState`
- `Player`
- `Bet`
- `Jackpot`
- `PrecomputeJobSession`
- `ScenarioRunLink`

## Relationship Notes
- Domain repositories coordinate via shared unit-of-work/session in coupled workflow steps.
- Services/providers remain responsible for async adaptation and orchestration.
- Repository boundaries are synchronous by contract.

## Validation Rules
- Domain validators must be explicit and not depend on placeholder/dummy payload construction.
- Validation failures must remain attributable to owning domain boundary.

## State Transitions

### Precompute Job Session (unchanged lifecycle semantics)
- `RUNNING` -> `COMPLETED`
- `RUNNING` -> `FAILED`
- Scenario-link statuses remain consistent with existing failure boundary semantics.

### Compatibility Facade Lifecycle
- `ACTIVE` -> `REMOVED` once first consumer migration trigger is met.
