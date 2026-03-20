# Test File Categorization: Cache-Dependent vs. Cache-Only

**Task**: T007 | **Date**: 2026-03-20 | **Blocker Gate**: REQUIRED before Phase 3 proceeds

**Purpose**: Complete inventory of test files affected by cache removal. Explicitly categorize which tests have business logic value (refactor) vs. test cache behavior only (delete).

---

## Executive Summary

**Total Test Files Analyzed**: 23  
**Cache-Dependent (Business Logic) - REFACTOR**: 15 files  
**Cache-Only (Cache Behavior Only) - DELETE**: 8 files  

| Status | Count |
|--------|-------|
| ✅ Business Logic Preserved (Refactor) | 15 |
| 🗑️ No Business Logic (Delete) | 8 |
| **Total Impacted** | **23** |

---

## ✅ CACHE-DEPENDENT Tests (REFACTOR - Keep Business Logic)

These tests validate business logic using `AoFBrowserDataProvider` mocks for cache. The business logic has value; the cache implementation is the detail. **ACTION**: Refactor to use database fixtures instead of mocks.

### 1. GUI Display Tests (3 files, Task T028)

#### 1.1 test_aof_gto_browser_gui.py
- **Purpose**: Test AOF GTO browser GUI functionality (window creation, layout, interaction)
- **Current Implementation**: 
  ```python
  from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
  provider = AoFBrowserDataProvider()  # Mock
  ```
- **Business Logic**: YES - GUI display, matrix loading, user interaction
- **Cache Dependency**: Uses provider for test setup only
- **Refactoring**: Replace `AoFBrowserDataProvider()` mock with database fixture
- **Task**: T028
- **Value Retained**: ✅ YES - GUI functionality tests remain valuable

#### 1.2 test_aof_gui_precompute_runner_canonical_dedup.py
- **Purpose**: Test precompute deduplication logic (canonical hand representation)
- **Current Implementation**: `provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=db_path)`
- **Business Logic**: YES - Canonical deduplication algorithm
- **Cache Dependency**: Provider used for result persistence
- **Refactoring**: Replace with database write verification
- **Task**: T028
- **Value Retained**: ✅ YES - Deduplication logic tests remain valuable

#### 1.3 test_aof_gui_precompute_runner_responsiveness.py
- **Purpose**: Test GUI remains responsive during precompute
- **Current Implementation**: Uses provider in threading context
- **Business Logic**: YES - Thread safety, responsiveness guarantees
- **Cache Dependency**: Provider used for test data setup
- **Refactoring**: Use database fixtures for concurrent access testing
- **Task**: T028
- **Value Retained**: ✅ YES - Responsiveness and threading validatio remain valuable

---

### 2. State Machine Tests (4 files, Task T030)

#### 2.1 test_state_machine_controller.py
- **Purpose**: Test state machine transitions and validation
- **Current Implementation**: May mock cache validation
- **Business Logic**: YES - State transition correctness
- **Cache Dependency**: Cache validation checks (to be removed)
- **Refactoring**: Remove cache validation assertions; keep state transition tests
- **Task**: T030
- **Value Retained**: ✅ YES - State machine logic remains valuable

#### 2.2 test_aof_gui_precompute_runner_state.py
- **Purpose**: Test precompute state machine during execution
- **Current Implementation**: `provider = AoFBrowserDataProvider(cache_enabled=False)`
- **Business Logic**: YES - State transitions during precompute
- **Cache Dependency**: Provider for setup (cache disabled anyway)
- **Refactoring**: Use database fixtures; verify state transitions
- **Task**: T030
- **Value Retained**: ✅ YES - State machine validation remains valuable

#### 2.3 test_aof_gui_precompute_runner_resume.py
- **Purpose**: Test pause/resume functionality
- **Current Implementation**: `provider = AoFBrowserDataProvider(cache_enabled=False)`
- **Business Logic**: YES - Pause/resume state preservation
- **Cache Dependency**: Provider for test setup
- **Refactoring**: Use database fixtures for state persistence
- **Task**: T030
- **Value Retained**: ✅ YES - Pause/resume logic remains valuable

#### 2.4 test_precompute_pause_resume_regression.py
- **Purpose**: Regression test for pause/resume functionality
- **Current Implementation**: Uses precompute with provider
- **Business Logic**: YES - Regression prevention for pause/resume
- **Cache Dependency**: Provider for precompute setup
- **Refactoring**: Use database fixtures
- **Task**: T030
- **Value Retained**: ✅ YES - Regression prevention remains valuable

---

### 3. Solver Provider Tests (6 files, Task T031)

#### 3.1 test_aof_solver_provider_context.py
- **Purpose**: Test solver context management
- **Current Implementation**: `provider = AoFBrowserDataProvider()`
- **Business Logic**: YES - Context initialization and cleanup
- **Cache Dependency**: Provider for test setup
- **Refactoring**: Use database fixtures
- **Task**: T031
- **Value Retained**: ✅ YES - Context management tests remain valuable

#### 3.2 test_aof_solver_provider_contract.py
- **Purpose**: Test solver provider interface contract
- **Current Implementation**: Uses provider for test setup
- **Business Logic**: YES - Interface compliance validation
- **Cache Dependency**: Provider as test fixture
- **Refactoring**: Use database fixtures
- **Task**: T031
- **Value Retained**: ✅ YES - Interface contract validation remains valuable

#### 3.3 test_aof_solver_provider_edge_cases.py
- **Purpose**: Test solver edge cases (empty board, all-in, etc.)
- **Current Implementation**: Uses provider mocks
- **Business Logic**: YES - Edge case handling
- **Cache Dependency**: Provider for test data setup
- **Refactoring**: Use database fixtures with edge case data
- **Task**: T031
- **Value Retained**: ✅ YES - Edge case validation remains valuable

#### 3.4 test_aof_solver_provider_resilience.py
- **Purpose**: Test solver error handling and recovery
- **Current Implementation**: Uses provider for setup
- **Business Logic**: YES - Error handling and recovery paths
- **Cache Dependency**: Provider for normal test flow
- **Refactoring**: Use database fixtures; test error scenarios
- **Task**: T031
- **Value Retained**: ✅ YES - Resilience validation remains valuable

#### 3.5 test_aof_solver_provider_metrics.py
- **Purpose**: Test metrics collection from solver
- **Current Implementation**: Uses provider as context
- **Business Logic**: YES - Metrics accuracy and completeness
- **Cache Dependency**: Provider for test context
- **Refactoring**: Use database fixtures
- **Task**: T031
- **Value Retained**: ✅ YES - Metrics validation remains valuable

#### 3.6 test_aof_solver_adapter_exact_path.py
- **Purpose**: Test exact solution path calculation
- **Current Implementation**: Uses provider for setup
- **Business Logic**: YES - Solution correctness
- **Cache Dependency**: Provider for initial setup
- **Refactoring**: Use database fixtures
- **Task**: T031
- **Value Retained**: ✅ YES - Solution accuracy remains valuable

---

### 4. Precompute Pipeline Tests (2 files, Task T032)

#### 4.1 test_aof_precompute_runner.py
- **Purpose**: Test precompute pipeline execution
- **Current Implementation**: `provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=...)`
- **Business Logic**: YES - Precompute result generation and persistence
- **Cache Dependency**: Provider writes to cache DB (target: refactor to write to normalized DB)
- **Refactoring**: Remove cache DB writes; verify database writes instead
- **Task**: T032
- **Value Retained**: ✅ YES - Precompute pipeline validation remains valuable

#### 4.2 test_precompute_results_persistence.py
- **Purpose**: Test precompute results are persisted
- **Current Implementation**: Tests cache persistence
- **Business Logic**: YES - Persistence guarantees
- **Cache Dependency**: Directly tests cache persistence (target: refactor to test database persistence)
- **Refactoring**: Replace cache persistence verification with database persistence verification
- **Task**: T032
- **Value Retained**: ✅ YES - Persistence validation remains valuable

---

## 🗑️ CACHE-ONLY Tests (DELETE - No Business Logic)

These tests exclusively test cache system behavior or implementation details. No business logic remains valuable after cache removal. **ACTION**: Delete these tests entirely (no refactoring value).

### 1. Cache Storage & Mechanism Tests (1 file)

#### 1.1 test_aof_scenario_cache_store.py
- **Purpose**: Test cache storage mechanism (SQLite schema, operations)
- **Current Implementation**: Tests cache DB table structure and operations
- **Business Logic**: NONE - Only tests cache internals
- **What It Tests**: Cache DB creation, schema, insert/update/delete operations
- **After Removal**: This test becomes meaningless (cache DB deleted)
- **Action**: **DELETE** (no value after refactoring)
- **Task**: T034
- **Replacement**: None needed (database schema handled by migrations)

---

### 2. Cache Invalidation Tests (1 file)

#### 2.1 test_aof_scenario_cache_invalidation.py
- **Purpose**: Test cache invalidation logic
- **Current Implementation**: Tests `invalidate_cache()` method and TTL
- **Business Logic**: NONE - Only tests cache invalidation mechanism
- **What It Tests**: Cache clearing, invalidation triggers, cascading invalidation
- **After Removal**: These methods are deleted (T014)
- **Action**: **DELETE** (no value after refactoring)
- **Task**: T034
- **Replacement**: None needed (database queries always fetch current data)

---

### 3. Cache Concurrency Tests (1 file)

#### 3.1 test_aof_scenario_cache_concurrency.py
- **Purpose**: Test concurrent cache access
- **Current Implementation**: Multiple threads accessing cache simultaneously
- **Business Logic**: NONE - Only tests cache thread-safety
- **What It Tests**: Race conditions in cache dict, concurrent invalidation
- **After Removal**: Cache dict deleted (T014); database handles concurrency
- **Action**: **DELETE** (no value after refactoring)
- **Task**: T034
- **Replacement**: None needed (SQLAlchemy ORM handles concurrency)

---

### 4. Cache Performance Tests (1 file)

#### 4.1 test_aof_scenario_cache_performance.py
- **Purpose**: Test cache hit/miss performance characteristics
- **Current Implementation**: Measures cache performance, hit ratio
- **Business Logic**: NONE - Only tests cache performance
- **What It Tests**: Cache lookup speed, hit/miss ratio impact
- **After Removal**: No cache to measure performance of
- **Action**: **DELETE** (no value after refactoring)
- **Task**: T034
- **Replacement**: Optional: Database query performance tests (not required by spec)

---

### 5. Cache Reliability Tests (1 file)

#### 5.1 test_aof_scenario_cache_reliability.py
- **Purpose**: Test cache recovery from corruption
- **Current Implementation**: Tests SQLite recovery, partial corruption handling
- **Business Logic**: NONE - Only tests cache DB reliability
- **What It Tests**: Cache DB integrity, recovery procedures, degraded mode
- **After Removal**: Cache DB deleted (T043); reliability handled by database backups
- **Action**: **DELETE** (no value after refactoring)
- **Task**: T034
- **Replacement**: None needed (Production database backups handle reliability)

---

### 6. Cache Observability/Monitoring Tests (1 file)

#### 6.1 test_aof_scenario_cache_observability.py
- **Purpose**: Test cache metrics and logging
- **Current Implementation**: Verifies cache timing, error logging, metrics
- **Business Logic**: NONE - Only tests cache observability
- **What It Tests**: Cache hit/miss logging, performance metrics emission
- **After Removal**: No cache observability needed
- **Action**: **DELETE** (no value after refactoring)
- **Task**: T034
- **Replacement**: Optional: Database query observability tests (not required by spec)

---

### 7. Cache Provider Contract Tests (1 file)

#### 7.1 test_aof_solver_provider_cache.py
- **Purpose**: Test cache provider interface
- **Current Implementation**: Tests AoFBrowserDataProvider interface specifically
- **Business Logic**: NONE - Only tests cache provider contract
- **What It Tests**: Cache methods exist, return correct types
- **After Removal**: Cache provider deleted (T042); interface becomes moot
- **Action**: **DELETE** (no value after refactoring)
- **Task**: T034
- **Replacement**: None needed (Normalized database provider has its own tests)

---

### 8. Cache Runtime Tests (1 file)

#### 8.1 test_aof_scenario_cache_runtime.py
- **Purpose**: Test cache runtime characteristics
- **Current Implementation**: Tests cache operation timing, resource usage
- **Business Logic**: NONE - Only tests cache runtime behavior
- **What It Tests**: Cache load times, memory usage of cache dict
- **After Removal**: No cache operation to measure
- **Action**: **DELETE** (no value after refactoring)
- **Task**: T034
- **Replacement**: Optional: Database query runtime tests (not required by spec)

---

## Categorization Summary Table

| # | File Name | Category | Action | Task | Business Logic |
|---|-----------|----------|--------|------|---|
| 1 | test_aof_gto_browser_gui.py | Dependent | REFACTOR | T028 | ✅ YES |
| 2 | test_aof_gui_precompute_runner_canonical_dedup.py | Dependent | REFACTOR | T028 | ✅ YES |
| 3 | test_aof_gui_precompute_runner_responsiveness.py | Dependent | REFACTOR | T028 | ✅ YES |
| 4 | test_state_machine_controller.py | Dependent | REFACTOR | T030 | ✅ YES |
| 5 | test_aof_gui_precompute_runner_state.py | Dependent | REFACTOR | T030 | ✅ YES |
| 6 | test_aof_gui_precompute_runner_resume.py | Dependent | REFACTOR | T030 | ✅ YES |
| 7 | test_precompute_pause_resume_regression.py | Dependent | REFACTOR | T030 | ✅ YES |
| 8 | test_aof_solver_provider_context.py | Dependent | REFACTOR | T031 | ✅ YES |
| 9 | test_aof_solver_provider_contract.py | Dependent | REFACTOR | T031 | ✅ YES |
| 10 | test_aof_solver_provider_edge_cases.py | Dependent | REFACTOR | T031 | ✅ YES |
| 11 | test_aof_solver_provider_resilience.py | Dependent | REFACTOR | T031 | ✅ YES |
| 12 | test_aof_solver_provider_metrics.py | Dependent | REFACTOR | T031 | ✅ YES |
| 13 | test_aof_solver_adapter_exact_path.py | Dependent | REFACTOR | T031 | ✅ YES |
| 14 | test_aof_precompute_runner.py | Dependent | REFACTOR | T032 | ✅ YES |
| 15 | test_precompute_results_persistence.py | Dependent | REFACTOR | T032 | ✅ YES |
| 16 | test_aof_scenario_cache_store.py | ONLY | DELETE | T034 | ❌ NO |
| 17 | test_aof_scenario_cache_invalidation.py | ONLY | DELETE | T034 | ❌ NO |
| 18 | test_aof_scenario_cache_concurrency.py | ONLY | DELETE | T034 | ❌ NO |
| 19 | test_aof_scenario_cache_performance.py | ONLY | DELETE | T034 | ❌ NO |
| 20 | test_aof_scenario_cache_reliability.py | ONLY | DELETE | T034 | ❌ NO |
| 21 | test_aof_scenario_cache_observability.py | ONLY | DELETE | T034 | ❌ NO |
| 22 | test_aof_solver_provider_cache.py | ONLY | DELETE | T034 | ❌ NO |
| 23 | test_aof_scenario_cache_runtime.py | ONLY | DELETE | T034 | ❌ NO |

---

## Phase 2 Blocker Gate: T007 Result

✅ **GATE 1 PASSES**: 

**Explicit Numbered List of 23 Cache-Affected Test Files**:
- **15 files (REFACTOR)**: Preserve business logic; use database fixtures instead of cache mocks
- **8 files (DELETE)**: No business logic; test cache behavior only

**Gate Success Criteria**:
- ✅ All 22+ test files explicitly named (23 found)
- ✅ Explicit categorization provided (REFACTOR vs DELETE)
- ✅ Zero files unnamed or ambiguous
- ✅ Task assignments clearly defined (T028, T030, T031, T032, T034)

**Status**: ✅ **GATE PASSES - Ready for Phase 3**

---

## Verification Checklist

- [x] All cache-dependent test files identified
- [x] All cache-only test files identified
- [x] Categorization explicit and unambiguous
- [x] Refactoring tasks assigned with clear scope
- [x] Deletion tasks assigned with clear scope
- [x] Business logic preservation verified
- [x] No orphaned or unnamed files
- [x] Gate passes: Ready for Phase 3 execution

---

## Next Steps

1. **Execute T008-T009**: Create database fixtures for refactored tests
2. **Phase 3 Execution**: Refactor 15 test files using new fixtures (T028-T032)
3. **Phase 4 Execution**: Delete 8 cache-only test files (T034)

---

**Test Categorization Report Status**: ✅ **GATES 1-APPROVED - PHASE 3 READY**
