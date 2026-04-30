# Feature Specification: Database Repository Refactor

**Feature Branch**: `001-refactor-database-repository`  
**Created**: 2026-04-29  
**Status**: Draft  
**Input**: User description: "create a spec to refactor `python\hopilot\gto\database_repository.py` according to `plans\database_repository_refactor_plan.md`"

## Clarifications

### Session 2026-04-29

- Q: Which async/sync boundary should the refactor enforce for repository interfaces? → A: Repository boundaries are sync-only; async behavior is handled in service/provider adapters.
- Q: When should the compatibility facade be removed? → A: Remove it immediately after the first consumer migration lands.
- Q: What counts as the first consumer migration? → A: `aof_precompute_runner.py` and `precompute_job_persistence.py` must both be migrated.
- Q: How should transactions work across split repositories? → A: Use a shared unit-of-work/session per workflow step.
- Q: What regression gate is required during migration? → A: Targeted required suites per migration step, plus full suite required before merge.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Isolate Persistence Domains (Priority: P1)

As a maintainer, I can work on raw game-state persistence, job/session tracking, and analytics/query behaviors independently so that one change does not create broad regression risk across unrelated domains.

**Why this priority**: This is the core risk reduction objective. The current repository is a high-coupling bottleneck.

**Independent Test**: Deliver the domain split and prove that each domain has an independently testable interface with no behavior loss in existing consumers.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** maintainers inspect repository boundaries, **Then** raw game-state persistence and precompute job/session tracking are handled by separate components with clear ownership.
2. **Given** an existing workflow that writes raw simulation records, **When** the refactored components are used, **Then** output and persisted data semantics remain unchanged.
3. **Given** an existing workflow that tracks precompute job/session state, **When** the refactored components are used, **Then** lifecycle state transitions and counters remain unchanged.

---

### User Story 2 - Preserve Consumer Compatibility During Migration (Priority: P2)

As a maintainer, I can migrate existing consumers incrementally so that browser, runner, and query workflows keep working while internals are reorganized.

**Why this priority**: A big-bang migration would create unnecessary delivery risk; compatibility allows safer phased rollout.

**Independent Test**: Keep compatibility entry points available while migrating one consumer at a time and verifying unchanged externally visible behavior.

**Acceptance Scenarios**:

1. **Given** existing consumers still call the legacy repository entry points, **When** refactored internals are introduced, **Then** those consumers continue to function without requiring immediate rewrite.
2. **Given** one consumer is migrated to the new boundary, **When** regression tests run, **Then** migrated and non-migrated consumers both pass.

---

### User Story 3 - Improve Testability and Defect Isolation (Priority: P3)

As a maintainer, I can validate each persistence domain with focused tests so defects are detected where they originate instead of surfacing as cross-domain failures.

**Why this priority**: Smaller, explicit boundaries reduce debugging time and improve confidence in future changes.

**Independent Test**: Introduce focused tests per domain and confirm they identify failures without needing full end-to-end orchestration.

**Acceptance Scenarios**:

1. **Given** a validation or query rule change in one domain, **When** tests execute, **Then** failures are localized to that domain’s test suite.
2. **Given** full regression execution, **When** the refactor is complete, **Then** prior critical workflows remain green.

### Edge Cases

- A run has partial data (for example, missing summary rows but present raw rows); boundaries must still report accurate status and avoid data loss.
- A migration step updates one consumer while others remain on compatibility paths; mixed usage must remain valid.
- Domain-level validation rejects malformed updates; error behavior must remain explicit and consistent.
- A failed scenario in job/session tracking occurs after raw records were already written; tracking state must remain reconcilable and truthful.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST separate raw game-state persistence responsibilities from precompute job/session tracking responsibilities into distinct components.
- **FR-002**: The system MUST separate simulation/matrix persistence responsibilities from analytics/query projection responsibilities into distinct components.
- **FR-003**: The system MUST define explicit ownership for validation rules so update validation no longer depends on placeholder or dummy payload construction.
- **FR-004**: The system MUST preserve current externally visible behavior for existing browser, precompute runner, replay, and migration workflows during phased migration.
- **FR-005**: The system MUST provide a compatibility path that allows incremental consumer migration without requiring all consumers to switch at once.
- **FR-006**: The system MUST preserve durable tracking semantics for precompute job/session lifecycle state and scenario-link outcomes.
- **FR-007**: The system MUST preserve raw write semantics, including data fidelity and ordering guarantees used by downstream aggregation/replay workflows.
- **FR-008**: The system MUST remove connection/session inconsistencies so all persistence domains use a single, consistent connection access pattern.
- **FR-009**: The system MUST ensure refactored components expose interfaces that can be tested independently from unrelated domains.
- **FR-010**: The system MUST keep failure diagnostics explicit so boundary-level failures can be attributed to the owning domain.
- **FR-011**: The system MUST define repository boundaries as synchronous interfaces only; asynchronous execution MUST be handled by higher-level services or provider adapters.
- **FR-012**: The system MUST remove the compatibility facade immediately after the first consumer migration lands.
- **FR-013**: For FR-012, "first consumer migration" MUST mean both `aof_precompute_runner.py` and `precompute_job_persistence.py` have been migrated to the new repository boundaries.
- **FR-014**: The system MUST use a shared unit-of-work/session across participating repositories for each workflow step that performs coupled writes.
- **FR-015**: The system MUST enforce targeted required regression suites for each migration step, and MUST pass the full test suite before merge.

### Key Entities *(include if feature involves data)*

- **Raw Persistence Domain**: Capability boundary responsible for creating, updating, querying, and bulk-writing raw game-state records and related player/bet/jackpot data.
- **Tracking Domain**: Capability boundary responsible for durable precompute job/session lifecycle state and scenario-link status updates.
- **Simulation/Matrix Domain**: Capability boundary responsible for simulation metadata and matrix-level write/read operations.
- **Analytics/Query Domain**: Capability boundary responsible for read projections and matrix/query summaries used by browser/replay workflows.
- **Compatibility Facade**: Transitional entry point that keeps existing consumers operational while delegating to new domain boundaries.

### Assumptions

- Existing architecture constraints remain in force: solver writes raw game-state data, and aggregation/summary concerns remain separate.
- Migration proceeds in phases, but compatibility facade removal occurs immediately after first consumer migration.
- Existing high-value test suites are used as regression gates for each migration phase.
- Repository methods are synchronous; async wrappers are outside repository boundaries.
- Compatibility facade lifetime is intentionally short and ends after first consumer migration.
- First consumer migration is complete only when both `aof_precompute_runner.py` and `precompute_job_persistence.py` are migrated.
- Workflow-step transaction boundaries are coordinated through a shared unit-of-work/session.
- Regression gating uses targeted required suites per step and full-suite pass before merge.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing critical workflows (browser matrix retrieval, precompute job tracking, replay/raw projections, and migration flows) continue to pass their regression tests after refactor completion.
- **SC-002**: At least four explicit domain boundaries are documented and implemented, each with a clearly scoped responsibility set and no overlapping ownership.
- **SC-003**: For each new domain boundary, focused tests exist and can fail independently when that domain is broken, without requiring unrelated domain failures.
- **SC-004**: Compatibility migration is demonstrably incremental: at least one consumer can be migrated while at least one non-migrated consumer continues to work unchanged.
- **SC-005**: Connection/session access consistency defects identified in the current repository are eliminated, verified by tests covering affected query paths.
