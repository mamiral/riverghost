# Phase 0 Research: In-GUI AoF Precompute Runner

## Decision 1: Keep sequential cell execution with cooperative chunks
- Decision: Process the 169 matrix cells in fixed row-major order, but execute each cell in bounded cooperative chunks so pause/stop requests are checked frequently.
- Rationale: Preserves deterministic progression while satisfying <= 1 second interruption responsiveness and UI responsiveness goals.
- Alternatives considered: fully synchronous per-cell solve loop, parallel worker pool per row.

## Decision 2: Reuse existing persistent cache + precompute run metadata
- Decision: Persist GUI run checkpoints in the existing precompute metadata path (`aof_precompute_run`, `aof_precompute_write_result`) and reuse canonical solver-equivalence keys.
- Rationale: Avoids introducing divergent checkpoint semantics and preserves already-validated dedup behavior from offline precompute.
- Alternatives considered: separate GUI-only checkpoint file, in-memory-only resume state.

## Decision 3: Introduce explicit GUI run-state machine
- Decision: Model run lifecycle as Idle -> Running -> Paused -> Running, with Stopping as a transient state and terminal Completed/Failed states.
- Rationale: Matches feature requirements, makes control enablement deterministic, and simplifies testing of transitions.
- Alternatives considered: loosely coupled boolean flags (`is_running`, `is_paused`, `stop_requested`).

## Decision 4: Preserve deterministic status semantics and failure continuation
- Decision: Keep per-cell statuses constrained to AVAILABLE/MISSING/NO_CONTEST/TIMEOUT/ERROR and continue processing subsequent cells after TIMEOUT/ERROR while incrementing failure telemetry.
- Rationale: Aligns with existing provider behavior and user requirement for trustworthy deterministic outcomes during long runs.
- Alternatives considered: abort-on-first-error policy, retry-without-status policy.

## Decision 5: Guard scenario-defining controls during active run
- Decision: Lock scenario controls while Running/Stopping and require explicit stop-confirm-restart flow when user attempts scenario-changing actions.
- Rationale: Prevents checkpoint ambiguity and context leakage while preserving user control.
- Alternatives considered: allow free changes with implicit cancellation, queue scenario change for post-run apply.

## Decision 6: Hydrate request-local context even on canonical cache reuse
- Decision: Continue using canonical persistent cell reuse but always return payload context from the active GUI selection.
- Rationale: Keeps dedup efficiency while preventing cross-context UI confusion; aligns with existing provider hydration behavior.
- Alternatives considered: return canonical context directly from store, disable canonical dedup for GUI runs.

## Decision 7: Emit runner telemetry from authoritative session counters
- Decision: Compute telemetry (`completed/169`, current cell, elapsed, ETA, failures) from session checkpoint counters and chunk timing samples rather than inferred matrix scans.
- Rationale: Produces stable progress values during pauses/resumes and avoids expensive per-frame recomputation.
- Alternatives considered: derive completion by scanning matrix statuses every frame.
