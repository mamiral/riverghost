# Feature Specification: Remove Cache-Based System from AOF GTO Browser

**Feature Branch**: `001-cache-removal`  
**Created**: 2026-03-20  
**Status**: Draft  
**Input**: User description: "Remove Cache-Based System from AOF GTO Browser. The aof_gto_browser_gui is using an obsolete three-layer cache system (in-memory, persistent SQLite, aggregation cache) as its primary data source instead of the normalized database. This is a design mistake causing stale data issues and maintenance burden. Replace the cache-based data source with direct normalized database queries. Eliminate all cache infrastructure, cache-related configuration, and cache-dependent code paths. The normalized database becomes the single source of truth."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - GUI Displays Current Database State (Priority: P1)

AOF GTO Browser users (poker analysts) expect the GUI to display current analysis data from the latest precompute runs. Currently, data may be stale due to cache layers not being automatically invalidated.

**Why this priority**: This is the core value proposition—the GUI must reflect ground truth (current database state), not outdated cache. Without this, users cannot trust the analysis.

**Independent Test**: Can be fully tested by launching the GUI after a precompute run and verifying that displayed matrices match database values WITHOUT any manual cache refresh/invalidation.

**Acceptance Scenarios**:

1. **Given** a precompute run has completed and written data to normalized database, **When** GUI loads the AOF browser, **Then** all displayed matrices match the database values exactly (zero stale cache risk)
2. **Given** user navigates between different positions/actions in GUI, **When** each view loads, **Then** data is queried fresh from database without cache layer intermediation
3. **Given** user compares GUI display to database query results, **When** values are matched, **Then** they are identical (no aggregation mismatch)

---

### User Story 2 - No Cache-Related Configuration Needed (Priority: P1)

Application configuration must be simplified by removing all cache tuning parameters. Developers should not need to manage cache TTLs, cache DB paths, cache enable/disable flags, or aggregation cache modes.

**Why this priority**: Simplified configuration reduces operational complexity and prevents misconfiguration (e.g., cache disabled when developer expects it enabled).

**Independent Test**: Can be fully tested by loading application with configuration containing ONLY database settings (no cache settings) and verifying that all GUI data loads correctly.

**Acceptance Scenarios**:

1. **Given** config file with NO cache-related settings, **When** application starts, **Then** GUI functions normally with all data from database
2. **Given** application attempts to parse configuration, **When** obsolete cache settings are encountered, **Then** they are ignored or error clearly (with migration guidance)

---

### User Story 3 - Tests Pass Without Cache Mocking (Priority: P1)

All existing tests for AOF browser (22 test files identified) must pass after replacing cache mocks with database fixtures.

**Why this priority**: Tests are the safety net for this large refactoring. They must validate that behavior is preserved while implementation changes.

**Independent Test**: Can be fully tested by running full test suite after refactoring and verifying all tests pass.

**Acceptance Scenarios**:

1. **Given** test file mocks `AoFBrowserDataProvider` cache methods, **When** test is refactored to use database fixture instead, **Then** test passes and covers equivalent functionality
2. **Given** test file creates cache DB or cache files, **When** tests run after refactoring, **Then** no cache artifacts are created
3. **Given** multiple tests run concurrently, **When** database fixtures are used, **Then** tests remain isolated (no cross-test cache pollution)

---

### User Story 4 - Precompute System Writes to Database (Priority: P2)

Precompute pipeline (`aof_precompute_runner.py`) must write all results directly to normalized database. No intermediate cache DB writes.

**Why this priority**: The precompute system is the data producer. It must produce data in the normalized form, not cache form.

**Independent Test**: Can be fully tested by running precompute, querying normalized database, and verifying all computed values are present and correct.

**Acceptance Scenarios**:

1. **Given** precompute runner configured with database URL, **When** simulation completes, **Then** all results written to normalized database tables
2. **Given** precompute progress callbacks fire, **When** callbacks reference data location, **Then** they mention database, not cache
3. **Given** precompute encounters missing pre-computed values, **When** missing values are computed, **Then** results go to normalized database, not cache

### Edge Cases

- What happens when normalized database contains no data for a requested position/action? (Should GUI show "no data" gracefully, not fall back to cache computation)
- How does GUI handle database connection failures? (Should error clearly, not silently degrade to cached value)
- What if precompute system crashes mid-run before all data is written? (Database transactions should ensure incomplete runs don't corrupt state; cache will not be partially updated)

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: GUI component `AoFBrowserPanel` MUST query normalized database for all matrix data using SQLAlchemy ORM
- **FR-002**: System MUST NOT initialize, populate, or use in-memory cache (`_matrix_cache`) for GUI data retrieval
- **FR-003**: System MUST NOT create or persist any cache database files; all existing cache DB files and persistent cache artifacts MUST be deleted during the refactoring without attempting data migration
- **FR-004**: System MUST eliminate cache TTL logic, cache invalidation callbacks, and cache fallback simulation paths
- **FR-005**: Configuration system MUST NOT require or parse cache-related settings (`aof_browser_cache.enabled`, `cache_db_path`, `aggregation.cache_mode`)
- **FR-006**: Precompute runner MUST write all simulation results directly to normalized database tables without intermediate cache layer
- **FR-007**: All 22 test files MUST be updated to use database fixtures instead of cache mocking; tests that only test cache behavior MUST be deleted
- **FR-008**: System MUST remove `AoFBrowserDataProvider` class entirely, deleting all cache-based methods and leaving no trace of cache-based data access patterns
- **FR-009**: GUI state machine MUST NOT have transitions dependent on cache validation or cache availability

### Key Entities *(cache components to be removed)*

- **In-Memory Cache** (`_matrix_cache`): Temporary storage in `AoFBrowserDataProvider` holding matrix payloads. Must be eliminated completely.
- **Persistent Cache DB**: SQLite database storing aggregated statistics and cached computations. Files to be deleted.
- **Cache Configuration**: Settings in `config/gto_defaults.yaml` for cache TTL, paths, and enable/disable flags. Must be removed.
- **Cache Utility Classes**: Helper modules for cache initialization, invalidation, and aggregation. Must be deleted or refactored.
- **Normalized Database Schema** (replaces cache): `positions`, `actions`, `metrics`, `hands`, `strategy_matrix`, `matrix_values` tables as source of truth.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All GUI data queries come from normalized database: 100% of matrix payload requests use `DatabaseRepository` queries (zero cache lookups)
- **SC-002**: Zero cache artifacts created: No in-memory cache created during GUI session; no persistent cache DB files created
- **SC-003**: All 22 test files pass: 100% of original test suite passes with refactored database fixtures (tests deleted only if they SOLELY tested cache behavior)
- **SC-004**: Configuration simplified: Number of cache-related configuration settings = 0 (all removed from config schema)
- **SC-005**: Data consistency verified: GUI display matches database values with zero stale-data risk (all data flows through database queries)
- **SC-006**: Precompute integration tested: Precompute runner successfully writes to database; GUI loads and displays precompute results correctly on next launch
- **SC-007**: No breaking API changes: Public API contracts preserved (if `AoFBrowserDataProvider` is public, it remains callable; only implementation changes to use database)

## Clarifications

### Session 2026-03-20

- Q1: Database Query Layer → A: SQLAlchemy ORM (project standard)
- Q2: Existing Cache Data Handling → A: Delete without migration (cache is not source of truth)
- Q3: Other Systems Consuming Cache → A: GUI-only dependency (safe to delete `AoFBrowserDataProvider` entirely with no other fallout)

- Normalized database schema exists and is queryable (verified in architecture analysis)
- `DatabaseRepository` or equivalent ORM query layer is available and ready to use
- Precompute system can be modified to write directly to normalized database without breaking simulations
- GUI does not require in-memory caching for responsiveness (database + connection pooling + query optimization will be sufficient)
- 22 identified test files are all the cache-dependent tests; no cache dependencies hidden elsewhere
- `AoFBrowserDataProvider` is only imported by GUI components (no other systems depend on it)
- SQLAlchemy ORM models are available for querying normalized database

## Clarification Status

✅ **COMPLETE** — All 3 critical ambiguities resolved:
1. **Database Query Layer** → SQLAlchemy ORM (project standard)
2. **Cache Data Migration** → Delete without migration (cache is not source of truth)
3. **Dependency Scope** → GUI-only (safe deletion of `AoFBrowserDataProvider`)
