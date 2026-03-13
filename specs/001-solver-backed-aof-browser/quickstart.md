# Quickstart: Solver-Backed AoF Browser

## Prerequisites
- Active virtual environment in repo root (`.venv`).
- Commands run from repository root unless explicitly noted.

## Run AoF Browser
```powershell
cd python
python -m hopilot.aof_gto_browser_gui
```

## Validate Feature Behavior
1. Start with default context and verify matrix renders 169 cells.
2. Toggle position action states and confirm context summary changes.
3. Switch metrics (`WIN_LOSE_PROBABILITY`, `EV`, `EQUITY`, `EQR`) and verify matrix updates.
4. Trigger repeated context toggles and verify responsive cached behavior.
5. Exercise edge-case contexts:
   - all positions fold
   - only one all-in
   - selected position folds while others all-in
   - solver timeout or failure simulation

## Automated Tests
```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_solver_adapter_exact_path.py tests/test_aof_gto_browser_gui.py tests/test_gto_gui_integration.py tests/test_aof_solver_provider_contract.py tests/test_aof_solver_provider_metrics.py tests/test_aof_solver_provider_context.py tests/test_aof_solver_provider_edge_cases.py tests/test_aof_solver_provider_cache.py tests/test_aof_solver_provider_resilience.py tests/test_poker_simulator_gui.py -q
```

## Test Evidence
- Last validated: 2026-03-13
- Command:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_solver_adapter_exact_path.py tests/test_aof_gto_browser_gui.py tests/test_gto_gui_integration.py tests/test_aof_solver_provider_contract.py tests/test_aof_solver_provider_metrics.py tests/test_aof_solver_provider_context.py tests/test_aof_solver_provider_edge_cases.py tests/test_aof_solver_provider_cache.py tests/test_aof_solver_provider_resilience.py tests/test_poker_simulator_gui.py -q
```

- Result: `67 passed, 2 warnings`
- Warnings observed:
   - pygame/pkg_resources deprecation warning from upstream dependency path
   - pydantic v1 `@validator` deprecation warning in `python/hopilot/hand_range.py`

## Performance Validation
- Target: >=95% of context switches and metric switches complete within 1.0s in reference environment.
- Use integration latency tests and provider-level benchmarks for regression checks.

## Expected Outputs
- Solver-backed values in matrix payload normal path.
- Deterministic status messaging for timeout/failure/edge states.
- No UI crash during degraded conditions.
