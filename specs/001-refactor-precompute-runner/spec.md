# Feature Specification: Precompute Orchestration Refactor

**Feature Branch**: `001-refactor-precompute-runner`  
**Created**: 2026-04-29  
**Status**: Draft  
**Input**: User description: "create spec to refactor code according to plans\\aof_precompute_runner_refactor_plan.md file"

## Clarifications

### Session 2026-04-29

- Scope boundary: Include new collaborator classes now (not helper extraction only).
- Provider policy: Remove `get_matrix_payload` fallback from precompute scenario context resolution.
- Repository split timing: Defer full `DatabaseRepository` responsibility split.
- Success evidence: Automated test results are sufficient acceptance evidence for maintainability outcomes.

## User Scenarios & Testing

### User Story 1 - Stabilize Precompute Orchestration (Priority: P1)

As a maintainer of the precompute workflow, I need the run workflow to be decomposed into clear orchestration responsibilities so behavior stays correct while future changes are safer and faster.

**Why this priority**: The precompute runner is a central execution path. Instability here causes broad regression risk and slows every follow-on change.

**Independent Test**: Can be fully tested by executing existing precompute regression and matrix sweep tests and confirming behavior is unchanged while orchestration logic is moved behind dedicated helpers.

**Acceptance Scenarios**:

1. **Given** a valid precompute profile, **When** a run executes, **Then** scenario orchestration, execution dispatch, and job finalization are delegated through distinct units with identical external run outcomes.
2. **Given** orchestration, aggregation, and execution failures, **When** a run processes scenarios, **Then** failure boundaries and persisted statuses remain consistent with current behavior.

---

### User Story 2 - Clarify Provider Context Contract (Priority: P2)

As a maintainer of provider integrations, I need one clear context-resolution path so runner behavior does not depend on ambiguous provider method combinations.

**Why this priority**: Provider coupling is a recurring regression source and directly affects orchestration correctness.

**Independent Test**: Can be tested by exercising runs against providers that implement direct context construction and confirming orchestration fails explicitly when direct context cannot be produced.

**Acceptance Scenarios**:

1. **Given** a provider that returns complete scenario context directly, **When** precompute orchestration requests context, **Then** the run proceeds without requiring payload retrieval.
2. **Given** a provider that cannot return complete context directly, **When** orchestration requests context, **Then** the run fails with explicit orchestration failure classification and does not use payload retrieval fallback.

---

### User Story 3 - Separate Persistence Responsibilities (Priority: P3)

As a maintainer of persistence code, I need job/session tracking concerns separated from raw sweep persistence concerns so each can evolve independently.

**Why this priority**: This reduces long-term complexity by introducing dedicated collaborators now while explicitly deferring a full repository split.

**Independent Test**: Can be tested by validating that job session creation, progress updates, scenario link updates, and final state transitions remain correct while persistence responsibilities are isolated.

**Acceptance Scenarios**:

1. **Given** a multi-scenario run with mixed outcomes, **When** progress is persisted, **Then** completed/failed counters and final run state are persisted correctly through isolated persistence paths.
2. **Given** cancellation state during dispatch, **When** finalization occurs, **Then** final state is persisted as canceled and no new scenarios are dispatched.

---

### Edge Cases

- Profile yields zero scenarios after filtering or max-scenario limits.
- Provider returns malformed or partial context that fails validation.
- Scenario orchestration succeeds but sweep execution throws an unclassified runtime error.
- Job cancellation is requested between scenario dispatches.
- Job session state is missing or stale at finalization time.
- Mixed success/failure scenarios must still persist accurate aggregate counts.
- A provider exposes payload retrieval but no direct context builder.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST preserve the current external run behavior while decomposing precompute orchestration into smaller units with single responsibilities.
- **FR-002**: The system MUST resolve scenario context through direct context construction only and MUST NOT use payload retrieval fallback during precompute orchestration.
- **FR-003**: The system MUST persist scenario link lifecycle transitions (pending, running, completed, failed) with the same semantics as current behavior.
- **FR-004**: The system MUST persist failure boundaries using existing classifications for orchestration, aggregation, and execution failures.
- **FR-005**: The system MUST update job progress counters after each scenario attempt, regardless of scenario outcome.
- **FR-006**: The system MUST finalize each precompute job with a terminal state that reflects completion, failure, or cancellation status.
- **FR-007**: The system MUST introduce collaborator classes in this feature for orchestration and job/session persistence responsibilities while preserving existing external behavior.
- **FR-008**: The system MUST preserve compatibility with existing regression and integration test expectations for precompute and matrix-sweep behavior.
- **FR-009**: The system MUST provide maintainers with dedicated, independently testable orchestration units for context resolution, scenario orchestration, result recording, failure recording, and finalization.
- **FR-010**: The system MUST defer full `DatabaseRepository` responsibility splitting to a later feature while documenting that boundary in this feature's design outputs.

### Assumptions

- Existing behavior and test assertions are the baseline for correctness.
- Failure boundary names and job state labels are considered stable business rules for this refactor.
- No schema redesign is required in this phase.
- Collaborator class extraction is in-scope for this feature after behavior-preserving decomposition is established.
- Full repository responsibility split is out of scope for this feature.

### Key Entities

- **Precompute Job Session**: Represents one end-to-end precompute run, including lifecycle state and aggregate progress counters.
- **Scenario Run Link**: Represents one scenario attempt under a job session, including status, failure diagnostics, and sweep result references.
- **Scenario Context**: Represents validated execution metadata required to build a sweep contract.
- **Sweep Contract**: Represents normalized run instructions used to execute one matrix sweep scenario.
- **Sweep Outcome Record**: Represents the recorded completion or failure result for one scenario attempt.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All existing targeted precompute and matrix-sweep regression tests pass with no behavior regressions.
- **SC-002**: The precompute orchestration flow is represented by dedicated, independently testable units for context resolution, orchestration, result/failure recording, progress updates, and finalization.
- **SC-003**: Failure diagnostics remain complete, with 100% of failed scenario links containing a persisted failure boundary and reason.
- **SC-004**: For mixed-outcome scenario runs, persisted completed and failed scenario counts always reconcile to the number of attempted scenarios.
- **SC-005**: Targeted regression and integration tests covering precompute orchestration and matrix sweep behavior pass after refactoring collaborator boundaries.
