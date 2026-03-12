# Implementation Plan: GTO Analysis Integration in Poker Simulator

**Branch**: `002-gto-simulator-integration` | **Date**: 2026-03-03 | **Spec**: [specs/002-gto-simulator-integration/spec.md](specs/002-gto-simulator-integration/spec.md)
**Input**: Feature specification from `/specs/002-gto-simulator-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Integrate Game Theory Optimal (GTO) analysis functionality directly into the existing poker simulator GUI, enhancing it with all-in strategy recommendations while preserving all current functionality for range assignment, card selection, and equity calculations. The integration will add GTO threshold calculations and optimal range analysis for tournament scenarios with bonus payouts.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Existing PokerKit, Pygame, Pydantic, PyYAML
**Storage**: N/A (leverages existing simulator state and GTO result caching)
**Testing**: pytest with mocked Monte Carlo simulations
**Target Platform**: Windows (maintains existing dxcam integration)
**Project Type**: Desktop application enhancement (integrates into existing poker_simulator_gui.py)
**Performance Goals**: GTO calculation completes in <30 seconds for typical all-in scenarios
**Constraints**: Must integrate seamlessly into existing poker simulator GUI without disrupting current functionality, maintain real-time responsiveness
**Scale/Scope**: Single feature integration affecting one GUI file, leverages existing GTO solver and analysis components

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I. Real-Time Poker Analysis
**Status: ✅ PASS** - Feature enhances real-time poker analysis with GTO threshold calculations for all-in decisions
**Alignment**: Integrates GTO analysis into existing Monte Carlo simulation framework

### Principle II. Computer Vision Accuracy
**Status: ✅ PASS** - No computer vision changes required, leverages existing card detection infrastructure
**Alignment**: Feature is analysis-focused, doesn't impact CV accuracy requirements

### Principle III. Modular Design
**Status: ✅ PASS** - Integration follows modular architecture, adding GTO components without disrupting existing modules
**Alignment**: GTO analysis integrates as independent component within existing GUI structure

### Principle IV. Configuration Management
**Status: ✅ PASS** - Uses existing YAML configuration patterns for bonus payouts and GTO parameters
**Alignment**: Bonus payout settings follow established Pydantic validation patterns

### Principle V. Real-Time Screen Capture
**Status: ✅ PASS** - No changes to screen capture functionality
**Alignment**: Integration occurs post-capture in the analysis/GUI layer

### Principle VI. Comprehensive Testing
**Status: ✅ PASS** - Will include pytest coverage for integration points and GTO functionality
**Alignment**: New integration tests will mock external dependencies as per existing patterns

### Principle VII. Consistent Logging
**Status: ✅ PASS** - Uses existing logging configuration throughout integration
**Alignment**: All new code will import and use get_logger(__name__) consistently

### Principle VIII. Virtual Environment Management
**Status: ✅ PASS** - No changes to virtual environment requirements
**Alignment**: Integration runs within existing venv setup

**Overall Assessment: ✅ ALL PRINCIPLES PASS** - Feature aligns with all constitutional requirements and enhances existing functionality without violations.

---

**Post-Design Re-evaluation: ✅ ALL PRINCIPLES STILL PASS**
- Integration enhances existing poker simulator with GTO analysis
- Maintains modular design by extending existing SimulationPanel
- Preserves all existing real-time analysis capabilities
- Uses established configuration patterns for bonus payouts
- No changes to screen capture or CV functionality
- Comprehensive testing through existing pytest framework
- Consistent logging via existing infrastructure
- Runs within existing virtual environment setup

## Project Structure

### Documentation (this feature)

```text
specs/002-gto-simulator-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
python/hopilot/
├── poker_simulator_gui.py    # PRIMARY: Enhanced with GTO analysis integration
├── all_in_fold_gto.py        # EXISTING: GTO solver (already implemented)
├── gui_components/           # EXISTING: Reusable GUI components
│   ├── gto_solver_panel.py   # EXISTING: May be deprecated/removed
│   └── [other components]
└── gto/                      # EXISTING: GTO analysis components
    ├── gto_models.py         # EXISTING: Data models
    ├── range_manager.py      # EXISTING: Range persistence
    └── gto_optimizer.py      # EXISTING: Advanced optimization
```

**Structure Decision**: Integration-focused enhancement of existing poker simulator. Primary changes to `poker_simulator_gui.py` to add GTO analysis UI elements and logic. Leverages existing GTO solver infrastructure without major architectural changes. Maintains all existing simulator functionality while adding GTO capabilities.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
