# Feature Specification: Provider and Repository Responsibility Split

**Feature Branch**: `001-split-provider-repository`  
**Created**: 2026-04-29  
**Status**: Draft  
**Input**: User description: "create specs to implement points 3 and 4 from plans\aof_precompute_runner_refactor_plan.md file. points 1 and 2 were implemented in specs\001-refactor-precompute-runner spec."

## Clarifications

### Session 2026-04-29

- Q: What consistency model should govern raw sweep writes vs job/session tracking updates when one side fails? → A: B (separate transactions with mandatory reconciliation/finalization pass).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Separate Provider Contracts (Priority: P1)

As a maintainer of the precompute and browser flows, I need provider responsibilities split into explicit contracts so orchestration logic and UI payload logic cannot accidentally depend on each other.

**Why this priority**: Provider contract ambiguity is a direct source of coupling and regression risk between runner and browser paths.

**Independent Test**: This can be tested by running precompute orchestration tests and browser payload tests independently and confirming each uses only its intended provider contract.

**Acceptance Scenarios**:

1. **Given** a precompute run, **When** scenario context is requested, **Then** orchestration uses only the direct context contract and does not invoke payload retrieval behavior.
2. **Given** a browser matrix read request, **When** payload data is requested, **Then** payload retrieval is served through the browser-facing contract without exposing orchestration concerns.

---

### User Story 2 - Isolate Job Tracking Persistence (Priority: P2)

As a maintainer of persistence code, I need precompute job/session tracking responsibilities isolated from raw sweep/game-state persistence so each can evolve without cross-impact.

**Why this priority**: Mixed repository responsibilities increase maintenance cost and make persistence changes riskier.

**Independent Test**: This can be tested by running precompute integration tests that validate job/session lifecycle behavior and separate tests for raw sweep persistence behavior without cross-dependencies.

**Acceptance Scenarios**:

1. **Given** a precompute run with scenario outcomes, **When** job/session records are persisted, **Then** job and link lifecycle transitions are handled through dedicated job-tracking persistence responsibilities.
2. **Given** matrix sweep writes raw simulation/game-state outputs, **When** persistence occurs, **Then** raw data writes proceed without requiring job/session tracking internals.
3. **Given** raw writes and job/link writes commit in separate transactions, **When** one side fails, **Then** a mandatory reconciliation/finalization pass resolves mismatches deterministically.

---

### User Story 3 - Preserve Backward-Compatible Behavior During Split (Priority: P3)

As a maintainer, I need the provider and repository responsibility split to preserve existing external behavior so the refactor is safe to adopt.

**Why this priority**: Behavior regressions would negate maintainability gains and block adoption.

**Independent Test**: This can be tested by running the targeted regression and integration suites plus full test suite and confirming no externally observable behavior changes.

**Acceptance Scenarios**:

1. **Given** existing precompute and browser workflows, **When** the split is introduced, **Then** outputs and lifecycle outcomes remain consistent with baseline expectations.
2. **Given** failure conditions during orchestration and persistence, **When** the split is in place, **Then** failure boundaries and diagnostics remain complete and unchanged in meaning.

### Edge Cases

- Provider implements payload retrieval but does not provide valid direct context for orchestration.
- Browser payload request contains partial or invalid scenario context.
- Job/session tracking is available but raw sweep persistence fails mid-scenario.
- Raw sweep persistence succeeds but job/link update fails after execution.
- Cancellation occurs while a scenario is in progress and the job must finalize consistently.
- Legacy callers still using previous repository entry points during migration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define and enforce separate provider contracts for orchestration context resolution and browser payload retrieval.
- **FR-002**: The orchestration path MUST use only the direct context contract and MUST NOT call browser payload retrieval methods for context resolution.
- **FR-003**: The browser payload path MUST remain available as a dedicated contract for UI/data consumption and MUST NOT require orchestration-only context rules.
- **FR-004**: The system MUST isolate precompute job/session and scenario-link lifecycle persistence responsibilities from raw sweep/game-state persistence responsibilities.
- **FR-005**: The system MUST preserve existing job/session lifecycle semantics, including status transitions, progress counters, and terminal states.
- **FR-006**: The system MUST preserve existing raw sweep persistence semantics and data integrity behavior.
- **FR-007**: The system MUST preserve existing failure boundary classification semantics for orchestration, aggregation, and execution failures.
- **FR-008**: The system MUST provide maintainers with independently testable seams for provider contract behavior and persistence responsibility boundaries.
- **FR-009**: The system MUST maintain backward-compatible external behavior for precompute and browser workflows during and after the split.
- **FR-010**: The system MUST document migration boundaries so maintainers can identify which responsibilities are handled by provider contracts and which by persistence services.
- **FR-011**: The system MUST use separate transactions for raw sweep persistence and job/session tracking persistence.
- **FR-012**: The system MUST execute a mandatory reconciliation/finalization pass that detects and resolves mismatches between raw sweep outcomes and job/session tracking state.
- **FR-013**: The system MUST make reconciliation outcomes deterministic and repeatable for identical persisted inputs.

### Assumptions

- Points 1 and 2 from the prior precompute runner refactor are already completed and are out of scope for reimplementation in this feature.
- Existing regression and integration test expectations are the behavior baseline for this feature.
- No database schema redesign is required to complete this responsibility split.
- Incremental migration of call sites is acceptable as long as behavior remains consistent.
- Separate-transaction behavior is acceptable because reconciliation/finalization is mandatory and part of correctness criteria.

### Key Entities *(include if feature involves data)*

- **Provider Context Contract**: The orchestration-facing contract that returns validated scenario context required to build execution contracts.
- **Provider Payload Contract**: The browser-facing contract that returns matrix payload data for UI/read consumers.
- **Job Tracking Persistence Service**: The persistence boundary responsible for precompute job sessions and scenario link lifecycle updates.
- **Raw Sweep Persistence Service**: The persistence boundary responsible for simulation, matrix, game-state, and related raw output writes.
- **Migration Boundary Record**: The documented mapping of responsibilities and allowed dependencies during the split.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of targeted precompute orchestration tests pass while demonstrating orchestration uses only direct context provider behavior.
- **SC-002**: 100% of targeted browser payload tests pass while demonstrating browser reads remain available through the payload contract.
- **SC-003**: For test runs covering mixed outcomes, persisted job progress values always reconcile so completed plus failed equals attempted scenarios.
- **SC-004**: 100% of failures in targeted precompute suites retain a persisted failure boundary and reason with unchanged semantic meaning.
- **SC-005**: Full automated test suite passes with no regressions in externally observable precompute or browser behavior.
- **SC-006**: 100% of simulated split-write mismatch scenarios are resolved by reconciliation/finalization without manual data correction.
