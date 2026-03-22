# Implementation Plan: Database Schema Remediation

**Feature**: 004-db-schema-remediation
**Created**: 2026-03-21
**Status**: Planning Complete

## Executive Summary

This implementation plan addresses the critical architectural violation where MatrixCells are incorrectly treated as primary data instead of being derived from GameStates. The remediation restores the intended GameStates-first architecture while implementing comprehensive analytical capabilities.

**Key Decisions from Clarification:**
- Data aggregation: Simple averaging per matrix cell
- Migration strategy: Clean slate (drop existing MatrixCells, recompute from scratch)
- Backward compatibility: None during transition (GUI broken until completion)

**Scope**: Major architectural refactoring affecting data persistence, GUI integration, and analytical capabilities.

---

## Phase 1: Foundation & Data Model (Week 1-2)

### Objectives
Establish the corrected data model and basic CRUD operations for the GameStates-first architecture.

### Deliverables
- Complete GameStates, Players, Bets, BoardCards, Jackpots table implementations
- DatabaseRepository CRUD methods for all entities
- Data integrity constraints and relationships
- Migration scripts to drop existing MatrixCells/AggregatedMetrics

### Key Tasks
1. **Database Schema Updates**
   - Verify all table models exist and are correctly defined
   - Add any missing foreign key constraints
   - Create database migration scripts for clean slate approach

2. **CRUD Operations Implementation**
   - Implement `create_game_state()` with full game data
   - Implement `create_player()`, `create_bet()`, `create_board_card()`
   - Implement `create_jackpot()` for bonus payout tracking
   - Add bulk insertion methods for performance

3. **Data Integrity Validation**
   - Implement foreign key constraint validation
   - Add transaction management for data consistency
   - Create data validation helpers

### Success Criteria
- All table models compile without errors
- CRUD operations can create/read/update/delete all entity types
- Foreign key relationships are properly enforced
- Migration scripts successfully drop old data structures

### Risks & Mitigations
- **Risk**: Schema changes break existing functionality
- **Mitigation**: Implement in isolated database transactions, rollback on failure

---

## Phase 2: Simulation Data Capture (Week 3-4)

### Objectives
Modify the simulation pipeline to capture and store complete GameStates instead of aggregated metrics.

### Deliverables
- Modified AoFPrecomputeRunner to store individual game states
- Jackpot detection logic during simulation
- Integration with existing simulation framework
- Performance monitoring for data capture overhead

### Key Tasks
1. **Simulation Pipeline Modification**
   - Modify `AoFPrecomputeRunner.compute_gui_cell()` to store GameStates
   - Update simulation result processing to capture complete game data
   - Implement game state serialization and bulk storage

2. **Jackpot Detection Implementation**
   - Define jackpot qualification rules (royal flush, straight flush, etc.)
   - Implement jackpot detection during board card evaluation
   - Store jackpot events with payout amounts and qualifying cards

3. **Data Capture Performance**
   - Optimize bulk insertion for high-volume simulation data
   - Implement batching for large simulation runs
   - Add progress tracking for long-running simulations

### Success Criteria
- Simulations successfully store GameStates in database
- Jackpot events are detected and recorded during simulation
- Data capture adds minimal overhead (<10% performance impact)
- All simulation types (GUI and programmatic) work with new data flow

### Dependencies
- Phase 1 CRUD operations must be complete
- Database schema must support the new data volume

---

## Phase 3: Aggregation Engine (Week 5-6)

### Objectives
Implement the computation engine that derives MatrixCells and AggregatedMetrics from stored GameStates.

### Deliverables
- MatrixCells computation from GameStates aggregation
- AggregatedMetrics calculation with jackpot-adjusted EV
- Background aggregation processing
- Caching layer for computed results

### Key Tasks
1. **Aggregation Logic Implementation**
   - Create aggregation queries to compute MatrixCells from GameStates
   - Implement simple averaging for equity, EV, and other metrics
   - Add jackpot-adjusted EV calculations

2. **MatrixCells Derivation**
   - Implement logic to group GameStates by hand combinations
   - Create MatrixCells records from aggregated GameStates data
   - Handle edge cases (insufficient samples, timeouts, etc.)

3. **Performance Optimization**
   - Implement incremental aggregation for ongoing simulations
   - Add database indexes for efficient aggregation queries
   - Create materialized views for frequently accessed aggregations

### Success Criteria
- MatrixCells can be computed from GameStates data
- AggregatedMetrics include jackpot-adjusted calculations
- Aggregation completes within performance requirements (<30s for 10k hands)
- Results are consistent with simple averaging approach

### Dependencies
- Phase 2 must provide GameStates data for aggregation
- CRUD operations must support bulk aggregation operations

---

## Phase 4: Analytical Query Implementation (Week 7-8)

### Objectives
Implement the advanced analytical capabilities promised by the original specification.

### Deliverables
- Game replay functionality with chronological data
- Temporal convergence analysis queries
- Jackpot frequency analysis capabilities
- Complex join query optimization

### Key Tasks
1. **Game Replay Implementation**
   - Create queries to reconstruct complete game sequences
   - Implement chronological ordering of betting actions and board reveals
   - Add filtering capabilities for specific hand combinations

2. **Convergence Analysis**
   - Implement time-series queries for equity progression
   - Create aggregation functions for convergence metrics
   - Add visualization data preparation

3. **Jackpot Analysis**
   - Implement frequency analysis queries
   - Create EV impact calculations from jackpot data
   - Add statistical analysis functions

4. **Query Performance**
   - Optimize complex joins for analytical queries
   - Implement query result caching
   - Add database indexes for analytical workloads

### Success Criteria
- Game replay queries return complete chronological data
- Convergence analysis completes within 30 seconds for 10k hands
- Jackpot frequency queries complete within 10 seconds for 100k+ GameStates
- All complex analytical queries execute without errors

### Dependencies
- Phase 3 aggregation must provide MatrixCells data
- Database must contain sufficient GameStates for testing

---

## Phase 5: GUI Integration & Testing (Week 9-10)

### Objectives
Integrate the corrected data architecture with the GUI and ensure full functionality.

### Deliverables
- Updated GUI components to work with derived MatrixCells
- Game replay interface implementation
- Convergence analysis visualization
- Comprehensive test suite

### Key Tasks
1. **GUI Data Source Updates**
   - Modify BrowserDatabaseProvider to work with computed MatrixCells
   - Update data fetching logic for the new architecture
   - Implement loading states during aggregation

2. **Game Replay Interface**
   - Create UI components for chronological game viewing
   - Implement filtering and navigation controls
   - Add export capabilities for game data

3. **Convergence Visualization**
   - Implement charts for equity progression over time
   - Add statistical analysis displays
   - Create interactive exploration tools

4. **Integration Testing**
   - End-to-end testing of simulation → storage → aggregation → display
   - Performance testing against success criteria
   - Compatibility testing with existing workflows

### Success Criteria
- GUI displays matrix data from computed aggregations
- Game replay interface shows complete chronological data
- Convergence analysis provides interactive visualizations
- All performance requirements are met
- Existing user workflows are preserved (post-migration)

### Dependencies
- All previous phases must be complete
- Aggregation engine must be stable and performant

---

## Phase 6: Migration & Deployment (Week 11-12)

### Objectives
Execute the clean slate migration and deploy the completed system.

### Deliverables
- Production migration scripts
- Data validation and integrity checks
- Rollback procedures
- Documentation updates

### Key Tasks
1. **Migration Execution**
   - Run clean slate migration (drop old data, recreate schema)
   - Execute full system validation
   - Perform performance benchmarking

2. **Data Validation**
   - Verify all GameStates are properly stored
   - Confirm MatrixCells are correctly computed
   - Validate jackpot detection and storage

3. **System Integration**
   - Deploy to production environment
   - Execute full regression test suite
   - Validate all user scenarios work end-to-end

4. **Documentation Updates**
   - Update architecture documentation
   - Create operational procedures for new system
   - Document analytical query capabilities

### Success Criteria
- Migration completes without data loss (clean slate approach)
- All user stories are fulfilled
- Performance requirements are met in production
- System is ready for analytical workloads

### Dependencies
- All development phases must be complete and tested
- Production environment must be prepared

---

## Research & Unknowns

### Technical Research Required
1. **Bulk Insertion Performance**: Research optimal batch sizes for GameStates insertion during high-volume simulations
2. **Aggregation Query Optimization**: Investigate most efficient SQL patterns for computing MatrixCells from GameStates
3. **Jackpot Detection Rules**: Research exact qualification rules for different jackpot types in target poker platforms

### Business Research Required
1. **Performance Expectations**: Validate 30s/10s performance requirements with actual user workflows
2. **Data Volume Estimates**: Determine typical GameStates volume for user simulation scenarios

### Risk Research
1. **Migration Rollback**: Develop procedures for reverting to old architecture if issues arise
2. **Data Integrity**: Research validation methods for ensuring GameStates consistency

---

## Quality Assurance Strategy

### Testing Approach
- **Unit Tests**: CRUD operations, aggregation logic, jackpot detection
- **Integration Tests**: End-to-end simulation → storage → aggregation → display
- **Performance Tests**: Query performance against success criteria
- **Regression Tests**: Ensure existing functionality still works

### Quality Gates
- **Phase Exit Criteria**: Each phase must pass all defined success criteria
- **Integration Testing**: Full system testing before Phase 5 GUI integration
- **Performance Validation**: All timing requirements verified before deployment

---

## Resource Requirements

### Team Composition
- **Lead Architect**: Database schema design and architectural oversight
- **Backend Developer**: CRUD operations, aggregation engine, query optimization
- **Frontend Developer**: GUI integration, game replay interface
- **QA Engineer**: Test automation, performance validation

### Infrastructure Needs
- **Development Database**: SQLite instance for development testing
- **Performance Testing**: Dedicated environment for load testing
- **Production Database**: Properly configured for analytical workloads

---

## Success Metrics

### Technical Metrics
- Query performance within specified time limits
- Data integrity maintained (no FK violations)
- System availability during and after migration

### Business Metrics
- All user stories implemented and tested
- Analytical capabilities exceed original specification
- System ready for advanced poker analysis workflows

---

## Risk Mitigation

### High-Risk Items
1. **Performance Degradation**: Monitored through performance testing phases
2. **Data Loss During Migration**: Mitigated by clean slate approach (no existing data to lose)
3. **GUI Compatibility**: Tested extensively in Phase 5

### Contingency Plans
- **Performance Issues**: Implement query optimization and caching
- **Data Issues**: Comprehensive validation and rollback procedures
- **Schedule Slippage**: Parallel development of phases where possible

---

## Conclusion

This implementation plan provides a structured approach to correcting the critical architectural violation in the database schema. The phased approach ensures each component is thoroughly tested before integration, minimizing risk and ensuring the final system meets all analytical requirements of the original specification.

**Total Timeline**: 12 weeks
**Major Milestones**: 6 phase completions
**Risk Level**: Medium (architectural change, but clean slate migration reduces complexity)