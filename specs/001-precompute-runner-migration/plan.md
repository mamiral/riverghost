# Implementation Plan: Precompute Runner Sweep Delegation

**Branch**: `001-precompute-runner-migration` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `C:\Users\U446541\sandbox\riverghost\specs\001-precompute-runner-migration\spec.md`

## Summary

Replace the precompute runner's legacy per-cell persistence flow with direct delegation to the production matrix sweep orchestration service. The runner remains responsible for job/session lifecycle, scenario iteration, progress snapshots, cancellation, and failure classification, while the sweep pipeline owns raw GameState writes and post-run aggregation into `HandMatrix`, `MatrixCell`, and `AggregatedMetric`. Add dedicated job-to-simulation linkage records so UI-triggered jobs can be traced to persisted run outputs.

## Technical Context

**Language/Version**: Python 3.13 in project `.venv`  
**Primary Dependencies**: SQLAlchemy ORM, existing `hopilot` repository/service modules, `pokerkit`, `pytest`  
**Storage**: SQLite via SQLAlchemy (`python/hopilot/data/normalized_poker.db` in production, temp SQLite DBs in tests)  
**Testing**: `pytest` in root `tests/` directory  
**Target Platform**: Windows desktop development environment; application logic is platform-neutral Python  
**Project Type**: Python desktop application with service/repository orchestration layer  
**Performance Goals**: Preserve actionable progress updates during long-running precompute jobs; no regression in scenario throughput caused by orchestration overhead  
**Constraints**: No `GameState.cell_id` writes in runner path; no board-card/jackpot dead-schema writes in migrated flow; cooperative cancellation only; no automatic retries; preserve existing lifecycle state semantics  
**Scale/Scope**: Multi-scenario UI-triggered jobs; each scenario maps to one sweep run; each successful run yields one `Simulation` and one `HandMatrix` with 169 canonical cells

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase-0 Gate Check

- **III. Modular Design**: PASS. Plan separates runner orchestration concerns from sweep execution and aggregation concerns.
- **VI. Comprehensive Testing**: PASS with requirement. Migration will be validated with real persisted outputs, not mock-only callback checks.
- **IX. DRY Principle**: PASS. Existing production matrix sweep service is reused rather than duplicating persistence logic.
- **X. Single Responsibility Principle**: PASS. Runner retains lifecycle orchestration; sweep service owns run data generation.
- **XI. Established Design Patterns**: PASS. Maintains service/repository layering already present in `python/hopilot/gto/`.
- **XII. Quality Assurance**: PASS with requirement. Tests must prove real delegated runs persist expected records and classify failures by phase boundary.

No constitution violations identified.

### Post-Phase-1 Re-Check

- PASS. Data model and contracts preserve clear runner-versus-sweep ownership boundaries.
- PASS. Failure and cancellation behavior are specified as deterministic lifecycle outcomes.
- PASS. Quickstart verifies real DB persistence and lifecycle compatibility through targeted test suites.

## Project Structure

### Documentation (this feature)

```text
specs/001-precompute-runner-migration/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── precompute-run-orchestration-contract.md
│   └── precompute-lifecycle-progress-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
python/
└── hopilot/
    ├── gto/
    │   ├── aof_precompute_runner.py
    │   ├── aof_precompute_cli.py
    │   ├── matrix_sweep_service.py
    │   ├── matrix_sweep_aggregation_service.py
    │   ├── matrix_sweep_contract.py
    │   └── database_repository.py
    └── models/
        ├── simulation.py
        ├── hand_matrix.py
        ├── matrix_cell.py
        ├── aggregated_metric.py
        ├── game_state.py
        └── player.py

tests/
├── test_aof_precompute_runner.py
├── test_matrix_sweep_pipeline.py
├── test_matrix_sweep_aggregation_service.py
└── integration/
    └── test_precompute_runner_migration_integration.py
```

**Structure Decision**: Keep the current single-project Python structure and implement migration in `aof_precompute_runner.py` by removing dead-schema write branches and routing scenario execution through `MatrixSweepService.run_sweep(...)`. Add persistence linkage support in repository/model layers if existing session cache-only behavior is insufficient for durable UI traceability.

## Complexity Tracking

No constitution exceptions required.
