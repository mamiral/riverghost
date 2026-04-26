# Data Model: Productionize Matrix Sweep

## Overview

This feature does not require a new raw-hand schema. It introduces a production run contract and a service-owned run boundary over the existing HoPilot models, then derives summarized matrix data from those raw rows after the sweep completes.

## Entities

### MatrixSweepScenarioContract

**Purpose**: Canonical persisted description of one fixed-scenario sweep run. Stored in `Simulation.parameters`.

**Fields**

- `selected_position: str`
- `hero_action: str`
- `position_actions: dict[str, str]`
- `active_players: list[str]`
- `num_opponents: int`
- `pot_size: float`
- `bet_amount: float`
- `sims_per_combo: int`
- `matrix_size: str` with value `13x13`
- `game_type: str`
- `run_kind: str` with value `matrix_sweep`

**Compatibility fields**

- `num_simulations: int` alias for existing validation that still expects this key

**Validation rules**

- `num_opponents >= 1`
- `sims_per_combo >= 1`
- `matrix_size == "13x13"`
- `run_kind == "matrix_sweep"`
- `position_actions` and `active_players` must describe the same fixed scenario for the entire run

### SweepRunBoundary

**Purpose**: Non-schema entity owned by the sweep service that isolates raw rows for one run. Persisted inside `Simulation.parameters`.

**Fields**

- `simulation_id: int`
- `raw_game_state_id_start: int`
- `raw_game_state_id_end: int`
- `start_timestamp: datetime`
- `end_timestamp: datetime | null`

**Validation rules**

- `raw_game_state_id_start <= raw_game_state_id_end` after a completed sweep
- `end_timestamp` must be null until raw sweep completion
- boundary must be written before aggregation begins

### Simulation

**Purpose**: One persisted run record for a matrix sweep.

**Current model**: Existing `Simulation` ORM model.

**Feature-specific use**

- created once per sweep run before raw simulation begins
- stores the scenario contract and boundary metadata in `parameters`
- updated with `end_timestamp` when the raw sweep finishes

**State transitions**

- `created` -> `raw_sweep_complete` -> `aggregated`
- `aggregated` -> `aggregated` on rerun of aggregation for the same run

### GameState

**Purpose**: Raw outcome record, one per Monte Carlo iteration.

**Current model**: Existing `GameState` ORM model with `timestamp`, `round`, `pot_size`, `board_cards_str`, `outcome`.

**Feature-specific rules**

- written during the sweep phase only
- never stores `cell_id`
- never stores `board_cards_id`
- is isolated to a run only through the persisted boundary metadata, not by foreign key

### Player

**Purpose**: Raw player resolution record belonging to a `GameState`.

**Current model**: Existing `Player` ORM model.

**Feature-specific rules**

- hero player must have `is_hero = True`
- aggregation derives matrix identity from hero `hole_cards`
- `hand_class` and `final_strength` remain raw inputs to later analysis and must not be overwritten during aggregation

### HandMatrix

**Purpose**: One summarized matrix container for a run.

**Current model**: Existing `HandMatrix` ORM model.

**Feature-specific rules**

- exactly one `HandMatrix` per `Simulation`
- created during first aggregation for the run
- reused on aggregation rerun for the same run

### MatrixCell

**Purpose**: One summarized canonical cell inside a run’s `HandMatrix`.

**Current model**: Existing `MatrixCell` ORM model.

**Feature-specific rules**

- exactly 169 rows per completed run
- `row_index` and `col_index` come from canonical hero hand mapping
- `hand_combination` should be a stable label for the hero cell, not a raw-hand foreign key substitute
- deleted and recreated only within one run boundary on aggregation rerun

### AggregatedMetric

**Purpose**: Stored metrics for one `MatrixCell`.

**Current model**: Existing `AggregatedMetric` ORM model.

**Feature-specific rules**

- exactly one per `MatrixCell`
- computed only from raw rows inside the run boundary
- cannot be written during the raw sweep phase
- deleted and recreated together with `MatrixCell` summaries on aggregation rerun

## Relationships

- `Simulation 1 -> 1 HandMatrix`
- `HandMatrix 1 -> 169 MatrixCell`
- `MatrixCell 1 -> 1 AggregatedMetric`
- `GameState 1 -> many Player`
- Raw `GameState` and `Player` rows are associated to a run by `SweepRunBoundary`, not by direct foreign key to `MatrixCell`

## Derived Values

### Canonical Cell Identity

Derived from the hero player’s `hole_cards`:

- pair: diagonal cell
- suited non-pair: upper-right triangle
- offsuit non-pair: lower-left triangle

### Summary Metrics

Derived per canonical cell from raw outcomes within one run boundary:

- `equity = (wins + 0.5 * ties) / total`
- `win_probability = wins / total`
- optional `ev` only if derived directly from persisted raw values without fabrication
- `convergence_status` based on actual sample counts or honest convergence logic

## Failure Cases

### Unmappable Hero Hand

- raw row remains persisted
- row is excluded from summary aggregation
- failure is counted and surfaced in service output/logging

### Zero Valid Samples For A Cell

- run still completes
- cell summary is created with empty/nullable metric fields or an explicit zero-sample status depending on final implementation choice
- no fabricated equity or EV values are allowed

### Aggregation Rerun

- existing `GameState` and `Player` rows are untouched
- existing `HandMatrix` is reused
- only that run’s `MatrixCell` and `AggregatedMetric` rows are deleted and recreated