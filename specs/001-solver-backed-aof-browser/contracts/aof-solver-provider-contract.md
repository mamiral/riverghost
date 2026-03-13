# Contract: AoF Solver-Backed Provider

## Purpose
Define the input-output contract for AoF browser matrix payload generation using solver-backed logic.

## Input Contract
- `selected_position`: `UTG | BTN | SB | BB`
- `position_actions`: `{ UTG: FOLD|ALL_IN, BTN: FOLD|ALL_IN, SB: FOLD|ALL_IN, BB: FOLD|ALL_IN }`
- `metric`: `WIN_LOSE_PROBABILITY | EV | EQUITY | EQR`
- `pot_size`: positive number
- `bet_amount`: positive number
- `num_simulations`: bounded integer
- `timeout_ms`: positive integer

## Output Contract
```json
{
  "context": {
    "position": "UTG",
    "action": "FOLD",
    "metric": "WIN_LOSE_PROBABILITY",
    "position_actions": {"UTG":"FOLD","BTN":"FOLD","SB":"FOLD","BB":"FOLD"},
    "active_players": 0
  },
  "cells": [
    {
      "row": 0,
      "col": 0,
      "hand_key": "AA",
      "value": 0.73,
      "status": "AVAILABLE",
      "display": "73.0%"
    }
  ],
  "status_message": null
}
```

## Status Semantics
- `AVAILABLE`: valid solver-backed value exists.
- `MISSING`: no computable value for this hand/context.
- `NO_CONTEST`: context has no contested pot (for example all fold).
- `TIMEOUT`: computation exceeded timeout policy.
- `ERROR`: solver/analyzer failed deterministically for this request.

## Metric Semantics
- `WIN_LOSE_PROBABILITY`: `value = win_probability` and implied loss is `1 - value`.
- `EV`: expected value in chip-equivalent units per policy.
- `EQUITY`: showdown equity for the effective context.
- `EQR`: `value = max(0.0, min(1.0, equity / max(1e-6, raw_equity_baseline)))`, where `raw_equity_baseline` is pre-action showdown equity under the same context. If baseline is 0, EQR is `0.0`. Values are rounded to 4 decimal places before display formatting.

## Edge-Case Contract Rules
1. All fold: return non-available/no-contest semantics with clear `status_message`.
2. Single all-in where selected position is not all-in: evaluate selected vs one all-in opponent context.
3. Selected position is FOLD while others are ALL_IN:
  - `analysis` mode: return `AVAILABLE` what-if values with deterministic status message indicating analysis mode.
  - `strict-current-action` mode: return `NO_CONTEST` with null values and deterministic status message.
4. Selected all-in and others fold: uncontested-win semantics with deterministic values.
5. Multiple all-in opponents: use multiway solver/analyzer evaluation path.
6. No valid combos: cell status must be non-available and value null.
7. Timeout/failure: deterministic status with message, no crash.

## Non-Functional Contract
- Preserve matrix payload shape consumed by AoF browser renderer.
- Cache key must include all fields that influence solver outcome.
- Any degraded mode must be visible through `status_message` and logs.
- Silent fallback to heuristic or synthetic data in normal operation is disallowed.
