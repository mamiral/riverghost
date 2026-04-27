# Data Model: Replay Query Migration

## Overview

This feature does not add a new persistence schema. It defines a truthful replay and raw-hand query contract over the current production model: `Simulation.parameters` stores scenario identity and raw-hand boundaries, `HandMatrix` provides a summary entry point back to one simulation run, `GameState` stores hand-level raw facts, and `Player` stores participant-level hand resolution.

## Entities

### ReplayReadRequest

**Purpose**: A direct request to replay one stored hand.

**Fields**

- `game_state_id: int`
- `include_optional_details: bool`

**Validation rules**

- `game_state_id` must identify one persisted `GameState`
- request does not accept `cell_id`, `matrix_id`, or `board_card_id`

### ReplayView

**Purpose**: Truthful replay output for one stored hand.

**Fields**

- `game_state_id: int`
- `timestamp: str | None`
- `round: str`
- `pot_size: float`
- `outcome: str | None`
- `board_cards: list[str]`
- `players: list[ReplayPlayerView]`
- `optional_details: ReplayOptionalDetails`
- `replay_status: str`
- `status_message: str | None`

**Validation rules**

- board cards come only from `GameState.board_cards_str`
- replay remains valid with an empty board-card list for preflop hands
- missing required `Player` rows makes the replay unreadable
- optional details are additive and never required for a replay to exist

### ReplayPlayerView

**Purpose**: One participant record inside a replayed hand.

**Fields**

- `position: str`
- `hole_cards: str`
- `is_hero: bool`
- `hand_class: str | None`
- `final_strength: int | None`
- `stack_size: float`

**Validation rules**

- at least one player row must exist for a readable replay
- hero identification comes from `Player.is_hero`
- hand resolution fields may be absent but must be passed through truthfully when present

### ReplayOptionalDetails

**Purpose**: Optional persisted detail block for one replay.

**Fields**

- `bets: list[dict]`
- `jackpots: list[dict]`
- `availability: dict[str, str]`

**Validation rules**

- absent optional rows do not invalidate replay
- unavailable detail categories must be marked explicitly as unavailable or empty, not fabricated

### RawHandQueryScope

**Purpose**: The scope selector for analytical inspection of raw hands.

**Variants**

- `by_simulation_id`
- `by_hand_matrix_id`
- `by_scenario_contract`
- `by_game_state_id`

**Validation rules**

- `by_scenario_contract` uses exact canonical contract matching only
- ambiguous exact scenario matches require explicit run selection
- `by_hand_matrix_id` resolves through the owning simulation
- `by_game_state_id` bypasses run-boundary lookup and targets one stored hand directly

### SimulationRunBoundary

**Purpose**: The authoritative raw-hand ownership boundary for one run.

**Backing model**: `Simulation.parameters`

**Fields**

- `simulation_id: int`
- `raw_game_state_id_start: int | None`
- `raw_game_state_id_end: int | None`
- `scenario_contract: dict`
- `run_status: str | None`

**Validation rules**

- start and end IDs must both exist and define an inclusive range for readable raw scope
- missing or invalid boundaries make the run unreadable for raw replay/query purposes

### RawHandQueryResult

**Purpose**: The analytical result for a run-scoped raw-hand query.

**Fields**

- `scope_type: str`
- `simulation_id: int | None`
- `hand_matrix_id: int | None`
- `matched_runs: list[int]`
- `game_states: list[RawHandSummary]`
- `status: str`
- `status_message: str`

**Validation rules**

- result preserves run isolation and never merges raw hands from multiple runs into one undifferentiated list
- unreadable raw boundaries return an empty `game_states` list
- ambiguous scenario-contract lookups do not auto-select a run

### RawHandSummary

**Purpose**: A compact analytical projection for one stored hand within a run-scoped query.

**Fields**

- `game_state_id: int`
- `timestamp: str | None`
- `board_cards: list[str]`
- `outcome: str | None`
- `hero_hole_cards: str | None`
- `player_count: int`

**Validation rules**

- summary fields come directly from raw persisted data
- hero hand is derived from the hero `Player` row, not from matrix-cell identity

## Relationships

- `Simulation 1 -> 1 HandMatrix` for one matrix-sweep run
- `Simulation.parameters -> SimulationRunBoundary` defines raw-hand membership
- `GameState 1 -> many Player`
- `GameState 1 -> many Bet` when optional action data exists
- `GameState 1 -> many Jackpot` when optional jackpot data exists
- `HandMatrix -> Simulation` is a valid entry point for selecting one run, but it does not own raw hands directly

## Derived Values

### Replay Board Cards

Derived from `GameState.board_cards_str`:

- `None` or empty string -> `[]`
- comma-separated string -> ordered list of community cards

### Scenario Contract Match

Derived from `Simulation.parameters`:

- normalize stored parameters through the canonical matrix-sweep contract helper
- compare only exact canonical fields
- if more than one run matches, require explicit run selection

### Hand-Matrix Raw Scope

Derived from `HandMatrix.simulation_id`:

- resolve the owning `Simulation`
- read the run boundary from `Simulation.parameters`
- return raw hands only inside that inclusive ID range

## Failure Cases

### Missing `GameState`

- replay request returns not found / unreadable status
- no synthetic replay payload is created

### Missing `Player` Rows For A Stored Hand

- replay request returns unreadable status for that hand
- raw-hand summary may still identify the `GameState`, but full replay cannot be produced truthfully

### Missing Or Invalid Run Boundary

- run-scoped raw query returns empty `game_states`
- status explains that the run is unreadable for raw-hand inspection

### Ambiguous Exact Scenario Match

- scenario-only query returns a disambiguation-required status
- `matched_runs` lists the candidate run identifiers

### Optional Detail Gaps

- replay output preserves the hand and player facts
- missing `Bet` and `Jackpot` rows remain explicitly unavailable rather than implied absent history