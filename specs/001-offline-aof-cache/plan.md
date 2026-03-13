# Implementation Plan: Offline AoF Matrix Precomputation and SQLite Scenario Cache

**Branch**: `001-offline-aof-cache` | **Date**: 2026-03-13 | **Spec**: `specs/001-offline-aof-cache/spec.md`
**Input**: Feature specification from `/specs/001-offline-aof-cache/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a persistent scenario-cache layer for the standalone AoF browser using SQLite and SQLAlchemy, plus an offline precompute workflow that generates and stores full 169-cell matrix payloads. Runtime flow will be cache-first with deterministic fallback compute and write-back, while preserving existing payload shape and status semantics. Add canonical solver-equivalence keying so seat-label permutations with equivalent solver semantics reuse persisted matrix cells.

## Technical Context

**Language/Version**: Python 3.13 (project virtual environment)  
**Primary Dependencies**: SQLAlchemy (new), sqlite3 runtime, existing hopilot AoF modules (`aof_browser_data_provider`, `aof_solver_adapter`, `all_in_fold_gto`)  
**Storage**: SQLite database file for persistent scenario cache (with SQLAlchemy ORM/core access)  
**Testing**: pytest (unit + integration + cache lifecycle tests)  
**Target Platform**: Windows desktop runtime (pygame AoF browser), local filesystem persistence
**Project Type**: Python desktop application module enhancement  
**Performance Goals**: Cached scenario retrieval p95 <= 250ms over 200 repeated requests; preserved <= 1.0s interactive switch p95 for runtime matrix flow  
**Constraints**: Deterministic status semantics; no silent synthetic fallback; standalone AoF browser remains decoupled from simulator  
**Scale/Scope**: Scenario-keyed cache for AoF context combinations plus canonical solver-equivalence dedup keying, offline precompute batches with resume support

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Real-Time Poker Analysis**: PASS. Feature accelerates real-time analysis by moving repeated solve work to precomputed persistent cache.
- **II. Computer Vision Accuracy**: PASS (not in scope). No changes to detection/classification path.
- **III. Modular Design**: PASS. Cache persistence, offline precompute, and runtime provider integration remain separable modules.
- **IV. Configuration Management**: PASS. Runtime knobs and cache signatures remain configuration-driven and validated.
- **V. Real-Time Screen Capture**: PASS (not in scope). No impact to capture pipeline.
- **VI. Comprehensive Testing**: PASS with required additions for DB schema, invalidation, corruption, and resume flow.
- **VII. Consistent Logging**: PASS. Cache hit/miss/degraded paths will log via centralized logger.
- **VIII. Virtual Environment Management**: PASS. Python tooling and SQLAlchemy dependencies stay in project venv.

Post-Phase-1 Re-check: PASS. Design artifacts preserve modularity, deterministic behavior, and testability.

## Project Structure

### Documentation (this feature)

```text
specs/001-offline-aof-cache/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
python/
└── hopilot/
  ├── gto/
  │   ├── aof_browser_data_provider.py
  │   ├── aof_solver_adapter.py
  │   ├── aof_browser_state.py
  │   └── aof_hand_matrix.py
  └── gui_components/
    └── aof_browser_panel.py

config/
└── gto_defaults.yaml

tests/
├── test_aof_solver_provider_cache.py
├── test_aof_solver_provider_resilience.py
├── test_aof_solver_provider_context.py
├── test_aof_solver_provider_contract.py
├── test_aof_solver_adapter_exact_path.py
└── test_gto_gui_integration.py
```

**Structure Decision**: Keep single-project Python structure. Add persistent scenario cache and offline precompute modules under `python/hopilot/gto/`, integrate runtime cache-first behavior through the existing provider, and validate with focused pytest suites in `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
