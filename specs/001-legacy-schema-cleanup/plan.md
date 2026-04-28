# Implementation Plan: Legacy Schema Cleanup

**Branch**: `001-legacy-schema-cleanup` | **Date**: 2026-04-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `C:\Users\U446541\sandbox\riverghost\specs\001-legacy-schema-cleanup\spec.md`

## Summary

Retire stale HoPilot production and test paths that still encode legacy schema assumptions (`GameState.cell_id`, `board_cards_id`, `BoardCard` joins, and matrix-cell-coupled raw writes), while preserving and validating the GameStates-first architecture. Execute cleanup in gated phases: prove replacement-path stability, rewrite mixed test coverage in place, rewrite mixed production modules, then delete fully dead modules once runtime imports are clean.

## Technical Context

**Language/Version**: Python 3.13 in the project `.venv`  
**Primary Dependencies**: SQLAlchemy ORM, existing `hopilot` repository/service modules, `pytest`  
**Storage**: SQLite through SQLAlchemy in production and temporary SQLite databases in tests  
**Testing**: `pytest` test suites from repository root (`tests/`)  
**Target Platform**: Windows development environment; Python modules remain platform-neutral  
**Project Type**: Python desktop/service codebase with repository, solver, and analytical query layers  
**Performance Goals**: Cleanup must not degrade replay or run-scoped raw query behavior beyond existing local development expectations  
**Constraints**: No compatibility shims unless migration need is proven; delete dead code surgically; preserve only active GameStates-first paths; strict delete gate requires runtime import graph cleanup first  
**Scale/Scope**: Focused cleanup across `python/hopilot/` and `tests/` modules already classified in spec; no schema expansion and no unrelated refactors

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase-0 Gate Check

- **III. Modular Design**: PASS. Cleanup preserves module boundaries while removing dead responsibilities.
- **VI. Comprehensive Testing**: PASS with requirement. Replacement behavior must be proven with real persistence-backed tests before deletion.
- **IX. DRY Principle**: PASS. Removes duplicate legacy query and aggregation paths that shadow canonical services.
- **X. Single Responsibility Principle**: PASS. Legacy mixed-responsibility modules are rewritten or removed.
- **XI. Established Design Patterns**: PASS. Continues repository/service strategy pattern already in use.
- **XII. Quality Assurance**: PASS with requirement. Mixed tests are rewritten in place to validate real implementation behavior.

No constitution violations identified.

### Post-Phase-1 Re-Check

- PASS. Plan enforces strict sequencing and validates replacement paths before deletion.
- PASS. BoardCard path is marked immediate hard removal per clarified policy.
- PASS. Final regression gate scope is explicit and aligned to active architecture.

## Project Structure

### Documentation (this feature)

```text
specs/001-legacy-schema-cleanup/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cleanup-classification-contract.md
│   └── sequencing-gate-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
python/
└── hopilot/
    ├── gto/
    │   ├── database_repository.py
    │   ├── replay_query_service.py
    │   ├── game_replay_queries.py
    │   ├── query_builder.py
    │   ├── aof_precompute_runner.py
    │   ├── convergence_analysis_queries.py
    │   ├── jackpot_frequency_queries.py
    │   ├── aggregation_engine.py
    │   └── incremental_aggregation.py
    ├── database/
    │   └── aggregation.py
    ├── models/
    │   ├── game_state.py
    │   ├── board_card.py
    │   └── __init__.py
    ├── queries.py
    └── database.py

tests/
├── integration/
│   └── test_replay_query_migration.py
├── test_game_replay_queries.py
├── test_analytical_query_integration.py
├── test_matrix_sweep_pipeline.py
├── test_matrix_sweep_aggregation_service.py
├── test_database_repository_crud.py
├── test_matrix_aggregation.py
├── test_incremental_aggregation.py
├── test_aggregation_engine_comprehensive.py
└── test_aggregation.py
```

**Structure Decision**: Keep a single Python project structure and execute cleanup directly in existing modules. Remove dead files where replacements are proven, rewrite mixed modules in place, and retain only canonical GameStates-first query and aggregation paths.

## Complexity Tracking

No constitution exceptions required.

## Runtime Entrypoint Import Verification Checklist

Use this checklist before deleting any `DELETE`-classified module.

- [ ] Identify all runtime entrypoints importing cleanup targets.
- [ ] Remove direct imports of `python/hopilot/queries.py` from runtime entrypoints.
- [ ] Remove direct imports of `python/hopilot/database/aggregation.py` from runtime entrypoints.
- [ ] Remove direct imports of `python/hopilot/models/board_card.py` (and BoardCard re-exports) from runtime entrypoints.
- [ ] Verify no import-time failures in active entrypoints after import cleanup.
- [ ] Record verification evidence and date in `specs/001-legacy-schema-cleanup/quickstart.md`.

## Implementation Outcomes and Residual Risks

### Outcomes

- Final regression gate evidence shows the cleanup preserved production behavior: `26 passed` across the replay migration, analytical integration, and matrix-sweep aggregation suites.
- All active production code now routes through GameStates-first storage and query paths.
- Obsolete legacy modules/docs were removed or reclassified with explicit rationale and deadline tracking.

### Residual Risks

- `python/hopilot/database/persistence/database.py::store_board_cards` remains a deprecation wrapper and must be removed by `2026-05-31` to avoid carrying legacy storage semantics into the next release.
- Any leftover prototyping artifacts in `prototyping/` are outside this feature scope and could still reference legacy BoardCard patterns; those should be explicitly excluded from production cleanup decisions.
- Downstream consumers using `BoardCard`-specific fixtures or import paths may still require coordination if they are not part of the `tests/` regression gate suite.

## Deprecation Deadline Policy

Any target classified `DEPRECATE` must record a one-release-cycle removal deadline in the cleanup plan.

- `python/hopilot/database/persistence/database.py::store_board_cards` — `DEPRECATE` — removal deadline `2026-05-31`

All deprecate targets should be removed by the next release boundary after the cleanup branch merges.
