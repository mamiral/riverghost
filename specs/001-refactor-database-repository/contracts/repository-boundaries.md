# Internal Interface Contract: Repository Boundaries

## Scope
Defines internal contracts for repository/service boundaries introduced by this refactor.

## Contract A: Sync-only Repository Interfaces
- All repository methods are synchronous.
- Repositories must not expose async signatures.
- Async adaptation is implemented only in service/provider layers.

## Contract B: Unit-of-Work Coordination
- For workflow steps with coupled writes across domains, participating repositories share one unit-of-work/session.
- A failed coupled workflow step must not leave partial committed state for that step.

## Contract C: Ownership Boundaries
- `GameStateRepository`: raw game-state and related entities.
- `SimulationRepository`: simulation/matrix metadata and matrix persistence/lookups.
- `PrecomputeJobRepository`: precompute session and scenario-link tracking.
- `AnalyticsRepository`: read/query projections.

## Contract D: Transitional Facade
- `DatabaseRepository` may delegate during migration.
- Facade removal trigger: both `aof_precompute_runner.py` and `precompute_job_persistence.py` migrated to new repositories.
- Trigger consumers are migrated in this implementation.
- `DatabaseRepository` is retained as a thin compatibility facade while split repositories own domain behavior.

## Contract E: Regression Gates
- Each migration step must pass targeted required suites.
- Full `pytest tests/` pass is required before merge.

Validation status:
- Final full gate passed: `949 passed, 1 skipped`.

## Contract F: Implementation Scope for Phase 1
- Phase 1 includes creation of repository split stubs, a shared unit-of-work helper, and dedicated validation helpers.
- Phase 1 implementation should preserve the legacy `DatabaseRepository` facade until downstream consumers are migrated.
