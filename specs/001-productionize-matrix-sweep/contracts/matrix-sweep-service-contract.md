# Contract: Matrix Sweep Orchestration Service

## Interface Type
Internal service contract (Python module boundary), consumed by precompute/CLI layers.

## Operation
`run_sweep(scenario_contract) -> run_result`

## Request Contract

### scenario_contract (required)
- `selected_position`: string
- `hero_action`: string
- `position_actions`: object[string -> string]
- `active_players`: integer
- `num_opponents`: integer
- `pot_size`: number
- `bet_amount`: number
- `sims_per_combo`: integer
- `matrix_size`: string (`13x13`)
- `game_type`: string
- `run_kind`: string (`matrix_sweep`)

### Validation Rules
- `num_opponents` fixed for entire run
- `sims_per_combo` > 0
- `matrix_size` must be canonical 13x13 for this feature scope
- scenario contract persisted unchanged in `Simulation.parameters`

## Response Contract

### run_result (success)
- `simulation_id`: integer
- `matrix_id`: integer
- `raw_game_states_written`: integer
- `raw_players_written`: integer
- `matrix_cells_written`: integer (expected 169)
- `aggregated_metrics_written`: integer (expected 169)
- `failed_combinations`: integer
- `unmapped_hero_records`: integer
- `status`: enum[`completed`]

### run_result (failure)
- `simulation_id`: integer | null (if failure before simulation creation)
- `matrix_id`: integer | null
- `status`: enum[`failed`]
- `error_code`: string
- `error_message`: string

## Behavioral Guarantees
- Sweep phase writes only raw `GameState` and `Player` rows.
- Aggregation phase runs after sweep and writes summaries under one run boundary.
- Historical runs remain unchanged when new run executes.

## Rerun Aggregation Contract
Operation: `rerun_aggregation(simulation_id) -> rerun_result`

Behavior:
- resolve run's `HandMatrix`
- delete existing `MatrixCell` + `AggregatedMetric` rows for that `matrix_id`
- recreate summaries from existing raw records
- do not modify raw `GameState`/`Player` rows
- do not modify other runs

Response fields:
- `simulation_id`
- `matrix_id`
- `matrix_cells_recreated`
- `aggregated_metrics_recreated`
- `status`: enum[`completed`, `failed`]
