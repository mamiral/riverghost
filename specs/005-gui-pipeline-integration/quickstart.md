# Quickstart: GUI Integration and UX Hardening on the GameStates-First Pipeline

**Feature branch**: `005-gui-pipeline-integration`

## What This Feature Does

- Adds a `PanelState` enum and computed property to `AoFBrowserPanel` so all seven states (`LOADING`, `AVAILABLE`, `MISSING`, `COMPUTING`, `STALE`, `NO_CONTEST`, `ERROR`) are explicit and rendering/button logic reads from a single source.
- Fixes the Start button to be enabled in `AVAILABLE` state, with the panel keeping previous cell data visible during a rerun (computing overlay instead of blank screen).
- Adds cross-run cumulative aggregation: scenarios run multiple times show combined sample counts and weighted-average equity.
- Adds `sample_count` to `AggregatedMetric` for cell detail panel display.
- Fixes context invalidation: position/metric changes clear stale cell data immediately.
- Adds a partial cell count indicator ("84 / 169 cells") when the matrix is partially populated.
- Triggers automatic DB re-fetch after precompute completion.

## Files Changed

| File | Change |
|------|--------|
| `python/hopilot/models/aggregated_metric.py` | Add `sample_count` column |
| `python/hopilot/gto/matrix_sweep_aggregation_service.py` | Write `sample_count` during `aggregate_run` |
| `python/hopilot/gto/database_repository.py` | Add `get_cross_run_cells()` method |
| `python/hopilot/gto/browser_database_provider.py` | Call cross-run method; use `sample_count` in payload |
| `python/hopilot/gui_components/aof_browser_panel.py` | `PanelState` enum, `panel_state` property, `_rerun_in_progress` flag, `_last_error`, context invalidation, auto-refresh, cell count indicator, button enable logic |

## Running Tests

```powershell
# From repo root with venv active
pytest tests/
```

All existing tests must pass. New tests:
- `tests/test_cross_run_aggregation.py` — cross-run merge logic
- Additions to `tests/test_aof_browser_panel_database_integration.py` — panel state transitions

## Manual Validation Steps (SC-005)

1. Open the AoF Browser against an empty database: `python -m hopilot.aof_gto_browser_gui --database-url sqlite:///temp_test_db/test.db`
2. Select any position → panel shows `MISSING`
3. Click Start → panel shows `COMPUTING`
4. Let run complete → panel auto-refreshes to `AVAILABLE`
5. Check a cell → detail panel shows metric value and sample count
6. Note the scenario-level sample count
7. Click Start again (from `AVAILABLE`) → panel stays `AVAILABLE` showing previous data; computing overlay appears
8. Let run complete → panel refreshes; sample count is higher than step 6

## Key Design Decisions

- **`panel_state` is computed, not stored** — derived from `is_loading`, `precompute_session.run_state`, `payload["cells"]`, `_rerun_in_progress`, `_last_error`. Single source of truth, no risk of desync.
- **Cross-run merge is weighted average** — `equity = Σ(equity_i × n_i) / Σ(n_i)` where `n_i = sample_count`. Legacy rows with NULL sample_count are excluded from the weighted average.
- **No new ORM tables** — `sample_count` is a nullable column on `AggregatedMetric`. SQLite `create_all` handles new databases automatically. Existing databases need a one-time `ALTER TABLE`.

## Caveats

- Partial stop and pause preserve computed values that are already available. Remaining cells are still marked `MISSING` until they are recomputed or a fresh run completes.
- `AVAILABLE` reruns keep previous scenario data visible and show a computing overlay; the panel does not immediately discard past results when rerunning.
- The `sample_count` field is only available after the back-end aggregation path writes it. Older payload rows without `sample_count` are still displayed, but their weighted-average equity will ignore those legacy rows.
- Manual SC-005 validation remains required to complete the feature acceptance checklist. Record actual run results under `Manual Validation Status` once performed.

## Manual Validation Status

- SC-005 manual workflow: pending
- Notes: The GUI state machine and database refresh behavior have been validated by targeted and full pytest runs, but the final acceptance result must be confirmed with a live DB run.
