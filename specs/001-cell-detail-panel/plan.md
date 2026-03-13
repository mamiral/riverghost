# Implementation Plan: Cell Detail Middle Panel

**Branch**: `[001-cell-detail-panel]` | **Date**: 2026-03-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-cell-detail-panel/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a compact middle `Cell Detail` panel between the hand matrix and right-side controls in the AoF browser GUI. The panel reacts to matrix selection, metric changes, and scenario context refreshes; renders a vertical stacked bar for WIN_LOSE_PROBABILITY (win/tie/loss), provides analogous metric-aware views for EV/EQUITY/EQR, and displays explicit fallback states for non-available cells.

## Technical Context

**Language/Version**: Python 3.13 (project venv runtime)  
**Primary Dependencies**: `pygame`, existing HoPilot AoF GUI/payload modules  
**Storage**: N/A (read-only UI over existing in-memory payload)  
**Testing**: `pytest` with existing GUI integration/unit patterns  
**Target Platform**: Desktop app (Windows primary), pygame-supported environments
**Project Type**: Desktop GUI application module within single Python package  
**Performance Goals**: Cell-detail refresh on next render tick after selection/metric change; maintain smooth interactive browsing without noticeable lag  
**Constraints**: Preserve compact 3-column layout (matrix, middle detail, right controls) and avoid regression in right-side control usability  
**Scale/Scope**: Single feature slice affecting AoF browser panel composition, state selection handling, and GUI tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate Review

- **Principle I: Real-Time Poker Analysis**: PASS. Feature is visualization-only over existing real-time outputs.
- **Principle II: Computer Vision Accuracy**: PASS. No change to detection pipeline.
- **Principle III: Modular Design**: PASS. Implement as dedicated middle-panel component and minimal orchestration changes.
- **Principle IV: Configuration Management**: PASS. No new config required.
- **Principle V: Real-Time Screen Capture**: PASS. No change.
- **Principle VI: Comprehensive Testing**: PASS with condition. Must add/extend pytest GUI tests for selection, metric switching, and fallback states.
- **Principle VII: Consistent Logging**: PASS. No new critical logging requirement; existing status messaging patterns sufficient.
- **Principle VIII: Virtual Environment Management**: PASS. Execute and test in existing venv workflow.

**Gate Decision (Pre-Phase 0)**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-cell-detail-panel/
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
  ├── gui_components/
  │   ├── aof_browser_panel.py
  │   ├── aof_hand_matrix_panel.py
  │   └── aof_cell_detail_panel.py        # planned
  └── gto/
    └── aof_browser_state.py

tests/
├── test_aof_gto_browser_gui.py
└── test_gto_gui_integration.py
```

**Structure Decision**: Extend the existing single-package desktop GUI structure under `python/hopilot/gui_components` by introducing a dedicated detail-panel component and minimal state orchestration updates. Tests remain in existing GUI test modules under `tests/`.

## Phase 0 Research Output

- [research.md](research.md) captures rendering, state, and fallback decisions with alternatives.

## Phase 1 Design Output

- [data-model.md](data-model.md) defines selected-cell and detail-view entities/state transitions.
- [contracts/cell-detail-panel-contract.md](contracts/cell-detail-panel-contract.md) defines UI interaction and data-display contract.
- [quickstart.md](quickstart.md) provides implementation and validation runbook.

### Post-Design Constitution Re-Check

- **Principle I**: PASS (read-only visualization).
- **Principle III**: PASS (explicit modular component boundary documented in data model/contracts).
- **Principle VI**: PASS with planned coverage in quickstart test commands.
- **All other principles**: PASS, unaffected.

**Gate Decision (Post-Phase 1)**: PASS

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
