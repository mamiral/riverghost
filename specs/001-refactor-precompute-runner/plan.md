# Implementation Plan: Precompute Orchestration Refactor

**Branch**: `001-refactor-precompute-runner` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-refactor-precompute-runner/spec.md`

## Summary

Refactor the precompute orchestration flow so `AoFPrecomputeRunner.run()` becomes a thin coordinator and delegates scenario context resolution, scenario orchestration, result/failure recording, progress updates, and finalization to dedicated collaborators. Preserve external behavior and failure classification semantics while removing payload-based fallback during scenario context resolution.

## Technical Context

**Language/Version**: Python 3.13 (project currently running on Python 3.13.7)  
**Primary Dependencies**: SQLAlchemy ORM, pytest, project-local `MatrixSweepService`/`DatabaseRepository` modules  
**Storage**: SQLite/SQLAlchemy-backed relational persistence (`precompute_job_sessions`, `scenario_run_links`, simulation/matrix tables)  
**Testing**: pytest (unit + integration + regression suites)  
**Target Platform**: Windows/Linux development environments with virtualenv  
**Project Type**: Python application/library (backend orchestration and persistence services)  
**Performance Goals**: No regression in bounded precompute regression runtime; no additional scenario dispatch overhead visible in targeted tests  
**Constraints**: Preserve current run return semantics, failure boundary names, and job/session lifecycle behavior; no schema redesign in this feature  
**Scale/Scope**: Refactor centered on `python/hopilot/gto/aof_precompute_runner.py` plus new collaborator modules and targeted test updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ I. Real-Time Poker Analysis: unchanged analytical behavior; refactor only
- ✅ III. Modular Design: core objective is decomposition into modular collaborators
- ✅ VI. Comprehensive Testing: acceptance based on targeted regression/integration pytest suites
- ✅ IX. DRY Principle: repeated persistence and failure recording paths will be consolidated
- ✅ X. Single Responsibility Principle: orchestration responsibilities separated by concern
- ✅ XI. Established Design Patterns: coordinator + collaborator/service split follows established patterns
- ✅ XII. Quality Assurance: no fake data shortcuts; behavior-preserving refactor with real test validation

**Gate Result (Pre-Design)**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-refactor-precompute-runner/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── orchestration-contract.md
└── tasks.md              # Created later by /speckit.tasks
```

### Source Code (repository root)

```text
python/hopilot/gto/
├── aof_precompute_runner.py
├── matrix_sweep_service.py
├── browser_database_provider.py
├── database_repository.py
├── precompute_orchestration.py        # new (planned)
└── precompute_job_persistence.py      # new (planned)

tests/
├── test_aof_precompute_runner.py
├── test_precompute_runner_regression.py
├── test_matrix_sweep_precompute_runner.py
└── integration/
    └── test_precompute_runner_integration.py
```

**Structure Decision**: Keep the existing `python/hopilot/gto` package layout and introduce focused collaborator modules there. Keep tests in existing root `tests/` and `tests/integration/` paths.

## Phase 0: Research & Clarifications

See [research.md](research.md).

## Phase 1: Design & Contracts

- Domain/behavioral entities and lifecycle model: [data-model.md](data-model.md)
- Internal orchestration interface and behavioral contract: [contracts/orchestration-contract.md](contracts/orchestration-contract.md)
- Verification workflow for maintainers: [quickstart.md](quickstart.md)

## Implementation Strategy (High Level)

1. Extract explicit scenario context resolver with direct-context-only policy.
2. Introduce orchestration collaborator for scenario preparation and sweep dispatch coordination.
3. Introduce job/session persistence collaborator for link/job status transitions.
4. Refactor `AoFPrecomputeRunner.run()` into a thin coordinator.
5. Preserve failure boundary and job finalization semantics.
6. Update targeted tests to assert collaborator-driven behavior without changing external outcomes.

## Success Validation

- Run targeted suites from spec success criteria:
  - `tests/test_aof_precompute_runner.py`
  - `tests/test_precompute_runner_regression.py`
  - `tests/test_matrix_sweep_precompute_runner.py`
  - `tests/integration/test_precompute_runner_integration.py`
- Confirm no behavior regressions for:
  - scenario link states
  - failure boundary classification
  - completed/failed counters and final run state

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| None | N/A | N/A |
