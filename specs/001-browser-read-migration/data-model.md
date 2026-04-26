# Data Model: Browser Read-Path Migration

## Overview

This feature does not add a new persistence schema. It introduces a deterministic browser read contract over the existing production run model: `Simulation.parameters` identifies the scenario, `HandMatrix` identifies the selected run's matrix, `MatrixCell` provides canonical cell identity, and the selected run's aggregated metric records supply the displayable values for the requested browser metric.

## Entities

### BrowserScenarioReadContract

**Purpose**: Canonical scenario identity derived from browser context and matched against `Simulation.parameters`.

**Fields**

- `selected_position: str`
- `hero_action: str`
- `position_actions: dict[str, str]`
- `active_players: list[str]`
- `num_opponents: int`
- `pot_size: float`
- `bet_amount: float`
- `sims_per_combo: int | None` for compatibility with persisted matrix-sweep runs
- `matrix_size: str` with value `13x13`
- `game_type: str`
- `run_kind: str` with value `matrix_sweep`

**Validation rules**

- must normalize browser actions into canonical seat order `UTG`, `BTN`, `SB`, `BB`
- `hero_action` must be derived from the normalized action for `selected_position`
- `num_opponents` must match the normalized set of active non-hero players
- `strict_current_action` is not part of this contract

### CurrentScenarioRun

**Purpose**: The one historical run the browser treats as authoritative for a scenario.

**Backing model**: Existing `Simulation` plus its `HandMatrix`.

**Selection rules**

- scenario contract fields must match exactly
- run must be in aggregated/completed state
- prefer latest completion timestamp
- if completion timestamp is tied or absent, prefer highest simulation ID

### MatrixPayload

**Purpose**: GUI-facing payload returned by `BrowserDatabaseProvider.get_matrix_payload(...)`.

**Fields**

- `context: dict`
- `cells: list[MatrixPayloadCell]`
- `status: str`
- `status_message: str`

**Validation rules**

- always preserve the current top-level keys
- available and missing payloads both return 169 canonical cells except invalid-context responses, which preserve the current empty-cell validation response
- missing scenario payload must not imply background computation

### MatrixPayloadCell

**Purpose**: One browser-visible cell in the 13x13 matrix.

**Fields**

- `row: int`
- `col: int`
- `hand_key: str`
- `value: float | None`
- `status: str`
- `display: str`

**Validation rules**

- all 169 canonical cells must be present for available and missing scenarios
- `row`, `col`, and `hand_key` come from `MatrixCell` or canonical matrix helpers, not raw `GameState` relationships
- if a run exists but the selected metric value is unavailable for a cell, return `value = 0`

### BrowserMetricSelection

**Purpose**: Internal mapping from browser metric IDs to persisted aggregated metric records for one selected run.

**Fields**

- `browser_metric: str`
- `metric_name: str`

**Initial mapping target**

- `WIN_LOSE_PROBABILITY -> metric_name == "WIN_LOSE_PROBABILITY"`
- `EQUITY -> metric_name == "EQUITY"`
- `EV -> metric_name == "EV"`
- `EQR -> metric_name == "EQR"`

**Validation rules**

- every supported browser metric must map deterministically to one persisted metric name
- the read layer, not the GUI, owns the mapping

## Relationships

- `Simulation 1 -> 1 HandMatrix` for one matrix-sweep run
- `HandMatrix 1 -> 169 MatrixCell`
- `MatrixCell 1 -> AggregatedMetric rows scoped to the selected run and requested browser metric`
- browser read path consumes the selected run through `Simulation -> HandMatrix -> MatrixCell -> AggregatedMetric`

## Derived Values

### Scenario Contract Normalization

Derived from browser inputs:

- normalize `position_actions`
- derive `hero_action`
- derive `active_players`
- derive `num_opponents`
- stamp fixed compatibility fields such as `matrix_size`, `game_type`, and `run_kind`

### Cell Display Value

Derived from the selected run and browser metric:

- resolve the persisted `metric_name` for the requested browser metric
- read `metric_value` from the selected cell's matching `AggregatedMetric` row
- if the matching metric row is absent for that cell, substitute `0`
- format the value using existing provider display helpers

## Failure Cases

### Invalid Browser Context

- provider returns the existing invalid-context response shape
- no repository lookup occurs

### No Matching Run

- provider returns a 169-cell missing-status payload
- payload must not use `LOADING` or `Computing...`
- no new persistence side effects occur

### Matching Simulation Without HandMatrix

- treat as missing scenario
- preserve canonical cells and explicit missing-status messaging

### Historical Run Tie

- repository/read service resolves to latest completion timestamp
- if tied or absent, choose highest simulation ID

### Metric Mapping Drift

- if a browser metric cannot be mapped to a persisted metric name, fail validation in the read layer rather than silently reading the wrong value