# Quickstart: Implement Cell Detail Middle Panel

## Prerequisites
- Activate project venv.
- Run from repository root for tests unless a command explicitly requires `python/`.

## 1) Implement middle panel component
1. Add `python/hopilot/gui_components/aof_cell_detail_panel.py`.
2. Implement renderer API that accepts:
   - selected cell detail view model
   - current metric
   - fallback/empty state
3. Implement vertical stacked rendering for WIN_LOSE_PROBABILITY.
4. Implement scalar-consistent rendering for EV/EQUITY/EQR.

## 2) Add selection wiring
1. Extend matrix panel or browser panel event handling to detect clicked matrix cell.
2. Add/maintain `selected_cell` browser state.
3. Build a detail view model from selected payload cell + metric + status.

## 3) Integrate layout and reflow
1. Update `AoFBrowserPanel` layout budget to create a compact middle panel column.
2. Ensure matrix, middle panel, and right controls remain visible and non-overlapping.
3. Keep right-side control interaction behavior unchanged.

## 4) Fallback behavior
1. Map statuses (`MISSING`, `TIMEOUT`, `ERROR`, `NO_CONTEST`) to explicit detail-panel fallback messages.
2. Add empty-state for no selection.

## 5) Validate with tests
- Suggested commands:
```bash
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_gto_browser_gui.py -q
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_gto_gui_integration.py -k "aof or precompute or metric" -q
```

### Validation Run (2026-03-13)
- Executed:
```bash
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_gto_browser_gui.py -q
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_gto_gui_integration.py -q
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_gto_browser_gui.py tests/test_gto_gui_integration.py -q
```
- Outcome:
   - All targeted AoF GUI tests passed after middle panel integration.
   - Final combined regression run passed: 45 passed, 1 warning.
   - Warning was from upstream pygame/setuptools deprecation notice (`pkg_resources`) and is unrelated to feature behavior.

## 6) Manual verification
1. Launch GUI from `python/` directory:
```bash
python -m hopilot.aof_gto_browser_gui
```
2. Confirm:
   - no-selection empty state
   - click-to-update detail panel
   - metric switch updates detail representation
   - right control panel remains fully usable

### Expected Middle Panel Checks
- WIN_LOSE_PROBABILITY shows stacked Win/Tie/Loss segments with labels.
- EV/EQUITY/EQR show scalar view with metric-formatted value.
- MISSING/TIMEOUT/ERROR/NO_CONTEST display explicit fallback text and fallback badge.
