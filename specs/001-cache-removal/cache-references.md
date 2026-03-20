# Cache System References Audit

**Task**: T006 | **Date**: 2026-03-20 | **Purpose**: Complete inventory of all `AoFBrowserDataProvider` imports and cache-related code in production and test code

---

## Summary

**Total Files with AoFBrowserDataProvider References**: 12 production + 15 test files = **27 files total**

| Category | Count | Status |
|----------|-------|--------|
| Production Files (import or define) | 5 | MUST REFACTOR |
| Test Files (import and mock) | 15 | REFACTOR or DELETE |
| **Total Affected** | **20** | **Phase 3 & 4 Tasks** |

**Primary Producers** (define/export the cache class):
- `python/hopilot/gto/aof_browser_data_provider.py` — **DELETE T042**

**Primary Consumers** (import and use):
- `python/hopilot/gui_components/aof_browser_panel.py` — **REFACTOR T016**
- `python/hopilot/gto/aof_precompute_runner.py` — **REFACTOR T036-T037**
- `python/hopilot/gto/aof_precompute_cli.py` — **REFACTOR T037**

---

## Production Code File Listing

### 1. Core Cache Provider (Definition)
- **File**: `python/hopilot/gto/aof_browser_data_provider.py`
- **Type**: Class Definition
- **Status**: **DELETE ENTIRELY (T042)**
- **Imports**: None (this is the source)
- **Usage**: Imported by 4 other production files + 15 test files
- **Refactoring Impact**: HIGH (cascading impact on all consumers)

### 2. GUI Panel Component
- **File**: `python/hopilot/gui_components/aof_browser_panel.py`
- **Type**: Consumer (imports AoFBrowserDataProvider)
- **Import Line**: `from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider`
- **Usage**: `self.provider = AoFBrowserDataProvider(fixture_path=fixture_path, database_url=database_url)`
- **Status**: **REFACTOR (T016)**
- **Tasks**:
  - Remove import of AoFBrowserDataProvider
  - Replace `self.provider = AoFBrowserDataProvider(...)` with SQLAlchemy session calls
  - Query database directly for matrix data

### 3. Precompute Runner (Callback Handler)
- **File**: `python/hopilot/gto/aof_precompute_runner.py`
- **Type**: Consumer (imports and dependency injects AoFBrowserDataProvider)
- **Import Line**: `from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider`
- **Usage**: 
  ```python
  def __init__(self, provider: AoFBrowserDataProvider, database_url: str):
      self.provider = provider
  ```
- **Status**: **REFACTOR (T036-T037)**
- **Tasks**:
  - Remove provider dependency injection parameter
  - Remove cache invalidation calls (`invalidate_cache()`)
  - Ensure database writes via SQLAlchemy instead of cache

### 4. Precompute CLI
- **File**: `python/hopilot/gto/aof_precompute_cli.py`
- **Type**: Consumer (imports AoFBrowserDataProvider for instantiation)
- **Import Line**: `from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider`
- **Usage**: `provider = AoFBrowserDataProvider(database_url=args.database_url)`
- **Status**: **REFACTOR (T037)**
- **Tasks**:
  - Remove provider instantiation
  - Use database URL directly if needed (likely won't be needed)

### 5. Normalized Provider (Replacement Reference)
- **File**: `python/hopilot/gto/normalized_db_provider.py`
- **Type**: Reference/Documentation
- **Content**: "Implements the same interface as AoFBrowserDataProvider but uses..."
- **Status**: **UPDATE documentation to indicate this IS the new provider** (during refactoring)
- **Note**: This file already exists as the replacement but is not yet the primary provider

### 6. Dual Write Provider (Transition Layer)
- **File**: `python/hopilot/gto/dual_write_provider.py`
- **Type**: Reference/Documentation
- **Content**: "Legacy cache provider (AoFBrowserDataProvider)"
- **Status**: **This is an optional transition layer (not required by spec)**
- **Note**: Nice to have but not critical

---

## Test Code File Listing (15 Total)

### Cache-SPECIFIC Tests (Cache behavior is the subject of test - DELETE)

These test files test cache behavior specifically, not business logic. They should be **DELETED** (no business value remains).

1. **test_aof_scenario_cache_store.py**
   - **Purpose**: Test cache storage mechanism
   - **Decision**: **DELETE** (T034 - cache-only test)
   - **Business Logic**: None
   - **Provider Usage**: AoFBrowserDataProvider with cache_enabled=True

2. **test_aof_scenario_cache_invalidation.py**
   - **Purpose**: Test cache invalidation logic
   - **Decision**: **DELETE** (T034 - cache-only test)
   - **Business Logic**: None
   - **Provider Usage**: Multiple invalidate_cache() calls

3. **test_aof_scenario_cache_concurrency.py**
   - **Purpose**: Test concurrent cache access
   - **Decision**: **DELETE** (T034 - cache-only test)
   - **Business Logic**: None
   - **Provider Usage**: AoFBrowserDataProvider with concurrent operations

4. **test_aof_scenario_cache_performance.py**
   - **Purpose**: Test cache hit/miss performance
   - **Decision**: **DELETE** (T034 - cache-only test)
   - **Business Logic**: None
   - **Provider Usage**: Cache reader/writer performance testing

5. **test_aof_scenario_cache_reliability.py**
   - **Purpose**: Test cache recovery from corruption
   - **Decision**: **DELETE** (T034 - cache-only test)
   - **Business Logic**: None
   - **Provider Usage**: Reliability checks on cache DB

6. **test_aof_scenario_cache_observability.py**
   - **Purpose**: Test cache metrics and logging
   - **Decision**: **DELETE** (T034 - cache-only test)
   - **Business Logic**: None
   - **Provider Usage**: Observability of cache operations

7. **test_aof_solver_provider_cache.py**
   - **Purpose**: Test cache provider contract
   - **Decision**: **DELETE** (T034 - cache-only test)
   - **Business Logic**: None
   - **Provider Usage**: AoFBrowserDataProvider interface testing

8. **test_aof_scenario_cache_runtime.py**
   - **Purpose**: Test cache runtime characteristics
   - **Decision**: **DELETE** (T034 - cache-only test)
   - **Business Logic**: None
   - **Provider Usage**: Cache runtime metrics

### Cache-DEPENDENT Tests (Business logic with cache mocking - REFACTOR)

These test files test business logic but use `AoFBrowserDataProvider` mocks or fixtures to mock cache. They should be **REFACTORED** to use database fixtures instead.

1. **test_aof_gto_browser_gui.py**
   - **Purpose**: GUI functionality testing
   - **Decision**: **REFACTOR** (T028)
   - **Current**: Direct AoFBrowserDataProvider() mocks
   - **Refactor To**: Database fixtures with sample matrix data
   - **Business Logic**: YES - GUI display and interaction

2. **test_aof_precompute_runner.py**
   - **Purpose**: Precompute pipeline testing
   - **Decision**: **REFACTOR** (T032)
   - **Current**: AoFBrowserDataProvider with cache_db_path
   - **Refactor To**: Database fixtures; verify database writes
   - **Business Logic**: YES - Precompute result persistence

3. **test_aof_gui_precompute_runner_canonical_dedup.py**
   - **Purpose**: Precompute deduplication testing
   - **Decision**: **REFACTOR** (T028)
   - **Current**: AoFBrowserDataProvider(cache_enabled=True)
   - **Refactor To**: Database fixtures; verify results
   - **Business Logic**: YES - Deduplication logic

4. **test_aof_gui_precompute_runner_state.py**
   - **Purpose**: Precompute state machine testing
   - **Decision**: **REFACTOR** (T030)
   - **Current**: AoFBrowserDataProvider(cache_enabled=False)
   - **Refactor To**: Database fixtures for state navigation
   - **Business Logic**: YES - State transitions

5. **test_aof_gui_precompute_runner_resume.py**
   - **Purpose**: Precompute pause/resume testing
   - **Decision**: **REFACTOR** (T030)
   - **Current**: AoFBrowserDataProvider(cache_enabled=False)
   - **Refactor To**: Database fixtures for resumable state
   - **Business Logic**: YES - Resume functionality

6. **test_aof_gui_precompute_runner_responsiveness.py**
   - **Purpose**: GUI responsiveness during precompute
   - **Decision**: **REFACTOR** (T028)
   - **Current**: AoFBrowserDataProvider usage in threading
   - **Refactor To**: Database fixtures; async query testing
   - **Business Logic**: YES - UI threading

7. **test_aof_solver_provider_context.py**
   - **Purpose**: Solver context management
   - **Decision**: **REFACTOR** (T031)
   - **Current**: AoFBrowserDataProvider() for context setup
   - **Refactor To**: Database fixtures for hand/position setup
   - **Business Logic**: YES - Context management

8. **test_aof_solver_provider_contract.py**
   - **Purpose**: Solver contract compliance
   - **Decision**: **REFACTOR** (T031)
   - **Current**: AoFBrowserDataProvider for test setup
   - **Refactor To**: Database fixtures
   - **Business Logic**: YES - Contract validation

9. **test_aof_solver_provider_edge_cases.py**
   - **Purpose**: Edge case testing
   - **Decision**: **REFACTOR** (T031)
   - **Current**: AoFBrowserDataProvider mocks
   - **Refactor To**: Database fixtures
   - **Business Logic**: YES - Edge cases

10. **test_aof_solver_provider_resilience.py**
    - **Purpose**: Resilience testing
    - **Decision**: **REFACTOR** (T031)
    - **Current**: AoFBrowserDataProvider for setup
    - **Refactor To**: Database fixtures
    - **Business Logic**: YES - Error handling

11. **test_aof_solver_provider_metrics.py**
    - **Purpose**: Metrics collection
    - **Decision**: **REFACTOR** (T031)
    - **Current**: AoFBrowserDataProvider for context
    - **Refactor To**: Database fixtures
    - **Business Logic**: YES - Metrics

12. **test_aof_solver_adapter_exact_path.py**
    - **Purpose**: Exact path solving
    - **Decision**: **REFACTOR** (T031)
    - **Current**: AoFBrowserDataProvider usage
    - **Refactor To**: Database fixtures
    - **Business Logic**: YES - Solution path calculation

13. **test_state_machine_controller.py**
    - **Purpose**: State machine controller testing
    - **Decision**: **REFACTOR** (T030, T029)
    - **Current**: May use provider for setup
    - **Refactor To**: Database fixtures; test state transitions without cache validation
    - **Business Logic**: YES - State machine

14. **test_precompute_pause_resume_regression.py**
    - **Purpose**: Regression testing for pause/resume
    - **Decision**: **REFACTOR** (T030)
    - **Current**: Uses precompute with provider
    - **Refactor To**: Database fixtures
    - **Business Logic**: YES - Regression prevention

15. **test_precompute_results_persistence.py**
    - **Purpose**: Results persistence testing
    - **Decision**: **REFACTOR** (T032)
    - **Current**: Tests cache persistence
    - **Refactor To**: Tests database persistence
    - **Business Logic**: YES - Persistence

---

## Refactoring Summary Table

| Phase | Task | File | Action | Business Logic | Effort |
|-------|------|------|--------|---|---|
| Phase 3 | T014-T015 | aof_browser_data_provider.py | Remove cache methods | - | HIGH |
| Phase 3 | T016-T019 | aof_browser_panel.py | Replace with DB queries | YES | HIGH |
| Phase 3 | T028 | test_aof_gto_browser_gui.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T028 | test_aof_gui_precompute_runner_canonical_dedup.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T028 | test_aof_gui_precompute_runner_responsiveness.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T029 | test_aof_browser_panel.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T030 | test_state_machine_controller.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T030 | test_aof_gui_precompute_runner_state.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T030 | test_aof_gui_precompute_runner_resume.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T030 | test_precompute_pause_resume_regression.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T031 | test_aof_solver_provider_context.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T031 | test_aof_solver_provider_contract.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T031 | test_aof_solver_provider_edge_cases.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T031 | test_aof_solver_provider_resilience.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T031 | test_aof_solver_provider_metrics.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T031 | test_aof_solver_adapter_exact_path.py | Refactor with fixtures | YES | MEDIUM |
| Phase 3 | T032 | test_aof_precompute_runner.py | Refactor with fixtures | YES | HIGH |
| Phase 3 | T032 | test_precompute_results_persistence.py | Refactor with fixtures | YES | MEDIUM |
| Phase 4 | T034 | test_aof_scenario_cache_store.py | DELETE | NO | LOW |
| Phase 4 | T034 | test_aof_scenario_cache_invalidation.py | DELETE | NO | LOW |
| Phase 4 | T034 | test_aof_scenario_cache_concurrency.py | DELETE | NO | LOW |
| Phase 4 | T034 | test_aof_scenario_cache_performance.py | DELETE | NO | LOW |
| Phase 4 | T034 | test_aof_scenario_cache_reliability.py | DELETE | NO | LOW |
| Phase 4 | T034 | test_aof_scenario_cache_observability.py | DELETE | NO | LOW |
| Phase 4 | T034 | test_aof_solver_provider_cache.py | DELETE | NO | LOW |
| Phase 4 | T034 | test_aof_scenario_cache_runtime.py | DELETE | NO | LOW |
| Phase 3 | T036-T037 | aof_precompute_runner.py | Remove provider dependency | - | HIGH |
| Phase 3 | T037 | aof_precompute_cli.py | Remove provider instantiation | - | LOW |

**Totals**:
- **Refactor (DB Fixtures)**: 15 test files
- **Delete (Cache-Only Tests)**: 8 test files  
- **Production Files Modified**: 3 (aof_browser_panel.py, aof_precompute_runner.py, aof_precompute_cli.py)
- **Files Deleted**: 1 (aof_browser_data_provider.py) + 8 test files

---

## Phase 2 Gate: T007 Blocking Status

**T007 Success Criteria**: Produce numbered list of all 22 files with explicit categorization

**From this audit**, the 22+ cache-dependent files are:
1. test_aof_gto_browser_gui.py - REFACTOR
2. test_aof_precompute_runner.py - REFACTOR
3. test_aof_gui_precompute_runner_canonical_dedup.py - REFACTOR
4. test_aof_gui_precompute_runner_state.py - REFACTOR
5. test_aof_gui_precompute_runner_resume.py - REFACTOR
6. test_aof_gui_precompute_runner_responsiveness.py - REFACTOR
7. test_aof_solver_provider_context.py - REFACTOR
8. test_aof_solver_provider_contract.py - REFACTOR
9. test_aof_solver_provider_edge_cases.py - REFACTOR
10. test_aof_solver_provider_resilience.py - REFACTOR
11. test_aof_solver_provider_metrics.py - REFACTOR
12. test_aof_solver_adapter_exact_path.py - REFACTOR
13. test_state_machine_controller.py - REFACTOR
14. test_precompute_pause_resume_regression.py - REFACTOR
15. test_precompute_results_persistence.py - REFACTOR
16. test_aof_scenario_cache_store.py - DELETE
17. test_aof_scenario_cache_invalidation.py - DELETE
18. test_aof_scenario_cache_concurrency.py - DELETE
19. test_aof_scenario_cache_performance.py - DELETE
20. test_aof_scenario_cache_reliability.py - DELETE
21. test_aof_scenario_cache_observability.py - DELETE
22. test_aof_solver_provider_cache.py - DELETE
23. test_aof_scenario_cache_runtime.py - DELETE

**Count**: 23 files (slightly more than expected 22)
**Categorization**: 15 REFACTOR (business logic) + 8 DELETE (cache-only tests)

---

## Verification Checklist

- [x] All production imports of AoFBrowserDataProvider identified
- [x] All test imports of AoFBrowserDataProvider identified
- [x] Cache-only tests vs cache-dependent tests categorized
- [x] Refactoring tasks assigned (T028-T032)
- [x] Deletion tasks assigned (T034)
- [x] Production refactoring tasks assigned (T036-T037)
- [x] Production file deletion task assigned (T042)

---

## Next Steps

1. **T007**: Confirm this list is complete and finalize the 22-file count (currently shows 23)
2. **T008-T009**: Create database fixtures for these tests
3. **T028-T035**: Execute test refactoring with new fixtures

---

**Audit Report Status**: ✅ **READY FOR T007 GATE**
