# Implementation Plan: Database Repository Refactor

**Branch**: `001-refactor-database-repository` | **Date**: 2026-04-29 | **Spec**: `specs/001-refactor-database-repository/spec.md`
**Input**: Feature specification from `specs/001-refactor-database-repository/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Split `python/hopilot/gto/database_repository.py` into domain-focused repositories/services while preserving external behavior. The refactor enforces sync-only repository interfaces, shared unit-of-work/session for coupled writes, immediate compatibility facade removal after runner+persistence consumer migration, and targeted-per-step regression gates with full-suite pass before merge.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13  
**Primary Dependencies**: SQLAlchemy ORM, pytest, Pydantic configuration, internal HoPilot GTO services  
**Storage**: SQLite via SQLAlchemy models (`Simulation`, `HandMatrix`, `MatrixCell`, `AggregatedMetric`, `GameState`, `PrecomputeJobSession`, `ScenarioRunLink`)  
**Testing**: pytest (unit, contract, integration, regression suites in `tests/`)  
**Target Platform**: Windows desktop runtime for HoPilot, Python module execution in repository virtual environment
**Project Type**: Python application/library modules (backend-like domain logic, no external HTTP API)  
**Performance Goals**: Behavior-preserving refactor with no statistically significant regression in existing precompute/browser query flows; maintain current responsiveness for AoF precompute and browser lookup paths  
**Constraints**: Sync-only repository interfaces; shared unit-of-work/session per coupled workflow step; no fake/placeholder implementation; compatibility facade constrained to thin delegation while split repositories own domain behavior  
**Scale/Scope**: Refactor one hotspot module (`database_repository.py`) and directly affected consumers (`aof_precompute_runner.py`, `precompute_job_persistence.py`, provider/query consumers) while keeping full repository test suite green

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- **I. Real-Time Poker Analysis**: PASS. Refactor preserves runtime analysis behavior; no feature-level behavior removal.
- **III. Modular Design**: PASS. This feature explicitly strengthens modularity by splitting repository domains.
- **VI. Comprehensive Testing**: PASS with enforced gate from spec FR-015 (targeted suites per migration step + full suite before merge).
- **IX. DRY Principle**: PASS. Boundary split removes repeated mixed concerns and duplicated validation/transaction handling patterns.
- **X. Single Responsibility Principle**: PASS. Primary objective is SRP-aligned repository decomposition.
- **XI. Established Design Patterns**: PASS. Uses repository/service + unit-of-work patterns already established in codebase.
- **XII. Quality Assurance**: PASS. No placeholder implementations allowed; tests must validate real behavior.

### Post-Phase 1 Re-Check

- PASS. Research/design artifacts preserve constitutional constraints and introduce no violations requiring exception.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
python/
└── hopilot/
  └── gto/
    ├── database_repository.py               # legacy facade (transitional)
    ├── game_state_repository.py             # planned
    ├── simulation_repository.py             # planned
    ├── precompute_job_repository.py         # planned
    ├── analytics_repository.py              # planned
    ├── precompute_job_persistence.py        # migrated consumer trigger
    ├── aof_precompute_runner.py             # migrated consumer trigger
    └── browser_database_provider.py         # downstream consumer

tests/
├── contract/
│   ├── test_precompute_runner_contracts.py
│   └── test_provider_contract_split.py
├── integration/
│   ├── test_precompute_runner_integration.py
│   └── test_browser_database_provider_integration.py
├── test_database_repository.py
├── test_database_repository_writes.py
├── test_precompute_job_persistence.py
└── test_precompute_runner_regression.py
```

**Structure Decision**: Use the existing single Python project layout under `python/hopilot/gto` and `tests/`, introducing new domain repositories alongside the legacy facade during migration.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
