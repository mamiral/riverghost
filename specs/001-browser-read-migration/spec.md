# Feature Specification: Browser Read-Path Migration

**Feature Branch**: `001-browser-read-migration`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Create a feature specification for migrating the HoPilot browser read path to the new scenario-scoped matrix aggregation model."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load the Current Scenario Matrix (Priority: P1)

A browser user opens a scenario that already has aggregated matrix results and sees the matrix payload for that exact scenario without triggering any new simulation work.

**Why this priority**: This is the core business outcome of the migration. If the browser cannot resolve an existing scenario deterministically and return the expected matrix payload, the migration fails.

**Independent Test**: Can be fully tested by seeding two different aggregated scenarios, requesting one browser scenario, and verifying that the returned payload contains the exact run's context and 169 canonical cells from the selected aggregated matrix.

**Acceptance Scenarios**:

1. **Given** persisted aggregated runs for multiple browser scenarios, **When** the user opens one scenario in the browser, **Then** the system resolves one deterministic scenario contract, selects the current matching run, and returns matrix payload data from that run's HandMatrix only.
2. **Given** a persisted aggregated run for the selected browser scenario, **When** the payload is returned to the GUI, **Then** the payload keeps the existing GUI-facing shape and each cell is identified by canonical `hand_key`, `row`, and `col`.
3. **Given** aggregated metrics for the selected run, **When** the user switches display metrics in the browser, **Then** the browser reads the requested metric from the same selected run rather than re-resolving to a different scenario.

---

### User Story 2 - Show a Deterministic Missing Scenario State (Priority: P2)

A browser user opens a scenario that has no aggregated run yet and sees a consistent missing-data payload instead of an ad hoc simulation or a schema-dependent failure.

**Why this priority**: Missing scenarios are a normal production condition. The browser must handle them cleanly while remaining read-only.

**Independent Test**: Can be fully tested by requesting a scenario that has no aggregated run and verifying that the browser receives the same payload shape, 169 canonical cells, and explicit missing-status messaging without any new persistence side effects.

**Acceptance Scenarios**:

1. **Given** no aggregated run exists for the selected browser scenario, **When** the browser requests matrix payload data, **Then** the system returns the standard payload shape with all 169 canonical cells present, `value` unset, cell identity intact, and an explicit missing-status message.
2. **Given** a missing scenario response, **When** the browser renders the matrix, **Then** it does not depend on `GameState.cell_id`, `board_cards_id`, or any board-card relationship to build the payload.
3. **Given** a missing scenario response, **When** the read path completes, **Then** no new simulation, hand-matrix, matrix-cell, or aggregated-metric records are created as a side effect of the read.

---

### User Story 3 - Prefer the Current Historical Run Deterministically (Priority: P3)

A maintainer or analyst can rerun the same scenario over time and know which historical run the browser treats as current.

**Why this priority**: Historical runs are append-only. Without an explicit current-run rule, the browser can silently drift between runs and show inconsistent results for the same UI context.

**Independent Test**: Can be fully tested by seeding multiple aggregated runs with the same canonical scenario contract and verifying that the browser always selects the same current run under the stated ordering rules.

**Acceptance Scenarios**:

1. **Given** multiple aggregated runs share the same canonical scenario contract, **When** the browser requests matrix payload data, **Then** the system selects the run with the latest completion timestamp as current.
2. **Given** multiple aggregated runs share the same canonical scenario contract and the completion timestamp is tied or unavailable, **When** the browser requests matrix payload data, **Then** the system selects the run with the highest simulation identity as the deterministic tie-breaker.
3. **Given** historical runs exist for the same scenario, **When** the browser loads the current run, **Then** older runs remain unchanged and are not merged into the current payload.

### Edge Cases

- A browser scenario resolves to a Simulation record that matches the scenario contract but does not yet have an aggregated HandMatrix. The response is treated as missing for browser purposes rather than partially available.
- The browser context omits some position actions. Scenario resolution must normalize them into the canonical seat map before lookup so equivalent UI states do not fan out into different queries.
- A historical run has the right scenario contract but is not in the aggregated state. It is excluded from current-run selection.
- A matching aggregated run exists but some cells have no aggregated metric row for the requested metric. The payload still returns canonical cell identity for all 169 cells and substitutes `0` for the missing metric value.
- Invalid browser context remains a validation failure and is not treated as a missing persisted scenario.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The browser read path MUST resolve matrix payloads from the production aggregated data model only: one selected Simulation, its HandMatrix, its MatrixCell rows, and their AggregatedMetric rows.
- **FR-002**: The browser read path MUST remain read-only and MUST NOT create ad hoc simulation, hand-matrix, matrix-cell, or aggregated-metric records during payload reads.
- **FR-003**: Scenario lookup MUST NOT depend on `GameState.cell_id`.
- **FR-004**: Scenario lookup and payload retrieval MUST NOT require `board_cards_id` or any board-card relationship.
- **FR-005**: The browser scenario contract MUST be deterministic and derived from canonical fields stored in `Simulation.parameters`.
- **FR-006**: The canonical scenario contract MUST include `selected_position`, `hero_action`, `position_actions`, `active_players`, `num_opponents`, `pot_size`, `bet_amount`, `matrix_size`, `game_type`, and `run_kind`.
- **FR-007**: Scenario normalization MUST use a canonical seat order and action vocabulary so equivalent browser states map to one identical query contract every time.
- **FR-008**: Scenario normalization MUST derive `hero_action` from the selected position's normalized action value.
- **FR-009**: Scenario normalization MUST derive `active_players` from the normalized action map in canonical seat order and MUST derive `num_opponents` from that same normalized scenario.
- **FR-010**: Scenario resolution MUST match runs by exact equality on the canonical scenario contract fields and MUST exclude runs that are not in the aggregated state.
- **FR-011**: When multiple aggregated runs match the same canonical scenario contract, the browser MUST treat the run with the latest completion timestamp as current.
- **FR-012**: If multiple matching runs have the same completion timestamp or no completion timestamp, the browser MUST treat the run with the highest simulation identity as current.
- **FR-013**: The browser-facing payload MUST preserve the current GUI contract by returning the existing top-level structure for `context`, `cells`, `status`, and `status_message`.
- **FR-014**: The payload MUST preserve cell identity using canonical `hand_key`, `row`, and `col` for every returned cell.
- **FR-015**: For a matching aggregated run, the payload MUST return 169 canonical cells for the selected HandMatrix and map each requested browser metric by selecting the `AggregatedMetric` row whose `metric_name` equals the requested metric and reading its `metric_value`.
- **FR-015A**: If a matching aggregated run lacks an `AggregatedMetric` row for the requested metric for a given cell, the payload MUST return that cell with canonical identity intact and substitute `0` for the missing metric value.
- **FR-016**: Missing scenarios MUST be represented with the same payload shape used for available scenarios, including 169 canonical cells with `value` unset, canonical cell identity preserved, and an explicit missing-status message that does not imply background computation.
- **FR-017**: A Simulation record that matches the canonical scenario contract but lacks an aggregated HandMatrix MUST be represented as a missing scenario in the browser payload.
- **FR-018**: Browser metric selection MUST change only which aggregated value is read from the selected run; it MUST NOT change scenario resolution.
- **FR-018A**: `strict_current_action` MUST be deprecated as part of this migration and MUST NOT participate in the canonical scenario contract, repository lookup, or payload selection behavior.
- **FR-019**: BrowserDatabaseProvider MUST remain responsible for browser-context construction and GUI payload formatting. The existing `get_matrix_payload` entry point MUST first attempt the aggregation-backed read path for the canonical scenario contract. If no matching aggregated run exists, it MUST preserve only the current provider-owned compatibility behaviors that remain consistent with this specification: invalid-context validation responses and `NO_CONTEST` short-circuit payload generation. It MUST NOT preserve the legacy `LOADING` or `Computing...` fallback for missing scenarios; unmatched scenarios MUST return the explicit missing-status payload defined by **FR-016**.
- **FR-020**: Scenario lookup, current-run selection, and aggregated-row retrieval MUST be owned by the repository layer or a dedicated read service behind the provider.
- **FR-021**: The design MUST preserve prototype code as reference-only evidence of desired scenario behavior and payload shape and MUST NOT introduce prototype code as a production dependency.
- **FR-022**: The read path MUST use canonical hand keys and matrix row and column identity from the aggregated matrix model rather than reconstructing cell identity from raw game-state relationships.
- **FR-023**: The feature MUST include tests that validate real browser-visible payload behavior for both existing and missing scenarios against the current schema and aggregated data model.
- **FR-024**: For a warm local database in development, one browser matrix payload read for a single scenario MUST complete in `<=250 ms`.

### Key Entities *(include if feature involves data)*

- **Browser Scenario Contract**: The canonical persisted description of one browser-visible situation, derived from the UI context and matched against fields stored in `Simulation.parameters`.
- **Current Scenario Run**: The single aggregated historical run that the browser treats as authoritative for one canonical scenario contract.
- **Matrix Payload**: The GUI-facing response containing browser context, 169 canonical cells, per-cell metric values or missing values, overall status, and status messaging.
- **Aggregated Matrix Slice**: The scenario-scoped summary rows belonging to one selected Simulation through its HandMatrix, MatrixCell, and AggregatedMetric records.

## Assumptions

- The browser scenario is an all-in-or-fold preflop context with canonical seat order `UTG`, `BTN`, `SB`, `BB` and canonical action vocabulary already normalized before repository lookup.
- The persisted production run contract remains the source of truth for `matrix_size`, `game_type`, and `run_kind`, and browser reads do not invent alternate contract fields at query time.
- `strict_current_action` is deprecated for this read path and does not affect persisted scenario matching.
- The browser continues to expect the current payload shape and 13x13 canonical hand matrix layout.
- Historical runs remain append-only; the browser chooses one current run by rule and does not merge data across runs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a browser scenario with one matching aggregated run, the browser returns one payload whose cells come only from that run's Simulation and HandMatrix and include all 169 canonical cell identities.
- **SC-002**: Given two or more historical aggregated runs for the same canonical scenario contract, repeated browser requests for the same UI context always select the same current run according to the published latest-run rule.
- **SC-003**: Given a browser scenario with no matching aggregated run, the browser returns the standard payload shape with explicit missing status and 169 canonical cells, and no new persistence records are created during the read.
- **SC-004**: Browser payload retrieval succeeds against the current schema and aggregated data model without using `GameState.cell_id`, `board_cards_id`, or prototype code as a production dependency.
- **SC-005**: Test coverage proves real payload behavior for existing scenarios, missing scenarios, and repeated historical runs of the same scenario.
- **SC-006**: In local development against a warm database, one scenario payload read completes in `<=250 ms`.

## Clarifications

### Session 2026-04-26

- Q: How should the existing `get_matrix_payload` method be migrated -- replace entirely, add a new method alongside, or delegate to the new path and fall back when missing? -> A: `get_matrix_payload` remains the entry point, first attempts the aggregation-backed read path, preserves only provider-owned compatibility behaviors that still match the spec (`invalid-context` responses and `NO_CONTEST` payload generation), and does not preserve the legacy `LOADING` or `Computing...` fallback for missing scenarios.
- Q: How should browser metric names map to aggregated metric storage? -> A: Use the `AggregatedMetric` row whose `metric_name` equals the requested browser metric and read its `metric_value`.
- Q: Should `strict_current_action` participate in scenario resolution for this migration? -> A: No. Deprecate `strict_current_action` for this migration; it does not participate in the canonical scenario contract, repository lookup, or payload selection.
- Q: How should the payload behave when a matching run exists but a cell has no `AggregatedMetric` row for the requested metric? -> A: Return the cell and substitute `0` for the missing metric value.
- Q: What latency target should this feature commit to for local development payload reads? -> A: `<=250 ms` per scenario payload read against a warm local database.