# Implementation Plan: Replay Query Migration

**Branch**: `001-replay-query-migration` | **Date**: 2026-04-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `C:\Users\U446541\sandbox\riverghost\specs\001-replay-query-migration\spec.md`

## Summary

Replace the legacy replay and analytical query path that still assumes `GameState.cell_id`, `BoardCard`, and matrix-cell-linked raw hands with a truthful raw-schema read path over `GameState.board_cards_str`, `Player` rows, and scenario-scoped run boundaries recorded in `Simulation.parameters`. Rebuild replay around one stored hand at a time, keep optional bet and jackpot details opportunistic rather than required, and make run-scoped raw-hand queries resolve through simulation and hand-matrix ownership instead of stale joins.

## Technical Context

**Language/Version**: Python 3.13 in the project `.venv`  
**Primary Dependencies**: SQLAlchemy ORM, existing `hopilot` models/repositories/services, `pytest`  
**Storage**: SQLite via SQLAlchemy (`python/hopilot/data/normalized_poker.db` in production, temporary SQLite DBs in tests)  
**Testing**: `pytest` from repository root (`tests/`)  
**Target Platform**: Windows development environment; Python service and repository code remains platform-neutral  
**Project Type**: Python desktop application with repository/service modules and analytical query consumers  
**Performance Goals**: Single-game replay lookup completes in `<=250 ms` on warm local SQLite data; run-scoped raw-hand query for one selected run completes in `<=1 s` for typical local development datasets  
**Constraints**: Must not depend on `GameState.cell_id`, `GameState.matrix_id`, or `BoardCard`; must remain honest to persisted data; must preserve explicit run isolation; must not import from `prototyping/`; tests must validate real persisted behavior rather than mock-only flows  
**Scale/Scope**: One replayed hand per direct game-state request; one explicit run per raw-hand query; multiple historical runs may share the same scenario contract; run-scoped raw queries may inspect thousands of game states within recorded ID boundaries

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase-0 Gate Check

- **III. Modular Design**: PASS. Plan keeps repository boundary resolution, replay shaping, and analytical query selection as separate responsibilities.
- **VI. Comprehensive Testing**: PASS with requirement. Tests will use real SQLite persistence and real `GameState`/`Player` rows.
- **IX. DRY Principle**: PASS with requirement. Reuse existing matrix-sweep contract normalization and recorded run-boundary helpers rather than duplicating scenario identity rules.
- **X. Single Responsibility Principle**: PASS. Repository owns run lookup and raw-boundary access; replay service/query engine owns truthful replay shaping.
- **XI. Established Design Patterns**: PASS. Continues repository/service layering already present in `python/hopilot/gto/`.
- **XII. Quality Assurance**: PASS with requirement. Missing-boundary, exact-contract, and explicit-run-selection behavior will be tested against real persisted rows with no fake pass-through assertions.

No constitution violations identified.

### Post-Phase-1 Re-Check

- PASS. Design preserves one authoritative run boundary per raw-hand query and does not reintroduce raw-hand-to-cell foreign keys.
- PASS. Data model stays within the current production schema and explicit scenario-contract rules.
- PASS. Planned contracts and quickstart focus on real replay/query behavior and regression checks over persisted data.

## Project Structure

### Documentation (this feature)

```text
specs/001-replay-query-migration/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── raw-hand-query-contract.md
│   └── replay-read-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
python/
└── hopilot/
    ├── gto/
    │   ├── game_replay_queries.py
    │   ├── query_builder.py
    │   ├── database_repository.py
    │   ├── matrix_sweep_contract.py
    │   └── replay_query_service.py
    └── models/
        ├── game_state.py
        ├── player.py
        ├── simulation.py
        └── hand_matrix.py

tests/
├── test_game_replay_queries.py
├── test_analytical_query_integration.py
├── test_database_repository.py
└── integration/
    └── test_replay_query_migration.py
```

**Structure Decision**: Keep a single Python project structure. Implement the migration inside the existing `python/hopilot/gto/` repository/query surfaces by replacing dead-schema replay assumptions, reusing matrix-sweep run-boundary helpers, and validating the behavior from root `tests/` with real SQLite-backed scenarios.

## Complexity Tracking

No constitution exceptions required.
