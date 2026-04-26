# Research: Browser Read-Path Migration

## Decision 1: Keep `BrowserDatabaseProvider.get_matrix_payload` as the public entry point

**Decision**: Retain `BrowserDatabaseProvider.get_matrix_payload(...)` as the GUI-facing API and route it through a new deterministic scenario-scoped lookup before payload formatting.

**Rationale**: The GUI and tests already depend on this entry point. Preserving it localizes the migration to internal read behavior instead of forcing a broad caller rewrite.

**Alternatives considered**:

- Add a new browser read API alongside `get_matrix_payload`: rejected because it would expand migration scope to every caller without improving correctness.
- Replace provider logic with direct repository calls from the GUI: rejected because it would collapse context-building and payload-formatting responsibilities into callers.

## Decision 2: Reuse the matrix-sweep contract as the canonical scenario identity

**Decision**: Normalize browser context into the persisted matrix-sweep scenario contract and reuse `normalize_scenario_contract(...)` / `validate_scenario_contract(...)` semantics where possible.

**Rationale**: The production pipeline already persists scenario identity in `Simulation.parameters`. Reusing that contract avoids inventing a second scenario vocabulary for the same data.

**Alternatives considered**:

- Keep the provider's ad hoc context shape as the lookup contract: rejected because it does not align with persisted run identity.
- Query by partial JSON fragments or display-oriented fields only: rejected because it is ambiguous and would not satisfy deterministic run selection.

## Decision 3: Use run-scoped summary retrieval instead of raw legacy matrix queries

**Decision**: Build the read path on `find_matrix_sweep_run_by_contract(...)` and `get_matrix_sweep_summary(...)` rather than the older provider/repository query surfaces.

**Rationale**: The newer matrix-sweep methods already express the run boundary the browser needs. The legacy provider path still returns `LOADING` on misses and carries assumptions from the pre-productionized browser database path.

**Alternatives considered**:

- Continue using `_run_async_query(...)` and patch its result shape: rejected because it preserves stale selection semantics and the wrong missing-data behavior.
- Query `MatrixCell` and `AggregatedMetric` directly inside the provider: rejected because it duplicates repository responsibilities.

## Decision 4: Keep the existing `AggregatedMetric` fixed-column schema and implement browser-metric mapping in the read layer

**Decision**: Treat browser metric selection as an explicit mapping from browser metric IDs to existing `AggregatedMetric` columns (`equity`, `win_probability`, `ev`, `jackpot_adjusted_ev`, or equivalent compatibility choices) instead of introducing a new row-per-metric schema in this feature.

**Rationale**: The production ORM model stores one `AggregatedMetric` row per cell with fixed columns. Changing that schema would expand this feature into a schema migration and rewrite of existing aggregation code.

**Alternatives considered**:

- Add `metric_name` / `metric_value` rows to the production schema now: rejected because it broadens scope beyond a read-path migration.
- Keep the legacy repository `_get_metric_column(...)` logic unchanged: rejected because the new browser path must operate on run-scoped summaries rather than old context filters.

## Decision 5: Preserve only spec-compatible provider fallback behavior

**Decision**: Preserve invalid-context responses and `NO_CONTEST` short-circuit payload generation, but remove the legacy `LOADING` / `Computing...` fallback for missing scenarios.

**Rationale**: The clarified spec explicitly requires a read-only missing-status payload that does not imply background computation. Invalid context and `NO_CONTEST` remain provider-owned compatibility behavior and do not violate the new scenario model.

**Alternatives considered**:

- Preserve the current `LOADING` behavior on misses: rejected because it contradicts FR-016 and SC-003.
- Remove `NO_CONTEST` handling in this migration: rejected because it would change existing provider semantics without a spec requirement.

## Decision 6: Select the current run in the repository/read service, not in the provider

**Decision**: Implement latest-run and highest-simulation-id tie-break logic behind the provider, ideally in the repository or a thin read service.

**Rationale**: Current-run determination is persisted-data selection logic, not UI formatting logic. Keeping it behind the provider makes it testable and reusable.

**Alternatives considered**:

- Sort historical runs in the provider: rejected because it mixes query semantics into GUI-facing code.
- Rely on database insertion order only: rejected because the spec requires explicit deterministic ordering.

## Decision 7: Validate with real SQLite-backed payload behavior only

**Decision**: Plan tests around real `Simulation`, `HandMatrix`, `MatrixCell`, and `AggregatedMetric` rows in temporary SQLite databases.

**Rationale**: This feature is about query semantics, historical-run selection, and payload formatting over persisted state. Mock-only tests would miss the actual failure modes.

**Alternatives considered**:

- Keep existing mock-heavy browser provider tests as the primary safety net: rejected because they do not prove run selection or persisted payload shape.
- Test repository methods in isolation only: rejected because the provider-owned payload contract is part of the feature scope.