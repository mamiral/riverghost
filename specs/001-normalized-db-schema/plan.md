# Implementation Plan: Normalized Relational Database Schema

**Branch**: `001-normalized-db-schema` | **Date**: 2026-03-15 | **Spec**: [specs/001-normalized-db-schema/spec.md](specs/001-normalized-db-schema/spec.md)
**Input**: Feature specification from `/specs/001-normalized-db-schema/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement a normalized relational database schema using SQLAlchemy and SQLite to replace the current inadequate cache system in the aof_gto_browser application. The schema supports all-in-or-fold poker simulations with comprehensive game state storage, jackpot tracking, and aggregated metrics for convergence analysis and EV calculations.

## Technical Context

**Language/Version**: Python 3.x (existing project standard)  
**Primary Dependencies**: SQLAlchemy (ORM for database abstraction), SQLite (built-in Python support)  
**Storage**: SQLite database file with SQLAlchemy ORM abstraction for future PostgreSQL migration  
**Testing**: pytest (existing project standard) with database fixtures and mocking  
**Target Platform**: Windows/Linux (existing project platforms)  
**Project Type**: Database schema and models for existing poker analysis application  
**Performance Goals**: Handle up to 10k game states per simulation with <100ms query response times for 16 concurrent simulations  
**Constraints**: Must use SQLAlchemy for ORM abstraction, support extensible jackpot types, maintain data integrity with foreign keys  
**Scale/Scope**: Up to 16 concurrent simulations, 10k game states max per simulation, 9 normalized tables

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **DRY Principle**: Database schema normalization eliminates data redundancy  
✅ **Single Responsibility**: Each table has clear, focused purpose  
✅ **SQLAlchemy ORM**: Uses established design pattern for database abstraction  
✅ **Modular Design**: Schema components are independently testable  
✅ **Configuration Management**: Database connection configurable via existing YAML system  

**Post-Design Re-evaluation**: All principles remain compliant. The normalized schema design maintains modularity, eliminates redundancy through proper normalization, and uses established ORM patterns. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-normalized-db-schema/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.plan command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
python/hopilot/  # Existing application directory
├── models/      # NEW: SQLAlchemy model definitions
│   ├── __init__.py
│   ├── base.py         # Base model class
│   ├── simulation.py   # Simulations table
│   ├── hand_matrix.py  # HandMatrices table
│   ├── matrix_cell.py  # MatrixCells table
│   ├── game_state.py   # GameStates table
│   ├── player.py       # Players table
│   ├── bet.py          # Bets table
│   ├── board_card.py   # BoardCards table
│   ├── jackpot.py      # Jackpots table
│   └── aggregated_metric.py  # AggregatedMetrics table
├── database.py         # NEW: Database connection and session management
├── schema.py           # NEW: Schema creation and migration utilities
└── queries.py          # NEW: Common query functions for analysis

tests/
├── test_models.py      # NEW: Model unit tests
├── test_database.py    # NEW: Database integration tests
└── test_queries.py     # NEW: Query function tests
```

**Structure Decision**: Following existing project structure in `python/hopilot/`, adding new database-related modules alongside existing components. Models organized by table for maintainability, with separate database management and query utilities.