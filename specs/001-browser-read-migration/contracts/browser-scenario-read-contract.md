# Contract: Browser Scenario Read

## Purpose

This contract defines how browser-visible context maps to one persisted matrix-sweep run and how the read layer selects the authoritative historical run.

## Canonical Scenario Shape

```json
{
  "selected_position": "UTG",
  "hero_action": "all_in",
  "position_actions": {
    "UTG": "all_in",
    "BTN": "fold",
    "SB": "fold",
    "BB": "call"
  },
  "active_players": ["UTG", "BB"],
  "num_opponents": 1,
  "pot_size": 20.0,
  "bet_amount": 10.0,
  "matrix_size": "13x13",
  "game_type": "nlhe",
  "run_kind": "matrix_sweep"
}
```

## Required Matching Fields

- `selected_position`
- `hero_action`
- `position_actions`
- `active_players`
- `num_opponents`
- `pot_size`
- `bet_amount`
- `matrix_size`
- `game_type`
- `run_kind`

## Excluded Fields

- `strict_current_action`
- browser display metric
- transient GUI-only formatting state

## Current-Run Selection Rules

1. Filter to persisted runs whose canonical contract matches exactly.
2. Exclude runs that are not in aggregated/completed state.
3. Prefer the latest completion timestamp.
4. If completion timestamp is tied or absent, prefer the highest simulation ID.

## Result Contract

### Match found

- selected `Simulation`
- selected `HandMatrix`
- ordered `MatrixCell` rows for the selected matrix
- only the `AggregatedMetric` rows whose `metric_name` matches the requested browser metric

### Match missing

- no selected run
- caller formats the explicit missing-status payload with 169 canonical cells and no background-compute messaging

### Match found but no aggregated matrix

- treat as missing for browser purposes
- do not partially hydrate a payload from raw rows or incomplete matrix state

## Forbidden Behavior

- no fallback to raw `GameState` / `Player` traversal for browser payload construction
- no writes during read-path execution
- no cross-run merges for one browser scenario response
- no dependence on `GameState.cell_id` or `board_cards_id`
- no metric-based re-resolution of the scenario once the current run has been selected