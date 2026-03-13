# Implementation Plan: Solver-Backed AoF Browser Data

**Branch**: `001-solver-backed-aof-browser` | **Date**: 2026-03-13 | **Spec**: `specs/001-solver-backed-aof-browser/spec.md`
**Input**: Feature specification from `/specs/001-solver-backed-aof-browser/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Upgrade the standalone AoF GTO Browser to replace heuristic matrix values with solver-backed outputs while preserving existing UI behavior and payload contracts. Implement a provider adapter layer that maps browser context (selected position, per-position actions, metric) to solver and analyzer evaluations, with deterministic edge-case policy, context-keyed caching, timeout handling, and comprehensive automated coverage.

## Technical Context

**Language/Version**: Python 3.13 (project venv)  
**Primary Dependencies**: pygame, pytest, pydantic, yaml, project modules `hopilot.all_in_fold_gto`, `hopilot.gto.gto_optimizer`, `hopilot.poker_analyzer`  
**Storage**: In-memory provider cache, optional YAML fixtures for tests/docs, no persistent DB changes  
**Testing**: pytest (`tests/test_aof_gto_browser_gui.py`, `tests/test_gto_gui_integration.py`, new provider-focused tests)  
**Target Platform**: Windows desktop runtime (pygame app), Python execution from `python/` directory
**Project Type**: Python desktop application module update  
**Performance Goals**: >=95% of context/metric toggles complete within 1.0s under reference test workload; no UI crash on solver failure/timeout  
**Constraints**: Deterministic test behavior despite Monte Carlo components, preserve current UI contract and standalone AoF app boundaries, avoid simulator recoupling  
**Scale/Scope**: One standalone AoF browser provider path; 169-cell matrix recomputation across 4 metrics and 4 position states

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Real-Time Poker Analysis**: PASS. Feature explicitly consumes existing analysis engines to deliver strategy values in interactive UI.
- **II. Computer Vision Accuracy**: PASS (not directly modified). No regression to card detection pipeline.
- **III. Modular Design**: PASS. Introduces adapter/provider-level changes without coupling UI renderer to solver internals.
- **IV. Configuration Management**: PASS. Any runtime knobs remain YAML-compatible where fixtures/config are used.
- **V. Real-Time Screen Capture**: PASS (not in scope). No impact.
- **VI. Comprehensive Testing**: PASS with required additions for edge cases, caching, timeout/failure handling.
- **VII. Consistent Logging**: PASS. Provider adapter and fallback paths will emit structured logs via centralized logger.
- **VIII. Virtual Environment Management**: PASS. Development and test commands remain in project venv.

Post-Phase-1 Re-check: PASS. Design artifacts preserve modularity, testability, and logging expectations.

## Project Structure

### Documentation (this feature)

```text
specs/001-solver-backed-aof-browser/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
python/
└── hopilot/
    ├── aof_gto_browser_gui.py
    ├── all_in_fold_gto.py
    ├── poker_analyzer.py
    ├── gto/
    │   ├── aof_browser_data_provider.py
    │   ├── aof_browser_state.py
    │   ├── aof_hand_matrix.py
    │   └── gto_optimizer.py
    └── gui_components/
        ├── aof_browser_panel.py
        └── aof_hand_matrix_panel.py

tests/
├── test_aof_gto_browser_gui.py
├── test_gto_gui_integration.py
└── test_all_in_fold_gto.py

docs/
└── initial_design/
    └── USAGE_GUIDE_WIN.md
```

**Structure Decision**: Keep a single Python desktop-app structure. Implement solver integration at provider/adapter layer under `python/hopilot/gto/` and validate via existing AoF GUI integration tests plus new provider/contract tests.

## Complexity Tracking

No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
