# Feature Specification: In-GUI AoF Precompute Runner

**Feature Branch**: `001-gui-precompute-runner`  
**Created**: 2026-03-13  
**Status**: Draft  
**Input**: User description: "Add an in-GUI precompute runner panel to the standalone AoF browser so users can start, pause, resume, and stop offline matrix precomputation for the currently selected scenario while watching live progress directly on the 13x13 matrix. The panel must include controls for simulations-per-cell (default 1000), run state (Idle/Running/Paused/Stopping/Completed/Failed), and progress telemetry (completed cells out of 169, current cell, elapsed time, ETA, failure count). During a run, each cell should be processed sequentially (1000 sims per cell, then move to next), update its matrix value/status immediately when finished, and persist progress checkpoints so interrupted runs can resume without recomputing completed cells. Users must be able to interrupt quickly (pause/stop within about 1 second via chunked/cooperative execution), and changing scenario-defining controls during an active run must be guarded (lock controls or require confirmation to stop and restart). Preserve deterministic status semantics (AVAILABLE/MISSING/NO_CONTEST/TIMEOUT/ERROR), preserve standalone AoF browser decoupling from simulator, and keep canonical solver-equivalence cache dedup behavior (seat-label-equivalent contexts reuse persisted cells without context leakage in UI payload). Include acceptance criteria and edge cases for: mid-run pause/resume, stop/restart, per-cell failure continuation, checkpoint recovery after app restart, UI responsiveness during long runs, and deterministic behavior under timeout/error conditions."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Run Precompute In Browser (Priority: P1)

As a standalone AoF browser user, I want to launch offline precompute directly from the browser UI so I can fill cache for the currently selected scenario without leaving the screen.

**Why this priority**: It unlocks the core workflow value immediately by making precompute available where users already work.

**Independent Test**: Open the AoF browser, start a run for current scenario, observe sequential 169-cell progression and completed run state without using CLI.

**Acceptance Scenarios**:

1. **Given** the browser is open and a valid scenario is selected, **When** the user clicks Start, **Then** precompute begins and run state changes to Running.
2. **Given** precompute is Running, **When** a cell completes, **Then** that cell in the matrix updates immediately with current value/status and progress increments.
3. **Given** a full matrix run completes, **When** the last cell is processed, **Then** run state changes to Completed and the final matrix is visible in UI.

---

### User Story 2 - Interrupt and Resume Safely (Priority: P2)

As a user running long precompute jobs, I want to pause, resume, or stop quickly so I stay in control and avoid wasting completed work.

**Why this priority**: Operational control and non-destructive interruption are essential for long-running GUI tasks.

**Independent Test**: Start a run, pause and resume it, stop it mid-way, then restart and verify the run continues from checkpoint without recomputing finished cells.

**Acceptance Scenarios**:

1. **Given** a run is Running, **When** the user clicks Pause, **Then** it transitions to Paused within about 1 second.
2. **Given** a run is Paused, **When** the user clicks Resume, **Then** it continues from the next unfinished cell.
3. **Given** a run is Running, **When** the user clicks Stop, **Then** current progress is checkpointed and state transitions to Stopping then Paused/Stopped.

---

### User Story 3 - Trustworthy Progress and Determinism (Priority: P3)

As a user, I want clear telemetry and deterministic run behavior so I can trust what is computed, what remains, and what failed.

**Why this priority**: Transparency and deterministic statuses reduce confusion and support confidence in cached results.

**Independent Test**: During run, verify telemetry updates (cells done, current cell, elapsed, ETA, failures) and deterministic status handling for timeout/error without UI freeze.

**Acceptance Scenarios**:

1. **Given** a run is active, **When** processing progresses, **Then** telemetry fields update continuously and accurately.
2. **Given** a cell times out or errors, **When** processing continues, **Then** failure count increases, deterministic cell status is shown, and next cells still run.
3. **Given** seat-label-equivalent contexts are requested, **When** cache is reused, **Then** deduplicated canonical cells are reused while request-local context display remains correct.

---

### Edge Cases

- User changes scenario-defining controls while run is active.
- App is closed during a Running or Paused run and reopened.
- Pause/stop is requested while a cell-chunk is in progress.
- A subset of cells fails repeatedly while others succeed.
- ETA cannot be computed early due to insufficient sample history.
- User starts a new run when a checkpoint for same scenario already exists.
- Canonical dedup causes cache hit for equivalent seat-label context.
- No-contest/strict-fold contexts should not enter compute loop.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST provide an in-GUI precompute runner panel in the standalone AoF browser.
- **FR-002**: Panel MUST provide controls for Start, Pause, Resume, Stop, and Reset.
- **FR-003**: Panel MUST provide simulations-per-cell input with default value 1000.
- **FR-004**: Run state MUST be visibly represented as Idle, Running, Paused, Stopping, Completed, or Failed.
- **FR-005**: Precompute execution MUST process cells sequentially from first to last until completion or interruption.
- **FR-006**: Matrix cell display MUST update immediately after each cell completes.
- **FR-007**: System MUST persist run checkpoints so interrupted runs resume without recomputing completed cells.
- **FR-008**: Pause and Stop requests MUST be cooperatively honored within about 1 second under normal workload.
- **FR-009**: UI MUST remain responsive during active runs.
- **FR-010**: Panel MUST show telemetry for completed cells, current cell, elapsed time, ETA, and failure count.
- **FR-011**: System MUST continue processing subsequent cells after per-cell timeout/error while recording failure count.
- **FR-012**: Deterministic status semantics MUST be preserved for AVAILABLE, MISSING, NO_CONTEST, TIMEOUT, and ERROR.
- **FR-013**: During active run, scenario-defining controls MUST be guarded by lock or confirmation gate.
- **FR-014**: Standalone AoF browser MUST remain decoupled from simulator workflows.
- **FR-015**: Canonical solver-equivalence dedup behavior MUST remain in effect for persistent cache reuse.
- **FR-016**: Canonical cache reuse MUST preserve request-local context in returned UI payloads.
- **FR-017**: Existing CLI precompute behavior MUST remain available and functionally consistent with GUI runner semantics.
- **FR-018**: Automated tests MUST cover run-state transitions, checkpoint resume, interruption responsiveness, deterministic status behavior, and canonical dedup correctness.

### Key Entities *(include if feature involves data)*

- **GuiPrecomputeRunSession**: Active UI run state for one selected scenario, including control state and progress counters.
- **CellPrecomputeProgress**: Per-cell checkpoint entry recording completion/failure and sequence cursor position.
- **RunnerTelemetrySnapshot**: Derived metrics displayed in panel, including elapsed time, ETA, current cell index, and failure count.
- **ScenarioGuardState**: UI-level lock/confirmation state for scenario-defining controls while run is active.

## Assumptions

- GUI precompute initially targets one currently selected scenario at a time.
- Sequential processing order is fixed matrix order for first implementation.
- Cell-level chunking is sufficient to satisfy pause/stop responsiveness target.
- Existing cache persistence layer is reused for checkpoint and result durability.

## Dependencies

- Existing AoF browser UI panel and matrix rendering components.
- Existing persistent cache store and canonical dedup key behavior.
- Existing solver-backed cell evaluation path with deterministic statuses.

## Risks

- UI responsiveness degradation under high simulations-per-cell settings.
- Inconsistent visual state if checkpoint writes fail during interruption.
- User confusion if active-run guard behavior is unclear.
- ETA volatility at early run stages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of pause/stop requests transition from Running to Paused/Stopping in <= 1 second under reference workload.
- **SC-002**: 100% of interrupted runs resume from persisted checkpoint without recomputing completed cells for the same scenario.
- **SC-003**: During active runs, UI remains interactive with no visible freeze longer than 200 ms on reference environment.
- **SC-004**: 100% of completed cell updates are visible in matrix immediately after each cell finishes.
- **SC-005**: 100% of timeout/error cells show deterministic statuses and do not abort full-run progression by default.
- **SC-006**: Automated tests validating run controls, checkpoint recovery, guard behavior, and canonical dedup all pass in CI.
