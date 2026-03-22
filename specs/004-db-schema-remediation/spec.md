# Feature Specification: Database Schema Remediation

**Feature Branch**: `004-db-schema-remediation`  
**Created**: 2026-03-21  
**Status**: Draft  
**Input**: User description: "Implement comprehensive remediation for the critical architectural violation in the normalized database schema implementation (found in this dir `specs\001-normalized-db-schema`). The current system incorrectly treats MatrixCells as primary data and stores AggregatedMetrics directly, violating the specification that requires GameStates as the primary data source with MatrixCells and AggregatedMetrics being derived/computed.

Key requirements:
- Modify data flow so GameStates are stored as primary data during Monte Carlo simulations
- Implement MatrixCells and AggregatedMetrics as computed aggregations from GameStates
- Add missing CRUD methods for GameStates, Players, Bets, BoardCards, and Jackpots
- Enable game replay functionality with chronological betting actions and board reveals
- Support temporal convergence analysis from historical GameStates
- Implement jackpot detection, storage, and frequency analysis during simulations
- Ensure all analytical query capabilities from the specification are functional
- Maintain backward compatibility during the transition

The remediation must restore the intended GameStates-first architecture while preserving existing GUI functionality.

Related documents:
* `database_schema_compliance_analysis.md`
* `specs\001-normalized-db-schema\spec.md`"
## Clarifications

### Session 2026-03-21
- Q: How should MatrixCells and AggregatedMetrics be computed from GameStates data? → A: Use simple averaging of all GameStates for each hand combination (Option B)
- Q: What migration strategy should be used for existing MatrixCells data during the transition to GameStates-first architecture? → A: Drop all existing MatrixCells and recompute everything from scratch (Option C)
- Q: What level of backward compatibility should be maintained for existing GUI functionality during the transition? → A: No compatibility - GUI completely broken until full migration to new architecture (Option D)
## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Poker Simulations with Full Data Persistence (Priority: P1)

As a poker analyst, I want to run Monte Carlo simulations for all-in-or-fold games and have all game states, player hands, and outcomes stored in a normalized database so that I can analyze convergence and replay specific hands.

**Why this priority**: This is the core functionality that enables the primary use case of the poker analysis tool - running simulations and storing results for analysis. The current architectural violation prevents proper data persistence and analysis.

**Independent Test**: Can be fully tested by running a simulation, verifying data is stored in GameStates, Players, Bets, BoardCards tables with proper relationships, and querying historical convergence data.

**Acceptance Scenarios**:

1. **Given** a 13x13 hand matrix simulation is run, **When** the simulation completes, **Then** all game states are stored with timestamps, player hands, board cards, and outcomes in the correct normalized tables.
2. **Given** stored simulation data, **When** querying for convergence analysis, **Then** equity values show proper convergence over time from historical GameStates data.
3. **Given** a specific hand matchup, **When** replaying the game, **Then** all betting actions and board reveals are available chronologically from the stored GameStates.

---

### User Story 2 - Analyze Jackpot Frequencies and EV Impact (Priority: P2)

As a poker analyst, I want to track jackpot events during simulations and see how they affect expected value calculations so that I can optimize strategies for jackpot-rich games.

**Why this priority**: Jackpots are significant value drivers in modern poker platforms, and understanding their impact is crucial for accurate analysis. The current system doesn't track jackpots at all.

**Independent Test**: Can be fully tested by simulating games with jackpot triggers, verifying jackpot events are recorded in the Jackpots table, and confirming EV calculations include jackpot payouts from historical data.

**Acceptance Scenarios**:

1. **Given** a simulation with jackpot-eligible hands, **When** a jackpot condition is met, **Then** the event is recorded with payout amount and specific cards used for jackpot qualification.
2. **Given** aggregated metrics computed from GameStates, **When** viewing EV calculations, **Then** jackpot-adjusted EV accounts for frequency and payout amounts from stored jackpot data.
3. **Given** multiple simulations, **When** analyzing jackpot frequency, **Then** statistics show accurate occurrence rates by hand type from the Jackpots table.

---

### User Story 3 - Query and Extend Database Schema (Priority: P3)

As a developer, I want to perform complex queries across the properly normalized schema and easily add new tables for future game features so that the system remains maintainable and extensible.

**Why this priority**: Ensures the database design supports long-term evolution and advanced analytical queries now that the architecture is corrected.

**Independent Test**: Can be fully tested by executing the complex query examples from the original specification and successfully adding a new table with foreign key relationships.

**Acceptance Scenarios**:

1. **Given** the corrected database schema, **When** running complex joins for game replay, **Then** queries execute efficiently and return correct data from GameStates and related tables.
2. **Given** a new game feature requirement, **When** adding a table to the schema, **Then** foreign key constraints maintain data integrity with the GameStates-first architecture.
3. **Given** different matrix sizes, **When** querying data, **Then** the schema adapts without structural changes while maintaining the normalized relationships.

---

### Edge Cases

- What happens when simulation data exceeds SQLite file size limits during GameStates storage?
- How does system handle corrupted database files during complex analytical queries?
- What occurs when foreign key constraints are violated during GameStates insertion?
- How does the system maintain backward compatibility when MatrixCells are now derived instead of primary?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST modify data flow so GameStates are stored as primary data during Monte Carlo simulations with complete game state information
- **FR-002**: System MUST implement MatrixCells and AggregatedMetrics as computed aggregations derived from stored GameStates data
- **FR-003**: System MUST add complete CRUD methods for GameStates, Players, Bets, BoardCards, and Jackpots tables
- **FR-004**: System MUST enable game replay functionality with chronological betting actions and board reveals from stored GameStates
- **FR-005**: System MUST support temporal convergence analysis through timestamped historical GameStates data
- **FR-006**: System MUST implement jackpot detection, storage, and frequency analysis during simulation runs
- **FR-007**: System MUST ensure all analytical query capabilities from the original specification are functional with the corrected architecture
- **FR-008**: System MUST maintain backward compatibility during the transition by preserving existing GUI functionality
- **FR-009**: System MUST enforce data integrity with foreign key constraints and ACID transactions in the corrected schema
- **FR-010**: System MUST use SQLAlchemy Python module for database abstraction to enable seamless switching between SQLite and PostgreSQL

### Key Entities *(include if feature involves data)*

- **Simulations**: Represents individual Monte Carlo simulation runs, with metadata like start/end times and parameters
- **HandMatrices**: Contains the 13x13 grid structure for each simulation, linked to Simulations
- **MatrixCells**: Derived cells in the matrix representing specific hand vs hand matchups, computed from GameStates and linked to HandMatrices
- **GameStates**: Primary data records of each simulated hand with timestamps, outcomes, and references to board cards (now the source of truth)
- **Players**: Player information including hole cards and positions within each game state
- **Bets**: All-in betting actions recorded for each game state
- **BoardCards**: Community cards (flop, turn, river) for each hand
- **Jackpots**: Special payout events triggered by specific hand combinations with payout amounts and qualifying cards
- **AggregatedMetrics**: Computed statistics per matrix cell including equity and jackpot-adjusted EV, calculated from GameStates

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can run simulations and query historical convergence data from GameStates within 30 seconds for 10,000 hands
- **SC-002**: System correctly stores and retrieves complete game replay data including all betting actions and board reveals
- **SC-003**: Jackpot frequency analysis queries complete in under 10 seconds for datasets with 100,000+ stored GameStates
- **SC-004**: Complex analytical queries (game replay, convergence analysis) execute without errors and return accurate results
- **SC-005**: Existing GUI functionality remains fully operational during and after the architectural transition
- **SC-006**: Data integrity is maintained with all foreign key constraints properly enforced in the corrected schema