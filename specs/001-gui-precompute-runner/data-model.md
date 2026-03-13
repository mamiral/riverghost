# Data Model: In-GUI AoF Precompute Runner

## GuiPrecomputeRunSession
- Description: Authoritative run session state for one selected AoF scenario in the browser UI.
- Fields:
  - run_id: nullable integer (links to persisted run record)
  - scenario_fingerprint: string (normalized scenario identity for guard/checkpoint matching)
  - run_state: enum (IDLE, RUNNING, PAUSED, STOPPING, COMPLETED, FAILED)
  - simulations_per_cell: integer (default 1000)
  - total_cells: integer (fixed 169)
  - completed_cells: integer
  - failed_cells: integer
  - next_cell_index: integer (0-169)
  - current_cell_index: nullable integer
  - started_at: datetime
  - paused_at: nullable datetime
  - finished_at: nullable datetime
  - elapsed_active_ms: integer
  - eta_seconds: nullable float
- Validation rules:
  - simulations_per_cell >= 1
  - completed_cells + failed_cells <= total_cells
  - next_cell_index in [0, total_cells]
  - run_state transitions must follow state machine constraints.

## CellPrecomputeProgress
- Description: Checkpointed per-cell progress and latest deterministic output for resume and telemetry.
- Fields:
  - run_id: integer
  - cell_index: integer (0-168)
  - hand_key: string
  - status: enum (AVAILABLE, MISSING, NO_CONTEST, TIMEOUT, ERROR)
  - value: nullable float
  - display: string
  - attempts: integer
  - updated_at: datetime
  - error_message: nullable string
- Validation rules:
  - Each (run_id, cell_index) unique in checkpoint snapshot view.
  - status must be from deterministic status set.
  - value must be null when status in (TIMEOUT, ERROR, MISSING, NO_CONTEST where value absent by policy).

## RunnerTelemetrySnapshot
- Description: UI-facing derived metrics refreshed during active run and pause/resume.
- Fields:
  - run_state: enum
  - completed_cells: integer
  - total_cells: integer (169)
  - current_cell_label: nullable string (for example "AKo")
  - elapsed_seconds: float
  - eta_seconds: nullable float
  - failure_count: integer
  - throughput_cells_per_minute: nullable float
  - last_update_at: datetime
- Validation rules:
  - completed_cells in [0, total_cells]
  - failure_count >= 0
  - eta_seconds is null until enough timing samples exist.

## ScenarioGuardState
- Description: Browser UI lock/confirmation state for scenario-defining controls during active run.
- Fields:
  - controls_locked: boolean
  - lock_reason: enum (RUN_ACTIVE, STOPPING, NONE)
  - pending_change: nullable object (position/actions/metric changes requested while locked)
  - requires_confirm_stop: boolean
  - prompt_visible: boolean
- Validation rules:
  - controls_locked true for RUNNING and STOPPING.
  - pending_change can be applied only after stop completion or explicit discard.

## PersistedRunCheckpoint
- Description: Durable checkpoint record mapped to existing precompute run metadata, extended for GUI resume semantics.
- Fields:
  - run_id: integer
  - scenario_fingerprint: string
  - canonical_solver_key: string
  - resume_cursor: integer
  - completed_cells: integer
  - failed_cells: integer
  - status: enum (RUNNING, PAUSED, COMPLETED, FAILED, STOPPED)
  - updated_at: datetime
- Validation rules:
  - resume_cursor monotonic non-decreasing for same run_id.
  - scenario_fingerprint and canonical_solver_key must match active selection before resume.

## Relationships
- GuiPrecomputeRunSession 1:1 RunnerTelemetrySnapshot
- GuiPrecomputeRunSession 1:1 ScenarioGuardState
- GuiPrecomputeRunSession 1:N CellPrecomputeProgress
- GuiPrecomputeRunSession 1:1 PersistedRunCheckpoint
- PersistedRunCheckpoint maps to existing `aof_precompute_run` and `aof_precompute_write_result` lifecycle records.

## State Transitions
- IDLE -> RUNNING: Start pressed with valid scenario and runner initialized.
- RUNNING -> PAUSED: Pause requested and acknowledged at cooperative chunk boundary (target <= 1 second).
- RUNNING -> STOPPING: Stop requested; runner drains current chunk and checkpoints.
- STOPPING -> PAUSED: Stop acknowledged before natural completion.
- RUNNING -> COMPLETED: all 169 cells processed.
- RUNNING -> FAILED: unrecoverable runner-level error (not per-cell deterministic failure).
- PAUSED -> RUNNING: Resume with unchanged scenario fingerprint.
- PAUSED -> IDLE: Reset/discard checkpoint.
- COMPLETED/FAILED -> IDLE: Start new run or explicit reset.
