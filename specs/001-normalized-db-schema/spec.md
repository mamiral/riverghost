# Feature Specification: Normalized Relational Database Schema

**Feature Branch**: `001-normalized-db-schema`  
**Created**: 2026-03-15  
**Status**: Draft  
**Application**: aof_gto_browser  
**Input**: User description: "Implement a normalized relational database schema to replace the current inadequate cache/database system for the poker analysis tool. The new schema must support all-in-or-fold poker games where players either go all-in or fold preflop, with full board cards dealt for equity calculations but no post-flop betting rounds.

Key requirements:
- Use SQLite for database storage (built-in Python support, file-based, no server needed)
- Create normalized tables: Simulations, HandMatrices, MatrixCells, GameStates, Players, Bets, BoardCards, Jackpots, AggregatedMetrics
- Support 13x13 hand matrix structure with proper foreign key relationships
- Enable comprehensive game state storage including expanded player hands, betting actions, and board cards
- Include jackpot tracking for platform-specific features (e.g., GGPoker straight flush bonuses with specific card usage requirements)
- Provide aggregated metrics with jackpot-adjusted EV calculations
- Support convergence analysis through timestamped historical data
- Enable flexible queries for game replay, jackpot frequency analysis, and EV comparisons
- Ensure data integrity with foreign key constraints and ACID transactions
- Allow easy extension for future game quirks or different matrix sizes

The implementation should maintain all analytical capabilities of the original proposed 13x13 table schema while providing better data management, query flexibility, and maintenance through normalization."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Poker Simulations with Full Data Persistence (Priority: P1)

As a poker analyst, I want to run Monte Carlo simulations for all-in-or-fold games and have all game states, player hands, and outcomes stored in a normalized database so that I can analyze convergence and replay specific hands.

**Why this priority**: This is the core functionality that enables the primary use case of the poker analysis tool - running simulations and storing results for analysis.

**Independent Test**: Can be fully tested by running a simulation, verifying data is stored in the correct tables with proper relationships, and querying historical convergence data.

**Acceptance Scenarios**:

1. **Given** a 13x13 hand matrix simulation is run, **When** the simulation completes, **Then** all game states are stored with timestamps, player hands, board cards, and outcomes.
2. **Given** stored simulation data, **When** querying for convergence analysis, **Then** equity values show proper convergence over time.
3. **Given** a specific hand matchup, **When** replaying the game, **Then** all betting actions and board reveals are available chronologically.

---

### User Story 2 - Analyze Jackpot Frequencies and EV Impact (Priority: P2)

As a poker analyst, I want to track jackpot events during simulations and see how they affect expected value calculations so that I can optimize strategies for jackpot-rich games.

**Why this priority**: Jackpots are significant value drivers in modern poker platforms, and understanding their impact is crucial for accurate analysis.

**Independent Test**: Can be fully tested by simulating games with jackpot triggers, verifying jackpot events are recorded, and confirming EV calculations include jackpot payouts.

**Acceptance Scenarios**:

1. **Given** a simulation with jackpot-eligible hands, **When** a jackpot condition is met, **Then** the event is recorded with payout amount and specific cards used.
2. **Given** aggregated metrics, **When** viewing EV calculations, **Then** jackpot-adjusted EV accounts for frequency and payout amounts.
3. **Given** multiple simulations, **When** analyzing jackpot frequency, **Then** statistics show accurate occurrence rates by hand type.

---

### User Story 3 - Query and Extend Database Schema (Priority: P3)

As a developer, I want to perform complex queries across the normalized schema and easily add new tables for future game features so that the system remains maintainable and extensible.

**Why this priority**: Ensures the database design supports long-term evolution and advanced analytical queries.

**Independent Test**: Can be fully tested by executing the provided query examples and successfully adding a new table with foreign key relationships.

**Acceptance Scenarios**:

1. **Given** the database schema, **When** running complex joins for game replay, **Then** queries execute efficiently and return correct data.
2. **Given** a new game feature requirement, **When** adding a table to the schema, **Then** foreign key constraints maintain data integrity.
3. **Given** different matrix sizes, **When** querying data, **Then** the schema adapts without structural changes.

---

### Edge Cases

- What happens when simulation data exceeds SQLite file size limits?
- How does system handle corrupted database files during analysis?
- What occurs when foreign key constraints are violated during data insertion?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create and manage SQLite database with normalized tables (Simulations, HandMatrices, MatrixCells, GameStates, Players, Bets, BoardCards, Jackpots, AggregatedMetrics)
- **FR-002**: System MUST support 13x13 hand matrix structure with proper foreign key relationships
- **FR-003**: System MUST store comprehensive game state data including expanded player hands, betting actions, board cards, and timestamps
- **FR-004**: System MUST track jackpot events with payout amounts and specific cards used for jackpot qualification
- **FR-005**: System MUST provide aggregated metrics including jackpot-adjusted expected value calculations
- **FR-006**: System MUST enable convergence analysis through timestamped historical simulation data
- **FR-007**: System MUST support flexible queries for game replay, jackpot analysis, and EV comparisons
- **FR-008**: System MUST enforce data integrity with foreign key constraints and ACID transactions
- **FR-009**: System MUST allow schema extension for future game quirks without breaking existing functionality
- **FR-010**: System MUST use SQLAlchemy Python module for database abstraction to enable seamless switching between SQLite and PostgreSQL

### Key Entities *(include if feature involves data)*

- **Simulations**: Represents individual Monte Carlo simulation runs, with metadata like start/end times and parameters
- **HandMatrices**: Contains the 13x13 grid structure for each simulation, linked to Simulations
- **MatrixCells**: Individual cells in the matrix representing specific hand vs hand matchups, linked to HandMatrices
- **GameStates**: Detailed records of each simulated hand with timestamps, outcomes, and references to board cards
- **Players**: Player information including hole cards and positions within each game state
- **Bets**: All-in betting actions recorded for each game state
- **BoardCards**: Community cards (flop, turn, river) for each hand
- **Jackpots**: Special payout events triggered by specific hand combinations (extensible to support various jackpot types as they are invented by platforms)
- **AggregatedMetrics**: Computed statistics per matrix cell including equity and jackpot-adjusted EV

#### Table Definitions and Example Columns

- **Simulations**
  - id (PK)
  - name
  - start_timestamp
  - end_timestamp
  - parameters (JSON: simulation settings)

- **HandMatrices**
  - id (PK)
  - simulation_id (FK to Simulations)
  - matrix_size (e.g., 13x13)
  - created_at

- **MatrixCells**
  - id (PK)
  - matrix_id (FK to HandMatrices)
  - row_index (0-12)
  - col_index (0-12)
  - hand_combination (e.g., "AsKh vs QdJd")

- **GameStates**
  - id (PK)
  - cell_id (FK to MatrixCells)
  - timestamp
  - round ('preflop' only, since all-in-or-fold)
  - pot_size
  - board_cards (FK to BoardCards)
  - outcome (win/loss for each player)

- **Players**
  - id (PK)
  - game_state_id (FK to GameStates)
  - position
  - hole_cards (expanded hand)
  - stack_size
  - is_hero (boolean)

- **Bets**
  - id (PK)
  - game_state_id (FK to GameStates)
  - player_id (FK to Players)
  - amount
  - action_type (fold, call, raise, etc.)

- **BoardCards**
  - id (PK)
  - flop1, flop2, flop3, turn, river (card representations)

- **Jackpots**
  - id (PK)
  - game_state_id (FK to GameStates)
  - player_id (FK to Players)
  - jackpot_type (e.g., 'straight_flush_both_hole_cards', extensible for future jackpot types)
  - payout_amount
  - cards_used (JSON: which specific cards formed the jackpot hand)
  - triggered_at

- **AggregatedMetrics**
  - id (PK)
  - cell_id (FK to MatrixCells)
  - last_updated
  - equity (standard win probability)
  - jackpot_adjusted_ev (expected value including jackpot payouts)
  - jackpot_frequency (how often jackpots occur in simulations)
  - avg_jackpot_payout (average jackpot amount when triggered)
  - convergence_status

#### Query Examples
- **Get all game states for a specific cell**: `SELECT * FROM GameStates WHERE cell_id = ?`
- **Aggregate equity across matrix**: `SELECT AVG(equity) FROM AggregatedMetrics WHERE matrix_id = ?`
- **Historical convergence**: `SELECT timestamp, equity FROM GameStates gs JOIN MatrixCells mc ON gs.cell_id = mc.id WHERE mc.row_index = 0 AND mc.col_index = 0 ORDER BY timestamp`
- **Game replay for cell '72o'**: `SELECT gs.*, p.hole_cards, p.position, b.amount, b.action_type, bc.flop1, bc.flop2, bc.flop3, bc.turn, bc.river FROM GameStates gs JOIN MatrixCells mc ON gs.cell_id = mc.id LEFT JOIN Players p ON gs.id = p.game_state_id LEFT JOIN Bets b ON gs.id = b.game_state_id LEFT JOIN BoardCards bc ON gs.board_cards = bc.id WHERE mc.hand_combination LIKE '%72o%' ORDER BY gs.timestamp ASC`
- **Jackpot frequency analysis**: `SELECT jackpot_type, COUNT(*) as frequency, AVG(payout_amount) as avg_payout FROM Jackpots GROUP BY jackpot_type ORDER BY frequency DESC`
- **EV with jackpot adjustment**: `SELECT mc.hand_combination, am.equity, am.jackpot_adjusted_ev, am.jackpot_frequency FROM AggregatedMetrics am JOIN MatrixCells mc ON am.cell_id = mc.id ORDER BY am.jackpot_adjusted_ev DESC`

### Measurable Outcomes

- **SC-001**: Simulations complete and store data in under 10% additional time compared to current system
- **SC-002**: Database handles up to 10,000 game states (max per simulation) with query response times under 100ms for up to 16 concurrent simulations
- **SC-003**: Jackpot-adjusted EV calculations show accurate results within 0.1% of manual verification
- **SC-004**: New database will be created without requiring data migration from existing systems
- **SC-005**: 95% of complex analytical queries execute successfully without performance degradation

#### Database Compatibility
This schema is fully compatible with **SQLite**, which is ideal for this application:

- **Built-in Support**: SQLite is included with Python's standard library (`sqlite3` module), requiring no additional server setup.
- **File-Based**: Single database file that's easy to backup, version control, and distribute.
- **Feature Support**: 
  - Foreign key constraints (enabled with `PRAGMA foreign_keys = ON;`)
  - JSON storage for simulation parameters
  - Complex joins and aggregations
  - ACID transactions
- **Performance**: Sufficient for simulation data storage and analysis queries. For very large datasets (>100GB), PostgreSQL might be preferable, but SQLite handles millions of rows well.
- **Concurrency**: Read-heavy workloads (analysis) work fine; write-heavy (during simulations) may benefit from batching.

**SQLAlchemy Abstraction**: The system MUST use SQLAlchemy for database operations to ensure seamless migration to PostgreSQL or other databases in the future without code changes.

**PostgreSQL Alternative**: If the dataset grows extremely large or requires advanced features (full-text search, advanced JSON queries, or concurrent multi-user access), PostgreSQL provides better scalability. However, it requires server setup and management, which adds complexity for a local analysis tool.
