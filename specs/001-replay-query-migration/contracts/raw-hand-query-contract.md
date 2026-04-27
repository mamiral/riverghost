# Contract: Raw Hand Query

## Purpose

Define how analytical queries retrieve raw hands by simulation, hand matrix, scenario contract, or direct game-state identifier without relying on dead-schema joins.

## Supported Scope Types

### Direct Game State

```text
scope_type: game_state_id
game_state_id: integer >= 1
```

Behavior:

- bypasses run-boundary lookup
- targets one stored hand directly

### Simulation Scope

```text
scope_type: simulation_id
simulation_id: integer >= 1
```

Behavior:

- resolve `raw_game_state_id_start` and `raw_game_state_id_end` from `Simulation.parameters`
- return only hands inside that inclusive range

### Hand Matrix Scope

```text
scope_type: hand_matrix_id
hand_matrix_id: integer >= 1
```

Behavior:

- resolve owning `simulation_id`
- apply the simulation's raw-hand boundary

### Scenario Contract Scope

```text
scope_type: scenario_contract
scenario_contract: exact canonical matrix-sweep contract
explicit_run_selection: integer | null
```

Behavior:

- compare exact canonical fields only
- if exactly one run matches, use that run
- if multiple runs match and no explicit run selection is provided, return disambiguation-required status
- if explicit run selection is provided, it must identify one of the matched runs

## Response

```text
scope_type: string
simulation_id: integer | null
hand_matrix_id: integer | null
matched_runs: list[integer]
game_states: list[RawHandSummary]
status: AVAILABLE | EMPTY_SCOPE | DISAMBIGUATION_REQUIRED | NOT_FOUND
status_message: string
```

## Status Semantics

- `AVAILABLE`: one concrete scope target is resolved and `game_states` may contain zero or more rows that are valid for that resolved scope.
- `EMPTY_SCOPE`: a scope target exists but is unreadable for raw-hand inspection (for example, missing or invalid run boundary); `game_states` MUST be empty.
- `DISAMBIGUATION_REQUIRED`: exact scenario contract matching produced multiple candidate runs and no valid explicit run selection was supplied; `matched_runs` MUST list candidates and `game_states` MUST be empty.
- `NOT_FOUND`: the requested scope target does not exist; `matched_runs` and `game_states` MUST be empty.
- `status_message` MUST be deterministic for each status class so callers can branch without parsing stack traces or SQL errors.

### RawHandSummary

```text
game_state_id: integer
timestamp: string | null
board_cards: list[string]
outcome: string | null
hero_hole_cards: string | null
player_count: integer
```

## Boundary Rules

- raw-hand membership is defined only by recorded run boundaries in `Simulation.parameters`
- raw-hand queries must not infer membership from `cell_id`, `matrix_id`, `MatrixCell`, or `BoardCard`
- hand-matrix selection is valid only as an entry point back to one simulation run

## Failure And Empty-Scope Rules

### Missing Run Boundary

```text
status: EMPTY_SCOPE
game_states: []
status_message: run has no readable raw-hand boundary
```

### Ambiguous Exact Scenario Match

```text
status: DISAMBIGUATION_REQUIRED
matched_runs: [simulation ids...]
game_states: []
```

### Missing Scope Target

```text
status: NOT_FOUND
game_states: []
```

## Ordering Rules

- run-scoped `game_states` are returned in ascending raw `GameState.id` order unless the caller later adds an explicit paging/sort extension
- scenario-contract ambiguity never auto-selects the newest run