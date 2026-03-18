# Implementation Plan: State Machine Integration

**Branch**: `001-state-machine-integration` | **Date**: 2024-12-19 | **Spec**: [link]
**Input**: Feature specification from `/specs/001-state-machine-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Integrate the completed state machine implementation with the AOF GTO Browser GUI by replacing manual precompute button handling with state machine control. The state machine will manage precompute operation lifecycle (idle → running → paused/stopped) while delegating execution to the existing AoFBrowserPanel infrastructure. This maintains all existing functionality while adding robust state management and preventing invalid operations.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

## Technical Context

**Language/Version**: Python 3.8+  
**Primary Dependencies**: transitions==0.9.3 (state machine), pygame (GUI), pydantic (config validation)  
**Storage**: SQLite database for scenario caching, YAML files for configuration  
**Testing**: pytest with mocking for GUI and state machine components  
**Target Platform**: Windows desktop application  
**Project Type**: Desktop GUI application with real-time computation  
**Performance Goals**: 60 FPS GUI updates, responsive state transitions (<100ms)  
**Constraints**: Single-threaded GUI with concurrent computation, thread-safe state machine  
**Scale/Scope**: 169 matrix cells, 1-16 worker threads, 100-50000 simulations per cell

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance Assessment

**✓ III. Modular Design**: Integration maintains modular separation between state machine control layer and existing panel execution logic.

**✓ IV. Configuration Management**: Uses existing YAML configuration system with Pydantic validation for precompute settings.

**✓ VI. Comprehensive Testing**: Will extend existing pytest test suite with integration tests for state machine + panel interaction.

**✓ VII. Consistent Logging**: Uses existing centralized logging configuration for all new components.

**✓ VIII. Virtual Environment Management**: All code runs within project's venv environment.

**✓ IX. DRY Principle**: State machine controller extracts common precompute control logic, eliminating duplication between manual event handling and state machine callbacks.

**✓ X. Single Responsibility Principle**: 
- StateMachineController: Manages state transitions and control flow
- AoFBrowserPanel: Handles GUI rendering and precompute execution
- PrecomputeConfig: Manages configuration loading and validation

**✓ XI. Established Design Patterns**: Implements State Machine pattern using transitions library, following established design patterns for complex state management.

### Non-Applicable Principles
- I. Real-Time Poker Analysis: Integration preserves existing analysis capabilities
- II. Computer Vision Accuracy: GUI integration doesn't affect card detection
- V. Real-Time Screen Capture: Not relevant to GUI state management

**GATE STATUS: PASS** - All applicable constitution principles satisfied. No violations requiring justification.

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
specs/001-state-machine-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── state_machine_interface.md
│   ├── panel_interface.md
│   └── configuration_interface.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
python/hopilot/
├── aof_gto_browser.py                    # Existing state machine GUI (completed)
├── aof_gto_browser_gui.py               # Main GUI entry point (modify)
├── gui_components/
│   ├── aof_browser_panel.py            # Existing panel (extend)
│   ├── state_machine_controller.py     # NEW: State machine controller
│   └── precompute_config.py            # NEW: Configuration management
└── gto/
    ├── state_machine_config.py         # Existing state config
    └── state_machine_utils.py          # Existing state utils

config/
└── gto_defaults.yaml                   # Existing config (extend)

tests/
├── test_state_machine_integration.py  # NEW: Integration tests
└── test_state_machine_controller.py   # NEW: Controller tests
```

**Structure Decision**: Extends existing GUI component structure with new controller and config classes. Maintains separation between state machine logic and existing panel functionality.


