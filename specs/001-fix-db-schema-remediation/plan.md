# Implementation Plan: Fix Database Schema Remediation

**Branch**: `001-fix-db-schema-remediation` | **Date**: April 1, 2026 | **Spec**: [specs/001-fix-db-schema-remediation/spec.md](specs/001-fix-db-schema-remediation/spec.md)
**Input**: Feature specification from `/specs/001-fix-db-schema-remediation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement genuine GameStates-first database architecture using the Strategy pattern for GameStatePersistence, where AllInFoldGTOSolver accepts pluggable persistence strategies (database, mock, in-memory), eliminating fake data generation and ensuring all tables contain real simulation data with proper foreign key constraints.

## Technical Context

**Design Patterns**: Strategy pattern for GameStatePersistence implementations, Dependency injection of persistence strategies, Repository pattern for data access  
**Testing Strategy**: Unit tests with mock persistence strategies, integration tests with real database strategy  
**Architecture**: Strategy pattern enables pluggable persistence behaviors - database, in-memory, file-based, etc. - while maintaining clean separation between computation and storage

## Constitution Check

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Potential Violations Identified:**
- None - resolved through dependency injection pattern

**Design Solution Adopted:**
- Implement Strategy pattern with `GameStatePersistence` as the strategy interface
- Create concrete strategies: `DatabasePersistenceStrategy`, `MockPersistenceStrategy`, `InMemoryPersistenceStrategy`
- Inject persistence strategy into `AllInFoldGTOSolver` via constructor
- Solver calls strategy methods during simulation (no direct coupling to storage)
- Enables testing with mock strategies and easy switching between storage backends

**Gates Status:** PASS - Strategy pattern provides clean separation, testability, and extensibility

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
specs/001-fix-db-schema-remediation/
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
├── poker_analyzer.py     # Contains AllInFoldGTOSolver - modified to accept persistence strategy
├── aof_solver_adapter.py # Will be eliminated
├── database/             # Database models and operations
│   ├── models.py         # SQLAlchemy models (GameState, Player, Bet, etc.)
│   ├── session.py        # Database session management
│   ├── schema.py         # Database schema definitions
│   └── persistence.py    # GameStatePersistence strategy interface and concrete implementations
│       ├── __init__.py
│       ├── base.py       # Abstract base strategy class
│       ├── database.py   # DatabasePersistenceStrategy (SQLAlchemy implementation)
│       └── mock.py       # MockPersistenceStrategy (for testing)
└── simulation/
    ├── monte_carlo.py    # Monte Carlo simulation logic
    └── game_state.py     # Game state capture logic

tests/
├── test_database_remediation.py    # Integration tests with DatabasePersistenceStrategy
├── test_solver_integration.py      # Unit tests with MockPersistenceStrategy
└── test_gamestate_queries.py       # Tests for game replay and analysis queries
```

**Structure Decision**: Strategy pattern enables clean separation with concrete strategies for different environments (production database, testing mocks, in-memory for development). Eliminates AoFSolverAdapter while maintaining testability and extensibility.

## Complexity Tracking

> **No violations to track - resolved through proper design patterns**
