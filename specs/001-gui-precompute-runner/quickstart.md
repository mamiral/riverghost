# Quickstart: In-GUI AoF Precompute Runner

## Prerequisites
- Active project virtual environment (`.venv`).
- Commands run from repository root unless noted.
- Existing AoF browser and cache modules available.

## 1. Baseline Targeted Tests
Run existing relevant tests before implementation changes:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_precompute_runner.py tests/test_aof_solver_provider_cache.py tests/test_gto_gui_integration.py -q
```

## 2. Launch AoF Browser for Manual Validation
Run the interactive simulator entrypoint and open the AoF browser panel flow:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m hopilot.aof_gto_browser_gui
```

Manual validation checklist:
1. Select scenario (position/actions/metric).
2. Start GUI precompute with default simulations-per-cell = 1000.
3. Confirm state transitions IDLE -> RUNNING and matrix updates per completed cell.
4. Pause during active run and confirm transition to PAUSED within about 1 second.
5. Resume and confirm processing continues from next unfinished cell.
6. Stop mid-run and confirm checkpoint saved.
7. Restart app and verify checkpoint recovery path restores paused/running checkpoint state.
8. While run is active, click position or metric controls and verify guard message is shown and scenario is not changed.

## 3. Deterministic Failure Semantics Validation
Use test doubles to force timeout/error outcomes and confirm:
1. Cell status rendered as TIMEOUT/ERROR deterministically.
2. Failure count increments.
3. Subsequent cells continue processing unless runner-level failure occurs.

Planned automated coverage:
- `tests/test_aof_gui_precompute_runner_state.py`
- `tests/test_aof_gui_precompute_runner_resume.py`
- `tests/test_aof_gui_precompute_runner_responsiveness.py`
- `tests/test_gto_gui_integration.py`

## 4. Canonical Dedup + Context Hydration Validation
1. Run a scenario to persist canonical cell data.
2. Request solver-equivalent seat-label scenario from GUI.
3. Verify persisted cells are reused and UI context reflects active selection without leakage.

Planned automated coverage:
- `tests/test_aof_gui_precompute_runner_canonical_dedup.py`

## 5. Acceptance Outcome Mapping
- SC-001: interruption responsiveness measured by pause/stop acknowledgement timing tests.
- SC-002: checkpoint resume without recompute validated by restart/resume tests.
- SC-003: UI responsiveness validated by integration tests and manual interaction checks.
- SC-004: immediate per-cell matrix updates validated by state-to-render tests.
- SC-005: deterministic timeout/error continuation validated by failure-path tests.
- SC-006: full control/guard/dedup suite passing in CI.

## Notes
- Maintain existing deterministic status semantics from `AoFBrowserDataProvider`.
- Preserve canonical solver-equivalence key usage from cache store and precompute runner paths.
