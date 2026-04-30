# Phase 0 Research: Database Repository Refactor

## Decision 1: Repository interfaces are sync-only
- Decision: New repository boundaries expose synchronous methods only.
- Rationale: Existing persistence logic is SQLAlchemy session-based and predominantly synchronous; enforcing sync-only boundaries reduces hidden thread/executor complexity and keeps transaction semantics explicit.
- Alternatives considered:
  - Async-only repositories: rejected due to broad consumer churn and unnecessary risk in behavior-preserving refactor.
  - Mixed sync/async repositories: rejected because mixed boundaries reintroduce ambiguity and coupling.

## Decision 2: Shared unit-of-work/session for coupled writes
- Decision: Coupled write workflow steps use a shared unit-of-work/session across participating repositories.
- Rationale: Prevents partial commits between simulation metadata writes and tracking updates; keeps error handling deterministic.
- Alternatives considered:
  - Independent per-repository transactions: rejected due to partial-write risk and rollback complexity.
  - Eventual consistency with compensating actions: rejected as over-complex for internal refactor.

## Decision 3: Compatibility facade removal timing
- Decision: Remove compatibility facade immediately after first consumer migration lands.
- Rationale: Prevents long-lived transitional layer and forces completion of migration intent.
- Alternatives considered:
  - Multi-release deprecation window: rejected to avoid facade becoming permanent.
  - Remove only after all consumers migrate: rejected as unnecessarily delaying cleanup.

## Decision 4: First consumer migration definition
- Decision: First consumer migration is complete only when both `aof_precompute_runner.py` and `precompute_job_persistence.py` are migrated.
- Rationale: These consumers cover highest-risk precompute/tracking write paths.
- Alternatives considered:
  - Any single consumer file: rejected as too weak to prove safe facade removal.
  - Browser provider first: rejected because it does not fully exercise write/tracking lifecycle.

## Decision 5: Regression gate policy
- Decision: Require targeted suites on each migration step and full suite before merge.
- Rationale: Keeps developer iteration fast while preserving integration confidence.
- Alternatives considered:
  - Full suite after every commit: rejected due to high cycle time.
  - Targeted-only tests: rejected due to hidden integration/regression risk.

## Decision 6: Domain decomposition shape
- Decision: Split into `GameStateRepository`, `SimulationRepository`, `PrecomputeJobRepository`, `AnalyticsRepository`, with `DatabaseRepository` as temporary delegating facade.
- Rationale: Maps directly to current mixed responsibilities and enables independent testing.
- Alternatives considered:
  - Keep monolith and only refactor internals: rejected because boundary clarity remains weak.
  - Split into only two repositories: rejected for preserving too much mixed ownership.

## Decision 7: Validation ownership
- Decision: Move validation ownership into domain-specific validators/helpers, avoiding dummy payload pattern in update methods.
- Rationale: Dummy payload validation is brittle and obscures true constraints.
- Alternatives considered:
  - Keep in-place validation as-is: rejected due to maintainability and correctness risk.

## Decision 8: Contracts artifact type
- Decision: Provide internal interface contracts in markdown under `contracts/` since this feature has no external HTTP/CLI protocol changes.
- Rationale: The critical contracts here are internal repository/service boundaries consumed by runtime modules.
- Alternatives considered:
  - Skip contracts entirely: rejected; interface changes are the core risk and need explicit documentation.

---

## Final Migration Summary (2026-04-30)

### Implemented repository split
- `GameStateRepository` owns raw game-state/player/bet/jackpot writes and projections.
- `SimulationRepository` owns simulation/matrix persistence, run lookup, and cross-run summary aggregation.
- `PrecomputeJobRepository` owns precompute session and scenario-run-link lifecycle.
- `AnalyticsRepository` owns strategy matrix and analytics projection reads.

### Compatibility behavior
- `DatabaseRepository` is now a thin delegating facade over split repositories.
- Legacy payload and call-shape compatibility was preserved where required by runtime/tests.
- Browser provider compatibility shim now supports both sync and await-style matrix access while routing to split repositories.

### Validation result
- Targeted migration gates passed during each phase.
- Final full regression gate passed:
  - `pytest tests/ -q`
  - `949 passed, 1 skipped, 3 warnings`

### Quality and risk notes
- Domain-scoped error mapping/logging is active across split repositories.
- Unit-of-work and validation helper tests pass and remain isolated.
- Remaining warnings are non-blocking and pre-existing deprecation/runtime warnings outside this refactor's scope.
