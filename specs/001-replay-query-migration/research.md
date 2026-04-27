# Research: Replay Query Migration

## Decision 1: Rebuild replay on raw `GameState` + `Player` rows, not chronological event reconstruction

**Decision**: Treat replay as a truthful read model built from one stored `GameState`, its related `Player` rows, and any optional `Bet` or `Jackpot` rows that happen to exist, rather than trying to reconstruct a richer hand-history sequence from legacy board-card and matrix-cell relationships.

**Rationale**: The current schema guarantees `GameState.board_cards_str`, `outcome`, and `Player` resolution fields. It does not guarantee a complete action timeline or cell-linked ownership for raw hands.

**Alternatives considered**:

- Keep the current chronological event engine and patch only the broken joins: rejected because the existing engine's core contract still assumes `matrix_cell`, `board_cards`, and always-available event sequences.
- Port the prototype script directly into production: rejected because the prototype is behavioral evidence, not production structure.

## Decision 2: Resolve raw-hand scope through simulation run boundaries recorded in `Simulation.parameters`

**Decision**: Use `raw_game_state_id_start` and `raw_game_state_id_end` from the canonical matrix-sweep run contract as the authoritative source of raw-hand membership for simulation- and hand-matrix-scoped queries.

**Rationale**: The GameStates-first architecture explicitly isolates raw hands by run boundary in `Simulation.parameters`, and the repository already exposes run-boundary helpers such as `get_run_game_states(...)`.

**Alternatives considered**:

- Infer membership from `GameState.cell_id` or `MatrixCell` joins: rejected because raw game states no longer carry cell ownership.
- Infer membership by timestamp windows: rejected because timestamps are weaker and less explicit than persisted raw ID boundaries.

## Decision 3: Keep scenario-contract lookup exact and require explicit run selection on ambiguity

**Decision**: Match scenario-scoped raw-hand queries only against the exact canonical matrix-sweep contract and require an explicit run identifier when multiple historical runs share that same contract.

**Rationale**: This was clarified in the spec and aligns with append-only history. Auto-selection would hide run history and make analytical reads non-deterministic.

**Alternatives considered**:

- Partial contract matching: rejected because it broadens the query surface beyond the clarified contract semantics.
- Auto-select the latest run by default: rejected because the clarified feature requires explicit run disambiguation.

## Decision 4: Treat missing or invalid raw boundaries as unreadable raw scope, not as recoverable data

**Decision**: If a simulation or hand matrix exists without a valid raw-hand boundary, raw replay and raw-hand query surfaces return an empty raw-hand result rather than guessing membership or falling back to summary joins.

**Rationale**: The spec explicitly forbids guessing from stale joins and chose empty results over hard errors for unreadable raw scope.

**Alternatives considered**:

- Fail the request with a hard exception: rejected by clarification.
- Return summary-only data through the raw-hand API: rejected because it would blur replay scope and aggregated scope.

## Decision 5: Hand-matrix filtering remains a summary-owned entry point that resolves back to one simulation run

**Decision**: Support hand-matrix-scoped raw queries by first resolving the owning `Simulation` and then applying that run's raw ID boundary.

**Rationale**: `HandMatrix` is still a valid user-facing boundary for analytical exploration, but it is not a raw-hand owner under the current schema.

**Alternatives considered**:

- Remove hand-matrix filtering entirely: rejected because the spec explicitly requires it.
- Introduce a raw-hand-to-matrix linking table: rejected because it expands schema scope and violates the GameStates-first rule.

## Decision 6: Keep replay and analytical-query responsibilities separated behind one repository-backed read path

**Decision**: Reuse `DatabaseRepository` for run lookup and boundary access, but place truthful replay shaping in a dedicated read/query surface rather than keeping all logic inside the legacy replay engine.

**Rationale**: The repository already knows how to find matrix-sweep runs by contract and return run-scoped raw game states. Replay formatting is a different responsibility from repository selection.

**Alternatives considered**:

- Move all replay formatting into `DatabaseRepository`: rejected because it mixes persistence selection with presentation shaping.
- Keep all behavior inside `GameReplayQueryEngine`: rejected because the current class is built on dead-schema assumptions and would remain a mixed-responsibility module unless split or rebuilt.

## Decision 7: Validate with real persisted rows and retire stale test assumptions

**Decision**: Replace or rewrite legacy replay/query tests that create `cell_id`- and `board_cards_id`-based game states, and add regression coverage using the actual raw schema: `GameState.board_cards_str`, related `Player` rows, and run boundaries in `Simulation.parameters`.

**Rationale**: The current replay/query tests prove the old schema path, not the migrated one. The constitution explicitly forbids mock-only or fake-success testing.

**Alternatives considered**:

- Preserve old tests and add new tests alongside them: rejected when the old tests codify dead-schema expectations as active behavior.
- Test only repository helpers: rejected because replay output shape is part of the feature contract.