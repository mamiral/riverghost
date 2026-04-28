# Research: GUI Integration and UX Hardening on the GameStates-First Pipeline

**Feature**: `005-gui-pipeline-integration`  
**Date**: 2026-04-28

## R-001: Panel State Machine — Current vs. Required

**Question**: Does `AoFBrowserPanel` already maintain a formal panel state enum?

**Finding**: No. Panel state is implicit — derived at render time from a combination of:
- `self.is_loading: bool`
- `self.precompute_session` existence and `precompute_session.run_state` (`GuiRunState`)
- `self.payload["cells"]` content (empty → MISSING, non-empty → AVAILABLE)

There is no `PanelState` enum and no single attribute that stores the current panel state. The spec requires seven explicit states (`LOADING`, `AVAILABLE`, `MISSING`, `COMPUTING`, `STALE`, `NO_CONTEST`, `ERROR`).

**Decision**: Introduce a `PanelState` enum in `aof_browser_panel.py` (or a shared module) with the seven values. Derive it as a computed property from the existing fields — no new state storage needed. This avoids a wholesale refactor while giving a single authoritative answer to "what state is the panel in?"

**Rationale**: Computed property approach is the minimum change that satisfies FR-001 without restructuring the data flow. Storing it redundantly would risk getting out of sync.

**Alternatives considered**:
- Full state machine with explicit transitions: Too invasive for a GUI hardening feature.
- Leave implicit: Directly violates FR-001.

---

## R-002: Cross-Run Cumulative Aggregation — Implementation Path

**Question**: How should `BrowserDatabaseProvider.get_matrix_payload` aggregate across multiple runs?

**Finding**: `DatabaseRepository.list_matrix_sweep_runs_by_contract()` already exists (L1323) and returns all completed runs matching a canonical scenario contract in descending `end_timestamp` order. It uses the same contract key matching as `find_matrix_sweep_run_by_contract`.

The current `get_matrix_payload` calls `get_matrix_sweep_run_summary` → `find_matrix_sweep_run_by_contract` → returns the single latest run.

**Finding — sample count**: `AggregatedMetric` does not have a `sample_count` column. The aggregation service in `MatrixSweepAggregationService.aggregate_run()` computes `equity = (wins + 0.5 * ties) / total` where `total` is counted per cell from GameState rows — but never persists `total` to the DB. To display sample count in the cell detail panel (FR-019) and to do weighted cross-run merging, `sample_count` must be added.

**Decision**:
1. Add `sample_count = Column(Integer, nullable=True)` to `AggregatedMetric`.
2. Write `sample_count = total` during `MatrixSweepAggregationService.aggregate_run()`.
3. Add `get_cross_run_matrix_payload(scenario_contract)` to `DatabaseRepository`: calls `list_matrix_sweep_runs_by_contract`, loads all per-run `MatrixCell + AggregatedMetric`, merges by `hand_combination` using weighted average: `equity = sum(equity_i * n_i) / sum(n_i)`, `sample_count = sum(n_i)`.
4. `BrowserDatabaseProvider.get_matrix_payload` calls the new cross-run method instead of the single-run method.

**Rationale**: Weighted average by sample count is the correct merge for Monte Carlo equity estimates. Simple average would under-weight runs with more samples. The `sample_count` column is needed anyway for FR-019 (cell detail panel display).

**Alternatives considered**:
- Re-aggregate from raw GameStates across all runs: Correct but O(total_game_states) per fetch — too slow for interactive GUI.
- Store a cross-run summary table: Over-engineering for one-user desktop app; computed on read is sufficient.

---

## R-003: Start Button State — Gap in Current Code

**Question**: Does the current Start button handler support AVAILABLE state?

**Finding**: In `aof_browser_panel.py`, the Start button click path calls `_start_precompute()` when `precompute_session is None or precompute_session.run_state in {IDLE, COMPLETED, FAILED}`. When the panel is AVAILABLE (cells loaded, no active session), `precompute_session` is `None` — so Start already triggers.

However, `_start_precompute()` immediately overwrites `self.payload` with a blank MISSING-status grid (all cells set to `"status": "MISSING"`). This clears the displayed data — violating FR-006a and the Q5 answer (panel must stay AVAILABLE showing previous data during rerun).

**Decision**: Modify `_start_precompute()` to NOT overwrite `self.payload` when the panel is currently AVAILABLE. Instead, keep the existing payload and set a `self._rerun_in_progress: bool = True` flag. The panel state computed property checks this flag to overlay the COMPUTING indicator while still returning AVAILABLE cells.

**Rationale**: Minimal change — one flag and one conditional in `_start_precompute`. No structural refactor.

---

## R-004: Auto-Refresh After Precompute Completion

**Question**: Does the panel currently auto-refresh after precompute completes?

**Finding**: In `_tick_precompute()`, when `run_state == COMPLETED` the code calls `_persist_completed_precompute_payload()` — which is a no-op (Phase 4 cache removed). It does NOT call `_refresh()`. The panel stays showing the in-flight cell-by-cell data from the precompute run. It does not re-fetch the aggregated database results.

**Decision**: After `run_state == COMPLETED` and futures drained, call `self._refresh()` to trigger a fresh DB fetch. Clear `self._rerun_in_progress` after the refresh completes. The auto-refresh fires the `_start_async_refresh` → `pygame.USEREVENT` → `_handle_async_refresh_result` path already in place.

**Rationale**: The async refresh path already exists and is correct. It just needs to be called at job completion.

---

## R-005: Partial Cell Count Indicator

**Question**: Where and how should the "84 / 169 cells" indicator be rendered?

**Finding**: `AoFHandMatrixPanel` renders the 13×13 grid. `AoFBrowserPanel` owns the panel frame and draws precompute controls on the right sidebar. There is no existing partial-cell count display anywhere.

**Decision**: Render the indicator as a small text label below the matrix grid, visible only when cell count is between 1 and 168 (not shown for 0 or 169). `AoFBrowserPanel.draw()` computes `available_cell_count = sum(1 for c in payload["cells"] if c.get("status") == "AVAILABLE")` and draws the label conditionally. No new component needed.

**Rationale**: Single-line label drawn by the panel is the simplest approach. Adding it to `AoFHandMatrixPanel` would couple the matrix widget to payload structure — wrong responsibility.

---

## R-006: Context Invalidation — Current Behavior

**Question**: Does position/metric change currently clear the panel before re-fetching?

**Finding**: `_refresh()` sets `self.is_loading = True` and calls `_start_async_refresh()`. It does NOT clear `self.payload["cells"]` first. While loading, the panel renders stale cells from the previous scenario — directly violating FR-002 and FR-004.

**Decision**: At the start of `_refresh()`, before dispatching the async fetch, set all cells in `self.payload["cells"]` to `"status": "LOADING"` and clear `self.payload["context"]`. This immediately invalidates the display in the next draw frame.

---

## R-007: `sims_per_combo` Contract Mismatch (Known Bug — Out of Scope)

**Question**: Does `_build_scenario_contract()` hardcode `sims_per_combo: 120`?

**Finding**: `BrowserDatabaseProvider._build_scenario_contract()` (L184) hardcodes `"sims_per_combo": 120` regardless of the user's slider setting (`precompute_simulations_per_cell`). This means a run started with 1000 sims/combo will not be found by `find_matrix_sweep_run_by_contract` if the contract builder uses 120.

**Decision**: This is a pre-existing bug. It is NOT in scope for this feature — fixing it requires understanding the full contract normalization path. Flag it as a follow-up issue during implementation. The cross-run aggregation logic (R-002) uses `list_matrix_sweep_runs_by_contract` which uses the same contract builder — the mismatch affects both single-run and cross-run lookups equally.

---

## R-008: Database Migration for `sample_count`

**Question**: Does adding `sample_count` to `AggregatedMetric` require a migration?

**Finding**: The project uses `connection.create_tables()` which calls `Base.metadata.create_all()`. SQLite `create_all` does NOT alter existing tables — it only creates missing ones. Existing rows will have `sample_count = NULL` (column is `nullable=True`), which is correct for legacy data. No migration script needed for SQLite in development. Production deployments would need `ALTER TABLE aggregated_metrics ADD COLUMN sample_count INTEGER`.

**Decision**: Add the column as `nullable=True`. Cross-run merge handles `NULL` sample_count by treating it as 0 (excluded from weighted average). Existing tests remain valid.
