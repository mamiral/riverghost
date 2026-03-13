# Data Model: Offline AoF Matrix Precomputation and SQLite Scenario Cache

## ScenarioKey
- Description: Canonical identity for a matrix scenario request.
- Fields:
  - selected_position: enum (UTG, BTN, SB, BB)
  - position_actions: normalized map of position -> action
  - metric: enum (WIN_LOSE_PROBABILITY, EV, EQUITY, EQR)
  - pot_size: positive number
  - bet_amount: positive number
  - strict_current_action: boolean
  - runtime_knobs: simulations, combo_samples, timeout budget, seed
  - solver_signature: string
  - policy_signature: string
- Validation rules:
  - All positions required in position_actions
  - Numeric values positive and normalized
  - Key hashing is stable and order-independent for maps

## CanonicalSolverKey
- Description: Solver-equivalence identity used to deduplicate persisted cell matrices across request contexts that differ only by non-semantic seat labels.
- Fields:
  - metric: enum (WIN_LOSE_PROBABILITY, EV, EQUITY, EQR)
  - selected_action: enum (FOLD, ALL_IN)
  - num_opponents: integer
  - pot_size: positive number
  - bet_amount: positive number
  - effective_mode: enum (analysis, strict-current-action)
  - runtime_knobs: simulations, combo_samples, timeout budget, seed
  - solver_signature: string
  - policy_signature: string
- Validation rules:
  - Key hashing is stable and order-independent
  - Equivalent solver semantics MUST resolve to the same canonical key

## MatrixPayloadRecord
- Description: Persisted UI-consumable payload for one scenario key.
- Fields:
  - scenario_key_hash: primary lookup key
  - context_json: serialized context object
  - cells_json: serialized 169-cell array with value/status/display
  - status_message: nullable string
  - created_at: timestamp
  - updated_at: timestamp

## CacheMetadata
- Description: Lifecycle metadata used for stale detection.
- Fields:
  - schema_version: integer/string version marker
  - solver_signature: string
  - policy_signature: string
  - runtime_signature: string
  - is_stale: boolean
  - stale_reason: nullable text

## OfflinePrecomputeRun
- Description: Tracks one offline batch run and resume status.
- Fields:
  - run_id: unique identifier
  - started_at: timestamp
  - finished_at: nullable timestamp
  - status: enum (RUNNING, COMPLETED, FAILED, CANCELLED)
  - total_scenarios: integer
  - completed_scenarios: integer
  - failed_scenarios: integer
  - resume_cursor: nullable token/index

## ScenarioWriteResult
- Description: Per-scenario outcome from precompute/runtime write-back.
- Fields:
  - run_id: nullable reference (runtime writes may be unscoped)
  - scenario_key_hash: string
  - outcome: enum (INSERTED, UPDATED, SKIPPED_CURRENT, FAILED)
  - error_message: nullable text
  - written_at: timestamp

## Relationships
- ScenarioKey N:1 CanonicalSolverKey
- CanonicalSolverKey 1:1 MatrixPayloadRecord (current materialized payload)
- MatrixPayloadRecord 1:1 CacheMetadata
- OfflinePrecomputeRun 1:N ScenarioWriteResult
