# Implementation Plan: Database Schema Browser Integration

**Branch**: `001-db-schema-browser-integration` | **Date**: 2026-03-17 | **Spec**: [specs/001-db-schema-browser-integration/spec.md](specs/001-db-schema-browser-integration/spec.md)
**Input**: Feature specification from `/specs/001-db-schema-browser-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Integrate the normalized relational database schema from 001-normalized-db-schema into the aof_gto_browser application, replacing the inadequate AoFScenarioCacheStore and AggregationService cache system with proper database persistence, query flexibility, and support for advanced analytical features like convergence analysis and jackpot-adjusted EV calculations.

## Technical Context

**Language/Version**: Python 3.x (existing project standard)  
**Primary Dependencies**: SQLAlchemy (ORM for database abstraction), SQLite (built-in Python support), existing browser components (AoFBrowserDataProvider, AoFBrowserPanel)  
**Storage**: SQLite database with normalized relational schema (9 tables: Simulations, HandMatrices, MatrixCells, GameStates, Players, Bets, BoardCards, Jackpots, AggregatedMetrics)  
**Testing**: pytest (existing project standard) with database fixtures and mocking  
**Target Platform**: Windows/Linux (existing project platforms)  
**Project Type**: Database integration for existing GUI application  
**Performance Goals**: <500ms query response times for matrix browsing, support up to 10 concurrent users  
**Constraints**: Must maintain existing browser UI functionality, use normalized schema from 001-normalized-db-schema, enforce data integrity with foreign keys  
**Scale/Scope**: Integration of existing components, up to 10 concurrent users, 13x13 hand matrices, timestamped simulation data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **I. Real-Time Poker Analysis**: Feature enables real-time browsing of GTO strategy matrices with <500ms response times  
✅ **II. Computer Vision Accuracy**: Not applicable to database integration feature  
✅ **III. Modular Design**: Integration creates new database-backed data provider while maintaining existing browser components  
✅ **IV. Configuration Management**: Database connection configuration will use validated YAML files with Pydantic  
✅ **V. Real-Time Screen Capture**: Not applicable to database integration feature  
✅ **VI. Comprehensive Testing**: All integration components will be tested using pytest with database fixtures and mocking  
✅ **VII. Consistent Logging**: Integration will use centralized logging configuration for database operations  
✅ **VIII. Virtual Environment Management**: All Python code runs within venv as per project standard  
✅ **IX. DRY Principle**: Eliminates duplication by replacing inadequate cache system with single normalized database  
✅ **X. Single Responsibility Principle**: Data provider focuses on database access, browser components focus on UI, clear separation maintained  
✅ **XI. Established Design Patterns**: Uses SQLAlchemy ORM pattern for database abstraction, established repository pattern for data access  

**Post-Design Re-evaluation**: All principles remain compliant. The database integration design maintains modularity through clear separation of data access layer, eliminates redundancy by consolidating storage approaches, and uses established ORM patterns. The repository pattern ensures single responsibility, and the design includes comprehensive testing and configuration management. No violations requiring justification.

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

### Source Code (repository root)

```text
python/hopilot/gto/
├── database_repository.py          # NEW: Repository for database access
├── normalized_db_provider.py       # NEW: Database-backed data provider
└── [existing browser files]

python/hopilot/data/
└── normalized_poker.db             # NEW: SQLite database file

config/gto_defaults.yaml            # UPDATED: Database connection config
```
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
