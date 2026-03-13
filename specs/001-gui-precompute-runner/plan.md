# Implementation Plan: In-GUI AoF Precompute Runner

**Branch**: `001-gui-precompute-runner` | **Date**: 2026-03-13 | **Spec**: `specs/001-gui-precompute-runner/spec.md`
**Input**: Feature specification from `/specs/001-gui-precompute-runner/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add an in-GUI precompute runner panel to the standalone AoF browser that executes sequential 13x13 cell precomputation with cooperative chunking, immediate matrix updates, and persisted checkpoint resume. The implementation will reuse existing deterministic status semantics and canonical solver-equivalence cache dedup by introducing a GUI runner controller over the current `AoFBrowserDataProvider` and `AoFScenarioCacheStore`, while enforcing scenario-change guards during active runs.

## Technical Context

**Language/Version**: Python 3.13 (project virtual environment)  
**Primary Dependencies**: pygame UI components, existing AoF modules (`aof_browser_panel`, `aof_browser_data_provider`, `aof_precompute_runner`, `aof_scenario_cache_store`), SQLAlchemy-backed cache models  
**Storage**: Existing SQLite cache store (`python/hopilot/cache/aof_scenario_cache.sqlite3`) with run/checkpoint metadata in precompute tables  
**Testing**: pytest (unit tests for run-state transitions and deterministic behavior, integration tests for panel responsiveness and checkpoint recovery)  
**Target Platform**: Windows desktop runtime (pygame AoF browser), local filesystem persistence
**Project Type**: Python desktop application module enhancement  
**Performance Goals**: Pause/stop request honored in <= 1 second (p95) under reference settings; UI avoids visible freeze > 200 ms while run is active; per-cell update visible immediately on completion  
**Constraints**: Sequential 169-cell execution per run; deterministic statuses (AVAILABLE/MISSING/NO_CONTEST/TIMEOUT/ERROR); browser remains decoupled from simulator; canonical solver-equivalence dedup preserved without context leakage  
**Scale/Scope**: One active scenario run at a time, 169 cells per run, resumable checkpoint over partially completed cells, continuation through per-cell failures

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Real-Time Poker Analysis**: PASS. In-GUI precompute reduces repeated runtime solve cost and improves real-time usability of AoF analysis.
- **II. Computer Vision Accuracy**: PASS (not in scope). No card-detection pipeline changes.
- **III. Modular Design**: PASS. Runner controller, checkpoint/state model, and panel UI updates are separable from solver/cache internals.
- **IV. Configuration Management**: PASS. Simulations-per-cell defaults and runtime settings stay aligned with validated config patterns and explicit UI input constraints.
- **V. Real-Time Screen Capture**: PASS (not in scope). No capture subsystem modifications.
- **VI. Comprehensive Testing**: PASS with planned additions covering control transitions, interruption responsiveness, checkpoint recovery, and deterministic failure continuation.
- **VII. Consistent Logging**: PASS. Run lifecycle and transition events will be emitted through centralized logger pathways used by existing AoF modules.
- **VIII. Virtual Environment Management**: PASS. No tooling changes outside project venv workflow.

Post-Phase-1 Re-check: PASS. Design artifacts preserve deterministic cache semantics, separation of concerns, and testability.

## Project Structure

### Documentation (this feature)

```text
specs/001-gui-precompute-runner/
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
    ├── gui_components/
    │   └── aof_browser_panel.py
    └── gto/
        ├── aof_browser_data_provider.py
        ├── aof_precompute_runner.py
        ├── aof_scenario_cache_store.py
        └── aof_scenario_cache_models.py

tests/
├── test_aof_precompute_runner.py
├── test_aof_solver_provider_cache.py
└── test_gto_gui_integration.py
```

**Structure Decision**: Keep the existing single-project Python layout. Add GUI-runner orchestration in AoF browser GUI/component paths while extending the existing precompute/cache modules for checkpoint and telemetry state continuity; validate behavior with focused pytest coverage in `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
