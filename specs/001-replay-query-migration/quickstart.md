# Quickstart: Replay Query Migration

## Goal

Validate that replay and analytical raw-hand queries work against the current GameStates-first schema, not the legacy `cell_id` / `BoardCard` path.

## Prerequisites

1. Activate the project environment.
2. Run commands from the repository root.
3. Use real SQLite-backed tests under `tests/`.

## Primary Validation Flow

1. Run the replay-focused tests.

```powershell
.venv\Scripts\Activate.ps1
python -m pytest tests/test_game_replay_queries.py
```

Expected outcome:

- replay tests build real `GameState` and `Player` rows using the current schema
- tests do not require `GameState.cell_id` or `BoardCard`
- replay output uses `board_cards_str` and player rows as the authoritative source

2. Run the analytical query integration slice.

```powershell
python -m pytest tests/test_analytical_query_integration.py
```

Expected outcome:

- run-scoped raw-hand queries resolve through `Simulation.parameters` boundaries
- hand-matrix lookup resolves back to the owning simulation
- ambiguous scenario contracts require explicit run selection
- missing or invalid raw boundaries produce empty raw-hand results

3. Run the replay-query migration integration slice.

```powershell
python -m pytest tests/integration/test_replay_query_migration.py
```

Expected outcome:

- explicit run disambiguation is enforced when two raw runs match the same scenario
- summary-to-raw mapping is validated for raw query workflows
- raw-run scope projection and hand-matrix projection both return the correct `Simulation` context

4. Run the repository coverage for run-boundary helpers if replay/query changes extend repository methods.

```powershell
python -m pytest tests/test_database_repository.py
```

Expected outcome:

- repository methods for exact scenario matching, raw-boundary reads, and hand-matrix-to-run resolution behave deterministically

## Manual Spot Checks

1. Persist a simulation with canonical scenario parameters and a valid `raw_game_state_id_start` / `raw_game_state_id_end` range.
2. Persist at least one raw `GameState` with `board_cards_str` and related `Player` rows inside that range.
3. Request replay by direct `game_state_id`.
4. Request raw-hand inspection by `simulation_id`.
5. Request raw-hand inspection by `hand_matrix_id` for the same run.
6. Request scenario-only raw-hand inspection for a contract with two matching historical runs and verify disambiguation is required.

## Regression Checks

- No replay or analytical raw-hand path relies on `GameState.matrix_cell`, `GameState.board_cards`, or `GameState.cell_id`.
- No test fixture creates raw hands through deprecated board-card or cell-linked write assumptions.
- Replay remains truthful when bets or jackpots are absent.
- Replay remains valid when `board_cards_str` is empty.

## Verification Results

The replay migration feature has been validated with these commands:

```powershell
python -m pytest tests/test_game_replay_queries.py -q
python -m pytest tests/integration/test_replay_query_migration.py -q
```

Results:

- `tests/test_game_replay_queries.py` passed
- `tests/integration/test_replay_query_migration.py` passed