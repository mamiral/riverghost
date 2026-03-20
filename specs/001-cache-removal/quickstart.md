# Quickstart: Cache Removal Refactoring

**Feature**: 001-cache-removal | **Date**: 2026-03-20  
**For**: GUI developers, test developers, precompute engineers

---

## For GUI Developers: Fetching Matrix Data

### Before (Cache-Based)

```python
from hopilot.aof_gto_browser_data_provider import AoFBrowserDataProvider

class AoFBrowserPanel:
    def __init__(self):
        self.data_provider = AoFBrowserDataProvider()
    
    def display_matrix(self, position, action):
        # Calls cache (or falls back to slow Monte Carlo simulation)
        payload = self.data_provider.get_matrix_payload(position, action)
        self._render_13x13_grid(payload)
```

**Problem**: `payload` might be stale cache or slow fallback computation

### After (Database-Based)

```python
from hopilot.models import StrategyMatrix, MatrixValue, Position, Action
from hopilot.db import get_db_session

class AoFBrowserPanel:
    def __init__(self):
        pass  # No data provider needed
    
    async def display_matrix(self, position_name, action_name):
        """Fetch matrix from database and display 13×13 grid"""
        with get_db_session() as session:
            # Query database for strategy matrix
            matrix = session.query(StrategyMatrix)\
                .join(Position)\
                .join(Action)\
                .filter(
                    Position.name == position_name,
                    Action.name == action_name
                ).first()
            
            if not matrix:
                self._show_error(f"No matrix found for {position_name} vs {action_name}")
                return
            
            # Fetch all cell values for this matrix
            cells = session.query(MatrixValue)\
                .filter(MatrixValue.strategy_matrix_id == matrix.id)\
                .all()
            
            # Build payload: {hero_hand: {opponent_hand: [frequency, color, ...]}}
            payload = self._build_payload(cells)
            self._render_13x13_grid(payload)
        
        # Session is automatically closed after with block
```

### Key Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Data source** | Cache DB (stale) | Normalized DB (current) |
| **Query method** | Provider method | Direct SQLAlchemy ORM |
| **Session** | Implicit in provider | Explicit context manager |
| **Fallback** | Monte Carlo simulation | None (DB is truth) |
| **Staleness** | Hours/days possible | Seconds old (current) |

---

## For Test Developers: Database Fixtures

### Before (Cache Mocking)

```python
import pytest
from unittest.mock import Mock, MagicMock

def test_aof_browser_panel_display_matrix(mocker):
    """Test that panel correctly displays matrix"""
    
    # Mock the data provider
    mock_provider = Mock()
    mock_provider.get_matrix_payload.return_value = {
        "13/13": {
            "As": [0.50, 0x4CAF50],  # frequency, color
            "Kh": [0.35, 0xFFC107],
            ...
        }
    }
    
    # Create panel with mock
    panel = AoFBrowserPanel()
    panel.data_provider = mock_provider
    
    # Test
    panel.display_matrix("CO", "open_raise")
    assert mock_provider.get_matrix_payload.called
    # ... more assertions
```

**Problem**: Tests don't validate real data structures or relationships

### After (Database Fixtures)

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hopilot.models import Base, Position, Action, StrategyMatrix, MatrixValue
from hopilot.db import get_db_session

# Fixture: In-memory test database
@pytest.fixture(scope="session")
def test_engine():
    """Create SQLite in-memory database for tests"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Per-test database session with rollback"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

# Fixture: Sample matrix data
@pytest.fixture
def sample_co_open_raise_matrix(db_session):
    """Populate database with CO open raise matrix"""
    
    # Create position
    position = Position(name="CO", seat_count=6)
    db_session.add(position)
    db_session.flush()
    
    # Create action
    action = Action(
        position_id=position.id,
        name="open_raise",
        action_order=1
    )
    db_session.add(action)
    db_session.flush()
    
    # Create matrix
    matrix = StrategyMatrix(
        position_id=position.id,
        action_id=action.id,
        hero_hand="AsKs",
        villain_hand_pattern="AA-QQ, AK+"
    )
    db_session.add(matrix)
    db_session.flush()
    
    # Add cell values (13×13 = 169 cells)
    test_hands = [
        ("As", "2d", 0.50, 0.8),
        ("Kh", "3h", 0.40, 0.6),
        # ... add 166 more rows
    ]
    for hero, villain, freq, confidence in test_hands:
        value = MatrixValue(
            strategy_matrix_id=matrix.id,
            hero_hand=hero,
            villain_hand=villain,
            win_probability=0.5,
            action_frequency=freq,
            confidence=confidence
        )
        db_session.add(value)
    
    db_session.commit()
    return matrix

# Test using fixtures
def test_aof_browser_panel_displays_matrix(db_session, sample_co_open_raise_matrix):
    """Test that panel correctly displays real matrix data from database"""
    
    # Create panel (no mocking needed)
    panel = AoFBrowserPanel()
    
    # Test
    panel.display_matrix("CO", "open_raise")
    
    # Verify: Query database directly to validate panel used correct data
    matrix = db_session.query(StrategyMatrix)\
        .join(Position).join(Action)\
        .filter(Position.name == "CO", Action.name == "open_raise")\
        .first()
    
    assert matrix is not None
    assert matrix.values.count() == 169  # All cells populated
    assert all(v.win_probability >= 0.0 for v in matrix.values)
    assert all(v.win_probability <= 1.0 for v in matrix.values)
    
    # Panel should display without error
    # (additional GUI assertions here)
```

### Key Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Data source** | Mock object | Real SQLite DB (in-memory) |
| **Setup** | Create mock, configure return values | Create fixtures, populate DB |
| **Data validation** | Only validates mock was called | Validates real data relationships |
| **Test isolation** | Implicit | Explicit (rollback per test) |
| **Maintainability** | Fragile (mock must match reality) | Robust (tests real DB schema) |

### Running Tests

```bash
# From project root
python -m pytest tests/test_aof_browser_panel.py -v

# With coverage
python -m pytest tests/ --cov=python/hopilot --cov-report=html
```

---

## For Precompute Engineers: Writing to Database

### Before (Cache-Based Write)

```python
from hopilot.cache_manager import CacheManager

class AoFPrecomputeRunner:
    def __init__(self):
        self.cache_manager = CacheManager()
    
    def run_simulation(self, position, action, num_iterations):
        """Run Monte Carlo and write to cache"""
        
        results = []
        for iteration in range(num_iterations):
            # Run simulation
            hero_outcomes = self._simulate_hand_outcomes()
            results.append(hero_outcomes)
        
        # Aggregate results
        aggregated = self._aggregate(results)
        
        # Write to cache DB (separate database)
        self.cache_manager.write_cache_db(position, action, aggregated)
```

**Problem**: Results written to separate cache DB, not normalized DB

### After (Database-Based Write)

```python
from hopilot.models import Position, Action, StrategyMatrix, MatrixValue, ConvergenceMetrics
from hopilot.db import get_db_session

class AoFPrecomputeRunner:
    def __init__(self):
        pass  # No cache manager needed
    
    def run_simulation(self, position_name, action_name, num_iterations):
        """Run Monte Carlo and write to normalized database"""
        
        with get_db_session() as session:
            # Get or create position and action
            position = session.query(Position).filter_by(name=position_name).first()
            action = session.query(Action)\
                .filter(
                    Action.position_id == position.id,
                    Action.name == action_name
                ).first()
            
            if not position or not action:
                raise ValueError(f"Position {position_name} or action {action_name} not found")
            
            # Create strategy matrix record
            matrix = StrategyMatrix(
                position_id=position.id,
                action_id=action.id,
                hero_hand="AsKs",  # Example starting hand
                villain_hand_pattern="AA-QQ, AK+"
            )
            session.add(matrix)
            session.flush()  # Get matrix.id for foreign keys
            
            # Run simulation iterations
            convergence_points = []
            for iteration in range(num_iterations):
                # Run one iteration of Monte Carlo
                hand_outcomes = self._simulate_iteration()
                
                # Track convergence
                error = self._compute_convergence_error(iteration, hand_outcomes)
                convergence = ConvergenceMetrics(
                    position_id=position.id,
                    action_id=action.id,
                    iteration=iteration * 1000,  # Every 1000 iterations
                    error=error
                )
                convergence_points.append(convergence)
                session.add(convergence)
            
            # Get aggregated strategy results
            aggregated_strategy = self._aggregate_results()
            
            # Write individual cell values
            for hero_hand, villain_hand, frequency, equity in aggregated_strategy:
                value = MatrixValue(
                    strategy_matrix_id=matrix.id,
                    hero_hand=hero_hand,
                    villain_hand=villain_hand,
                    action_frequency=frequency,
                    win_probability=equity,
                    confidence=self._compute_confidence(hero_hand, villain_hand)
                )
                session.add(value)
            
            # Commit all changes at once
            session.commit()
            print(f"Wrote {len(aggregated_strategy)} cells to database")
```

### Key Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Write target** | Cache DB (separate) | Normalized DB (single source) |
| **Data structure** | Aggregated cache format | Normalized rows (MatrixValue) |
| **Truth source** | Cache DB | Normalized DB |
| **GUI access** | Reads cache DB (stale copy) | Queries normalized DB (current) |

### Verifying Writes

```bash
# After precompute run, query database to verify data was written
python -c "
from hopilot.models import StrategyMatrix, MatrixValue
from hopilot.db import get_db_session

with get_db_session() as session:
    matrices = session.query(StrategyMatrix).count()
    cells = session.query(MatrixValue).count()
    print(f'Database contains {matrices} matrices with {cells} cells')
    
    # Show a sample matrix
    sample = session.query(StrategyMatrix).first()
    if sample:
        print(f'Sample: {sample.position.name} {sample.action.name} -> {len(sample.values)} cells')
"
```

---

## Configuration Changes

### Before (Cache Config)

```yaml
# config/gto_defaults.yaml
aof_browser_cache:
  enabled: true
  ttl: 3600  # 1 hour
  cache_db_path: "${HOME}/.hopilot/cache.db"

aggregation:
  cache_mode: "persistent"
  enabled: true
```

### After (No Cache Config)

```yaml
# config/gto_defaults.yaml (simplified)
database:
  url: "sqlite:///hopilot.db"  # or "postgresql://user:pass@host/dbname"
  pool_size: 5
  max_overflow: 10

# Cache settings REMOVED - no longer needed
```

---

## Troubleshooting

### "No matrix found" error

```python
# Debug: Verify data exists in database
with get_db_session() as session:
    matrices = session.query(StrategyMatrix).all()
    print(f"Total matrices: {len(matrices)}")
    for m in matrices:
        print(f"  - {m.position.name} {m.action.name}")
```

### Slow queries

```python
# Enable SQLAlchemy logging to see generated SQL
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Queries will be printed to console
```

### Test isolation issues

```python
# Ensure each test uses a fresh session/transaction
# pytest fixtures handle this automatically with rollback

# If tests interfere with each other:
# 1. Check fixture scope (should be "function", not "session")
# 2. Verify rollback is happening (check transaction.rollback())
# 3. Use unique test data (don't share fixture data between tests)
```

---

## Summary

| Role | Key Takeaway |
|------|--------------|
| **GUI Dev** | Replace `provider.get_matrix_payload()` with `session.query(StrategyMatrix).filter(...)` |
| **Test Dev** | Use database fixtures instead of mocks; validates real data relationships |
| **Precompute Eng** | Write to `StrategyMatrix` and `MatrixValue` tables instead of cache DB |

**Next Steps**:
1. Review contracts in `contracts/sqlalchemy-models.md`
2. Start refactoring: Pick one GUI panel component; migrate to database queries
3. Migrate tests: Start with simplest test file; replace mocks with fixtures
4. Iterate: Commit after each small component is working
