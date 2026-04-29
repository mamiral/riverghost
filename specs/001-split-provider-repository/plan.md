# Implementation Plan: Provider and Repository Responsibility Split

**Branch**: `001-split-provider-repository` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-split-provider-repository/spec.md`

## Summary

Split provider and repository responsibilities into explicit orchestration and browser-facing boundaries, and isolate job/session tracking persistence from raw sweep persistence while preserving external behavior. The implementation uses separate transactions for raw and tracking writes plus a mandatory deterministic reconciliation/finalization pass to resolve any mismatch between raw outcomes and tracking state.

## Technical Context

**Language/Version**: Python 3.13 (venv-managed)  
**Primary Dependencies**: SQLAlchemy ORM, pytest, existing `AoFPrecomputeRunner`, `PrecomputeOrchestrationService`, `PrecomputeJobPersistenceService`, `BrowserDatabaseProvider`, `DatabaseRepository`  
**Storage**: SQLite/SQLAlchemy relational persistence (precompute job/session tables and matrix/game-state raw tables)  
**Testing**: pytest targeted runner/provider/repository integration suites plus full `tests/` regression run  
**Target Platform**: Windows development environment with PowerShell and virtual environment  
**Project Type**: Python backend/service modules for orchestration, persistence, and browser payload retrieval  
**Performance Goals**: No material regression in precompute dispatch throughput; reconciliation pass bounded to deterministic post-run finalization  
**Constraints**: Preserve failure-boundary semantics and external behavior; no schema redesign; separate transactions are mandatory; reconciliation/finalization is correctness-critical (not optional)  
**Scale/Scope**: Changes centered in `python/hopilot/gto/` provider/repository/orchestration modules and corresponding tests in `tests/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS: I. Real-Time Poker Analysis (feature is architectural split; solver behavior preserved)
- PASS: III. Modular Design (primary objective is explicit contract and persistence seam isolation)
- PASS: VI. Comprehensive Testing (acceptance requires targeted integration/regression suites and full test pass)
- PASS: IX. DRY Principle (boundary extraction removes mixed responsibility duplication)
- PASS: X. Single Responsibility Principle (provider and persistence roles separated)
- PASS: XI. Established Design Patterns (strategy/service separation and deterministic finalization workflow)
- PASS: XII. Quality Assurance (no placeholders, behavior-based tests, deterministic reconciliation checks)

**Gate Result (Pre-Design)**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-split-provider-repository/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── provider-contracts.md
│   └── persistence-reconciliation-contract.md
└── tasks.md              # Created later by /speckit.tasks
```

### Source Code (repository root)

```text
python/hopilot/gto/
├── aof_precompute_runner.py
├── precompute_orchestration.py
├── precompute_job_persistence.py
├── browser_database_provider.py
├── database_repository.py
└── matrix_sweep_service.py

tests/
├── test_aof_precompute_runner.py
├── test_precompute_runner_regression.py
├── test_matrix_sweep_precompute_runner.py
└── integration/
    └── test_precompute_runner_integration.py
```

**Structure Decision**: Keep implementation in the existing `python/hopilot/gto/` package and preserve current root `tests/` layout. Add no new top-level packages or schema folders; this feature is a responsibility split and reconciliation behavior hardening inside existing modules.

## Phase 0: Research & Clarifications

See [research.md](research.md).

## Phase 1: Design & Contracts

- Behavioral entities and state transitions: [data-model.md](data-model.md)
- Provider boundary contracts: [contracts/provider-contracts.md](contracts/provider-contracts.md)
- Persistence split and deterministic reconciliation contracts: [contracts/persistence-reconciliation-contract.md](contracts/persistence-reconciliation-contract.md)
- Validation and verification workflow: [quickstart.md](quickstart.md)

## Post-Design Constitution Re-Check

- PASS: Design keeps solver raw writes and aggregation boundaries aligned with GameStates-first constraints.
- PASS: Design enforces modular decomposition and single responsibility across provider and persistence seams.
- PASS: Design includes deterministic reconciliation requirements and testable acceptance criteria.
- PASS: No constitutional violations introduced; no exceptions required.

**Gate Result (Post-Design)**: PASS

## Implementation Strategy (High Level)

1. Enforce two explicit provider contracts: direct orchestration context and browser payload retrieval.
2. Ensure orchestration path cannot call browser payload retrieval methods.
3. Isolate job/session link lifecycle persistence from raw sweep persistence into separate transaction scopes.
4. Add mandatory reconciliation/finalization pass after scenario execution to resolve split-write mismatches deterministically.
5. Preserve failure boundary semantics, run return behavior, and external workflow outputs.
6. Validate with targeted and full-suite regression tests.

## Success Validation

- Targeted suites:
  - `tests/test_aof_precompute_runner.py`
  - `tests/test_precompute_runner_regression.py`
  - `tests/test_matrix_sweep_precompute_runner.py`
  - `tests/integration/test_precompute_runner_integration.py`
- Full regression sweep:
  - `tests/`
- Deterministic reconciliation checks:
  - Completed plus failed equals attempted scenarios after finalization
  - Split-write mismatch scenarios resolve without manual correction

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| None | N/A | N/A |
