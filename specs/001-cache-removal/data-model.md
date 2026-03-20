# Data Model: Cache System Removal

**Feature**: 001-cache-removal | **Date**: 2026-03-20

## 1. Cache Components to Remove

### 1.1 In-Memory Cache

**Location**: `python/hopilot/aof_gto_browser_data_provider.py`

**Component**: `AoFBrowserDataProvider._matrix_cache`

```python
# BEFORE (remove)
class AoFBrowserDataProvider:
    def __init__(self):
        self._matrix_cache = {}  # Delete this
        self._cache_loader = CacheLoader()  # Delete this
        self._aggregation_stats = {}  # Delete this
    
    def get_matrix_payload(self, position, action):
        # Cache lookup (delete)
        if (position, action) in self._matrix_cache:
            return self._matrix_cache[(position, action)]
        # Cache miss → fallback to simulation (delete)
        result = self._compute_via_monte_carlo(position, action)
        self._matrix_cache[(position, action)] = result
        return result
    
    def invalidate_cache(self):  # Delete this method
        self._matrix_cache.clear()
```

**Replacement**: 
```python
# AFTER (new)
class AoFBrowserPanel:
    async def load_matrix(self, position, action):
        # Direct database query
        session = get_db_session()  # SQLAlchemy session
        matrix = session.query(StrategyMatrix).filter(
            StrategyMatrix.position == position,
            StrategyMatrix.action == action
        ).first()
        return matrix
```

**Files Affected**:
- `python/hopilot/aof_gto_browser_data_provider.py` — **DELETE ENTIRELY**

### 1.2 Persistent Cache Database

**Location**: Path configured in `config/gto_defaults.yaml` (e.g., `cache.db`)

**Components**:
- SQLite database file storing computed strategies
- Aggregation statistics tables
- Any other cached computations

**Deletion Strategy**:
- During refactoring: Stop creating new cache DB files
- During cleanup: Delete existing cache DB files from user installations
- Configuration: Remove `cache_db_path` setting

**Files Affected**:
- Configuration files referencing cache DB path
- Any cache initialization code (constructor calls, DB setup)

### 1.3 Cache Configuration Settings

**From** `config/gto_defaults.yaml`:

```yaml
# DELETE THESE
aof_browser_cache:
  enabled: true
  ttl: 3600
  cache_db_path: "${HOME}/.hopilot/cache.db"

aggregation:
  cache_mode: "persistent"
  enabled: true
```

**From** `python/hopilot/config.py`:

```python
# DELETE THESE
class AoFBrowserCacheConfig(BaseModel):
    enabled: bool
    ttl: int
    cache_db_path: str

class AggregationCacheConfig(BaseModel):
    cache_mode: str
    enabled: bool
```

**Replacement**: No cache configuration needed. Only database connection:

```yaml
# KEEP/ADD
database:
  url: "sqlite:///hopilot.db"  # or PostgreSQL
  pool_size: 5
```

### 1.4 Cache Utility Modules

**Files to Delete or Refactor**:

- `python/hopilot/cache_loader.py` (if exists) — **DELETE**
- `python/hopilot/cache_manager.py` (if exists) — **DELETE**
- `python/hopilot/aggregation_cache.py` (if exists) — **DELETE**
- Any cache initialization functions — **DELETE**
- Any cache invalidation callbacks — **DELETE**

---

## 2. Database Query Pattern Replacements

### 2.1 Matrix Payload Query

**Purpose**: GUI displays strategy matrix for a given position and opponent action

**Old Pattern** (cache):
```python
provider = AoFBrowserDataProvider()
payload = provider.get_matrix_payload(position="CO", action="open_raise")
# Returns: {"13/13": {"As": [0.45, 0.35, ...], ...}, ...}
```

**New Pattern** (SQLAlchemy):
```python
from hopilot.models import StrategyMatrix, MatrixValue  # SQLAlchemy models
from sqlalchemy import select

# In GUI component
session = get_db_session()
matrix = session.query(StrategyMatrix).filter(
    StrategyMatrix.position_name == "CO",
    StrategyMatrix.action_name == "open_raise"
).first()

# Extract matrix values
payload = {}
for hero_hand, villain_hand in matrix.values:
    # Build payload structure
    ...

return payload
```

**Database Tables Used**:
- `strategy_matrix` → position, action, matrix metadata
- `matrix_values` → individual cell values (equity, frequency, etc.)

### 2.2 Aggregation Statistics Query

**Purpose**: Display heatmap or convergence stats

**Old Pattern** (aggregation cache):
```python
stats = provider.get_aggregation_stats(position="CO")
# Returns: computed win/loss frequencies, convergence metrics
```

**New Pattern** (SQLAlchemy + View):
```python
# Option A: Database view + SQLAlchemy model
session = query.subquery(
    select(AggregationView).filter(
        AggregationView.position == "CO"
    )
)
stats = session.first()

# Option B: SQLAlchemy query with aggregation
from sqlalchemy import func
stats = session.query(
    MatrixValue.position,
    func.avg(MatrixValue.win_probability).label("avg_win"),
    func.count(MatrixValue.id).label("total_cells")
).group_by(MatrixValue.position).filter(
    MatrixValue.position == "CO"
).first()
```

**Database Tables/Views Used**:
- `matrix_values` → cell-level data
- `aggregation_view` (optional materialized view) → pre-computed stats

### 2.3 Convergence Metrics Query

**Purpose**: Display convergence plot (simulation convergence over time)

**Old Pattern** (cached statistics):
```python
convergence = provider.get_convergence_metrics(position="CO", action="open_raise")
# Returns: [{"iteration": 1000, "error": 0.05}, ...]
```

**New Pattern** (SQLAlchemy):
```python
session.query(ConvergenceMetrics).filter(
    ConvergenceMetrics.position == "CO",
    ConvergenceMetrics.action == "open_raise"
).order_by(ConvergenceMetrics.iteration).all()
```

**Database Tables Used**:
- `convergence_metrics` → stored after precompute completion

---

## 3. Normalized Database Schema (Expected)

### Core Tables

#### positions
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    name VARCHAR(10),        -- "UTG", "CO", "BTN", "SB", "BB"
    seat_count INTEGER,      -- 2-6 seat games
    button_position INTEGER,
    created_at TIMESTAMP
);
```

#### actions
```sql
CREATE TABLE actions (
    id INTEGER PRIMARY KEY,
    position_id INTEGER FOREIGN KEY positions(id),
    name VARCHAR(50),        -- "open_raise", "call", "3bet", etc.
    action_order INTEGER,    -- sequence in action tree
    created_at TIMESTAMP
);
```

#### hands
```sql
CREATE TABLE hands (
    id INTEGER PRIMARY KEY,
    hero_hand VARCHAR(4),    -- "As", "KhKd", etc.
    villain_range VARCHAR,   -- "AA-QQ, AK+", etc.
    created_at TIMESTAMP
);
```

#### strategy_matrix
```sql
CREATE TABLE strategy_matrix (
    id INTEGER PRIMARY KEY,
    position_id INTEGER FOREIGN KEY positions(id),
    action_id INTEGER FOREIGN KEY actions(id),
    hero_hand VARCHAR(4),
    villain_hand_pattern VARCHAR,
    matrix_data JSONB,       -- or individual rows
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### matrix_values
```sql
CREATE TABLE matrix_values (
    id INTEGER PRIMARY KEY,
    strategy_matrix_id INTEGER FOREIGN KEY strategy_matrix(id),
    hero_hand VARCHAR(4),
    villain_hand VARCHAR(4),
    win_probability FLOAT,   -- 0.0-1.0
    action_frequency FLOAT,  -- 0.0-1.0
    expected_value FLOAT,
    confidence FLOAT,        -- convergence confidence
    created_at TIMESTAMP
);
```

#### convergence_metrics
```sql
CREATE TABLE convergence_metrics (
    id INTEGER PRIMARY KEY,
    position_id INTEGER FOREIGN KEY positions(id),
    action_id INTEGER FOREIGN KEY actions(id),
    iteration INTEGER,
    error FLOAT,             -- convergence error at this iteration
    timestamp TIMESTAMP,
    created_at TIMESTAMP
);
```

### Optimization: View for GUI Queries

```sql
-- Pre-join strategy_matrix with related entities for GUI queries
CREATE VIEW matrix_with_context AS
SELECT
    sm.id as matrix_id,
    p.name as position_name,
    a.name as action_name,
    sm.hero_hand,
    sm.villain_hand_pattern,
    mv.hero_hand,
    mv.villain_hand,
    mv.win_probability,
    mv.action_frequency,
    mv.confidence
FROM strategy_matrix sm
JOIN positions p ON sm.position_id = p.id
JOIN actions a ON sm.action_id = a.id
LEFT JOIN matrix_values mv ON sm.id = mv.strategy_matrix_id;
```

---

## 4. Data Flow Diagram

### Old Flow (Cache-Based)

```
Precompute System
    ↓
    Write → Cache DB (SQLite)
    ↓
GUI Startup
    ↓
    Read → Cache DB
    ↓ (or miss)
    Fallback → Monte Carlo (slow)
    ↓
    Store in _matrix_cache (in-memory)
    ↓
GUI Display
```

**Problems**: Stale cache, multiple sources, inconsistency

### New Flow (Database-Based)

```
Precompute System
    ↓
    Write → Normalized Database (SQLAlchemy)
    ↓
GUI Startup
    ↓
    SQLAlchemy Session established (connection pool ready)
    ↓
GUI User Action (display matrix)
    ↓
    Query via SQLAlchemy ORM → Database
    ↓
GUI Display (always current)
```

**Advantages**: Single source, always current, no stale risk, connection pooling

---

## 5. Test Data Structure

### Database Fixture Pattern

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def test_db():
    """Create SQLite in-memory test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine

@pytest.fixture
def db_session(test_db):
    """Per-test database session"""
    connection = test_db.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def sample_matrix(db_session):
    """Sample strategy matrix for testing"""
    position = Position(name="CO", seat_count=6)
    action = Action(name="open_raise", position_id=position.id)
    matrix = StrategyMatrix(
        position_id=position.id,
        action_id=action.id,
        hero_hand="AsKs",
        villain_hand_pattern="AA-QQ, AK+"
    )
    db_session.add_all([position, action, matrix])
    db_session.commit()
    return matrix
```

### Test Refactoring

**Before** (cache mocking):
```python
def test_gui_display_matrix(mocker):
    mock_provider = mocker.Mock(AoFBrowserDataProvider)
    mock_provider.get_matrix_payload.return_value = {
        "13/13": {"As": [0.45, ...]}
    }
    panel = AoFBrowserPanel(data_provider=mock_provider)
    # ... test
```

**After** (database fixture):
```python
def test_gui_display_matrix(db_session, sample_matrix):
    panel = AoFBrowserPanel(db_session=db_session)
    result = panel.load_matrix("CO", "open_raise")
    assert result.hero_hand == "AsKs"
    # ... test with real data structure
```

---

## 6. Migration Checklist

| Component | Action | Status |
|-----------|--------|--------|
| `AoFBrowserDataProvider` | Delete entirely | Pending |
| Cache configuration | Remove from config.py & YAML | Pending |
| Cache initialization | Remove from GUI startup | Pending |
| In-memory cache | Remove `_matrix_cache` dict | Pending |
| Persistent cache DB | Delete initialization code | Pending |
| GUI queries | Replace `provider.get_matrix_payload()` with SQLAlchemy | Pending |
| Tests | Refactor to use database fixtures | Pending |
| Precompute writes | Verify writes to normalized DB | Pending |
| Performance test | Confirm < 100ms p95 query time | Pending |

---

## 7. Dependencies Between Component Changes

```
Phase 1: Identify what to delete
    ↓
Phase 2a: Delete cache utility classes (no deps)
    ↓
Phase 2b: Refactor GUI to use SQLAlchemy
    ├─> Requires SQLAlchemy models defined
    ├─> Requires DB connection in GUI
    └─> Can be tested immediately with DB fixtures
    ↓
Phase 2c: Update tests
    ├─> Replace cache mocks with fixtures
    └─> Delete cache-only tests
    ↓
Phase 2d: Update configuration
    └─> Remove cache settings (safe once GUI no longer references them)
    ↓
Phase 3: Integration testing
    └─> Verify GUI + precompute + DB interaction
```

---

## Summary

**Removal Scope**:
- 1 class (`AoFBrowserDataProvider`) — DELETE
- ~2000 lines of cache infrastructure — DELETE
- 4-5 config settings — DELETE

**Addition Scope**:
- ~800 lines of SQLAlchemy query code — ADD
- Database connection setup — ADD
- Test fixtures — ADD

**Net Change**: ~1200 lines removed (net negative; good for codebase simplicity)

**Truth Source**: Database (single, always current, no staleness)

**Testing**: 22 test files refactored to use database fixtures (safer regression detection)
