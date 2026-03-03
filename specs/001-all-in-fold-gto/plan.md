# Implementation Plan: All-In-or-Fold GTO Solver with Bonus Payouts

**Branch**: `001-all-in-fold-gto` | **Date**: 2026-02-27 | **Spec**: [specs/001-all-in-fold-gto/spec.md](specs/001-all-in-fold-gto/spec.md)
**Input**: Feature specification from `/specs/001-all-in-fold-gto/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement a Game Theory Optimal (GTO) solver for all-in-or-fold poker games with bonus payouts, including GUI integration and YAML-based range management. The solver will calculate optimal equity thresholds and enable range vs range optimization for tournament analysis.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Existing PokerKit, Pygame, Pydantic, PyYAML
**Storage**: Local YAML files for range definitions, no database required
**Testing**: pytest with mocked Monte Carlo simulations for fast unit tests
**Target Platform**: Windows (existing dxcam integration maintained)
**Project Type**: Desktop application enhancement (adds GTO analysis to existing poker tool)
**Performance Goals**: GTO calculation completes in <30 seconds for typical scenarios (1000+ hands)
**Constraints**: Must remain offline, no external API calls, maintain existing GUI responsiveness
**Scale/Scope**: Handles 1-10 opponents, pot sizes $10-1000, bonus multipliers up to 500x

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I. Real-Time Poker Analysis
**Status: ✅ PASS** - Feature extends Monte Carlo simulation capabilities with GTO threshold calculations
**Alignment**: Provides advanced poker analysis through optimal strategy computation

### Principle II. Computer Vision Accuracy
**Status: ✅ PASS** - No CV changes required, leverages existing card detection infrastructure
**Alignment**: Feature is analysis-focused, doesn't impact CV requirements

### Principle III. Modular Design
**Status: ✅ PASS** - New components (GTOSolver, RangeManager, GUI panels) follow modular architecture
**Alignment**: Independently testable components that integrate cleanly with existing system

### Principle IV. Configuration Management
**Status: ✅ PASS** - Uses YAML for range persistence with Pydantic validation
**Alignment**: Range files and bonus configurations follow existing YAML/Pydantic patterns

### Principle V. Real-Time Screen Capture
**Status: ✅ PASS** - No changes to capture functionality
**Alignment**: Feature is post-capture analysis, doesn't affect real-time requirements

### Principle VI. Comprehensive Testing
**Status: ✅ PASS** - Will include full pytest coverage with mocked simulations
**Alignment**: Unit tests for GTO logic, integration tests for GUI components

### Principle VII. Consistent Logging
**Status: ✅ PASS** - Uses existing logging_config throughout new components
**Alignment**: All new classes will import and use get_logger(__name__)

### Principle VIII. Virtual Environment Management
**Status: ✅ PASS** - No changes to environment requirements
**Alignment**: Feature runs within existing venv setup

**Overall Assessment: ✅ ALL PRINCIPLES PASS** - Feature aligns with all constitutional requirements.

---

**Post-Design Re-evaluation: ✅ ALL PRINCIPLES STILL PASS**
- Design maintains modular architecture with clear separation of concerns
- YAML-based persistence aligns with existing configuration patterns
- GTO calculations integrate cleanly with existing Monte Carlo infrastructure
- No changes required to core HoPilot functionality
- Performance goals respect real-time analysis requirements

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

## Project Structure

### Documentation (this feature)

```text
specs/001-all-in-fold-gto/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── gto-solver-api.md
│   └── range-format.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
python/hopilot/
├── gto/
│   ├── all_in_fold_gto.py    # Extend existing GTO solver
│   ├── range_manager.py      # New: YAML range persistence
│   └── gto_optimizer.py      # New: Range vs range optimization
├── gui_components/
│   ├── gto_solver_panel.py   # New: Main GTO analysis panel
│   ├── range_editor.py       # New: Range creation/editing
│   └── strategy_visualizer.py # New: Results display
└── config/
    └── gto_defaults.yaml     # New: Default bonus payouts
```

### Testing Structure

```text
tests/
├── test_all_in_fold_gto.py      # Unit tests for GTO logic
├── test_range_manager.py        # YAML persistence tests
├── test_gto_solver_panel.py     # GUI component tests
└── test_gto_integration.py      # End-to-end tests
```

### Configuration Files

```text
config/
└── gto_defaults.yaml             # Default bonus payout configurations
```

**Structure Decision**: Desktop application enhancement following existing HoPilot modular structure. New GTO components in dedicated `gto/` subdirectory, GUI components in `gui_components/`, tests in `tests/`. Maintains separation between analysis logic and presentation layers.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
