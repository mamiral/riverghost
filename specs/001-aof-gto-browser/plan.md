# Implementation Plan: Standalone AoF GTO Solution Browser

**Branch**: `001-aof-gto-browser` | **Date**: 2026-03-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-aof-gto-browser/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Deliver a standalone AoF GTO solution browser application inside HoPilot while removing AoF solver integration from the simulator GUI. The approach is to isolate AoF browsing into a dedicated GUI entrypoint and panel set, preserve existing solver/optimizer domain modules for data generation, and simplify simulator components by removing AoF-specific navigation and controls.

## Technical Context

**Language/Version**: Python 3.x (project uses Python with pygame; exact minor version managed by venv)  
**Primary Dependencies**: pygame, numpy, pokerkit, pydantic, pyyaml  
**Storage**: Local files (YAML/config and optional exported strategy data), in-memory UI state  
**Testing**: pytest with pygame-oriented tests and integration tests under `tests/`  
**Target Platform**: Windows desktop first (existing project capture stack is Windows-oriented), desktop pygame runtime
**Project Type**: Desktop application module within monorepo-style Python package  
**Performance Goals**: UI interactions (position/action/metric switching) update matrix in <=1s for 95% of interactions  
**Constraints**: Preserve simulator behavior, avoid card-assignment regressions, maintain centralized logging conventions  
**Scale/Scope**: One new standalone AoF GUI flow, four positions, two actions, four metrics, 169 matrix cells

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Pre-Research Gate Evaluation:

- Principle I (Real-Time Poker Analysis): PASS. Feature consumes poker-analysis outputs and presents strategy outcomes without degrading real-time analysis modules.
- Principle II (Computer Vision Accuracy): PASS. No detection logic changes required.
- Principle III (Modular Design): PASS. Scope explicitly separates AoF browser from simulator GUI and keeps modules independently testable.
- Principle IV (Configuration Management): PASS. Existing YAML/Pydantic config patterns remain applicable.
- Principle V (Real-Time Screen Capture): PASS. No screen-capture behavior changes.
- Principle VI (Comprehensive Testing): PASS with required action. Plan includes unit/integration updates for simulator decoupling and standalone AoF GUI.
- Principle VII (Consistent Logging): PASS with required action. New GUI modules must use centralized logger utility.
- Principle VIII (Virtual Environment Management): PASS. Commands remain venv-based and Python-directory aligned.

Post-Design Gate Evaluation:

- PASS. Design artifacts define modular boundaries, explicit regression coverage, and no constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-aof-gto-browser/
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
  ├── poker_simulator_gui.py               # Existing simulator GUI to decouple from AoF
  ├── all_in_fold_gto.py                   # Existing AoF solver engine retained
  ├── gto/
  │   ├── gto_models.py                    # Existing data contracts reused/extended
  │   └── gto_optimizer.py                 # Existing optimization engine reused
  │   ├── aof_browser_state.py             # AoF browser canonical view state
  │   ├── aof_hand_matrix.py               # Matrix topology and formatting helpers
  │   └── aof_browser_data_provider.py     # Context-based matrix data provider
  ├── gui_components/
  │   ├── simulation_panel.py              # Remove AoF controls/results coupling
  │   ├── gto_solver_panel.py              # Reuse/adapt portions for standalone browser
  │   ├── aof_browser_panel.py             # Standalone AoF browser composition
  │   ├── aof_position_selector.py         # Position selector control
  │   ├── aof_action_selector.py           # Action selector control
  │   ├── aof_metric_dropdown.py           # Metric selector dropdown
  │   └── aof_hand_matrix_panel.py         # 13x13 matrix rendering component
  └── aof_gto_browser_gui.py               # Dedicated standalone AoF app entrypoint

tests/
├── test_poker_simulator_gui.py              # Regression tests for simulator-only behavior
├── test_simulation_panel.py                 # Regression tests removing AoF controls
├── test_gto_gui_integration.py              # Re-target to standalone AoF app flow
└── test_aof_gto_browser_gui.py              # Standalone AoF app behavior and UAT-oriented checks
```

**Structure Decision**: Keep the single Python package architecture under `python/hopilot` and introduce a dedicated standalone AoF GUI module plus focused GUI components. This minimizes migration risk by preserving existing solver domain modules while removing simulator coupling at UI boundaries.

## Complexity Tracking

No constitution violations requiring justification.
