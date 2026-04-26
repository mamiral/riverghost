# Contract: Matrix Sweep Run

## Purpose

This contract defines the persisted run metadata stored in `Simulation.parameters` for the production matrix sweep feature. It is the stable interface between sweep orchestration, post-sweep aggregation, and later read/query consumers.

## Persisted Shape

```json
{
  "run_kind": "matrix_sweep",
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
  "sims_per_combo": 100,
  "num_simulations": 100,
  "matrix_size": "13x13",
  "game_type": "nlhe",
  "raw_game_state_id_start": 1200,
  "raw_game_state_id_end": 4815,
  "raw_rows_written": 3615,
  "mapping_failures": 0
}
```

## Required Fields

- `run_kind`
- `selected_position`
- `hero_action`
- `position_actions`
- `active_players`
- `num_opponents`
- `pot_size`
- `bet_amount`
- `sims_per_combo`
- `matrix_size`
- `game_type`

## Required Boundary Fields

- `raw_game_state_id_start`
- `raw_game_state_id_end`

## Compatibility Fields

- `num_simulations`: retained while current validation still expects this key

## Semantics

- One persisted contract identifies one sweep run.
- The raw boundary fields isolate which `GameState` rows belong to that run without adding a foreign key back onto `GameState`.
- Aggregation must read only raw rows inside the stored boundary.
- Aggregation rerun must reuse the same contract and boundary, delete only that run’s summaries, and recreate them from the same raw rows.

## Forbidden Coupling

- Do not add `cell_id` to `GameState`.
- Do not add `board_cards_id` back to `GameState`.
- Do not store per-cell raw references inside the contract as a substitute for summary derivation.