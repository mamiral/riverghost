# Research: Cache-Based System Removal

**Date**: 2026-03-20  
**Feature**: 001-cache-removal  
**Purpose**: Document technical research findings and design decisions for cache removal refactoring

## 1. Cache System Architecture (Current)

### Three-Layer Cache Structure

1. **In-Memory Cache**: `AoFBrowserDataProvider._matrix_cache`
   - Python dict storing matrix payloads
   - No TTL; persists for GUI session lifetime
   - Grows unbounded as user navigates different positions/actions

2. **Persistent Cache Database**: SQLite file (location TBD via config)
   - Stores aggregated statistics and cached computation results
   - Survives application restarts
   - Separate from normalized database

3. **Aggregation Cache**: Computed statistics cache
   - Precomputed win/loss frequencies
   - Cached to avoid recomputation

### Problems with Current Design

| Issue | Impact | Severity |
|-------|--------|----------|
| **Stale data risk** | Cache not auto-invalidated; users may trust outdated analysis | HIGH |
| **Multiple sources of truth** | GUI could read cache (stale) or DB (current); inconsistency | HIGH |
| **No data refresh mechanism** | Cache has no TTL; no automatic expiration | MEDIUM |
| **Maintenance cost** | Cache invalidation logic scattered across codebase | MEDIUM |
| **Memory bloat** | In-memory cache grows unbounded over session | MEDIUM |
| **Testing complexity** | Tests must mock cache layer; obscures true behavior | MEDIUM |

---

## 2. Database Query Layer Decision: SQLAlchemy ORM

### Why SQLAlchemy (Selected)

**Decision Rationale**:
- Already used in project (confirmed from context)
- Provides: ORM with session management, connection pooling, query composition
- Type-safe queries with model definitions
- Handles schema versioning and migrations
- Active community; mature stable

### Alternative Considered: Custom Repository Pattern

**Rejected Because**:
- Adds unnecessary abstraction layer post-ORM
- SQLAlchemy already provides abstraction; Repository redundant
- Direct ORM queries are clearer for maintenance team

### Alternative Considered: Raw SQL Queries

**Rejected Because**:
- No type safety; harder to refactor
- Manual session management error-prone
- Duplicates connection pooling logic

---

## 3. Data Migration Strategy

### Decision: Delete Without Migration (Option A)

**Rationale**:
1. Cache data is **NOT truth**—DB is truth
2. Any retained cache is stale by definition
3. Clean break prevents confusion about data sources
4. Precompute system will regenerate data in DB as needed
5. Users can re-run precompute if historical caches were important

### Alternative Considered: Migrate Cache → Database

**Rejected Because**:
- Cache contains STALE data not guaranteed to match current DB
- Complicates cleanup; keeps confusion about sources
- Precompute re-computation is faster than migration validation

### Alternative Considered: Deprecation Period

**Rejected Because**:
- Cache-to-DB bridge extends technical debt
- Postpones cleanup burden to future
- User confusion persists during transition period

---

## 4. Dependency Scope: GUI-Only Consumption

### Decision: AoFBrowserDataProvider GUI-Only (Option A)

**Confirmation**: 
- Spec clarification Q3 resolved: No other systems import `AoFBrowserDataProvider`
- Safe to delete entirely
- No hidden precompute, state machine, or utility code dependencies

### Audit Plan
- Grep search for all imports of `AoFBrowserDataProvider`
- Expected result: Only `aof_gto_browser_gui.py` and GUI component files
- If unexpected dependencies found → escalate (breaks Option A assumption)

---

## 5. SQLAlchemy Session Management

### Connection Strategy

**For GUI Components**:
- Session created at app startup
- Reused for GUI queries
- Closed at app shutdown
- Connection pool handles concurrent requests (if any)

**For Tests**:
- Per-test fixtures create isolated sessions
- Database fixture setup/teardown ensures test isolation
- Mock database can use SQLite in-memory for speed

### Configuration

```yaml
# config/gto_defaults.yaml
database:
  url: "sqlite:///hopilot.db"  # or PostgreSQL, etc.
  pool_size: 5
  max_overflow: 10
```

---

## 6. Test Categorization Strategy

### 22 Test Files: Split Approach

**Cache-Only Tests** (DELETE):
- Tests that **only test cache behavior** (cache hit/miss, cache invalidation)
- No business logic validation
- Examples: `test_aof_browser_cache.py` (if exists), cache TTL tests

**Cache-Dependent Tests** (REFACTOR):
- Tests that test business logic but **currently mock cache**
- Examples: `test_aof_browser_panel.py` (tests panel rendering, but mocks data provider)
- Refactor: Replace cache mock with database fixture

**Database-Ready Tests** (NO CHANGE):
- Tests already use database or don't depend on cache
- Examples: State machine tests (may not depend on data layer)

### Phase 0 Audit Task
Run grep to identify:
- Which test files import `AoFBrowserDataProvider`
- Which test files mock cache methods
- Categorize into delete vs. refactor buckets

---

## 7. Precompute System Integration

### Current: Precompute → Cache DB Write

**Flow**:
1. `aof_precompute_runner.py` runs simulations
2. Results written to cache SQLite database
3. GUI reads from cache DB (stale copy)

### Target: Precompute → Normalized DB Write

**Flow**:
1. `aof_precompute_runner.py` runs simulations
2. Results written to normalized database (SQLAlchemy)
3. GUI queries normalized database (current state)

### Decision: Precompute Refactoring **Out of Scope** for Cache Removal

**Rationale**:
- Precompute may already write to normalized DB (or could be independent change)
- This feature focuses on GUI cache removal
- But **must verify** precompute integration before declaring GUI refactor complete

**Action Item**: Confirm with precompute owner whether writes go to DB or cache

---

## 8. Configuration Removal Scope

### Cache Settings to Remove

From `config/gto_defaults.yaml`:
- `aof_browser_cache.enabled`
- `aof_browser_cache.ttl`
- `aof_browser_cache.cache_db_path`
- `aggregation.cache_mode`
- `aggregation.enabled` (if cache-dependent)

From `python/hopilot/config.py`:
- Cache configuration classes
- Cache path resolution logic
- Cache TTL defaults

### Configuration Validation

After removal, application **must start** without cache settings:
```python
config = load_config("config.yaml")
# Should NOT require cache_db_path, cache settings, etc.
# Should ONLY require database_url (for normalized DB connection)
```

---

## 9. Performance Expectations

### GUI Query Performance Target

**< 100ms p95** for matrix payload query

**Factors**:
- SQLAlchemy ORM overhead: ~5-10ms
- Database query time: ~20-50ms (depends on position complexity)
- Network (if remote DB): ~0ms (local) - ~30ms (network)
- Total budget: 50-80ms leaves 20ms margin

### Optimization Strategy

1. **SQLAlchemy Session**: Connection pooling reuses connections
2. **Database Indexing**: Indexes on `position_id`, `action_id`, `hero_hand`, `villain_hand`
3. **Query Composition**: Avoid N+1 queries; join matrices with related tables in single query
4. **Lazy Loading**: Disable lazy loading; use eager joins for related entities

### Test: Benchmark GUI Query Time

Create test that measures:
- Cache removal: GUI query time < 100ms
- Compare vs. old cache lookup time (should be similar or faster)

---

## 10. Rollback Strategy (If Needed)

### If Phase of Refactoring Breaks Critical Path

**Rollback to**: Last stable commit before cache removal started

**Recovery**:
1. Revert all code changes (git revert branch commits)
2. Restore cache initialization in GUI
3. Run test suite to confirm stability

**Prevention**: Commit frequently; each task phase has committed checkpoint

---

## Decisions Summary

| Decision | Choice | Confidence | Next Step |
|----------|--------|------------|-----------|
| **Database Query Layer** | SQLAlchemy ORM | 100% | Use in all refactored code |
| **Cache Data Migration** | Delete without migration | 100% | Remove cache files during cleanup |
| **Dependency Scope** | GUI-only (safe to delete) | High (pending audit) | Phase 0: Confirm via grep |
| **Session Management** | SQLAlchemy session pool + fixtures | 95% | Implement connection setup |
| **Test Approach** | Split: delete cache-only, refactor dependent | 90% | Phase 0: Audit & categorize tests |
| **Precompute Integration** | Verify writes to DB (scope may be separate) | 85% | Confirm with precompute owner |
| **Performance Target** | < 100ms p95 for GUI queries | 90% | Benchmark & optimize after refactor |

---

## Open Questions (If Any)

1. **Q**: Does precompute system currently write to normalized DB or cache DB?
   - **A**: [Pending confirmation in Phase 0 audit]

2. **Q**: Are there SQLAlchemy models already defined for normalized database tables?
   - **A**: [Confirm in Phase 0; if not, may need creation as separate task]

3. **Q**: What is current database connection strategy in application?
   - **A**: [Document in Phase 0: session management, pooling config, etc.]

---

## Phase 0 Deliverables (Complete ✓)

- [x] Documented cache architecture and problems
- [x] Confirmed SQLAlchemy ORM as query layer
- [x] Locked in data migration strategy (delete without migration)
- [x] Confirmed GUI-only dependency scope
- [x] Defined test categorization approach
- [x] Outlined precompute integration verification
- [x] Set performance targets

**Status**: Ready for Phase 1 (Design Artifacts)
