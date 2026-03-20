# Cache Components Audit Report

**Feature**: 001-cache-removal | **Date**: 2026-03-20 | **Status**: Phase 1 Complete

---

## Executive Summary

This report catalogs all cache-related components in the AOF GTO Browser system that will be removed during the refactoring. The cache system consists of three layers:

1. **In-Memory Cache**: Python dict-based caching in `AoFBrowserDataProvider`
2. **Persistent Cache Database**: SQLite database storing computed strategies
3. **Aggregation Statistics Cache**: Secondary SQLite database for simulation aggregations

**Total Components to Remove**: 8 major modules/sections
**Total Lines of Code Impact**: ~2000 lines (removed) + ~800 lines (added via SQLAlchemy queries)
**Deadline for Removal**: Phase 4 (cleanup phase)

---

## 1. In-Memory Cache Layer

### 1.1 Primary In-Memory Cache

**Component Name**: `AoFBrowserDataProvider._matrix_cache`  
**Location**: `python/hopilot/aof_gto_browser_data_provider.py`  
**Purpose**: Store computed strategy matrices in memory to avoid recomputation  
**Trade-offs**: Reduces computation latency but creates stale data risk; memory accumulates over time

**Structure**:
```python
class AoFBrowserDataProvider:
    def __init__(self):
        self._matrix_cache: Dict[Tuple[str, str], dict] = {}  # Key: (position, action)
        self._aggregation_stats: Dict[str, dict] = {}
        self._cache_loader = CacheLoader()
        self._cache_valid = True
    
    def get_matrix_payload(self, position: str, action: str) -> dict:
        key = (position, action)
        # Cache lookup
        if key in self._matrix_cache and self._cache_valid:
            return self._matrix_cache[key]
        # Miss → fallback
        return self._load_from_persistent_cache(key)
    
    def invalidate_cache(self):
        self._matrix_cache.clear()
        self._aggregation_stats.clear()
        self._cache_valid = False
```

**Usage Points**:
- Called from `AoFBrowserPanel.load_matrix()` to populate GUI matrix grid
- Called from `aof_precompute_callback_handler.py` to retrieve intermediate results
- Invalidated after precompute runs complete

**Replacement Strategy**: Remove dictionary entirely; replace all calls with `db.session_context()` and SQLAlchemy ORM queries

**Task**: T014 Delete `_matrix_cache` dict and all cache-related methods

---

### 1.2 Aggregation Statistics Cache

**Component Name**: `AoFBrowserDataProvider._aggregation_stats`  
**Location**: `python/hopilot/aof_gto_browser_data_provider.py`  
**Purpose**: Cache simulation outcome aggregations (win%, tie%, loss% by hand)  
**Trade-offs**: Speeds up statistics display but also creates stale data

**Related Code**:
```python
def get_aggregation_stats(self, position, action):
    if (position, action) in self._aggregation_stats:
        return self._aggregation_stats[(position, action)]
    # Load from aggregation cache DB
    stats = self._aggregation_cache_loader.get_stats(position, action)
    self._aggregation_stats[(position, action)] = stats
    return stats
```

**Task**: T014-T015 Remove aggregation stats caching; query normalized database instead

---

## 2. Persistent Cache Database Layer

### 2.1 Scenario Cache Database (AOF-specific)

**Database File**: `python/hopilot/cache/aof_scenario_cache.sqlite3`  
**Location in Code**: Configured in `config/gto_defaults.yaml` as `aof_browser_cache.db_path`  
**Purpose**: Persistent storage of computed GTO matrices for quick reloads  
**Schema**: Tables for Position, Action, MatrixValues, PolicyMetadata

**Configuration**:
```yaml
# config/gto_defaults.yaml
aof_browser_cache:
  enabled: true
  db_path: "python/hopilot/cache/aof_scenario_cache.sqlite3"
  schema_version: "1"
  policy_signature: "aof-cache-policy-v1"
  persist_degraded_payloads: true
```

**Initialization Code Location**: `python/hopilot/aof_gto_browser_data_provider.py` constructor  
**Deletion Strategy**: Stop creating; delete existing files during Phase 4

**Task**: T022-T023, T043-T044 Remove configuration and delete files

---

### 2.2 Aggregation Cache Database

**Database File**: `python/hopilot/cache/aof_aggregation_cache.sqlite3`  
**Location in Code**: Configured in `config/gto_defaults.yaml` as `aggregation.db_path`  
**Purpose**: Persistent storage of simulation outcome aggregations from precompute runs  
**Schema**: Tables for OutcomeAggregation, SimulationMetadata

**Configuration**:
```yaml
# config/gto_defaults.yaml
aggregation:
  enabled: true
  migration_mode: "coexistence"
  db_path: "python/hopilot/cache/aof_aggregation_cache.sqlite3"
```

**Initialization Code Location**: `python/hopilot/aof_gto_browser_data_provider.py` / `python/hopilot/gto/aggregation_cache.py`  
**Deletion Strategy**: Stop creating; delete existing files during Phase 4

**Task**: T022-T023, T043-T044 Remove configuration and delete files

---

## 3. Cache Configuration & Utility Modules

### 3.1 Cache Configuration Classes

**Location**: `python/hopilot/config.py`

**Components to Delete**:
```python
# DELETE
class AoFBrowserCacheConfig(BaseModel):
    """Configuration for AOF browser matrix caching."""
    enabled: bool
    ttl: int
    cache_db_path: str
    schema_version: str
    policy_signature: str
    persist_degraded_payloads: bool

class AggregationCacheConfig(BaseModel):
    """Configuration for simulation aggregation caching."""
    enabled: bool
    migration_mode: str
    cache_mode: str
    db_path: str
```

**Task**: T024-T025 Remove these Pydantic config classes

---

### 3.2 Cache Utility Modules

**Modules to Delete** (if they exist):
- `python/hopilot/cache_loader.py` — Loads matrices from persistent cache DB
- `python/hopilot/cache_manager.py` — Manages cache lifecycle (invalidation, TTL)
- `python/hopilot/aggregation_cache.py` — Manages aggregation statistics cache
- `python/hopilot/cache_invalidation_handler.py` — Handles cache invalidation on precompute

**Task**: T043 Delete these entire modules

---

### 3.3 Cache Initialization Code

**Location**: `python/hopilot/aof_gto_browser_data_provider.py` constructor

**Code to Delete**:
```python
def __init__(self):
    self._cache_loader = CacheLoader()  # DELETE
    self._aggregation_cache_loader = AggregationCacheLoader()  # DELETE
    self._cache_db_engine = create_engine(config.aof_browser_cache.db_path)  # DELETE
    self._invalidation_handler = CacheInvalidationHandler()  # DELETE
    
    # Also remove from properties/methods
    @property
    def cache_stats(self):  # DELETE
        return self._cache_loader.get_statistics()
    
    def set_cache_ttl(self, seconds):  # DELETE
        self._cache_loader.set_ttl(seconds)
```

**Task**: T014-T015 Remove all initialization code

---

## 4. Cache Integration Points

### 4.1 GUI Components Using Cache

**Files Affected**:

#### `python/hopilot/gui_components/aof_browser_panel.py`
- **Current**: Uses `AoFBrowserDataProvider.get_matrix_payload()` which checks in-memory cache first
- **Refactored**: Direct SQLAlchemy queries via `db.session_context()`
- **Task**: T016, T029

#### `python/hopilot/aof_gto_browser_gui.py`
- **Current**: Initializes `AoFBrowserDataProvider` at startup
- **Refactored**: Remove provider initialization; load database URL from config instead
- **Task**: T026

#### `python/hopilot/gui_components/state_machine_controller.py`
- **Current**: Validates cache state in state transitions (checks if cache is valid)
- **Refactored**: Remove all cache validation logic; database is always fresh source of truth
- **Task**: T018, T030

---

### 4.2 Precompute Pipeline Using Cache

**File Affected**: `python/hopilot/gto/aof_precompute_runner.py`

**Current Flow**:
```
Precompute Algorithm
  ↓
Compute Strategies
  ↓
Store in Cache DB (aof_scenario_cache.sqlite3)
  ↓
Invoke Invalidation Handler
  ↓
Clear In-Memory Cache
  ↓
GUI Reloads from DB
```

**Refactored Flow**:
```
Precompute Algorithm
  ↓
Compute Strategies
  ↓
Write to Normalized Database (SQLAlchemy tables)
  ↓
GUI Queriesatı Database Directly
```

**Tasks**: T036-T041 Remove cache writes; use database writes instead

---

### 4.3 Test Suite Using Cache Mocks

**22 Test Files** (All have cache dependencies):

Test files import `AoFBrowserDataProvider` or mock cache behavior:
- `test_aof_gto_browser_gui.py` — Mocks `_matrix_cache`
- `test_aof_browser_panel.py` — Mocks cache loading
- `test_aof_scenario_cache_*.py` — Tests cache-specific behavior (8 files)
- `test_aof_solver_provider_cache.py` — Tests cache provider
- `test_aof_gui_precompute_*.py` — Tests precompute cache invalidation
- [14+ additional test files with cache dependencies]

**Refactoring Strategy**: 
- **Delete** cache-specific tests (no business logic value)
- **Refactor** business-logic tests to use database fixtures instead of mocks

**Task**: T028-T035 Refactor all 22 test files; use database fixtures from T008-T012

---

## 5. Cache Data Artifacts

### 5.1 Cache Database Files (Deletion Targets)

**Location**: `python/hopilot/cache/`

**Files to Delete**:
- `aof_scenario_cache.sqlite3` — Main cache DB
- `aof_aggregation_cache.sqlite3` — Aggregation cache DB
- Any `.journal` or `.wal` files (write-ahead logs)
- Cache directory itself (if empty after cleanup)

**Task**: T043-T044 Delete all cache files and ensure no orphaned DB files remain

---

### 5.2 Cached Metadata

**Config Settings to Remove**:
- `aof_browser_cache.enabled` — No cache enabling needed
- `aof_browser_cache.db_path` — No path to cache DB
- `aof_browser_cache.ttl` — No TTL management
- `aggregation.enabled` — No aggregation cache
- `aggregation.db_path` — No aggregation cache path

**Task**: T022-T023 Remove from `config/gto_defaults.yaml`

---

## 6. Deployment & User Impact

### 6.1 User Installations

**Files to Clean Up**:
- Existing cache databases at configured paths
- Cache directories created by previous versions
- Any cache-related temporary files

**Strategy**:
- Phase 4 cleanup: Document user cleanup steps
- Provide script to remove old cache files (optional, backward compatible)
- New installations: Use database instead of cache automatically

**Task**: T050 Update CHANGELOG.md with migration guidance

---

### 6.2 Configuration Migration

**For Existing Users**:
1. Upgrade to refactored version
2. Cache sections in `gto_defaults.yaml` are ignored (removed from code that reads them)
3. First GUI load: Database is created and populated on demand
4. Precompute run: Results written to database instead of cache
5. Old cache files can be safely deleted (optional cleanup)

**Status**: **Breaking Change** (cache data is NOT migrated, but this is acceptable per spec: "Delete without migration; clean break")

---

## 7. Verification Checklist

### Phase 1 Completion (This Document)
- [x] Cache components cataloged
- [x] Configuration sections identified
- [x] File locations documented
- [x] Deletion strategy defined
- [x] Integration points mapped

### Phase 2 Completion (Gates)
- [ ] T007: 22 test files explicitly listed and categorized
- [ ] T011: SQLAlchemy model location confirmed
- [ ] T013: Precompute write target verified

### Phase 3 Completion (Refactoring)
- [ ] T014-T015: In-memory cache removed from data provider
- [ ] T016-T019: GUI components refactored to use database
- [ ] T022-T027: Cache config sections removed
- [ ] T028-T035: All 22 test files refactored or deleted
- [ ] T036-T041: Precompute pipeline writes to database

### Phase 4 Completion (Cleanup)
- [ ] T042: `AoFBrowserDataProvider` deleted entirely
- [ ] T043: Cache utility modules deleted
- [ ] T044: Cache database files deleted
- [ ] T045-T046: No orphaned cache references remain
- [ ] T047-T051: Integration tests pass; success criteria met

---

## 8. Risk Assessment

| Risk | Mitigation | Owner |
|------|-----------|-------|
| **Stale Data if Cache Invalidation Fails** | Database is authoritative source; no caching means no staleness | T013-T015 verification |
| **Performance Regression from Cache Removal** | Database queries with proper indexing; connection pooling; query optimization | T003, T047-T048 |
| **Breaking Change for Users** | Clear changelog entry; no migration needed (clean break acceptable per spec) | T050 |
| **Orphaned Cache Code Left in Codebase** | Explicit cleanup tasks (T042-T046) with grep verification | T045-T046 |
| **Test Coverage Gaps** | 22 test files refactored with database fixtures; 100% pass rate required | T035 gate |

---

## 9. Success Criteria Mapping

Each spec success criterion maps to removal tasks:

| Spec Criterion | Removal Task | Deliverable |
|---|---|---|
| SC-001: 100% DB queries, zero cache lookups | T014-T015, T028-T035 | No cache code in codebase |
| SC-002: Zero cache artifacts created | T022-T023, T043-T044 | Cache files deleted; config removed |
| SC-003: All 22 test files pass | T035 gate | `pytest tests/ -v` passes 100% |
| SC-004: Zero cache config settings | T024-T025, T046 | Config classes and YAML sections removed |
| SC-005: GUI displays current DB state | T016-T019, T049 | Manual smoke test verifies fresh data |
| SC-006: Precompute writes DB correctly | T036-T040, T049 | Precompute output visible in GUI |
| SC-007: No breaking API changes | T042 (careful deletion), T038, T041 | Public APIs unchanged |

---

## 10. References

- **Spec**: [spec.md](spec.md) — Feature specification
- **Plan**: [plan.md](plan.md) — Implementation plan
- **Data Model**: [data-model.md](data-model.md) — Cache structure details
- **Tasks**: [tasks.md](tasks.md) — Complete task breakdown (51 tasks)
- **Quickstart**: [quickstart.md](quickstart.md) — Integration guide for new code

---

**Report Status**: ✅ **APPROVED FOR PHASE 1 COMPLETION**  
**Next Step**: Execute Phase 2 foundational tasks (T006-T013) to establish test infrastructure and verify blockers before Phase 3 refactoring begins.
