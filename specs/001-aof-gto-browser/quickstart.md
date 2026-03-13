# Quickstart: Standalone AoF GTO Solution Browser

## 1. Environment
1. Activate virtual environment.
2. From repository root, move to python directory before running modules.

```powershell
.venv\Scripts\Activate.ps1
cd python
```

## 2. Run Existing Simulator (Regression Baseline)
Use this to verify simulator remains pristine after AoF decoupling.

```powershell
python -m hopilot.poker_simulator_gui
```

Expected baseline after implementation:
- Simulator loads without AoF browser controls or AoF navigation tab.
- Existing simulation workflows remain functional.

## 3. Run Standalone AoF Browser
Run the new standalone module entrypoint (module name finalized during implementation).

```powershell
python -m hopilot.aof_gto_browser_gui
```

Expected behavior:
- Position controls visible above matrix: UTG, BTN, SB, BB.
- Action controls available: fold, all-in.
- Metric dropdown options available: win/lose probability, EV, equity, EQR.
- Matrix shown in lower-middle area with suited/offsuit/pairs.

## 4. Test Scope
Run targeted tests for simulator regression and new AoF browser behavior.

```powershell
cd ..
pytest tests/test_poker_simulator_gui.py -v
pytest tests/test_simulation_panel.py -v
pytest tests/test_gto_gui_integration.py -v
pytest tests/ -k "aof or gto browser" -v
```

## 5. Manual Verification Flow
1. Launch standalone AoF browser.
2. Select each position and verify matrix updates.
3. For one position, toggle fold/all-in and verify values change.
4. For one context, switch all four metrics and verify matrix semantics update.
5. Validate empty-state behavior by loading a context with missing data.

## 6. Benchmark Method
- Startup timing: measured with `time.perf_counter()` around `AoFGTOBrowserGUI` construction in `tests/test_aof_gto_browser_gui.py`.
- Switch latency: measured with `time.perf_counter()` around selector event handling in `tests/test_gto_gui_integration.py`.
- Thresholds:
	- Startup <= 30.0s
	- Position/action/metric switch <= 1.0s per interaction (as baseline regression guard)

## 7. Latest Validation Results
- Date: 2026-03-12
- Command:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_gto_browser_gui.py tests/test_simulation_panel.py tests/test_poker_simulator_gui.py tests/test_gto_gui_integration.py -q
```

- Result: `67 passed, 2 warnings`
