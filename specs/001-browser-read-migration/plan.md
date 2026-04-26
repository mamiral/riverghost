# Implementation Plan: Browser Read-Path Migration

**Branch**: `001-browser-read-migration` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `C:\Users\U446541\sandbox\riverghost\specs\001-browser-read-migration\spec.md`

## Summary

Replace the browser's legacy matrix read path with a deterministic scenario-scoped read over production `Simulation`, `HandMatrix`, `MatrixCell`, and `AggregatedMetric` rows. Keep `BrowserDatabaseProvider.get_matrix_payload` as the GUI-facing entry point, but move scenario normalization, current-run selection, and run-scoped summary retrieval behind the repository or a dedicated read service. Preserve provider-owned compatibility behavior only for invalid-context responses and `NO_CONTEST` payload generation, and replace the legacy `LOADING` fallback with the explicit missing-status payload required by the spec.

## Technical Context

**Language/Version**: Python 3.13 in the project `.venv`  
**Primary Dependencies**: SQLAlchemy ORM, existing `hopilot` models/repositories/services, `pytest`  
**Storage**: SQLite via SQLAlchemy (`python/hopilot/data/normalized_poker.db` in production, temporary SQLite DBs in tests)  
**Testing**: `pytest` from repository root (`tests/`)  
**Target Platform**: Windows desktop development environment; Python service code remains platform-neutral  
**Project Type**: Python desktop application with repository/service modules and GUI consumers  
**Performance Goals**: Warm local scenario payload read completes in `<=250 ms`; response always returns 169 canonical cells  
**Constraints**: Remain read-only; do not depend on `GameState.cell_id` or `board_cards_id`; do not import from `prototyping/`; keep `get_matrix_payload` as the entry point; preserve append-only historical runs  
**Scale/Scope**: One browser scenario per request; one selected current run per scenario contract; 169 cells per payload; multiple historical runs may coexist for the same contract

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase-0 Gate Check

- **III. Modular Design**: PASS. Plan keeps provider formatting separate from repository/read-service lookup logic.
- **VI. Comprehensive Testing**: PASS with requirement. Feature tests will use real SQLite persistence and browser-visible payload assertions.
- **IX. DRY Principle**: PASS with requirement. Reuse existing scenario-contract normalization and matrix-sweep summary access instead of reimplementing lookup logic in the provider.
- **X. Single Responsibility Principle**: PASS. Provider owns context/payload formatting; repository/read service owns selection and retrieval.
- **XI. Established Design Patterns**: PASS. Continues repository/service layering already present in the codebase.
- **XII. Quality Assurance**: PASS with requirement. Missing-run, historical-run selection, and invalid-context behavior will be validated with real data, not mock-only assertions.

No constitution violations identified.

### Post-Phase-1 Re-Check

- PASS. Design keeps scenario-contract normalization, run selection, and payload formatting as separate responsibilities.
- PASS. Data model stays within existing production schema and append-only historical-run rules.
- PASS. Planned contracts and quickstart target real persisted behavior and focused regression checks.

## Project Structure

### Documentation (this feature)

```text
specs/001-browser-read-migration/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── browser-matrix-payload-contract.md
│   └── browser-scenario-read-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
python/
└── hopilot/
    ├── gto/
    │   ├── browser_database_provider.py
    │   ├── database_repository.py
    │   ├── matrix_sweep_contract.py
    │   └── [new browser read adapter/service if repository-only changes are insufficient]
    └── models/
        ├── aggregated_metric.py
        ├── hand_matrix.py
        ├── matrix_cell.py
        └── simulation.py

tests/
├── test_browser_database_provider.py
├── test_browser_database_provider_persistence.py
├── test_matrix_sweep_pipeline.py
└── integration/
    └── test_browser_database_provider_integration.py
```

**Structure Decision**: Keep a single Python project structure. Implement the migration by updating the existing provider and repository flow under `python/hopilot/gto/`, reusing the current matrix-sweep contract helpers and run-summary retrieval methods, and validating behavior in root `tests/` with real SQLite-backed scenarios.

## Complexity Tracking

No constitution exceptions required.
