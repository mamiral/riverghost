# Feature Specification: Precompute Runner Sweep Delegation

**Feature Branch**: `001-precompute-runner-migration`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Create a feature specification for migrating HoPilot's AOF precompute runner to the new production matrix sweep pipeline."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Precompute Jobs Through Sweep Pipeline (Priority: P1)

As an operator, I can run a UI-triggered precompute job and have each scenario executed through the matrix sweep pipeline so persisted outputs follow the validated GameStates-first flow.

**Why this priority**: This is the core migration outcome and removes dependency on the dead schema write path.

**Independent Test**: Start one precompute job with multiple scenarios and verify that each scenario is delegated to the sweep service, produces a persisted simulation run, and returns a run mapping back to the job.

**Acceptance Scenarios**:

1. **Given** a precompute job request with valid scenarios, **When** the runner executes the job, **Then** it delegates scenario execution to the sweep service instead of constructing low-level persistence rows itself.
2. **Given** a completed delegated scenario, **When** the job finishes, **Then** the job output includes a stable mapping from UI job/scenario identifiers to resulting simulation identifiers.
3. **Given** a persisted job session, **When** scenario linkage is stored, **Then** linkage is persisted in dedicated scenario-link records associated with the job session and produced simulation identifiers.

---

### User Story 2 - Preserve Lifecycle and Progress Visibility (Priority: P2)

As an operator, I can still observe meaningful precompute progress and lifecycle state even though scenario execution is now delegated.

**Why this priority**: Existing orchestration workflows depend on status and progress updates for user trust and operational control.

**Independent Test**: Run a job and verify start, in-progress, per-scenario progress, completion, and failure states are emitted consistently using the runner lifecycle model.

**Acceptance Scenarios**:

1. **Given** a running precompute job, **When** scenarios transition across delegated phases, **Then** the runner reports job status and progress using phase-aware updates (orchestration, solver write, aggregation).
2. **Given** a job with mixed scenario outcomes, **When** execution completes, **Then** final lifecycle output clearly reports successful and failed scenarios without hiding partial completion.
3. **Given** existing GUI lifecycle consumers, **When** the migrated runner reports status, **Then** lifecycle state names remain stable and progress payload fields may be extended without breaking existing state-driven behavior.

---

### User Story 3 - Enforce Failure Boundaries and Recovery Behavior (Priority: P3)

As an engineer, I can distinguish orchestration failures from solver-write and aggregation failures so retries and investigations are targeted and predictable.

**Why this priority**: Clear failure boundaries prevent ambiguous job states and reduce operational risk during migration.

**Independent Test**: Inject failures at each phase boundary and verify job results classify failures by boundary, persist diagnostics, and keep unaffected scenarios intact.

**Acceptance Scenarios**:

1. **Given** an orchestration validation failure before delegation, **When** the job processes scenarios, **Then** the scenario is marked failed without invoking the sweep execution.
2. **Given** a delegated scenario that fails in solver-write or aggregation, **When** the job finalizes, **Then** failure type and boundary are recorded and successful scenarios remain completed.
3. **Given** a cancellation request during active processing, **When** cancellation is applied, **Then** no new scenarios begin and any in-flight scenario is allowed to complete before the job enters a canceled terminal state.
4. **Given** a failed scenario, **When** the runner finalizes results, **Then** no automatic retry is attempted in this feature and the failure remains available for manual retry workflows.

### Edge Cases

- A job includes duplicate or semantically equivalent scenarios that normalize to the same sweep contract.
- A job is canceled while scenarios are mid-execution and must produce deterministic terminal state.
- Delegated sweep returns a simulation record but aggregation output is incomplete or delayed.
- Progress update callbacks fail transiently while sweep execution succeeds.
- A restarted runner must resume or reconcile a previously started job without duplicating completed scenario runs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The precompute runner MUST orchestrate precompute jobs by resolving scenario context and delegating each scenario run to the production matrix sweep orchestration service.
- **FR-002**: The precompute runner MUST NOT create GameState records with `cell_id` for this feature path.
- **FR-003**: The precompute runner MUST NOT create board card entities, jackpot entities, or other dead-schema artifacts for this feature path.
- **FR-004**: The precompute runner MUST remove duplicated low-level persistence logic for scenario data generation rather than adapting that logic.
- **FR-005**: The precompute runner MUST preserve existing job lifecycle semantics where practical, including start, running, completion, cancellation, and failure terminal states.
- **FR-006**: The precompute runner MUST persist per-job metadata linking each UI-driven scenario request to resulting simulation identifiers produced by delegated sweep runs.
- **FR-006a**: Job-to-simulation linkage metadata MUST be persisted in dedicated scenario-link records tied to the precompute job session.
- **FR-007**: The precompute runner MUST expose progress updates that remain meaningful after delegation, including at minimum scenario counts, active scenario identity, and current phase.
- **FR-007a**: Lifecycle state semantics MUST remain backward compatible for GUI consumers; progress payload fields MAY evolve as long as lifecycle states and terminal behavior remain stable.
- **FR-008**: The system MUST classify failures by boundary (orchestration, solver write phase, aggregation phase) and persist that boundary classification for each failed scenario.
- **FR-009**: The system MUST allow partial success: one scenario failure MUST NOT invalidate already completed scenarios in the same job.
- **FR-010**: The runner-to-sweep integration MUST use direct service delegation and MUST avoid callback-heavy indirection for core execution flow.
- **FR-011**: The migrated flow MUST produce persisted simulation and hand matrix outputs through the sweep pipeline for successful scenarios.
- **FR-012**: Existing GUI orchestration contracts MUST remain compatible for job submission and completion consumption, except where explicitly documented in migration notes.
- **FR-013**: Cancellation MUST be cooperative: after cancellation is requested, the runner MUST stop dispatching new scenarios and allow the currently active delegated scenario to finish.
- **FR-014**: Automatic retries MUST NOT be introduced in this feature; failed scenarios MUST be reported with boundary classification for manual retry handling.

### Key Entities *(include if feature involves data)*

- **Precompute Job Session**: Represents one UI-triggered precompute execution, including lifecycle status, requested scenarios, start/end timestamps, and aggregate job outcome.
- **Scenario Run Link**: Represents mapping between one requested scenario in a job and its resulting simulation identifier and phase outcomes.
- **Scenario Run Link**: Represents a dedicated persisted linkage record mapping one requested scenario in a job to its resulting simulation identifier and phase outcomes.
- **Phase Progress Snapshot**: Represents current observable progress for a job or scenario, including phase name, processed counts, total counts, and last update time.
- **Scenario Failure Record**: Represents a failed scenario outcome with failure boundary classification, reason, and retry-relevant metadata.

## Assumptions

- The production matrix sweep orchestration service from prior feature work is available and supports scenario-based execution with persisted outputs.
- Browser read behavior continues to consume sweep outputs and is not redesigned in this feature.
- Replay/query migration and jackpot redesign remain out of scope for this feature.
- Existing GUI job entry points and consumers can accept stable lifecycle and progress payloads without structural redesign.
- Existing runner lifecycle states are the compatibility contract; progress payload shape can be extended without requiring GUI state-model redesign.
- Automatic retries remain outside this feature and are handled by existing manual rerun workflows.

## Dependencies

- Availability of production matrix sweep orchestration and aggregation services in the main application runtime.
- Persistence support for storing job-to-simulation mapping metadata.
- Existing job orchestration interfaces used by the GUI layer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of successful scenarios in a precompute job produce persisted simulation outputs and corresponding hand matrix outputs through the delegated sweep pipeline.
- **SC-002**: 100% of scenarios processed by the runner are recorded as either completed or failed with explicit boundary classification; no scenario ends in an ambiguous terminal state.
- **SC-003**: For every completed precompute job, operators can retrieve a complete mapping from requested scenarios to resulting simulation identifiers.
- **SC-004**: Existing UI job lifecycle visibility is preserved such that job start, in-progress, and terminal states are observable for 100% of executed jobs.
- **SC-005**: Automated tests demonstrate delegated execution and persisted real outputs for representative successful and failure scenarios in the migrated path.
