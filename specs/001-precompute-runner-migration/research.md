# Research: Precompute Runner Sweep Delegation

## Decision 1: Delegate scenario execution through `MatrixSweepService.run_sweep(...)`

**Decision**: The runner will invoke `run_matrix_sweep(...)`/`MatrixSweepService.run_sweep(...)` per scenario and stop using per-cell solver and manual persistence writes.

**Rationale**: `MatrixSweepService` already owns the production GameStates-first raw-write and aggregation pipeline. Reusing it removes duplicate persistence behavior and aligns with validated architecture.

**Alternatives considered**:

- Keep `compute_gui_cell(...)` and patch dead-schema calls: rejected because runner remains coupled to low-level manufacturing and duplicates sweep logic.
- Embed prototype scripts directly in runner: rejected because it bypasses production service boundaries.

## Decision 2: Remove dead-schema persistence from runner path

**Decision**: Eliminate runner-side calls that create `board_cards`, `bets`, and `jackpots` as part of precompute execution (`_store_individual_outcomes_as_game_states`, `_check_and_create_jackpots_for_game_state`, `_persist_scenario_results` path).

**Rationale**: These methods implement old schema assumptions and violate the target architecture where solver raw writes and post-processing are owned by the sweep service.

**Alternatives considered**:

- Keep dead-schema writes behind feature flags: rejected because it leaves two authoritative write paths and increases risk.
- Convert dead-schema methods to wrappers around new service: rejected because wrappers add indirection without value.

## Decision 3: Keep lifecycle orchestration in runner with stable state semantics

**Decision**: Preserve `GuiRunState` transitions (`IDLE`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`, `FAILED`) and telemetry snapshot semantics while changing internal execution from cell-loop to scenario-sweep execution.

**Rationale**: GUI and orchestration flows depend on existing lifecycle semantics; migration goal is data-path replacement, not state-model redesign.

**Alternatives considered**:

- Replace lifecycle model with sweep-native statuses only: rejected because it would force broad UI contract changes.
- Keep cell-index progress as primary metric: rejected because scenario-sweep execution no longer has runner-managed per-cell dispatch.

## Decision 4: Persist dedicated job-to-simulation linkage records

**Decision**: Persist one dedicated linkage record per requested scenario with `job_session_id`, normalized scenario key/fingerprint, delegated `simulation_id`, terminal status, and failure boundary details.

**Rationale**: Session cache-only tracking is non-durable. Dedicated records satisfy traceability requirements for UI-driven job history and post-run inspection.

**Alternatives considered**:

- Store linkage only in memory (`_gui_sessions`): rejected because data is lost across restarts.
- Store linkage only in `Simulation.parameters`: rejected because it weakens queryability and job-centric reporting.

## Decision 5: Report progress by scenario-phase snapshots, not per-cell callbacks

**Decision**: Progress reporting will expose processed scenario counts, active scenario identity, and phase (`orchestration`, `solver_write`, `aggregation`) while preserving lifecycle state compatibility.

**Rationale**: Delegated sweep execution changes granularity from cell-level loops to run-level orchestration.

**Alternatives considered**:

- Retain `on_cell_complete` semantics as authoritative: rejected because the runner no longer drives cell-by-cell writes.
- Suppress progress until run completion: rejected because it degrades operator visibility.

## Decision 6: Enforce explicit failure boundaries with no automatic retries

**Decision**: Persist boundary-classified failures (`orchestration`, `solver_write`, `aggregation`) and do not add automatic retries in this feature.

**Rationale**: Clear failure boundaries are required for operational clarity, and automatic retry logic would expand scope and alter existing behavior.

**Alternatives considered**:

- Retry all failures once: rejected because it conflates deterministic data failures with transient orchestration failures.
- No boundary classification: rejected because it weakens observability and troubleshooting.
