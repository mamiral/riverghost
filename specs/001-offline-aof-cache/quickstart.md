# Quickstart: Offline AoF Matrix Precomputation and SQLite Scenario Cache

## Prerequisites
- Active project virtual environment (`.venv`).
- Commands run from repository root unless noted.
- Existing AoF solver-backed provider is available.

## 1. Run Targeted Tests (baseline)
```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_gto_browser_gui.py tests/test_gto_gui_integration.py tests/test_aof_solver_provider_contract.py tests/test_aof_solver_provider_cache.py tests/test_aof_solver_provider_resilience.py -q
```

## 1.1 Run Offline Cache Test Slice
```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_aof_scenario_cache_store.py tests/test_aof_scenario_cache_runtime.py tests/test_aof_scenario_cache_concurrency.py tests/test_aof_scenario_cache_invalidation.py tests/test_aof_precompute_runner.py tests/test_aof_scenario_cache_observability.py tests/test_aof_scenario_cache_performance.py tests/test_aof_scenario_cache_reliability.py -q
```

Latest validation result:
- 19 passed (no failures in offline cache test slice)

## 2. Precompute Scenario Set (offline job)
Run offline precompute against the persistent SQLite cache:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m hopilot.gto.aof_precompute_cli --db-path python/hopilot/cache/aof_scenario_cache.sqlite3 --max-scenarios 100
```

Resume an interrupted run:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m hopilot.gto.aof_precompute_cli --db-path python/hopilot/cache/aof_scenario_cache.sqlite3 --resume-run-id 1
```

## 3. Runtime Retrieval and Write-Back Validation
1. Request a scenario known to be precomputed and verify cache-hit behavior.
2. Request a non-precomputed scenario and verify fallback compute + write-back.
3. Re-request the same scenario and verify persistent cache-hit behavior.
4. Request a solver-equivalent scenario with a different selected seat label and verify persistent canonical cache reuse without recompute.

Validated by:
- `tests/test_aof_scenario_cache_runtime.py`
- `tests/test_aof_scenario_cache_store.py`
- `tests/test_aof_scenario_cache_runtime.py::test_solver_equivalent_positions_reuse_persistent_cells`

## 4. Invalidation Validation
1. Change schema/version/signature metadata.
2. Request existing scenario.
3. Verify stale entry is not served and deterministic refresh path occurs.

Validated by:
- `tests/test_aof_scenario_cache_invalidation.py`

## 5. Degraded Behavior Validation
1. Force timeout during fallback compute and verify deterministic TIMEOUT payload.
2. Force compute failure and verify deterministic ERROR payload.
3. Verify no silent synthetic fallback in normal operation.

Validated by:
- `tests/test_aof_scenario_cache_runtime.py`
- `tests/test_aof_scenario_cache_observability.py`

## 6. Benchmark Evidence (SC-001 and SC-003)
- SC-001 cached retrieval performance: `tests/test_aof_scenario_cache_performance.py` enforces p95 latency <= 250 ms over 200 repeated cached requests.
- SC-003 offline-precomputed reliability: `tests/test_aof_scenario_cache_reliability.py` enforces timeout-free load rate >= 99%.

Latest benchmark validation run:
- Both benchmark tests passed in the 19-test offline cache slice.

## Expected Outcomes
- Cached scenarios load rapidly and consistently across app restarts.
- Missing scenarios are deterministically computed and persisted.
- Stale/corrupt entries are safely bypassed.
- Offline runs are resumable and idempotent.
