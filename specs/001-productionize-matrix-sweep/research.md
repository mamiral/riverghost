# Research: Productionize Matrix Sweep

## Decision 1: Use a dedicated production sweep orchestrator under `hopilot.gto`

**Decision**: Add one `MatrixSweepService` in `python/hopilot/gto` to own fixed-scenario sweep execution, run creation, raw boundary capture, combo expansion, analyzer invocation, and handoff to aggregation.

**Rationale**: The current repo has no production service that owns the full run boundary. `AoFPrecomputeRunner` and `DatabaseRepository` are browser/precompute-oriented and still carry stale assumptions around cell-centric persistence. A dedicated orchestrator keeps the feature local, explicit, and testable.

**Alternatives considered**:

- Extend `AoFPrecomputeRunner`: rejected because it is tied to GUI/precompute state and currently persists cell summaries through stale repository paths.
- Extend `AllInFoldGTOSolver`: rejected because it solves hand strategy concerns and already contains stale `matrix_cell_id` assumptions.

## Decision 2: Reuse analyzer-level raw persistence, bypass stale solver entrypoints

**Decision**: Reuse `PokerAnalyzer.calculate_odds_random_opponents(..., persistence=...)` for raw `GameState` and `Player` writes rather than routing new work through `AllInFoldGTOSolver.analyze_hand_strategy()`.

**Rationale**: The analyzer already persists one raw game state per iteration with hero and opponent players and does not require `GameState.cell_id`. The old solver path still assumes cell-linked writes and is not a safe base for GameStates-first productionization.

**Alternatives considered**:

- Keep using `AllInFoldGTOSolver.analyze_hand_strategy()`: rejected because it still passes `matrix_cell_id` and does not reflect the current schema.
- Rebuild Monte Carlo simulation in a new service: rejected because it would duplicate working analyzer logic and violate the repo’s DRY guidance.

## Decision 3: Represent run boundaries with `Simulation` metadata plus raw `GameState.id` window

**Decision**: Create the `Simulation` record at run start and store a raw-row boundary in `Simulation.parameters`, using a `GameState.id` start/end window and timestamps rather than reintroducing `GameState.simulation_id` or `cell_id`.

**Rationale**: The feature needs a stable run identity and a way to isolate raw rows for post-processing, but the architecture explicitly forbids raw hand links to matrix cells. Capturing the ID window in run metadata stays within the existing schema and keeps the raw model unchanged.

**Alternatives considered**:

- Add `simulation_id` to `GameState`: rejected because it expands the raw schema and is unnecessary for the scoped feature.
- Infer the run solely from timestamps: rejected because timestamps are weaker boundaries than explicit ID snapshots.

## Decision 4: Treat the scenario contract as a persisted interface

**Decision**: Persist a canonical scenario contract in `Simulation.parameters` with the required fields from the spec, plus compatibility keys needed by current model validation.

**Rationale**: Consumers need a stable way to distinguish historical runs. `Simulation.parameters` is already the durable metadata surface. Adding compatibility aliases avoids touching more legacy validation than necessary.

**Alternatives considered**:

- Store only a free-form name: rejected because it is not query-safe or unambiguous.
- Change the `Simulation` schema: rejected because the current JSON field is sufficient and the feature scope does not require a migration.

## Decision 5: Build a new post-sweep aggregation service instead of extending existing aggregation code

**Decision**: Add `MatrixSweepAggregationService` that reads raw rows inside one run boundary, maps hero `hole_cards` to canonical matrix coordinates, and writes one `HandMatrix`, 169 `MatrixCell`, and 169 `AggregatedMetric` rows for the run.

**Rationale**: Existing aggregation surfaces in `python/hopilot/database/aggregation.py`, `python/hopilot/gto/aggregation_engine.py`, and `python/hopilot/metrics_calculator.py` still assume `GameState.cell_id`, `board_cards_id`, or randomized placeholder behavior. They are the wrong abstraction boundary for this feature.

**Alternatives considered**:

- Adapt `python/hopilot/database/aggregation.py`: rejected because it is cell-first and stale against the current schema.
- Extend `DatabaseRepository` aggregation hooks: rejected because repository code is already stale and too broad for this feature.

## Decision 6: Reuse `hopilot.gto.aof_hand_matrix` as the canonical matrix mapping source

**Decision**: Add a reverse-mapping helper next to `hand_key_from_index()` and `build_matrix_keys()` so both sweep orchestration and aggregation use the same canonical 13x13 convention.

**Rationale**: The spec requires HoPilot’s existing matrix convention as the single source of truth. The prototype proved the mapping logic, but production code must live under `python/hopilot` and not import from `prototyping/`.

**Alternatives considered**:

- Copy `hole_cards_to_cell()` from the prototype into the new service: rejected because it duplicates matrix logic.
- Keep mapping logic embedded in the aggregation service: rejected because other code will likely need the same canonical helper.

## Decision 7: Validate with real persisted behavior only

**Decision**: Use temporary SQLite databases and real model/session writes for all feature tests, covering raw write timing, aggregation, rerun idempotency, and run-boundary isolation.

**Rationale**: The constitution and testing rules reject fake data shortcuts and mock-only verification. This feature’s correctness depends on actual database state transitions.

**Alternatives considered**:

- Mock the persistence strategy: rejected because it would not verify the actual schema and transaction behavior.
- Test only per-function aggregation math: rejected because the failure modes here are architectural and persistence-related, not just arithmetic.

## Decision 8: Assume the current Python/SQLAlchemy/Pygame stack where user wording is truncated

**Decision**: Proceed on the current HoPilot repository stack: Python, SQLAlchemy/SQLite, PokerKit, pytest, and the existing Pygame-based app shell.

**Rationale**: The user explicitly allowed non-blocking ambiguity to be resolved using the current repository stack. No additional platform clarification is required to plan this feature.

**Alternatives considered**:

- Stop for clarification: rejected because it would block planning without changing the implementation direction.