# Implementation Plan: Productionize Matrix Sweep

**Branch**: `001-productionize-matrix-sweep` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `C:\Users\U446541\sandbox\riverghost\specs\001-productionize-matrix-sweep\spec.md`

## Summary

Build one production orchestration service under `python/hopilot` that executes a full fixed-scenario 13x13 sweep, writes only raw `GameState`/`Player` rows during simulation, then runs a separate aggregation phase that derives 169 `MatrixCell` and 169 `AggregatedMetric` records under one `Simulation` and one `HandMatrix`. Preserve historical runs and enforce idempotent rerun semantics for aggregation within a run boundary by replacing summaries only for the selected run.

## Technical Context

**Language/Version**: Python 3.13 (project venv)  
**Primary Dependencies**: `pokerkit`, `SQLAlchemy`, existing `hopilot` persistence strategies, `pytest`  
**Storage**: SQLite (`python/hopilot/data/normalized_poker.db`) via SQLAlchemy ORM  
**Testing**: `pytest` from repository root (`tests/`)  
**Target Platform**: Windows desktop development environment (Python service code remains cross-platform)  
**Project Type**: Python application with service modules + GUI consumers  
**Performance Goals**: Complete one full 169-cell sweep + aggregation as a bounded background job; no solver-side aggregation; no duplicate summaries per run on aggregation rerun  
**Constraints**: Preserve GameStates-first architecture; do not reintroduce `GameState.cell_id` or `board_cards_id`; do not import from `prototyping/` in production code; keep historical-run boundaries immutable  
**Scale/Scope**: One scenario per execution; 169 canonical cells; multiple historical runs coexisting in the same DB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase-0 Gate Check

- **I. Real-Time Poker Analysis**: PASS. This feature hardens the matrix pipeline used by poker analysis workflows.
- **III. Modular Design**: PASS. Plan uses one orchestration service plus dedicated aggregation step, not cross-cutting script logic.
- **VI. Comprehensive Testing**: PASS with requirement. Plan includes real-data persistence and aggregation tests; no fake-data shortcuts.
- **IX. DRY Principle**: PASS with requirement. Canonical hand-key logic will reuse existing `hopilot.gto.aof_hand_matrix` conventions.
- **X. Single Responsibility Principle**: PASS. Solver writes raw states; aggregator derives summaries.
- **XI. Established Design Patterns**: PASS. Continues strategy pattern for persistence and repository/service layering.
- **XII. Quality Assurance**: PASS with requirement. Acceptance/tests must validate real persisted behavior and failure handling.

No constitution violations identified.

### Post-Phase-1 Re-Check

- PASS. Design artifacts keep solver and aggregation responsibilities separated.
- PASS. Data model and contracts preserve run boundary and idempotent rerun semantics.
- PASS. Testing approach remains real-behavior focused with explicit edge-case handling.

## Project Structure

### Documentation (this feature)

```text
specs/001-productionize-matrix-sweep/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── matrix-sweep-service-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
python/
└── hopilot/
    ├── gto/
    │   ├── [new production sweep orchestration service]
    │   └── [new run-scoped aggregation module]
    ├── database/
    │   └── persistence/
    └── models/

tests/
├── integration/
│   └── [new sweep + aggregation integration tests]
└── [existing database and gto test modules updated for new flow]
```

**Structure Decision**: Keep a single Python project structure. Add production sweep/aggregation logic under `python/hopilot/gto/`, reuse existing models/persistence modules, and validate behavior through root `tests/`.

## Complexity Tracking

No constitution exceptions required.
