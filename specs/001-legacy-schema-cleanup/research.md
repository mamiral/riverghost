# Research: Legacy Schema Cleanup

## Decision 1: Enforce strict delete gate before module removal

**Decision**: Do not delete any `DELETE`-classified production module until all direct imports from active runtime entrypoints are removed.

**Rationale**: This prevents accidental runtime breakage when dead code is still transitively referenced.

**Alternatives considered**:

- Delete immediately and repair import failures later: rejected because it creates avoidable outage risk.
- Leave temporary stubs: rejected by clarified policy preferring strict cleanup.

## Decision 2: Apply immediate hard removal for BoardCard artifacts

**Decision**: Remove `python/hopilot/models/board_card.py` and BoardCard exports once strict delete-gate conditions are met.

**Rationale**: BoardCard is part of stale schema assumptions and keeping it increases regression risk.

**Alternatives considered**:

- Staged deprecation over multiple releases: rejected by clarified policy.

## Decision 3: Rewrite mixed tests in place

**Decision**: For test files containing both valid and stale assertions, rewrite in place instead of splitting into new files.

**Rationale**: Preserves canonical file locations and avoids duplicate test narratives.

**Alternatives considered**:

- Split files into legacy and migrated versions: rejected by clarified policy.

## Decision 4: Cleanup sequencing remains dependency-first

**Decision**: Execute phases in order: proof gate, test cleanup, production rewrite/deprecate, then deletion and final regression gate.

**Rationale**: Ensures replacement behavior is continuously validated and cleanup never gets ahead of proven architecture.

**Alternatives considered**:

- Delete first then repair: rejected due to high regression and rollback cost.

## Decision 5: Keep regression gate focused on active architecture suites

**Decision**: Final mandatory regression gate includes replay migration tests, run-boundary analytical tests, and matrix-sweep aggregation tests.

**Rationale**: These suites represent the active production path and cross-layer behavior under GameStates-first architecture.

**Alternatives considered**:

- Broad full-suite-only gate: rejected as inefficient for iterative cleanup checkpoints.
- Narrow single-suite gate: rejected as insufficient coverage.

## Legacy Dependency Scan Baseline (Phase 2)

Scan date: 2026-04-27

Search pattern:
- `GameState.cell_id|board_cards_id|BoardCard`

Baseline results:
- `python/hopilot/**/*.py`: 96 matches
- `tests/**/*.py`: 39 matches

Top production hotspots:
- `python/hopilot/gto/database_repository.py` (legacy `create_game_state` and BoardCard CRUD sections)
- `python/hopilot/database.py` (legacy cell-linked and board-card-linked helpers)
- `python/hopilot/queries.py` (legacy query facade)
- `python/hopilot/gto/aggregation_engine.py`, `python/hopilot/gto/incremental_aggregation.py` (cell-linked aggregation assumptions)
- `python/hopilot/models/game_state.py`, `python/hopilot/models/board_card.py`, `python/hopilot/models/__init__.py` (BoardCard coupling)

Top test hotspots:
- `tests/test_database_repository_crud.py`
- `tests/test_matrix_aggregation.py`
- `tests/test_incremental_aggregation.py`
- `tests/test_analytical_query_integration.py`
- `tests/test_aggregation_engine_comprehensive.py`
