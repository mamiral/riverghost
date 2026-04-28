# Data Model: GUI Integration and UX Hardening on the GameStates-First Pipeline

**Feature**: `005-gui-pipeline-integration`  
**Date**: 2026-04-28

## Overview

This feature introduces one new enum, one new flag, one new ORM column, and one new repository method. No new tables. No new ORM models. No changes to `GameState`.

---

## New: `PanelState` Enum

**Location**: `python/hopilot/gui_components/aof_browser_panel.py` (top of file, or extracted to `python/hopilot/gto/aof_browser_state.py`)

```python
from enum import Enum

class PanelState(str, Enum):
    LOADING    = "LOADING"     # Fetch in progress
    AVAILABLE  = "AVAILABLE"   # >=1 cells present
    MISSING    = "MISSING"     # Zero cells in DB
    COMPUTING  = "COMPUTING"   # Precompute job running (no prior data)
    STALE      = "STALE"       # Context changed, new fetch pending
    NO_CONTEST = "NO_CONTEST"  # All cells are NO_CONTEST
    ERROR      = "ERROR"       # Fetch failed or job failed
```

**Derivation** (computed property, not stored):

```
is_loading=True                          → LOADING
is_loading=False AND job RUNNING AND no prior data → COMPUTING
is_loading=False AND job RUNNING AND prior cells   → AVAILABLE (with _rerun_in_progress=True overlay)
is_loading=False AND cells=[] AND no error         → MISSING
is_loading=False AND all cells NO_CONTEST          → NO_CONTEST
is_loading=False AND cells>0                       → AVAILABLE
error present                                      → ERROR
```

**Validation rules**:
- State is read-only; derived from `is_loading`, `precompute_session.run_state`, `payload["cells"]`, `_rerun_in_progress`, and `_last_error`.
- Never stored redundantly — always computed on access.

---

## New Flag: `_rerun_in_progress`

**Location**: `AoFBrowserPanel` instance attribute  
**Type**: `bool`  
**Default**: `False`

Set to `True` when Start is clicked while panel is `AVAILABLE`. Cleared when the post-rerun `_refresh()` completes. Used by the computed `panel_state` property and `draw()` to show the COMPUTING overlay without clearing cell data.

---

## Modified ORM Model: `AggregatedMetric`

**Location**: `python/hopilot/models/aggregated_metric.py`

**New column**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `sample_count` | `Integer` | Yes | NULL | Number of raw GameState rows contributing to this cell's aggregated metric. Written by `MatrixSweepAggregationService.aggregate_run()`. NULL for legacy rows. |

**Existing columns unchanged**: `cell_id`, `equity`, `win_probability`, `ev`, `jackpot_adjusted_ev`, `jackpot_frequency`, `avg_jackpot_payout`, `convergence_status`, `last_updated`.

**Validation rules**:
- `sample_count >= 0` when not NULL.
- Written once per aggregation run; not updated by cross-run queries.

**Migration**: Column added as `nullable=True`; existing rows have `sample_count = NULL`. SQLite `create_all` adds the column to new databases only. Existing databases need: `ALTER TABLE aggregated_metrics ADD COLUMN sample_count INTEGER`.

---

## New Repository Method: `get_cross_run_matrix_payload`

**Location**: `python/hopilot/gto/database_repository.py` (or `BrowserDatabaseProvider`)

**Signature**:
```python
def get_cross_run_cells(
    self,
    scenario_contract: Dict[str, Any],
    metric: str,
) -> List[Dict[str, Any]]:
    """
    Return 169 merged cell records aggregated across all completed runs
    matching the canonical scenario contract.

    Returns cells sorted by (row_index, col_index).
    Each cell dict has: hand_combination, row_index, col_index,
    equity, win_probability, sample_count, status.
    """
```

**Merge logic**:
- For each `hand_combination` across all matching runs, collect `(equity_i, sample_count_i)` pairs where `sample_count_i > 0`.
- `merged_equity = sum(equity_i * n_i) / sum(n_i)`
- `merged_sample_count = sum(n_i)`
- Rows with `sample_count IS NULL` or `0` are skipped in the weighted average.
- If a cell has no samples across any run, `status = "MISSING"`.
- If `merged_equity` is non-NULL and count > 0, `status = "AVAILABLE"`.

**State transitions**: Replaces `get_matrix_sweep_run_summary` call path in `BrowserDatabaseProvider.get_matrix_payload`.

---

## Unchanged Entities

| Entity | Location | Change |
|--------|----------|--------|
| `GameState` | `python/hopilot/models/game_state.py` | None — Architecture constraint: no cell_id or run FK |
| `Simulation` | `python/hopilot/models/simulation.py` | None |
| `HandMatrix` | `python/hopilot/models/hand_matrix.py` | None |
| `MatrixCell` | `python/hopilot/models/matrix_cell.py` | None |
| `AoFBrowserViewState` | `python/hopilot/gto/aof_browser_state.py` | None |
| `GuiPrecomputeRunSession` | `python/hopilot/gto/aof_precompute_runner.py` | None |
| `GuiRunState` | `python/hopilot/gto/aof_precompute_runner.py` | None |

---

## State Transition Map

```
Panel opens
  └─→ is_loading=True → PanelState.LOADING

DB fetch completes (success, cells>0)
  └─→ is_loading=False, cells populated → PanelState.AVAILABLE

DB fetch completes (success, cells=0)
  └─→ is_loading=False, cells empty → PanelState.MISSING

DB fetch completes (all cells NO_CONTEST)
  └─→ is_loading=False → PanelState.NO_CONTEST

DB fetch fails
  └─→ is_loading=False, _last_error set → PanelState.ERROR

User clicks Start (from MISSING / NO_CONTEST / ERROR)
  └─→ precompute_session.run_state=RUNNING, payload cleared → PanelState.COMPUTING

User clicks Start (from AVAILABLE)
  └─→ precompute_session.run_state=RUNNING, _rerun_in_progress=True
      payload NOT cleared → PanelState.AVAILABLE + computing overlay

Position or metric changed
  └─→ payload cells set to LOADING status, is_loading=True → PanelState.LOADING

Precompute job COMPLETED (from COMPUTING)
  └─→ _refresh() called → PanelState.LOADING → PanelState.AVAILABLE

Precompute job COMPLETED (from AVAILABLE + _rerun_in_progress)
  └─→ _refresh() called, _rerun_in_progress=False → PanelState.LOADING → PanelState.AVAILABLE

Precompute job FAILED
  └─→ _last_error set → PanelState.ERROR
```
