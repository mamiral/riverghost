# Implementation Plan: Aggregated AoF Run Statistics Database

**Branch**: `001-aggregated-aof-stats` | **Date**: March 13, 2026 | **Spec**: [specs/001-aggregated-aof-stats/spec.md](specs/001-aggregated-aof-stats/spec.md)
**Input**: Feature specification from `/specs/001-aggregated-aof-stats/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Replace snapshot-style cache with cumulative per-scenario statistics storage. Implement append/merge behavior for runs, aggregate on read using weighted totals, and expose confidence metadata. Maintain backward compatibility and GUI responsiveness.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: pygame, sqlalchemy, pydantic, treys, numpy  
**Storage**: SQLite with SQLAlchemy ORM  
**Testing**: pytest with mocking  
**Target Platform**: Windows desktop  
**Project Type**: Desktop GUI application  
**Performance Goals**: Real-time GUI responsiveness, no noticeable slowdown in matrix load  
**Constraints**: Backward-compatible rollout, deterministic test behavior  
**Scale/Scope**: Single-user desktop app, moderate data volume (scenarios x hands x metrics)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**I. Real-Time Poker Analysis**: ✅ Feature enhances analysis accuracy through aggregation, aligning with real-time decision-making.

**II. Computer Vision Accuracy**: ✅ No impact on CV components.

**III. Modular Design**: ✅ Feature will maintain modular architecture with new aggregation components.

**IV. Configuration Management**: ✅ Uses existing YAML/Pydantic config patterns.

**V. Real-Time Screen Capture**: ✅ No impact on capture functionality.

**VI. Comprehensive Testing**: ✅ Feature includes extensive testing requirements.

**VII. Consistent Logging**: ✅ Will use existing logging infrastructure.

**VIII. Virtual Environment Management**: ✅ No changes to environment management.

**GATE STATUS**: ✅ PASS - No violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/001-aggregated-aof-stats/
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
├── gto/
│   ├── aof_scenario_cache_store.py    # Update for aggregation storage
│   ├── aof_browser_data_provider.py   # Update for aggregation retrieval
│   └── aof_browser_state.py           # Add confidence metadata
├── gui_components/
│   ├── aof_browser_panel.py           # Update for confidence display
│   ├── aof_cell_detail_panel.py       # Update for confidence indicators
│   └── aof_hand_matrix_panel.py       # No changes expected
└── config/
    └── gto_defaults.yaml              # Add aggregation config flags

tests/
├── test_aof_gto_browser_gui.py        # Update for aggregation tests
├── test_gto_gui_integration.py        # Update for integration tests
└── test_aggregation.py                # New aggregation unit tests
```

**Structure Decision**: Feature extends existing modular structure in python/hopilot/ with new aggregation logic in gto/ and UI updates in gui_components/. Maintains separation of data, GUI, and config layers.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
