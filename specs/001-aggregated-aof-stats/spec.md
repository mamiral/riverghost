# Feature Specification: Aggregated AoF Run Statistics Database

**Feature Branch**: `001-aggregated-aof-stats`  
**Created**: March 13, 2026  
**Status**: Draft  
**Input**: User description: "Create a new feature called Aggregated AoF Run Statistics Database.

Goal:
Replace snapshot-style cache behavior with cumulative per-scenario statistics so repeated runs improve estimate quality over time.

Problem statement:
Current behavior stores one payload snapshot per scenario key and overwrites it. We need a persistent run-history model where each run contributes additional samples, and loaded results are computed from aggregate totals.

User stories:

As a user, when I rerun the same scenario, I want new simulation evidence added to prior evidence so displayed metrics become more stable and accurate over time.
As a user, when I load a scenario, I want results computed from all matching historical runs rather than a single overwritten payload.
As a user, I want to see confidence metadata (sample size and uncertainty proxy) so I know how reliable each cell estimate is.
As a user, I want compatibility with existing UI flows (matrix view, precompute runner, metric switching) without regressions.
Functional requirements:

Introduce persistent per-scenario, per-hand cumulative statistics storage.
Treat each run as append/merge, not replace.
Aggregate on read using weighted totals (not average-of-averages).
Support at least WIN_LOSE_PROBABILITY, EV, EQUITY, EQR aggregation.
Store and expose sample_count per cell and scenario.
Compute and expose a confidence indicator derived from sample_count.
Keep scenario key semantics explicit and deterministic.
Define how runtime parameters affect keying:
Scenario semantics key (position/action/opponents/pot/bet/mode)
Runtime profile dimensions (sim count, combo samples, timeout, seed) and whether they partition or merge evidence
Provide migration behavior from old snapshot table:
One-time conversion or coexistence with fallback
No data corruption
Preserve existing degraded status handling (timeout/error/missing/no_contest) with clear aggregation rules.
Keep GUI responsiveness and threading model stable.
Non-functional requirements:

Backward-safe rollout with feature flag or migration gate.
No noticeable slowdown in matrix load compared to current implementation.
Deterministic behavior for test fixtures.
Edge cases:

Mixing runs with different runtime profiles.
Partially completed precompute runs.
Degraded cells in one run and available cells in another.
No prior runs for a scenario.
Corrupt or stale legacy payload rows.
Success criteria:

Re-running identical scenarios increases cumulative sample counts.
Reloaded results are derived from aggregated totals and visibly converge with more runs.
Existing AoF browser GUI tests pass with added aggregation tests.
No regressions in right-side controls, metric switching, or context refresh behavior.
Testing requirements:

Unit tests for aggregation math and keying policy.
Integration tests for repeated-run convergence behavior.
Migration tests validating legacy snapshot compatibility.
GUI tests ensuring selected-cell detail panel reflects aggregated values."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cumulative Evidence Aggregation (Priority: P1)

As a user, when I rerun the same scenario, I want new simulation evidence added to prior evidence so displayed metrics become more stable and accurate over time.

**Why this priority**: This is the core value proposition - improving accuracy through repeated runs is the primary goal of the feature.

**Independent Test**: Can be tested by running the same scenario multiple times and verifying that sample counts increase and metrics converge.

**Acceptance Scenarios**:

1. **Given** a scenario has been run once with 1000 simulations, **When** I run the same scenario again with 1000 simulations, **Then** the total sample count becomes 2000 and metrics reflect the combined evidence.
2. **Given** multiple runs of the same scenario, **When** I load the scenario, **Then** displayed probabilities and EVs are computed from all historical runs, not just the last one.

---

### User Story 2 - Aggregated Scenario Loading (Priority: P1)

As a user, when I load a scenario, I want results computed from all matching historical runs rather than a single overwritten payload.

**Why this priority**: Ensures the feature delivers on replacing snapshot behavior with aggregation.

**Independent Test**: Can be tested by loading a scenario after multiple runs and verifying results match aggregated calculations.

**Acceptance Scenarios**:

1. **Given** multiple historical runs for a scenario, **When** I load the scenario in the browser, **Then** the matrix shows aggregated results from all runs.
2. **Given** a scenario with no prior runs, **When** I load it, **Then** it shows empty or default state without errors.

---

### User Story 3 - Confidence Metadata Display (Priority: P2)

As a user, I want to see confidence metadata (sample size and uncertainty proxy) so I know how reliable each cell estimate is.

**Why this priority**: Provides transparency about estimate quality, important for user trust but secondary to core aggregation.

**Independent Test**: Can be tested by checking that sample counts and confidence indicators are displayed in the UI.

**Acceptance Scenarios**:

1. **Given** a cell with aggregated data, **When** I select it, **Then** the detail panel shows sample count and confidence indicator.
2. **Given** cells with varying sample sizes, **When** I view them, **Then** confidence indicators reflect the reliability (higher samples = higher confidence).

---

### User Story 4 - UI Flow Compatibility (Priority: P3)

As a user, I want compatibility with existing UI flows (matrix view, precompute runner, metric switching) without regressions.

**Why this priority**: Ensures the feature doesn't break existing functionality.

**Independent Test**: Can be tested by running existing GUI tests and verifying no regressions.

**Acceptance Scenarios**:

1. **Given** existing matrix view, **When** I switch metrics, **Then** aggregated data displays correctly for each metric.
2. **Given** precompute runner, **When** I run computations, **Then** results are stored and aggregated without affecting UI responsiveness.

---

### Edge Cases

- What happens when mixing runs with different runtime profiles (e.g., different sim counts)?
- How does the system handle partially completed precompute runs?
- What occurs when some runs have degraded cells (timeout/error) and others have available data for the same cell?
- How is the scenario handled when there are no prior runs?
- What happens with corrupt or stale legacy payload rows during migration?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST introduce persistent per-scenario, per-hand cumulative statistics storage.
- **FR-002**: System MUST treat each run as append/merge, not replace.
- **FR-003**: System MUST aggregate on read using weighted totals (not average-of-averages).
- **FR-004**: System MUST support aggregation for at least WIN_LOSE_PROBABILITY, EV, EQUITY, EQR metrics.
- **FR-005**: System MUST store and expose sample_count per cell and scenario.
- **FR-006**: System MUST compute and expose a confidence indicator derived from sample_count.
- **FR-007**: System MUST keep scenario key semantics explicit and deterministic.
- **FR-008**: System MUST define how runtime parameters affect keying: scenario semantics key (position/action/opponents/pot/bet/mode) and runtime profile dimensions (sim count, combo samples, timeout, seed) determining whether they partition or merge evidence.
- **FR-009**: System MUST provide migration behavior from old snapshot table: one-time conversion or coexistence with fallback, no data corruption.
- **FR-010**: System MUST preserve existing degraded status handling (timeout/error/missing/no_contest) with clear aggregation rules.
- **FR-011**: System MUST keep GUI responsiveness and threading model stable.
- **FR-012**: System MUST support backward-safe rollout with feature flag or migration gate.
- **FR-013**: System MUST have no noticeable slowdown in matrix load compared to current implementation.
- **FR-014**: System MUST have deterministic behavior for test fixtures.

### Key Entities *(include if feature involves data)*

- **Scenario**: Represents a unique poker scenario configuration (position, action, opponents, pot, bet, mode); has a deterministic key for identification.
- **Run**: Represents a single execution of simulations for a scenario; includes timestamp, runtime parameters (sim count, combo samples, timeout, seed), and payload data.
- **Statistics**: Per-hand, per-metric aggregated data; includes value, sample_count, and confidence indicator; computed from multiple runs.

## Assumptions

- Runtime parameters like sim count and combo samples will be merged across runs for the same scenario key, not partitioned.
- Confidence indicator will be computed as a simple function of sample_count (e.g., sqrt(sample_count) or similar).
- Migration will use coexistence with fallback, allowing gradual rollout.
- Degraded statuses will be aggregated by prioritizing available data over degraded, with sample counts still accumulated.

## Testing Requirements

- Unit tests for aggregation math and keying policy.
- Integration tests for repeated-run convergence behavior.
- Migration tests validating legacy snapshot compatibility.
- GUI tests ensuring selected-cell detail panel reflects aggregated values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Re-running identical scenarios increases cumulative sample counts.
- **SC-002**: Reloaded results are derived from aggregated totals and visibly converge with more runs.
- **SC-003**: Existing AoF browser GUI tests pass with added aggregation tests.
- **SC-004**: No regressions in right-side controls, metric switching, or context refresh behavior.
