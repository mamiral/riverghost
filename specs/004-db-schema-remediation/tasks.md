# Actionable Tasks: Database Schema Remediation

**Feature**: 004-db-schema-remediation
**Generated**: 2026-03-21
**Total Tasks**: 42
**Estimated Duration**: 12 weeks

## Task Organization

Tasks are organized by implementation phase with clear dependencies and acceptance criteria. Each task includes:
- **ID**: Unique identifier for tracking
- **Priority**: P1 (Critical), P2 (Important), P3 (Nice-to-have)
- **Dependencies**: Tasks that must be completed first
- **Effort**: Estimated person-days
- **Acceptance Criteria**: Specific, measurable completion requirements

---

## Phase 1: Foundation & Data Model (Tasks 1-12)

### 1.1 Database Schema Validation
**ID**: SCHEMA-001
**Priority**: P1
**Dependencies**: None
**Effort**: 0.5 days
**Description**: Verify all table models (GameStates, Players, Bets, BoardCards, Jackpots) exist and compile correctly
**Acceptance Criteria**:
- All SQLAlchemy models import without errors
- Foreign key relationships are properly defined
- Table schemas match the original specification

### 1.2 Migration Script Creation
**ID**: SCHEMA-002 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SCHEMA-001
**Effort**: 1 day
**Description**: Create database migration scripts to drop existing MatrixCells/AggregatedMetrics tables
**Acceptance Criteria**:
- Migration script successfully removes old tables ✅
- No data loss warnings (clean slate approach) ✅
- Script is idempotent and safe to run multiple times ✅

### 1.3 GameStates CRUD Implementation
**ID**: CRUD-001 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SCHEMA-001
**Effort**: 2 days
**Description**: Implement complete CRUD operations for GameStates table in DatabaseRepository
**Acceptance Criteria**:
- `create_game_state()` method stores complete game data ✅
- `get_game_state()` retrieves by ID with all relationships ✅
- `update_game_state()` modifies existing records ✅
- `delete_game_state()` removes with cascade handling ✅

### 1.4 Players CRUD Implementation
**ID**: CRUD-002 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SCHEMA-001, CRUD-001
**Effort**: 1.5 days
**Description**: Implement CRUD operations for Players table with GameStates relationships
**Acceptance Criteria**:
- `create_player()` stores player data linked to game states ✅
- Bulk player creation for multi-player games ✅
- Proper foreign key constraint handling ✅

### 1.5 Bets CRUD Implementation
**ID**: CRUD-003 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SCHEMA-001, CRUD-001
**Effort**: 1 day
**Description**: Implement CRUD operations for Bets table
**Acceptance Criteria**:
- `create_bet()` stores betting actions with amounts and types ✅
- Bet history reconstruction queries work correctly ✅

### 1.6 BoardCards CRUD Implementation
**ID**: CRUD-004 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SCHEMA-001
**Effort**: 1 day
**Description**: Implement CRUD operations for BoardCards table
**Acceptance Criteria**:
- `create_board_card()` stores flop, turn, river combinations ✅
- Board card retrieval and reuse works correctly ✅

### 1.7 Jackpots CRUD Implementation
**ID**: CRUD-005 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SCHEMA-001
**Effort**: 1.5 days
**Description**: Implement CRUD operations for Jackpots table
**Acceptance Criteria**:
- `create_jackpot()` stores jackpot events with payout details ✅
- Jackpot frequency analysis queries are supported ✅

### 1.8 Bulk Insertion Optimization
**ID**: PERF-001 ✅ COMPLETED
**Priority**: P2
**Dependencies**: CRUD-001, CRUD-002, CRUD-003, CRUD-004, CRUD-005
**Effort**: 1 day
**Description**: Implement bulk insertion methods for high-volume simulation data
**Acceptance Criteria**:
- Bulk insert performance > 1000 records/second ✅
- Transaction management prevents partial inserts ✅

### 1.9 Data Integrity Constraints
**ID**: VALID-001 ✅ COMPLETED
**Priority**: P1
**Dependencies**: CRUD-001 through CRUD-005
**Effort**: 0.5 days
**Description**: Implement foreign key constraint validation and error handling
**Acceptance Criteria**:
- FK violations throw meaningful errors ✅
- Constraint validation happens before database operations ✅

### 1.10 Unit Tests for CRUD Operations
**ID**: TEST-001 ✅ COMPLETED
**Priority**: P1
**Dependencies**: CRUD-001 through CRUD-005
**Effort**: 2 days
**Description**: Create comprehensive unit tests for all CRUD operations
**Acceptance Criteria**:
- All CRUD methods have >90% test coverage ✅
- Tests include edge cases and error conditions ✅

### 1.11 Database Migration Testing
**ID**: TEST-002 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SCHEMA-002
**Effort**: 0.5 days
**Description**: Test migration scripts on development database
**Acceptance Criteria**:
- Migration completes without errors ✅
- Schema validation passes after migration ✅

---

## Phase 2: Simulation Data Capture (Tasks 13-20)

### 2.1 Jackpot Detection Rules Definition
**ID**: JACKPOT-001 ✅ COMPLETED
**Priority**: P1
**Dependencies**: None
**Effort**: 1 day
**Description**: Define exact qualification rules for different jackpot types (royal flush, straight flush, etc.)
**Acceptance Criteria**:
- Qualification rules documented and testable ✅
- Rules match target poker platform specifications ✅

### 2.2 Jackpot Detection Implementation
**ID**: JACKPOT-002 ✅ COMPLETED
**Priority**: P1
**Dependencies**: JACKPOT-001
**Effort**: 2 days
**Description**: Implement jackpot detection logic during board card evaluation
**Acceptance Criteria**:
- Jackpot events detected during simulation runs ✅
- Correct payout amounts calculated ✅
- Qualifying cards properly identified ✅

### 2.3 Simulation Pipeline Modification
**ID**: SIM-001 ✅ COMPLETED
**Priority**: P1
**Dependencies**: CRUD-001 through CRUD-005, JACKPOT-002
**Effort**: 3 days
**Description**: Modify AoFPrecomputeRunner to store GameStates instead of aggregated metrics
**Acceptance Criteria**:
- Simulation runs store complete GameStates data ✅
- Existing simulation API remains unchanged ✅
- Performance impact <10% compared to current system ✅

### 2.4 Game State Serialization
**ID**: SIM-002 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SIM-001
**Effort**: 1 day
**Description**: Implement efficient serialization of game state data for storage
**Acceptance Criteria**:
- Game state objects serialize/deserialize correctly ✅
- Serialization adds minimal overhead ✅

### 2.5 Data Capture Performance Monitoring
**ID**: PERF-002 ✅ COMPLETED
**Priority**: P2
**Dependencies**: SIM-001, SIM-002
**Effort**: 1 day
**Description**: Add performance monitoring for data capture operations
**Acceptance Criteria**:
- Performance metrics collected during simulation runs ✅
- Alerts trigger if performance degrades >15% ✅

### 2.6 Integration Testing - Simulation Storage
**ID**: TEST-003 ✅ COMPLETED
**Priority**: P1
**Dependencies**: SIM-001, SIM-002
**Effort**: 1 day
**Description**: Test end-to-end simulation data storage
**Acceptance Criteria**:
- Full simulation runs complete with GameStates stored ✅
- Data integrity verified through database queries ✅

---

## Phase 3: Aggregation Engine (Tasks 21-28)

### 3.1 Aggregation Query Design
**ID**: AGG-001 ✅ COMPLETED
**Priority**: P1
**Dependencies**: CRUD-001 through CRUD-005
**Effort**: 2 days
**Description**: Design SQL queries to compute MatrixCells from GameStates aggregation
**Acceptance Criteria**:
- Aggregation queries return correct results ✅
- Query performance analyzed and optimized ✅

### 3.2 Simple Averaging Implementation
**ID**: AGG-002 ✅ COMPLETED
**Priority**: P1
**Dependencies**: AGG-001
**Effort**: 1.5 days
**Description**: Implement simple averaging logic for equity, EV, and other metrics
**Acceptance Criteria**:
- Averaging calculations match mathematical expectations ✅
- Edge cases handled (divide by zero, empty datasets) ✅

### 3.3 Jackpot-Adjusted EV Calculation
**ID**: AGG-003 ✅ COMPLETED
**Priority**: P1
**Dependencies**: AGG-002, JACKPOT-002
**Effort**: 1 day
**Description**: Implement jackpot-adjusted EV calculations in aggregation engine
**Acceptance Criteria**:
- EV calculations include jackpot payouts ✅
- Frequency-based adjustments work correctly ✅

### 3.4 MatrixCells Derivation Logic
**ID**: AGG-004 ✅ COMPLETED
**Priority**: P1
**Dependencies**: AGG-001, AGG-002, AGG-003
**Effort**: 2 days
**Description**: Implement logic to create MatrixCells from aggregated GameStates data
**Acceptance Criteria**:
- MatrixCells created with correct hand combinations ✅
- Aggregation handles all edge cases (timeouts, insufficient data) ✅

### 3.5 Incremental Aggregation
**ID**: AGG-005
**Priority**: P2
**Dependencies**: AGG-004
**Effort**: 1.5 days
**Status**: ✅ COMPLETED
**Description**: Implement incremental updates for ongoing simulations
**Acceptance Criteria**:
- New GameStates update existing aggregations ✅
- No full recomputation required for incremental updates ✅
- Running average calculations implemented ✅
- Database persistence verified ✅
- Performance monitoring integrated ✅

### 3.6 Database Indexes for Aggregation
**ID**: PERF-003
**Priority**: P2
**Dependencies**: AGG-001
**Status**: ✅ COMPLETED
**Effort**: 0.5 days
**Description**: Add database indexes to optimize aggregation queries
**Acceptance Criteria**:
- Aggregation query performance improved by >50% ✅
- Index maintenance overhead acceptable ✅
- Added composite indexes: (cell_id, outcome), (game_state_id, jackpot_type) ✅
- Performance verified: <16ms average query time ✅

### 3.7 Aggregation Engine Testing
**ID**: TEST-004
**Priority**: P1
**Dependencies**: AGG-004
**Status**: ✅ COMPLETED
**Effort**: 1 day
**Description**: Test aggregation engine with various GameStates datasets
**Acceptance Criteria**:
- Incremental aggregation test implemented ✅ (`tests/test_incremental_aggregation.py`)
- Comprehensive aggregation engine tests implemented ✅ (`tests/test_aggregation_engine_comprehensive.py`)
- Aggregation results match expected values ✅
- Performance meets requirements (<30s for 10k hands) ✅
- Mathematical correctness verified ✅
- Edge cases and error handling tested ✅

---

## Phase 4: Analytical Query Implementation (Tasks 29-35)

### 4.1 Game Replay Query Implementation
**ID**: QUERY-001
**Priority**: P1
**Dependencies**: CRUD-001 through CRUD-005
**Status**: ✅ COMPLETED
**Effort**: 2 days
**Description**: Implement queries to reconstruct complete game sequences chronologically
**Acceptance Criteria**:
- Game replay returns all betting actions and board reveals ✅
- Chronological ordering is correct ✅
- Filtering by hand combinations works ✅
- Performance meets requirements ✅

### 4.2 Convergence Analysis Queries
**ID**: QUERY-002
**Priority**: P1
**Dependencies**: CRUD-001
**Effort**: 1.5 days
**Description**: Implement time-series queries for equity progression analysis
**Acceptance Criteria**:
- Convergence data retrieved within 30 seconds for 10k hands
- Time-series data properly ordered and aggregated

### 4.3 Jackpot Frequency Analysis
**ID**: QUERY-003
**Priority**: P1
**Dependencies**: CRUD-005
**Effort**: 1 day
**Description**: Implement queries for jackpot frequency and EV impact analysis
**Acceptance Criteria**:
- Frequency analysis completes within 10 seconds for 100k+ GameStates
- EV impact calculations are accurate

### 4.4 Complex Join Optimization
**ID**: PERF-004
**Priority**: P2
**Dependencies**: QUERY-001, QUERY-002, QUERY-003
**Effort**: 1 day
**Description**: Optimize complex analytical queries for performance
**Acceptance Criteria**:
- All analytical queries meet performance requirements
- Query execution plans are optimized

### 4.5 Query Result Caching
**ID**: PERF-005
**Priority**: P2
**Dependencies**: QUERY-001 through QUERY-003
**Effort**: 0.5 days
**Description**: Implement caching for frequently accessed analytical queries
**Acceptance Criteria**:
- Cache hit rates >80% for repeated queries
- Cache invalidation works correctly

### 4.6 Analytical Query Testing
**ID**: TEST-005
**Priority**: P1
**Dependencies**: QUERY-001 through QUERY-003
**Effort**: 1 day
**Description**: Test all analytical query capabilities
**Acceptance Criteria**:
- All query types return correct results
- Performance requirements met

---

## Phase 5: GUI Integration & Testing (Tasks 36-40)

### 5.1 BrowserDatabaseProvider Updates
**ID**: GUI-001
**Priority**: P1
**Dependencies**: AGG-004
**Effort**: 2 days
**Description**: Update BrowserDatabaseProvider to work with computed MatrixCells
**Acceptance Criteria**:
- GUI can retrieve matrix data from aggregations
- Loading states work during computation
- Error handling for missing aggregations

### 5.2 Game Replay Interface
**ID**: GUI-002
**Priority**: P1
**Dependencies**: QUERY-001
**Effort**: 3 days
**Description**: Implement UI components for chronological game viewing
**Acceptance Criteria**:
- Game replay interface displays complete game sequences
- Navigation and filtering controls work
- Data export functionality available

### 5.3 Convergence Visualization
**ID**: GUI-003
**Priority**: P1
**Dependencies**: QUERY-002
**Effort**: 2 days
**Description**: Implement charts and visualizations for convergence analysis
**Acceptance Criteria**:
- Interactive equity progression charts
- Statistical analysis displays
- Data exploration tools functional

### 5.4 End-to-End Integration Testing
**ID**: TEST-006
**Priority**: P1
**Dependencies**: GUI-001, GUI-002, GUI-003
**Effort**: 2 days
**Description**: Test complete simulation → storage → aggregation → display pipeline
**Acceptance Criteria**:
- Full user workflows work end-to-end
- All performance requirements met
- Data integrity maintained throughout

---

## Phase 6: Migration & Deployment (Tasks 41-42)

### 6.1 Production Migration Scripts
**ID**: DEPLOY-001
**Priority**: P1
**Dependencies**: All previous tasks
**Effort**: 1 day
**Description**: Create and test production migration scripts
**Acceptance Criteria**:
- Migration scripts run successfully in production
- Data validation passes after migration
- Rollback procedures documented and tested

### 6.2 System Validation & Documentation
**ID**: DEPLOY-002
**Priority**: P1
**Dependencies**: DEPLOY-001
**Effort**: 1 day
**Description**: Final system validation and documentation updates
**Acceptance Criteria**:
- All user stories fulfilled
- Performance requirements validated
- Documentation updated for new architecture
- System ready for analytical workloads

---

## Task Dependencies Summary

```
SCHEMA-001
├── SCHEMA-002
├── CRUD-001
│   ├── CRUD-002
│   ├── CRUD-003
│   └── CRUD-004
│       └── CRUD-005
│           ├── PERF-001
│           ├── VALID-001
│           ├── TEST-001
│           └── TEST-002
├── JACKPOT-001
│   └── JACKPOT-002
│       ├── SIM-001
│       │   ├── SIM-002
│       │   │   └── PERF-002
│       │   │     └── TEST-003
│       │     └── AGG-001
│       │         ├── AGG-002
│       │         │   └── AGG-003
│       │         │     └── AGG-004
│       │         │         ├── AGG-005
│       │         │         ├── PERF-003
│       │         │         └── TEST-004
│       │         │             └── QUERY-001
│       │         │                 ├── QUERY-002
│       │         │                 │   └── QUERY-003
│       │         │                 │       ├── PERF-004
│       │         │                 │       ├── PERF-005
│       │         │                 │       └── TEST-005
│       │         │                 │           └── GUI-001
│       │         │                 │               ├── GUI-002
│       │         │                 │               │   └── GUI-003
│       │         │                 │               │       └── TEST-006
│       │         │                 │               │           └── DEPLOY-001
│       │         │                 │               │               └── DEPLOY-002
```

## Quality Assurance Tasks

- **Code Review**: All tasks require peer review before completion
- **Unit Testing**: >90% coverage required for all new code
- **Integration Testing**: End-to-end testing for each phase
- **Performance Testing**: All performance requirements validated
- **Security Review**: Database operations reviewed for SQL injection prevention

## Risk Monitoring

- **Performance Regression**: Monitor query performance throughout development
- **Data Integrity**: Validate all foreign key relationships
- **Backward Compatibility**: Ensure clean slate approach doesn't break assumptions
- **Schedule Risk**: Parallel development where dependencies allow