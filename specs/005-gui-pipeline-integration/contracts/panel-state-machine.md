# Contract: Panel State Machine

**Feature**: `005-gui-pipeline-integration`  
**Date**: 2026-04-28  
**Type**: Internal GUI contract — defines the authoritative interface between panel state derivation and rendering/control logic.

---

## Overview

`AoFBrowserPanel` exposes a single computed property `panel_state: PanelState` that all rendering and button-enable logic MUST read. No rendering code may inspect `is_loading`, `precompute_session`, or `payload` directly to determine what to draw — it MUST go through `panel_state`.

---

## `PanelState` Values and Triggers

| Value | Trigger Condition | Start | Pause | Resume | Stop |
|-------|-------------------|-------|-------|--------|------|
| `LOADING` | `is_loading=True` | disabled | disabled | disabled | disabled |
| `AVAILABLE` | cells ≥ 1, no active job | **enabled** | disabled | disabled | disabled |
| `AVAILABLE` + overlay | cells ≥ 1, `_rerun_in_progress=True` | disabled | **enabled** | disabled | **enabled** |
| `MISSING` | cells = 0, no error | **enabled** | disabled | disabled | disabled |
| `COMPUTING` | job RUNNING, cells = 0 | disabled | **enabled** | disabled | **enabled** |
| `STALE` | _(reserved — not used in this feature)_ | disabled | disabled | disabled | disabled |
| `NO_CONTEST` | all cells NO_CONTEST | **enabled** | disabled | disabled | disabled |
| `ERROR` | `_last_error` set | **enabled** | disabled | disabled | disabled |

---

## Derivation Algorithm

```python
@property
def panel_state(self) -> PanelState:
    if self._last_error and not self.is_loading:
        return PanelState.ERROR
    if self.is_loading:
        return PanelState.LOADING
    cells = self.payload.get("cells", [])
    has_data = any(c.get("status") == "AVAILABLE" for c in cells)
    job_running = (
        self.precompute_session is not None
        and self.precompute_session.run_state == GuiRunState.RUNNING
    )
    if job_running and not has_data:
        return PanelState.COMPUTING
    # job_running + has_data is AVAILABLE with overlay (checked via _rerun_in_progress)
    if not cells or not has_data:
        all_no_contest = cells and all(
            c.get("status") == "NO_CONTEST" for c in cells if c.get("status") != "MISSING"
        )
        if all_no_contest:
            return PanelState.NO_CONTEST
        return PanelState.MISSING
    return PanelState.AVAILABLE
```

---

## Button Enable Contract

```python
def _start_enabled(self) -> bool:
    state = self.panel_state
    return state in (PanelState.AVAILABLE, PanelState.MISSING, PanelState.NO_CONTEST, PanelState.ERROR) \
        and not self._rerun_in_progress

def _pause_enabled(self) -> bool:
    return self._rerun_in_progress or self.panel_state == PanelState.COMPUTING

def _resume_enabled(self) -> bool:
    return (
        self.precompute_session is not None
        and self.precompute_session.run_state == GuiRunState.PAUSED
    )

def _stop_enabled(self) -> bool:
    return self._rerun_in_progress or self.panel_state == PanelState.COMPUTING
```

---

## Cell Count Indicator Contract

The indicator MUST be rendered when:
```python
available_count = sum(1 for c in payload["cells"] if c.get("status") == "AVAILABLE")
show_indicator = 1 <= available_count <= 168
indicator_text = f"{available_count} / 169 cells"
```

The indicator MUST NOT be rendered when `available_count == 0` or `available_count == 169`.

---

## Context Invalidation Contract

When `set_position()` or `set_metric()` is called on `AoFBrowserViewState`, `AoFBrowserPanel._refresh()` MUST:
1. Set all cells in `payload["cells"]` to `{"status": "LOADING"}` before dispatching the async fetch.
2. Clear `payload["context"]`.
3. Set `is_loading = True`.

This guarantees FR-004: no stale data from a previous scenario is visible during loading.

---

## Refresh-After-Completion Contract

When `precompute_session.run_state` transitions to `COMPLETED` and `precompute_futures` is empty:
1. Clear `_rerun_in_progress`.
2. Call `self._refresh()` to trigger a new DB fetch.
3. The fetch MUST use `get_cross_run_cells` (cross-run aggregation path, per FR-010a).

---

## Error Handling Contract

When an async DB fetch fails:
1. Set `self._last_error = error_message`.
2. Set `self.is_loading = False`.
3. Clear `payload["cells"]` to empty list.
4. `panel_state` → `ERROR`.

When a precompute job fails (`run_state == FAILED`):
1. Set `self._last_error = failure_reason`.
2. Clear `_rerun_in_progress`.
3. `panel_state` → `ERROR`.

When the user clicks Start from `ERROR` state:
1. Clear `self._last_error`.
2. Proceed with normal `_start_precompute()`.
