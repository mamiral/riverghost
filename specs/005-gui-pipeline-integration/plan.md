# Implementation Plan: GUI Integration and UX Hardening on the GameStates-First Pipeline

**Branch**: `005-gui-pipeline-integration` | **Date**: 2026-04-28 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/005-gui-pipeline-integration/spec.md`

## Summary

Make the AoF Browser GUI behave as a coherent product on top of the GameStates-first pipeline: enforce seven explicit panel states (`LOADING`, `AVAILABLE`, `MISSING`, `COMPUTING`, `STALE`, `NO_CONTEST`, `ERROR`), connect precompute lifecycle to panel state transitions, implement cross-run cumulative aggregation, add a partial-cell count indicator, and validate the full end-to-end flow manually.

The backend pipeline is complete. All work is in the GUI layer (`aof_browser_panel.py`), the read path (`BrowserDatabaseProvider.get_matrix_payload`), and a new cross-run aggregation helper in `DatabaseRepository`.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: pygame (GUI rendering), SQLAlchemy 2.x (ORM), pytest (testing)  
**Storage**: SQLite via SQLAlchemy (`DatabaseRepository` / `DatabaseConnection`)  
**Testing**: pytest; root `tests/` directory; no pygame GUI automation — manual validation is the acceptance gate  
**Target Platform**: Windows desktop (pygame window, dxcam screen capture)  
**Project Type**: desktop-app  
**Performance Goals**: Panel state transitions ≤ 1 frame (16ms); post-run auto-refresh ≤ 5 seconds (SC-004); cross-run fetch must not block the pygame event loop (run in `ThreadPoolExecutor`)  
**Constraints**: All DB I/O must stay off the main thread (existing pattern via `concurrent.futures`); no new ORM models without migration; `GameState` receives no new FK columns (Architecture Constraint)  
**Scale/Scope**: Single-user desktop app; one scenario active at a time; 169 cells per scenario; multiple completed runs per scenario (cross-run aggregation)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Real-Time Poker Analysis | PASS | Feature is about displaying precomputed data correctly — analysis pipeline unchanged |
| III. Modular Design | PASS | Panel state logic contained in `aof_browser_panel.py`; cross-run aggregation in `DatabaseRepository` |
| VI. Comprehensive Testing | PASS | Panel state transitions tested via unit tests; end-to-end via manual validation (pygame defers automated GUI tests) |
| IX. DRY | PASS | Cross-run fetch is a single new method; no duplication with existing `find_matrix_sweep_run_by_contract` |
| X. Single Responsibility | PASS | `BrowserDatabaseProvider` owns read path; `AoFBrowserPanel` owns panel state; `DatabaseRepository` owns queries |
| XI. Established Patterns | PASS | Observer pattern for state transitions; ThreadPoolExecutor for async DB I/O (existing pattern) |
| XII. Quality Assurance | PASS | No placeholder tests; no `assert True`; cross-run aggregation tested against real DB writes |
| Architecture: GameStates-First | PASS | No `cell_id` added to `GameState`; no equity computed in solver |
| Architecture: No direct DB in solver | PASS | Panel receives `BrowserDatabaseProvider` via constructor; no new direct DB calls in GUI |

**Post-design re-check**: Required after Phase 1 — confirm `AggregatedMetric.sample_count` addition does not break existing aggregation service writes.

**Post-implementation re-check**: Completed during Phase 8. Targeted and full pytest runs passed, and the cross-run aggregation path remains consistent with the GameStates-first architecture constraints.

## Project Structure

### Documentation (this feature)

```text
specs/005-gui-pipeline-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── panel-state-machine.md
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
python/hopilot/
├── gto/
│   ├── browser_database_provider.py   # MODIFY: get_matrix_payload → cross-run fetch
│   ├── database_repository.py         # MODIFY: add list_matrix_sweep_runs_by_contract usage + cross-run merge
│   └── matrix_sweep_aggregation_service.py  # MODIFY: write sample_count during aggregate_run
├── gui_components/
│   └── aof_browser_panel.py           # MODIFY: panel state machine, Start button, overlay, cell count badge
├── models/
│   └── aggregated_metric.py           # MODIFY: add sample_count column

tests/
├── test_aof_browser_panel_database_integration.py  # MODIFY: add state transition coverage
├── test_cross_run_aggregation.py                   # NEW: cross-run merge logic
└── integration/
    └── test_aof_browser_panel_integration.py       # MODIFY: add AVAILABLE+rerun overlay scenario
```

**Structure Decision**: Single project layout. All changes are within the existing `python/hopilot/` tree. New test file for cross-run aggregation logic only; all GUI state tests extend existing test files to preserve existing passing tests.

## Complexity Tracking

> No constitution violations requiring justification.
