# Feature Specification: Solver-Backed AoF Browser Data

**Feature Branch**: `001-solver-backed-aof-browser`  
**Created**: 2026-03-13  
**Status**: Draft  
**Input**: User description: "Upgrade standalone AoF GTO Browser from synthetic placeholder data to real solver-backed outputs with deterministic edge-case handling, caching, tests, and docs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy Matrix Decisions (Priority: P1)

As a player using the AoF Browser, I need the hand matrix values to come from real strategy calculations so that my shove or fold decisions are based on meaningful data rather than placeholders.

**Why this priority**: This is the core product value. Without trustworthy data, the browser is only a visual demo.

**Independent Test**: Can be fully tested by selecting a fixed game context and confirming matrix values match solver-driven expectations across all four metrics.

**Acceptance Scenarios**:

1. **Given** a valid browsing context, **When** the matrix is loaded, **Then** every available cell value is produced from solver-backed calculations.
2. **Given** solver-backed mode is active, **When** users switch between WIN_LOSE_PROBABILITY, EV, EQUITY, and EQR, **Then** values update consistently for the same hand and context.

---

### User Story 2 - Correct Context Across Position Actions (Priority: P2)

As a player, I need each position's FOLD or ALL-IN state to change the matrix context so I can evaluate decisions for realistic table participation states.

**Why this priority**: Position action state is fundamental to AoF decision quality, but it depends on Story 1's solver-backed values.

**Independent Test**: Can be fully tested by toggling position action states and confirming context changes produce deterministic matrix and summary updates.

**Acceptance Scenarios**:

1. **Given** a selected position and metric, **When** another position toggles from FOLD to ALL-IN, **Then** the matrix recalculates for the updated multi-position context.
2. **Given** a selected position, **When** only that position is ALL-IN and all others are FOLD, **Then** the browser shows uncontested-win semantics.

---

### User Story 3 - Stable Performance and Failure Transparency (Priority: P3)

As a user, I need fast context switching and clear status when data cannot be computed so the browser remains usable during repeated exploration.

**Why this priority**: Performance and resilience drive usability, but can be implemented after solver correctness and context semantics.

**Independent Test**: Can be fully tested by repeatedly toggling context, validating cache hits reduce recomputation, and validating timeout or failure messaging behavior.

**Acceptance Scenarios**:

1. **Given** repeated revisits to the same context, **When** users switch back to prior states, **Then** cached payloads are returned with faster response.
2. **Given** a solver timeout or calculation failure, **When** matrix data is requested, **Then** the UI shows deterministic status messaging and non-crashing fallback behavior defined by policy.

### Edge Cases

- All positions set to FOLD.
- Exactly one position set to ALL-IN.
- Selected position set to FOLD while one or more other positions are ALL-IN.
- Selected position set to ALL-IN while all other positions are FOLD.
- Multiple opponent positions set to ALL-IN.
- No valid hand combinations for a matrix cell in the current context.
- Solver timeout while building payload.
- Solver failure or unavailable context inputs.
- Unknown or unsupported metric request.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The AoF browser data provider MUST compute matrix values using existing strategy calculation engines rather than heuristic placeholder formulas under normal operation.
- **FR-002**: The provider MUST keep the current matrix payload contract (context + 169 cells with value, display, and status fields) so the current UI rendering flow continues to work.
- **FR-003**: The system MUST treat position actions as an explicit context input and recalculate matrix values when any position action changes.
- **FR-004**: The system MUST support WIN_LOSE_PROBABILITY, EV, EQUITY, and EQR for every available cell and define deterministic calculation semantics for each metric. EQR MUST be computed as `max(0.0, min(1.0, equity / max(1e-6, raw_equity_baseline)))`, where `raw_equity_baseline` is the pre-action showdown equity under the same context; if baseline is 0, EQR MUST be `0.0`; numeric EQR values MUST be rounded to 4 decimal places before display formatting.
- **FR-005**: In WIN_LOSE_PROBABILITY mode, the system MUST provide values that map to valid win and loss complements for stacked-bar rendering.
- **FR-006**: The system MUST aggregate combo-level evaluations into a single deterministic value per hand matrix cell.
- **FR-007**: The system MUST detect invalid combo conditions (such as card collisions) and mark affected cells with a non-available status rather than returning misleading values.
- **FR-008**: The system MUST define deterministic outputs and status messaging for all edge cases listed in this specification.
- **FR-009**: The system MUST implement context-keyed caching for matrix payloads and return cached results for repeated identical contexts.
- **FR-010**: The system MUST define cache invalidation rules for any input that changes output values (such as position actions, selected position, metric, and game parameters).
- **FR-011**: The system MUST enforce a documented timeout strategy for long-running calculations and must return deterministic, non-crashing responses when timeouts occur.
- **FR-012**: The system MUST define and implement a clear fallback policy for solver failures, including user-visible status and logging of degraded behavior. Silent fallback to heuristic or synthetic matrix generation is prohibited in normal operation. Timeout paths MUST return deterministic `TIMEOUT` status with null values and a deterministic status message. Solver failure paths MUST return deterministic `ERROR` status with null values and a deterministic status message.
- **FR-013**: The standalone AoF browser MUST remain decoupled from the simulator workflow and MUST not reintroduce prior simulator integration behavior.
- **FR-014**: The system MUST include automated tests proving values are solver-backed, edge cases behave as specified, cache behavior is correct, and failure or timeout paths are handled.
- **FR-015**: The system MUST update user-facing documentation to describe data provenance, metric interpretation, performance expectations, and known limits.

### Key Entities *(include if feature involves data)*

- **Browser Context**: The active state used to compute matrix data, including selected position, per-position action states, selected metric, and analysis parameters.
- **Matrix Cell Result**: A per-hand aggregate result containing hand key, computed value, display value, and availability status.
- **Solver Evaluation Record**: A normalized intermediate result representing per-combination strategy outputs used to build cell-level aggregates.
- **Edge-Case Resolution**: A deterministic rule mapping from exceptional context states to expected matrix semantics and status messaging.
- **Cache Entry**: A stored payload keyed by full browser context, including metadata needed for validity checks and invalidation.

## Assumptions

- Existing strategy calculation engines are sufficiently mature to provide AoF-relevant outputs for browser contexts.
- Existing UI interaction patterns (compact position cards, matrix navigation, metric switching) remain unchanged.
- Browser mode defaults to analysis mode, where selected-position `FOLD` can still show what-if values unless strict-current-action mode is explicitly enabled.
- Calculation variance from simulation can be controlled to a deterministic level suitable for automated testing.
- Product acceptance prioritizes clear deterministic behavior over exhaustive real-time precision in rare failure states.

## Dependencies

- Existing strategy calculation modules and analysis services currently used elsewhere in the project.
- Browser provider and matrix rendering contract currently used by the standalone AoF browser.
- Existing test harness for AoF browser and integration tests.
- Existing quickstart and usage documentation that will be updated for solver-backed operation.

## Risks

- **Runtime Cost Risk**: Full matrix recomputation can exceed acceptable interaction latency under heavy contexts.
- **Stochastic Variance Risk**: Simulation-driven outputs may fluctuate between runs without deterministic controls.
- **Context Explosion Risk**: Per-position action combinations multiply state space and can increase cache size and recomputation pressure.
- **Fallback Clarity Risk**: Users may misinterpret degraded results if fallback behavior is not clearly signaled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of available matrix cells in normal operation are produced by solver-backed calculations, with no heuristic placeholder generation in the standard path.
- **SC-002**: p95 latency across 200 position-action or metric switches MUST be <= 1.0 second on the project reference environment.
- **SC-003**: 100% of specified edge-case contexts return deterministic status and value semantics matching automated test expectations.
- **SC-004**: Automated test coverage includes all defined edge-case categories, cache behavior, and failure or timeout handling, with all tests passing in CI.
- **SC-005**: Documentation updates enable a reviewer to identify data source, metric meaning, fallback policy, and performance constraints in under 5 minutes.
