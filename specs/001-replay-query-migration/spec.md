# Feature Specification: Replay Query Migration

**Feature Branch**: `[001-replay-query-migration]`  
**Created**: 2026-04-27  
**Status**: Draft  
**Input**: User description: "Create a feature specification for rebuilding HoPilot replay and analytical query tooling on top of the current GameStates-first schema."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Replay A Stored Hand Truthfully (Priority: P1)

An analyst can replay a stored hand from persisted raw data and see only the details that truly exist in the current schema for that hand.

**Why this priority**: Replay is the core recovery path for validating solver output, investigating surprising outcomes, and replacing broken legacy replay code that still depends on removed relationships.

**Independent Test**: Can be fully tested by persisting a real game state with player rows, requesting a replay by game state identifier, and verifying that the replay output contains stored board, player, and outcome data without inventing actions or jackpot details that were not persisted.

**Acceptance Scenarios**:

1. **Given** a stored game state with `board_cards_str`, outcome, pot size, and related player rows, **When** an analyst requests replay by game state identifier, **Then** the system returns a replay containing the stored board cards, participating players, hero marker, hole cards, hand resolution fields, and outcome for that exact hand.
2. **Given** a stored game state that has no persisted betting sequence or jackpot records, **When** an analyst requests replay, **Then** the replay remains valid and explicitly omits or marks those details as unavailable instead of fabricating a fuller hand history.

---

### User Story 2 - Filter Raw Hands By Run Boundary (Priority: P2)

An analyst can retrieve only the raw hands that belong to a selected simulation run, hand matrix, or scenario definition so cross-run data does not get mixed together.

**Why this priority**: Scenario-scoped analysis is the main protection against misleading results now that raw game states are written first and aggregated summaries are derived later.

**Independent Test**: Can be fully tested by storing multiple runs with distinct scenario metadata and raw hand ranges, then verifying that each supported filter returns only hands from the intended run boundary.

**Acceptance Scenarios**:

1. **Given** two stored runs with non-overlapping raw hand ranges, **When** an analyst filters by simulation, **Then** only raw hands belonging to that simulation's recorded range are returned.
2. **Given** a hand matrix linked to one simulation, **When** an analyst filters by hand matrix, **Then** the result set is limited to the raw hands owned by that matrix's simulation and does not require a direct raw hand to matrix foreign key.
3. **Given** a scenario contract that identifies a specific run context, **When** an analyst filters by that scenario contract, **Then** the returned hands match only runs whose stored scenario metadata satisfies that contract.
4. **Given** a scenario contract exactly matches more than one historical run, **When** an analyst issues a scenario-only raw-hand query, **Then** the system requires explicit run selection instead of auto-selecting or merging runs.

---

### User Story 3 - Inspect Raw Hands Alongside Aggregated Context (Priority: P3)

An analyst can move from scenario-level summaries to the underlying raw hands without reviving stale schema assumptions about cell-linked game states or separate board card records.

**Why this priority**: The migration is incomplete unless analytical queries and replay entry points align with the GameStates-first write model and the later aggregation model.

**Independent Test**: Can be fully tested by selecting a stored run that already has summary records, requesting raw-hand inspection from that run context, and verifying that the system resolves the raw-hand scope through run metadata rather than dead joins.

**Acceptance Scenarios**:

1. **Given** a run with both raw hands and post-processed summary records, **When** an analyst inspects underlying hands from that run context, **Then** the system returns raw hands through scenario-aware boundaries while keeping summary context separate from replay content.
2. **Given** a request that references a legacy-only concept such as a direct raw hand cell link, **When** the analytical query is evaluated, **Then** the system rejects or ignores that stale assumption and uses supported run-scoped filters instead.

### Edge Cases

- A requested game state identifier exists but has no related player rows; the replay must fail clearly because the stored hand is incomplete for truthful replay.
- A requested simulation or hand matrix exists but its recorded raw hand boundary is missing or invalid; the query must return no raw hands and must not guess membership from stale joins.
- A scenario contract matches multiple historical runs; the query must require explicit run disambiguation rather than auto-selecting or merging runs silently.
- A stored board string is empty because the hand never reached a community-card street; the replay must still present a valid preflop hand view.
- Optional persisted details such as bets or jackpot events are present for some historical rows but absent for others; replay must expose them only when they exist and keep the minimum replay shape consistent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST rebuild replay behavior around stored `GameState` and `Player` data from the current raw schema.
- **FR-002**: The system MUST derive replay board information from `GameState.board_cards_str` and MUST NOT depend on separate board-card relationships.
- **FR-003**: The system MUST produce a valid replay for a single stored hand using, at minimum, the game state identifier, timestamp, round, pot size, outcome, board cards, and related player rows including hero marker, position, hole cards, hand class, and final strength when present.
- **FR-004**: The system MUST define the minimum truthful replay shape for the current schema and treat betting details, jackpot details, and other event history as optional only when such records actually exist.
- **FR-005**: The system MUST NOT require `GameState.cell_id`, `GameState.matrix_id`, or any equivalent raw-hand-to-cell foreign key to replay or query stored hands.
- **FR-006**: The system MUST support replay lookup by direct game state identifier.
- **FR-007**: The system MUST support raw-hand filtering by simulation using the simulation's recorded run boundary and scenario metadata rather than stale raw-hand joins.
- **FR-008**: The system MUST support raw-hand filtering by hand matrix by resolving the owning simulation boundary and MUST NOT assume raw hands directly reference the hand matrix.
- **FR-009**: The system MUST support raw-hand filtering by scenario contract using an exact match against the canonical stored simulation parameters that define the run context.
- **FR-010**: The system MUST require explicit run selection when the same exact scenario contract appears in multiple historical runs, and the behavior MUST preserve run isolation.
- **FR-011**: The system MUST keep replay output honest to persisted data by omitting or explicitly marking unavailable details instead of reconstructing richer hand histories from assumptions.
- **FR-012**: The system MUST expose analytical query entry points that let users inspect raw hands for a selected run without requiring dead relationships such as board-card joins or cell-linked game states.
- **FR-013**: The system MUST define how aggregated context and raw replay relate so that summary records can lead users to matching raw hands without altering the raw replay payload.
- **FR-014**: The system MUST validate supported replay and query behavior with tests built from real persisted game states and related player rows.
- **FR-015**: The system MUST make failures explicit when a requested replay cannot be truthfully produced because required stored inputs are missing or inconsistent.
- **FR-016**: The system MUST return an empty raw-hand result set when a simulation or hand matrix lacks a valid recorded raw-hand boundary, and it MUST treat that run as unreadable for raw replay and raw-hand query purposes.

### Key Entities *(include if feature involves data)*

- **Stored Game State**: A persisted raw hand record containing hand-level facts such as identifier, timestamp, round, pot size, board card string, and outcome.
- **Stored Player Result**: A persisted participant record linked to a stored game state containing role, position, hole cards, and final hand resolution fields.
- **Simulation Run**: A recorded execution boundary that stores scenario metadata and the raw hand range associated with one scenario-scoped run.
- **Hand Matrix Context**: The summary boundary owned by a simulation run that provides aggregated context for the run but does not directly own raw hands.
- **Scenario Contract**: The set of stored simulation parameters used to identify a run context for analysis and replay filtering.
- **Explicit Run Selection**: A caller-provided simulation or equivalent run identifier used to disambiguate among multiple historical runs that share the same scenario contract.
- **Replay View**: The truthful hand representation returned to analysts, limited to data actually persisted for one stored hand.

## Assumptions

- Scenario-scoped runs record enough metadata to distinguish run context and enough raw hand boundary information to recover the raw hands for that run.
- Scenario-contract filtering uses exact canonical matching rather than partial matching.
- A hand matrix remains a summary artifact owned by one simulation run, not a raw-hand ownership mechanism.
- The minimum replay experience is valuable even when no detailed action timeline or jackpot history is available.
- Historical rows with optional ancillary records may still appear, but those records are not required for a replay to be considered complete under the current schema.

## Out of Scope

- Changing solver write behavior or adding new solver-side fields solely to satisfy legacy replay expectations.
- Reworking browser matrix payload behavior.
- Precompute orchestration changes.
- Inventing event-level hand histories that are not supported by persisted raw data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance tests built from persisted fixtures, 100% of supported replay requests by direct game state identifier return only the requested stored hand and no unrelated hand data.
- **SC-002**: In validation fixtures containing multiple historical runs, 100% of supported filters by simulation, hand matrix, and scenario contract preserve run isolation and return no cross-run false positives.
- **SC-003**: In replay validation tests where betting or jackpot details are absent, 100% of replay outputs omit or clearly mark those details as unavailable rather than presenting fabricated history.
- **SC-004**: Analysts can inspect raw hands for a selected run and confirm the expected board and player facts for representative fixtures without relying on removed raw-hand relationships.
