# Feature Specification: Fix Database Schema Remediation

**Feature Branch**: `001-fix-db-schema-remediation`  
**Created**: April 1, 2026  
**Status**: Draft  
**Input**: User description: "I need a comprehensive specification to fix the critical database schema remediation failure in the HoPilot poker analysis tool.

## Current Problem Analysis

The existing `specs/004-db-schema-remediation` claims to implement a "GameStates-first" architecture but is completely fraudulent. Analysis reveals:

### Fake Implementation Evidence:
- **GameStates Table**: Contains 169 dummy records (1 per MatrixCell) with placeholder data
- **Empty Tables**: Players (0 records), Bets (0 records), Jackpots (0 records) 
- **Fake Data Generation**: `AoFSolverAdapter` creates random "individual_outcomes" instead of real simulation data
- **Silent Failures**: GameState storage code swallows exceptions and continues with fake data
- **Disabled Integrity**: Foreign key constraints are disabled in SQLite

### Root Cause:
The `AllInFoldGTOSolver.analyze_hand_strategy()` only returns aggregated results (equity, EV), not individual simulation outcomes. The adapter fabricates fake individual outcomes using `random.random() < win_prob`.

### Architectural Violation:
- MatrixCells remain primary data (created directly)
- GameStates are secondary (created as dummies)
- No real individual simulation capture
- No game replay capability
- No temporal convergence analysis
- No jackpot detection

## Required Solution

Create a specification for a **genuine GameStates-first architecture** that:

### Core Requirements:
1. **Real Simulation Data Capture**: Modify solvers to return actual individual outcomes from Monte Carlo simulations
2. **Complete GameState Storage**: Store full game state (players, bets, board cards) for every simulation
3. **MatrixCell Derivation**: Compute MatrixCells and AggregatedMetrics from stored GameStates
4. **Game Replay**: Enable chronological replay of betting actions and board reveals
5. **Temporal Analysis**: Support convergence analysis from historical GameStates
6. **Jackpot Integration**: Detect and store jackpot events during simulations

### Technical Changes Needed:
- Modify `AllInFoldGTOSolver` to return individual simulation outcomes
- Update `AoFSolverAdapter` to pass through real data (not generate fake data)
- Fix GameState storage pipeline to handle real data volumes
- Implement proper foreign key relationships and constraints
- Add data validation and integrity checks
- Update aggregation engine to work with real GameStates data

### Success Criteria:
- All tables contain real simulation data (not placeholders/fakes)
- Game replay queries return actual chronological game sequences
- Convergence analysis uses real historical equity progression
- Jackpot tables contain detected bonus events
- Foreign key constraints enforced
- Performance meets requirements with real data volumes

## Output Requirements

Create a new specification that replaces the fraudulent `specs/004-db-schema-remediation` with a genuine implementation plan. Include:

1. **Accurate Problem Analysis**: Document the current fake implementation
2. **Real Technical Solution**: Specify how to capture actual simulation outcomes
3. **Implementation Phases**: Break down the work into verifiable phases
4. **Testing Strategy**: Include tests that verify real data (not fakes)
5. **Success Metrics**: Measurable outcomes that prove genuine functionality

The new specification must ensure the system actually implements GameStates-first architecture, not just pretend to."

## Clarifications

### Session 2026-04-01
- Q: Performance Requirements - Define specific latency, throughput, and data volume targets for the genuine GameStates-first architecture. → A: Simulation processing: < 30 seconds for 1K iterations, < 5 minutes for 10K iterations; Data volume: < 200MB storage per analysis session
- Q: GameState Data Structure - Confirm or clarify the data model defined in `specs/001-normalized-db-schema` and `specs/004-db-schema-remediation` for the genuine GameStates-first implementation. → A: Use existing schema from specs/001-normalized-db-schema: GameState(id, cell_id, timestamp, round, pot_size, board_cards, outcome); Player(id, game_state_id, position, hole_cards, stack_size, is_hero); Bet(id, game_state_id, player_id, amount, action_type); etc.
- Q: Jackpot Detection Rules - Define specific rules for detecting jackpot events during Monte Carlo simulations to ensure accurate bonus event tracking. → A: Standard platform jackpots: straight flush using both hole cards (GGPoker style), royal flush, four of a kind with specific kickers; payout based on hand rank and qualifying cards
- Q: AllInFoldGTOSolver Modifications - Specify the exact changes needed to return individual simulation outcomes instead of only aggregated results. → A: Modify to accept GameStatePersistence strategy interface for storing simulation data during runs, implementing Strategy pattern with concrete strategies for different environments
- Q: Data Validation Rules - Define specific validation and integrity checks to prevent silent failures and ensure genuine simulation data quality. → A: Foreign key validation on all inserts, data type checking, required field validation, referential integrity checks with detailed error logging

## User Scenarios & Testing

### User Story 1 - Run Genuine Game State Simulations (Priority: P1)

As a poker analyst using HoPilot, I want to run Monte Carlo simulations that capture and store complete, real game states for every simulation outcome, so that I can perform accurate temporal analysis and game replay without relying on fabricated data.

**Why this priority**: This is the core functionality that enables all downstream analysis features and fixes the fraudulent implementation.

**Independent Test**: Can be tested by running a simulation, querying the database, and verifying that GameStates table contains real chronological game sequences with actual player actions and board cards, not dummy data.

**Acceptance Scenarios**:

1. **Given** a poker hand scenario with specific hole cards and board, **When** I run a Monte Carlo simulation, **Then** the GameStates table stores complete game state records for every simulation iteration, including player positions, bet amounts, and board progression.
2. **Given** stored GameStates data, **When** I query for game replay, **Then** I receive chronological sequences of betting actions and board reveals that actually occurred in the simulations.

---

### User Story 2 - Derive Matrix Cells from Game States (Priority: P2)

As a poker analyst, I want MatrixCells and aggregated metrics to be computed from stored GameStates data, so that equity calculations and strategy analysis are based on real simulation outcomes rather than being created independently.

**Why this priority**: This ensures the architecture is truly GameStates-first, with MatrixCells as derived data.

**Independent Test**: Can be tested by verifying that MatrixCell records are created by aggregating GameStates data, and that changes to GameStates are reflected in updated MatrixCell calculations.

**Acceptance Scenarios**:

1. **Given** a set of stored GameStates from simulations, **When** the aggregation engine runs, **Then** MatrixCells are computed from the actual simulation outcomes, showing real equity values and frequencies.
2. **Given** new GameStates data added to the database, **When** I trigger re-aggregation, **Then** MatrixCell values update to reflect the combined dataset.

---

### User Story 3 - Detect and Store Jackpot Events (Priority: P3)

As a poker analyst, I want jackpot events detected during simulations to be stored in the database, so that I can analyze bonus event frequencies and their impact on strategy.

**Why this priority**: This completes the data capture requirements and enables jackpot-aware analysis.

**Independent Test**: Can be tested by running simulations with jackpot conditions, then verifying that Jackpots table contains records of detected bonus events with correct timing and amounts.

**Acceptance Scenarios**:

1. **Given** simulation parameters that include jackpot rules, **When** simulations run, **Then** jackpot events are detected and stored with their occurrence details.
2. **Given** stored jackpot data, **When** I query jackpot statistics, **Then** I receive accurate counts and timing information from real simulation events.

### Edge Cases

- What happens when simulations generate extremely large numbers of GameStates (millions of records)?
- How does the system handle simulation failures that prevent complete GameState storage?
- What occurs when foreign key constraints are violated during data insertion?
- How does the system behave when jackpot detection logic encounters unexpected board combinations?

## Requirements

### Functional Requirements

- **FR-001**: System MUST modify `AllInFoldGTOSolver` to accept a `GameStatePersistence` strategy for storing simulation data, eliminating the `AoFSolverAdapter` layer and ensuring genuine data storage
- **FR-002**: System MUST implement Strategy pattern with concrete strategies: `DatabasePersistenceStrategy` (SQLAlchemy), `MockPersistenceStrategy` (testing), and `InMemoryPersistenceStrategy` (development)
- **FR-003**: System MUST compute MatrixCells and AggregatedMetrics by aggregating stored GameStates data
- **FR-004**: System MUST enable chronological replay of betting actions and board reveals from stored GameStates
- **FR-005**: System MUST support temporal convergence analysis using historical GameStates data
- **FR-006**: System MUST detect and store jackpot events during simulations using standard platform rules (straight flush with both hole cards, royal flush, four of a kind with specific kickers)
- **FR-007**: System MUST enforce foreign key constraints and data integrity in the SQLite database
- **FR-008**: System MUST validate data integrity on all inserts (foreign key validation, data type checking, required field validation, referential integrity checks) with detailed error logging
- **FR-009**: System MUST maintain performance requirements: simulation processing < 30 seconds for 1K iterations, < 5 minutes for 10K iterations; data volume < 200MB per analysis session
- **FR-010**: System MUST use integration tests to verify genuine data storage and eliminate fake data generation

### Non-Functional Requirements

- **NFR-001**: Simulation processing MUST complete in < 30 seconds for 1K iterations and < 5 minutes for 10K iterations
- **NFR-002**: Data storage MUST not exceed 200MB per analysis session
- **NFR-003**: All database operations MUST enforce foreign key constraints with detailed error logging instead of silent failures
- **NFR-004**: Data validation MUST occur on all inserts with immediate error reporting rather than continuing with fake data

### Key Entities

- **GameState**: Confirmed schema from `specs/001-normalized-db-schema`: (id, cell_id, timestamp, round, pot_size, board_cards, outcome) - represents complete game state snapshots
- **Player**: Confirmed schema: (id, game_state_id, position, hole_cards, stack_size, is_hero) - player information within each game state
- **Bet**: Confirmed schema: (id, game_state_id, player_id, amount, action_type) - all-in betting actions recorded for each game state
- **BoardCards**: Confirmed schema: (id, flop1, flop2, flop3, turn, river) - community cards for each hand
- **Jackpot**: Confirmed schema: (id, game_state_id, player_id, jackpot_type, payout_amount, cards_used, triggered_at) - special payout events with qualifying card details
- **MatrixCell**: Derived from GameStates: (id, matrix_id, row_index, col_index, hand_combination) - computed aggregations from stored simulation data
- **AggregatedMetric**: Derived from GameStates: (id, cell_id, equity, jackpot_adjusted_ev, jackpot_frequency, convergence_status) - statistical measures computed from historical data

## Success Criteria

### Measurable Outcomes

- **SC-001**: All database tables (GameStates, Players, Bets, Jackpots) contain real simulation data with record counts matching actual simulation iterations
- **SC-002**: Game replay queries return chronological sequences of actual betting actions and board reveals from stored GameStates
- **SC-003**: Convergence analysis uses real historical equity progression data from GameStates, showing proper statistical convergence over time
- **SC-004**: Jackpot tables contain detected bonus events with accurate timing and frequency data from simulations
- **SC-005**: Foreign key constraints are enforced, preventing invalid data relationships in the database
- **SC-006**: System maintains performance with real data volumes: simulation processing < 30 seconds for 1K iterations, < 5 minutes for 10K iterations; data volume < 200MB per analysis session
- **SC-007**: MatrixCell computations are derived from GameStates data, with equity values matching aggregated simulation outcomes
- **SC-008**: Data validation prevents silent failures, with proper error handling and logging for storage pipeline issues
- **SC-009**: Unit tests with `MockPersistenceStrategy` verify solver logic, integration tests with `DatabasePersistenceStrategy` verify genuine data storage, and Strategy pattern enables easy switching between persistence implementations

## Assumptions

- Monte Carlo simulations can be modified to return individual outcomes without significant performance degradation
- Database schema supports the required foreign key relationships and constraints
- Storage pipeline can handle increased data volumes from real simulation capture
- Aggregation engine can be updated to work with GameStates-first data model

## Dependencies

- Existing `AllInFoldGTOSolver` implementation must be accessible for modification to accept `GameStatePersistence` strategy
- Database schema from `specs/001-normalized-db-schema` must be available and confirmed
- Simulation framework must support Strategy pattern injection of persistence behaviors
- Unit testing framework must support strategy mocking for different persistence implementations
