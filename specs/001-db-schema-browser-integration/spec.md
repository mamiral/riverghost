# Feature Specification: Database Schema Browser Integration

**Feature Branch**: `001-db-schema-browser-integration`  
**Created**: 2026-03-17  
**Status**: Draft  
**Application**: aof_gto_browser  
## Clarifications

### Session 2026-03-17

- Q: What are the acceptable query response times for browsing GTO strategy matrices? → A: <500ms - This provides a responsive real-time browsing experience suitable for interactive strategy analysis.
- Q: What is the expected concurrent user load for the browser? → A: Up to 10 concurrent users - This reflects the typical usage pattern of a specialized poker analysis tool rather than a high-traffic web application.
- Q: How does the browser's PositionContext map to database storage? → A: PositionContext (UTG, BTN, SB, BB) maps to position metadata stored in AggregatedMetrics table or derived from simulation parameters - This ensures position-specific GTO data can be efficiently queried and filtered.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse GTO Solutions with Persistent Data Storage (Priority: P1)

As a poker analyst, I want to browse all-in-or-fold GTO strategy matrices for different positions and actions, with all data stored in a normalized database that supports advanced analysis features.

**Why this priority**: This is the core functionality that enables the primary use case of the poker analysis tool - browsing GTO solutions with reliable data persistence and advanced analytical capabilities.

**Independent Test**: Can be fully tested by opening the browser, selecting positions and actions, and verifying that strategy matrices are displayed correctly with data retrieved from the normalized database.

**Acceptance Scenarios**:

1. **Given** the aof_gto_browser is open, **When** I select a position (UTG, BTN, SB, BB), **Then** the strategy matrix displays GTO data retrieved from the normalized database tables.
2. **Given** a position is selected, **When** I toggle between fold and all-in actions, **Then** the matrix updates to show the appropriate strategy values from the database.
3. **Given** position and action are selected, **When** I choose different metrics (win/lose probability, EV, equity, EQR), **Then** the matrix displays the corresponding values stored in the AggregatedMetrics table.

---

### User Story 2 - Analyze Convergence and Jackpot Impacts (Priority: P2)

As a poker analyst, I want to analyze how GTO solutions converge over multiple simulations and understand the impact of jackpots on expected value calculations.

**Why this priority**: Advanced analytical features like convergence analysis and jackpot-adjusted EV are key differentiators that provide deeper insights into poker strategy.

**Independent Test**: Can be fully tested by running multiple simulations, storing results in the database, and querying convergence metrics and jackpot-adjusted calculations.

**Acceptance Scenarios**:

1. **Given** multiple simulation runs stored in the database, **When** I query for convergence analysis, **Then** I can see how equity values stabilize over time across different matrix cells.
2. **Given** simulations with jackpot events, **When** I view EV calculations, **Then** the values account for jackpot frequencies and payout amounts from the Jackpots table.
3. **Given** aggregated metrics, **When** I analyze jackpot impact, **Then** I can compare standard equity vs jackpot-adjusted EV for different hand combinations.

---

### User Story 3 - Query and Extend Integrated Database System (Priority: P3)

As a developer, I want to perform complex queries across the integrated database schema and easily extend it for future game features while maintaining data integrity.

**Why this priority**: Ensures the integrated system remains maintainable, queryable, and extensible for future poker analysis features.

**Independent Test**: Can be fully tested by executing complex SQL joins across the normalized tables and successfully adding new columns or tables that maintain referential integrity.

**Acceptance Scenarios**:

1. **Given** the integrated database schema, **When** I perform complex queries joining Simulations, MatrixCells, and AggregatedMetrics, **Then** queries execute efficiently and return correct GTO strategy data.
2. **Given** a new analytical requirement, **When** I add fields to the AggregatedMetrics table, **Then** foreign key constraints maintain data integrity.
3. **Given** different matrix sizes or game variants, **When** I query data, **Then** the schema adapts without requiring structural changes to the browser application.

---

### Edge Cases

- What happens when the database connection fails during browser startup?
- How does the system handle corrupted or missing data in the AggregatedMetrics table?
- What occurs when foreign key constraints are violated during data updates?
- How does the browser behave when no GTO data exists for a selected position/action/metric combination?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The aof_gto_browser application MUST use the normalized relational database schema from 001-normalized-db-schema instead of the AoFScenarioCacheStore and AggregationService cache system.
- **FR-002**: The browser MUST map its data model (PositionContext, ActionContext, MetricType, HandKey, StrategyCellMetricValue) to the normalized schema's tables (AggregatedMetrics, MatrixCells, etc.).
- **FR-003**: The browser MUST retrieve GTO strategy matrices from the AggregatedMetrics table filtered by position, action, and metric contexts.
- **FR-004**: The browser MUST maintain all existing user interface functionality for position selection, action toggling, and metric switching.
- **FR-005**: The browser MUST support advanced analytical features including convergence analysis using timestamped simulation data.
- **FR-006**: The browser MUST display jackpot-adjusted EV calculations when available in the AggregatedMetrics table.
- **FR-007**: The system MUST enforce data integrity through foreign key constraints and ACID transactions.
- **FR-008**: The browser MUST handle database connection failures gracefully with appropriate error messages.
- **FR-009**: The integrated system MUST support efficient queries for real-time matrix browsing without performance degradation.
- **FR-010**: The database schema MUST be extensible to support future game features and matrix sizes without breaking the browser functionality.

### Key Entities *(include if feature involves data)*

- **StrategyCellMetricValue**: Maps to AggregatedMetrics table, stores displayable GTO values for specific hand/position/action/metric combinations
- **PositionContext**: Maps to position metadata in AggregatedMetrics table or derived from simulation parameters, enables position-specific GTO data filtering
- **ActionContext**: Query filter for fold/all-in actions, mapped to simulation parameters or aggregated data
- **MetricType**: Determines which field from AggregatedMetrics to display (equity, jackpot_adjusted_ev, etc.)
- **HandKey**: Maps to MatrixCells table via row_index/col_index for specific hand combinations
- **AggregatedMetrics**: Core storage for computed GTO statistics and convergence data
- **MatrixCells**: Represents individual hand vs hand matchups in the strategy matrix
- **Simulations**: Tracks simulation runs that generate the GTO data displayed in the browser

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can browse GTO strategy matrices with <500ms response times for all position/action/metric combinations
- **SC-002**: The browser displays accurate GTO data from the normalized database without data corruption or missing values
- **SC-003**: Advanced analytical features (convergence analysis, jackpot-adjusted EV) are accessible through the browser interface
- **SC-004**: Database queries support up to 10 concurrent browser users without performance degradation
- **SC-005**: The integrated system maintains 99.9% data integrity with proper foreign key enforcement
- **SC-006**: Schema extensions can be made without requiring browser application changes
