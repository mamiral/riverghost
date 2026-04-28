# Feature Specification: [FEATURE NAME]
# Feature Specification: GUI Integration and UX Hardening on the GameStates-First Pipeline

**Feature Branch**: `005-gui-pipeline-integration`  
**Created**: 2026-04-28  
**Status**: Draft

## Context

The backend pipeline has been migrated to a GameStates-first architecture. The solver writes raw `GameState` and `Player` rows per simulation. A post-processing aggregation phase reads those rows and produces `Simulation`, `HandMatrix`, `MatrixCell`, and `AggregatedMetric` records. The browser read path queries aggregated matrix data scoped to a scenario. The precompute runner calls the production sweep service.

The data path is correct. This feature is about making the GUI behave as a coherent user-facing product on top of that pipeline: honest panel states, explicit precompute lifecycle handling, deterministic refresh after completion, and validated end-to-end manual flows.

## Clarifications

### Session 2026-04-28

- Q: For repeated runs of the same scenario, should results be accumulated across runs or only the latest run shown? -> A: Accumulate across completed runs that match the same canonical scenario contract.
- Q: Should the Start button be enabled in NO_CONTEST state? -> A: Yes — Start is enabled in NO_CONTEST, same as MISSING, ERROR, and AVAILABLE.
- Q: If a fetch returns some but not all 169 cells, does the panel show AVAILABLE? → A: Yes — AVAILABLE triggers on >=1 cells present; a partial count indicator (e.g., "84/169 cells") shows completeness alongside the matrix.
- Q: When the user clicks Start from AVAILABLE state, what does the panel show during the new run? → A: Panel stays AVAILABLE (previous run's cell data remains visible); a COMPUTING progress overlay is shown so the user knows a new run is in progress. No cells are cleared until the new run completes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Precomputed Matrix for Current Scenario (Priority: P1)

A user opens the AoF Browser, selects a position and metric, and wants to see the matrix results for that scenario. If the scenario has already been precomputed, the matrix loads and displays data immediately. If it has not been computed, the GUI clearly tells the user the data is missing — it does not show stale or phantom data from a different scenario.

**Why this priority**: This is the primary use case. Without honest state representation, users cannot trust any data the GUI shows. It also unblocks all subsequent stories since they depend on knowing which state the GUI is in.

**Independent Test**: Open the AoF Browser with a database that contains precomputed data for exactly one scenario. Select that scenario — matrix shows AVAILABLE cells. Select any other scenario — matrix shows MISSING or empty cells, not the previous scenario's data.

**Acceptance Scenarios**:

1. **Given** the database has aggregated matrix data for position UTG with metric WIN_LOSE_PROBABILITY, **When** the user selects position UTG, **Then** the matrix panel shows all 169 cells in AVAILABLE status with correct values within 3 seconds.
2. **Given** the database has no data for position BB, **When** the user selects position BB, **Then** the matrix panel displays all cells in MISSING status and shows a clear message that the scenario has not been computed.
3. **Given** the database has data for position UTG, **When** the user switches from UTG to HJ, **Then** the matrix panel clears the UTG data immediately before loading HJ data — it does not keep showing UTG values while HJ loads.
4. **Given** the matrix is loading (fetch in progress), **When** the user inspects the panel, **Then** a loading indicator is visible and no partial or stale data is shown.

---

### User Story 2 - Trigger Precompute for a Missing Scenario (Priority: P1)

A user sees a MISSING matrix for their selected scenario and wants to compute it. They click Start, monitor progress through intermediate states, and the matrix automatically refreshes to show computed results when the job completes.

**Why this priority**: Without the ability to compute missing scenarios and see results, the browser is read-only and only useful if data already exists. This story makes the application self-sufficient.

**Independent Test**: Open the AoF Browser against an empty database. Select any position. Click Start. Let the job run to completion. The matrix transitions from MISSING → COMPUTING → AVAILABLE without any additional user action.

**Acceptance Scenarios**:

1. **Given** the matrix is in MISSING state, **When** the user clicks Start, **Then** the matrix transitions to COMPUTING state, the start button is disabled, and a progress indicator is visible.
2. **Given** a precompute job is COMPUTING, **When** cells complete, **Then** the matrix incrementally updates to show those cells as AVAILABLE — the user sees progress, not a blank screen until completion.
3. **Given** the precompute job completes successfully, **When** the final cell finishes, **Then** the matrix automatically refreshes from the aggregated data and transitions to AVAILABLE state without requiring a manual reload.
4. **Given** the precompute job completes, **When** the user inspects cell detail, **Then** the cell detail panel shows the computed metric value, sample count, and confidence indicator.

---

### User Story 3 - Handle Precompute Failure Gracefully (Priority: P2)

A user triggers a precompute job that fails partway through (worker crash, DB write failure, etc.). The GUI transitions to an ERROR state, shows a meaningful message, and allows the user to retry without restarting the application.

**Why this priority**: Failures are inevitable in a long-running compute process. Without first-class error handling, users are left with a broken UI and no recovery path.

**Independent Test**: Trigger a precompute run and simulate a failure (e.g., kill the DB connection mid-run). The GUI transitions to ERROR state with a visible error message. After the error is cleared, clicking Start again initiates a new fresh run.

**Acceptance Scenarios**:

1. **Given** a precompute job is COMPUTING, **When** the job fails, **Then** the matrix transitions to ERROR state, a visible error message is displayed (not just a log entry), and partial results are not presented as complete data.
2. **Given** the matrix is in ERROR state, **When** the user clicks Start, **Then** the previous error is cleared and a new precompute run begins from COMPUTING state.
3. **Given** a precompute job fails after completing some cells, **When** the user retries, **Then** the new run re-computes all cells for the scenario and does not silently reuse incomplete prior results.

---

### User Story 4 - Context Change Invalidates Current Matrix (Priority: P2)

A user changes the selected position or metric while viewing a matrix. The GUI immediately invalidates the current display and loads the correct data for the new context — it never silently shows old data under new parameters.

**Why this priority**: Stale data under changed context is a trust-breaking failure. The user believes they are looking at one scenario but they are seeing another.

**Independent Test**: Load UTG matrix. Change position to BTN. The matrix clears and either shows MISSING or loads BTN data. At no point does UTG data remain visible under the BTN label.

**Acceptance Scenarios**:

1. **Given** the user is viewing an AVAILABLE matrix for scenario A, **When** they change the position, **Then** the matrix clears immediately (cells go to LOADING or MISSING) before the new data is fetched.
2. **Given** the user is viewing an AVAILABLE matrix, **When** they change the metric, **Then** the matrix re-fetches and re-renders for the new metric without retaining the old metric's cell colors.
3. **Given** a precompute job is COMPUTING for scenario A, **When** the user changes to scenario B, **Then** the in-flight job for scenario A is stopped (or continues in background without affecting the UI), and the GUI shows the state for scenario B.

---

### User Story 5 - Cancel or Pause a Running Precompute Job (Priority: P3)

A user who started a precompute job wants to pause or stop it before completion. The GUI responds correctly to pause, resume, and stop actions — it does not lock up or leave the matrix in an ambiguous state.

**Why this priority**: Precompute runs can take minutes. Users need control over long-running jobs. This is lower priority than correct state display and run completion.

**Independent Test**: Start a precompute job. Click Pause — job halts, matrix stays in COMPUTING state, resume button becomes active. Click Resume — job continues. Click Stop — job terminates, matrix shows partial results honestly (cells computed so far as AVAILABLE, rest as MISSING).

**Acceptance Scenarios**:

1. **Given** a precompute job is COMPUTING, **When** the user clicks Pause, **Then** the job pauses, progress freezes, and the Resume button becomes active.
2. **Given** a paused job, **When** the user clicks Resume, **Then** the job continues from where it stopped.
3. **Given** a precompute job is COMPUTING or PAUSED, **When** the user clicks Stop, **Then** the job terminates, partial results are retained for cells that completed, and the matrix state reflects the partial completion honestly (not shown as fully AVAILABLE).

---

### Edge Cases

- What if the database is unavailable when the panel opens? The GUI must show an ERROR state with a connection failure message — not an empty matrix that looks like MISSING.
- What if precompute completes but aggregation has not yet written MatrixCell rows? The panel must not show a blank AVAILABLE matrix — it should remain in LOADING until cells are confirmed present, or explicitly show partial availability.
- What if the user changes position while the matrix is in LOADING state (fetch in progress)? The in-flight fetch must be cancelled or its result discarded, and a new fetch for the changed context must begin.
- What if a cell is in NO_CONTEST state (e.g., duplicate holdings in a heads-up scenario)? The cell must render in NO_CONTEST color and the cell detail panel must show the NO_CONTEST fallback message — not an empty or zero-value cell.
- What if the GUI is opened against a database that has data for multiple scenarios simultaneously? The panel must query only the scenario matching the current selection — it must not mix data across scenarios.

## Requirements *(mandatory)*

### Functional Requirements

**Panel State Management**

- **FR-001**: The matrix panel MUST display one of seven explicit states for the current scenario: `LOADING`, `AVAILABLE`, `MISSING`, `COMPUTING`, `STALE`, `NO_CONTEST`, `ERROR`. The state must be visible to the user at all times.
- **FR-002**: The matrix panel MUST transition to `LOADING` immediately when the scenario context changes, before any new data is fetched.
- **FR-003**: The matrix panel MUST transition to `MISSING` when a fetch completes and no aggregated data exists for the current scenario.
- **FR-004**: The matrix panel MUST NOT display data from a previously-viewed scenario while a new scenario is loading.
- **FR-005**: The matrix panel MUST transition to `ERROR` when a data fetch or precompute job fails, with a user-visible error message.

**Precompute Job Lifecycle**

- **FR-006**: The Start button MUST be active when the matrix is in `MISSING`, `NO_CONTEST`, `ERROR`, or `AVAILABLE` state. It MUST be disabled in `LOADING` and `COMPUTING` states.
- **FR-006a**: If Start is triggered while in `AVAILABLE`, the system MUST launch a new run for the current scenario and include that run in scenario-level aggregated results after completion. While the new run is in progress, the panel MUST remain in `AVAILABLE` state with previous cell data visible, overlaid with a `COMPUTING` progress indicator. The previous data MUST NOT be cleared until the new run's post-processing completes and a new fetch is issued.
- **FR-007**: The Pause button MUST only be active when the matrix is in `COMPUTING` state.
- **FR-008**: The Resume button MUST only be active when the job is paused.
- **FR-009**: The Stop button MUST be active in `COMPUTING` and paused states.
- **FR-010**: When a precompute job completes successfully, the GUI MUST automatically re-fetch aggregated data for the current scenario and transition to `AVAILABLE` — no manual reload required.
- **FR-010a**: Scenario-level fetches MUST aggregate over all completed runs matching the canonical scenario contract, not just the latest run.
- **FR-011**: When a precompute job fails, the GUI MUST transition to `ERROR` state and clear any partial results from view.

**Context Invalidation**

- **FR-012**: Changing the selected position MUST invalidate the current matrix and trigger a re-fetch for the new position.
- **FR-013**: Changing the selected metric MUST invalidate the current matrix and trigger a re-fetch for the new metric.
- **FR-014**: If a precompute job is running when context changes, the GUI MUST stop the job before switching context — it MUST NOT silently continue computing the old scenario while displaying the new one.

**Scenario Parameters**

- **FR-015**: The currently active scenario parameters (position and metric) MUST be visible in the panel at all times — the user must always know which scenario they are viewing.
- **FR-016**: The panel MUST NOT imply that a scenario has been computed when no data exists for it.

**Cell-Level Display**

- **FR-017**: Each cell in the matrix MUST display its individual status (`AVAILABLE`, `NO_CONTEST`, `ERROR`, `MISSING`) independently — a matrix can have a mix of cell statuses within a single scenario fetch.
- **FR-017a**: When the matrix is in `AVAILABLE` state with fewer than 169 cells present, the panel MUST display a cell count indicator (e.g., "84 / 169 cells") so the user knows the matrix is partially populated. The indicator MUST NOT be shown when all cells are present.
- **FR-018**: The cell detail panel MUST show the correct fallback message for non-AVAILABLE cells (`NO_CONTEST`, `ERROR`, `MISSING`, `TIMEOUT`).
- **FR-019**: For AVAILABLE cells, the cell detail panel MUST show the metric value, sample count, and confidence indicator sourced from `AggregatedMetric` data.

**End-to-End Validation**

- **FR-020**: Manual end-to-end validation MUST be performed against a real database with a real precompute run — not mock data or unit test fixtures.
- **FR-021**: The validation MUST confirm that the matrix refresh after precompute completion is automatic and does not require the user to restart the application or manually trigger a refresh.

### Key Entities

- **Scenario**: The combination of position and metric that identifies a specific matrix query. The GUI's entire state model is scoped to the current scenario. Changing any component invalidates the current state.
- **Panel State**: The GUI-level state that the matrix panel is in at any given moment. Distinct from backend simulation state. Derives from the result of a data fetch and the status of any in-flight precompute job.
- **Precompute Job**: A run of the precompute pipeline for the current scenario. Has its own lifecycle: COMPUTING → COMPLETED or FAILED. The GUI tracks this lifecycle and reacts to each transition.
- **MatrixCell**: A single cell in the 13×13 hand matrix. Has an individual status (`AVAILABLE`, `NO_CONTEST`, `ERROR`, `MISSING`) and metric value sourced from the aggregated pipeline output.
- **AggregatedMetric**: The per-cell aggregated result (win rate, equity, etc.) that the cell detail panel reads to populate sample count, confidence, and metric value display.

## UI State Definitions

These states are the authoritative specification for what the matrix panel renders. No state outside this list is valid.

| State | Trigger Condition | Panel Behavior | Controls Active |
|-------|-------------------|----------------|-----------------|
| `LOADING` | Fetch in progress for current scenario | Spinner or loading indicator; no cell data shown | None (all disabled during fetch) |
| `AVAILABLE` | Fetch complete, at least one cell with data | Matrix rendered with cell values and colors; a cell count indicator (e.g., "84/169 cells") is shown if fewer than all cells are present | Start enabled; cells clickable |
| `MISSING` | Fetch complete, zero cells in database | Empty matrix with "Not computed" message | Start enabled |
| `COMPUTING` | Precompute job running | Matrix shows computed cells incrementally; progress visible | Pause and Stop enabled |
| `STALE` | Context changed while AVAILABLE; new fetch pending | Previous data replaced with loading state | None |
| `NO_CONTEST` | Fetch complete, all cells are NO_CONTEST | Matrix rendered in NO_CONTEST color; message shown | Start enabled (recompute allowed) |
| `ERROR` | Fetch failed or precompute job failed | Error message visible; no data shown | Start enabled (retry) |

## State Transition Rules

- Panel opens → `LOADING`
- Fetch completes with data → `AVAILABLE`
- Fetch completes with no data → `MISSING`
- Fetch completes with all NO_CONTEST → `NO_CONTEST`
- Fetch fails → `ERROR`
- User changes position or metric while in any state → `LOADING` (previous data cleared immediately)
- User clicks Start while in `MISSING`, `NO_CONTEST`, or `ERROR` → `COMPUTING`
- User clicks Start while in `AVAILABLE` → panel stays `AVAILABLE` with previous data visible + `COMPUTING` progress overlay (no state transition to `COMPUTING`; overlay distinguishes active rerun)
- Precompute job completes → automatic re-fetch → `LOADING` → `AVAILABLE`
- Precompute job fails → `ERROR`
- User clicks Stop while `COMPUTING` → re-fetch partial results → `AVAILABLE` (partial) or `MISSING`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can select a scenario, trigger precompute, and view the completed matrix in a single uninterrupted workflow — no application restart required.
- **SC-002**: The matrix panel never shows data from scenario A while the user has selected scenario B. Context changes always clear old data before new data appears.
- **SC-003**: All seven panel states (`LOADING`, `AVAILABLE`, `MISSING`, `COMPUTING`, `STALE`, `NO_CONTEST`, `ERROR`) are reachable and visually distinct in manual testing.
- **SC-004**: After a precompute job completes, the matrix automatically refreshes and displays the new data within 5 seconds of job completion — no user action required.
- **SC-004a**: If the user runs the same scenario twice, the second post-completion refresh shows increased scenario-level sample count versus the first completed run (assuming successful writes in both runs).
- **SC-005**: Manual end-to-end validation against a real database confirms the full flow: open browser → MISSING → Start → COMPUTING → AVAILABLE → cell detail shows correct aggregated values.
- **SC-006**: Precompute failure transitions the panel to ERROR state with a visible message, and clicking Start successfully initiates a new run.
- **SC-007**: The active scenario (position + metric) is visible in the panel at all times during all state transitions.

## Assumptions

- The browser read path migration (querying scenario-scoped aggregated data) is complete and correct before this feature begins.
- The precompute runner migration (calling the new production sweep service) is complete before this feature begins.
- The state machine controller (`StateMachineController`) already handles RUNNING → STOPPING → COMPLETED → FAILED transitions at the job level. This feature adds scenario-scoped panel-level state on top of it, without replacing the job state machine.
- `BrowserDatabaseProvider.get_matrix_from_database()` is the canonical read path; this feature does not change its interface, only how the panel responds to its results.
- Pause/resume capability already exists in `AoFPrecomputeRunner` via `GuiPrecomputeRunSession` and `GuiRunState`. This feature connects it correctly to panel state, not re-implements it.
- No visual redesign is in scope. Existing colors, fonts, and layout are preserved unless a state change requires a new visual indicator (e.g., loading spinner, error badge).

## Out of Scope

- New visual redesign unrelated to state representation.
- Changes to solver math or simulation algorithms.
- Reworking `SimulationPanel` or other GUI systems unrelated to the AoF Browser matrix pipeline.
- Solver math changes or hand evaluation algorithm changes.
- Automated GUI tests (pygame-based GUI is deferred; manual validation is the acceptance gate).
