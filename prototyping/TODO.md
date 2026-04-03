# Phase 1.3 Prototyping - Todo List

## Database Layer

- [x] **Create test queries to verify the data** ✓ Complete (18/18 tests passing)
  - Write SQL queries to validate relational integrity (FK constraints, cascades, constraints) ✓
  - Test convergence tracking by timestamp ✓
  - Verify jackpot frequency aggregations ✓
  - Confirm game replay queries work correctly with 2-4 player all-in games ✓

- [x] **Build views/reports from this data** ✓ Complete (4 views created)
  - Create SQL views for matrix display (equity rankings, EV displays) ✓
  - Build convergence analysis view (equity over time per hand) ✓
  - Build jackpot frequency report view (frequency % and payout impact) ✓
  - Build game replay view (full hand history with all actions) ✓

- [x] **Set up SQLAlchemy ORM models** ✓ Complete (9 models + 5 repositories)
  - Create ORM models for all 9 tables (Simulation, HandMatrix, MatrixCell, etc.) ✓
  - Define relationships (foreign keys, backrefs, cascade deletes) ✓
  - Add validators and computed properties ✓
  - Create Repository class for data access patterns (CRUD + complex queries) ✓

- [ ] **Create analysis services**
  - EquityService: Calculate equity from GameStates, handle convergence
  - JackpotService: Analyze jackpot frequency and EV impact
  - ConvergenceService: Track stability over time for quality assessment
  - ReplayService: Reconstruct full hand history from database records