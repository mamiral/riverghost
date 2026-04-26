# Feature Specification: Productionize Matrix Sweep

**Feature Branch**: `001-productionize-matrix-sweep`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Create a feature specification for productionizing the validated prototype matrix sweep and aggregation pipeline in HoPilot."

## Clarifications

### Session 2026-04-26

- Q: If aggregation is rerun for an existing completed sweep, what is the idempotency rule? → A: Delete and recreate only that Simulation's HandMatrix summaries, leaving raw GameState and Player rows and all other runs untouched.

## Domain Language

- **Scenario**: A fixed user-selected poker context for a matrix run. The scenario keeps opponent count constant across the entire run and captures the run-defining inputs needed to distinguish one run from another.
- **Sweep**: One end-to-end pass across all 169 canonical preflop hand cells, where each cell is expanded into concrete dealt combinations and each combination is simulated for a fixed number of iterations.
- **Aggregation**: A post-simulation step that reads raw hand records from the completed sweep, derives the hero hand cell from stored hero hole cards, and writes one summarized result per matrix cell for that run.
- **Matrix Run Boundary**: The records that belong to one completed sweep only. A matrix run boundary starts with a single simulation record, contains one hand matrix under that simulation, and includes only the matrix cells and aggregated metrics created for that same run.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a Fixed Scenario Sweep (Priority: P1)

An analyst or developer can launch one full matrix sweep for a single fixed scenario and receive a complete run that captures raw hand outcomes first, then summarized matrix results after the sweep finishes.

**Why this priority**: This is the core capability. Without a reliable end-to-end sweep, there is no production matrix pipeline to query or validate.

**Independent Test**: Can be fully tested by executing one fixed-opponent sweep, then verifying that raw hand records were written during simulation and that one completed run later contains one simulation, one hand matrix, 169 matrix cells, and 169 aggregated metric records.

**Acceptance Scenarios**:

1. **Given** a valid fixed scenario and a requested simulations-per-combination value, **When** a matrix sweep is executed, **Then** the system stores raw hand records for each simulated iteration and does not write summarized matrix results until the sweep phase is complete.
2. **Given** a completed sweep, **When** aggregation runs, **Then** the system creates one simulation record, one hand matrix for that simulation, and one summarized result for each of the 169 canonical matrix cells.
3. **Given** a completed sweep whose aggregation is rerun, **When** the rerun starts, **Then** the system replaces only that run's existing matrix-cell and aggregated-metric summaries and leaves the raw hand records and all other runs unchanged.

---

### User Story 2 - Query a Completed Run Cleanly (Priority: P2)

An analyst can distinguish one matrix run from another using a canonical scenario contract and retrieve only the summarized results that belong to the selected run.

**Why this priority**: Production use requires reliable run boundaries. Without clean run identification, browser and reporting work will mix historical data and produce incorrect comparisons.

**Independent Test**: Can be fully tested by creating multiple runs with different scenario inputs and verifying that each run can be selected by its scenario contract and returns only its own hand matrix, cells, and metrics.

**Acceptance Scenarios**:

1. **Given** two completed runs with different scenario contracts, **When** a consumer requests summarized results for one run, **Then** only the hand matrix, matrix cells, and aggregated metrics created under that run are returned.
2. **Given** a completed run, **When** a consumer inspects the run metadata, **Then** the scenario contract contains the required fields needed to identify the run unambiguously for later browser queries.

---

### User Story 3 - Preserve Historical Runs and Architectural Boundaries (Priority: P3)

A maintainer can add this production sweep capability without breaking the GameStates-first architecture or mutating historical matrix runs.

**Why this priority**: The feature is only safe to ship if it respects the current architecture and appends new runs instead of rewriting old data.

**Independent Test**: Can be fully tested by executing a new sweep in a database that already contains prior runs, then verifying that previous simulations and matrices remain unchanged and that new summarized data is appended under a new run boundary.

**Acceptance Scenarios**:

1. **Given** an existing database with historical runs, **When** a new sweep completes, **Then** the system appends a new simulation, a new hand matrix, and new summarized cell results without deleting or reassigning prior runs.
2. **Given** the production sweep capability, **When** simulation is executed, **Then** the solver persists raw hand records only and does not regain direct responsibility for cell identity or summarized metric calculation.

### Edge Cases

- If one or more concrete dealt combinations produce no valid simulated hands, the run still completes, the failure is isolated to the affected combinations, and aggregation summarizes only the successfully written raw hands.
- If aggregation encounters raw hands that cannot be mapped back to a canonical matrix cell from the hero hole cards, those records are excluded from summarized output and the run reports the mapping failure for investigation.
- If a sweep is executed for a scenario that already exists historically, the new run is still stored as a separate historical run rather than overwriting prior summarized results.
- If aggregation is rerun for the same completed sweep, the system deletes and recreates summarized matrix data only inside that run's hand matrix boundary and does not modify raw hand records or any other runs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide one production orchestration service for executing a full 13x13 matrix sweep for a single fixed scenario.
- **FR-002**: The system MUST treat a scenario as a fixed-context run with a constant opponent count for the entire sweep.
- **FR-003**: The system MUST expand each of the 169 canonical hand cells into its concrete dealt combinations and execute the requested number of simulations for each combination.
- **FR-004**: During the sweep phase, the system MUST persist raw hand outcomes and player records only.
- **FR-005**: The system MUST preserve the GameStates-first architecture by keeping summarized metric calculation out of the solver.
- **FR-006**: The system MUST create exactly one simulation record for each sweep run and store a canonical scenario contract on that record.
- **FR-007**: The scenario contract for each run MUST include, at minimum, selected position, hero action, position actions, active players, opponent count, pot size, bet amount, simulations per combination, matrix size, game type, and run kind.
- **FR-008**: The system MUST create exactly one hand matrix under the simulation created for the run.
- **FR-009**: The aggregation phase MUST derive matrix cell identity from the stored hero hole cards in the raw player records.
- **FR-010**: The aggregation phase MUST use HoPilot's existing canonical 13x13 hand-matrix convention when mapping hero hole cards back to matrix row and column identity.
- **FR-011**: The aggregation phase MUST create matrix-cell summaries only within the hand matrix owned by the current simulation.
- **FR-012**: The aggregation phase MUST store one aggregated metric record per matrix cell within the current hand matrix.
- **FR-013**: The system MUST append new simulation, hand matrix, matrix cell, and aggregated metric records for each new run and MUST NOT alter historical runs outside the current run boundary.
- **FR-013a**: If aggregation is rerun for an existing completed sweep, the system MUST delete and recreate only that run's MatrixCell and AggregatedMetric summaries inside the existing hand matrix boundary.
- **FR-013b**: A rerun of aggregation for an existing completed sweep MUST NOT modify that run's raw GameState or Player records and MUST NOT modify any other run.
- **FR-014**: The production feature MUST NOT reintroduce raw hand references that couple a game state directly to a matrix cell or to a separate board-card record.
- **FR-015**: The production implementation MUST treat the validated prototype as behavioral reference material only and MUST derive production structure from HoPilot's current architecture and persistence boundaries.
- **FR-016**: The feature MUST define acceptance tests against actual persisted raw and summarized records rather than against mocked storage behavior.

### Key Entities *(include if feature involves data)*

- **Scenario Contract**: The identifying description of one sweep run, including the fixed scenario inputs required to distinguish the run from all other runs.
- **Sweep Run**: The full execution boundary for one scenario, consisting of one simulation record, one hand matrix, the raw hand records produced during simulation, and the summarized cell results produced afterward.
- **Raw Hand Record**: One simulated hand outcome with its related player records. This is the source data for all later cell-level summaries.
- **Matrix Cell Summary**: The summarized result for one canonical hand cell inside one run's hand matrix, derived from the raw hand records mapped back from hero hole cards.

## Non-Goals

- Migrating browser read paths or query layers.
- Rewriting replay or historical query features beyond what this sweep pipeline requires.
- Broad cleanup of unrelated stale repository or aggregation code.
- Changing jackpot modeling or introducing new jackpot-specific metrics.
- Introducing advanced EV or EQR formulas that are not already supported cleanly by the current summarized schema.

## Assumptions

- The first production release covers one fixed scenario per execution and does not include randomized opponent-count selection inside a run.
- The canonical hand-matrix mapping already used elsewhere in HoPilot remains the single source of truth for row and column identity.
- The validated prototype has already proven the desired workflow and persisted behavior for sweep followed by aggregation; production work now needs to reproduce that behavior within the current architecture, not reproduce the prototype's script structure.
- Historical runs may share similar scenario values, so each run still requires its own distinct run boundary and summary records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can execute one fixed-scenario matrix sweep end-to-end and receive one completed run containing exactly one simulation, one hand matrix, 169 matrix cells, and 169 aggregated metric records.
- **SC-002**: During a completed run, all summarized matrix outputs are created only after raw hand and player records have been written for the sweep.
- **SC-003**: A user can distinguish and retrieve summarized results for a selected run using its scenario contract and run boundary without mixing data from historical runs.
- **SC-004**: Re-running the sweep for a new scenario or repeated scenario preserves all prior runs and adds a new independent run boundary rather than overwriting existing summarized results.
- **SC-004a**: Re-running aggregation for an existing completed sweep replaces only that run's matrix summaries and does not create duplicate summaries inside the same run boundary.
- **SC-005**: Test coverage proves the feature with real persisted data by validating raw hand writes, post-sweep aggregation, 169-cell coverage, and run-boundary isolation against the current schema.
