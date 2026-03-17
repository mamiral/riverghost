# Quick Start: Database Schema Browser Integration

**Feature**: 001-db-schema-browser-integration  
**Date**: 2026-03-17  
**Audience**: Developers integrating the browser with normalized database  

## Overview

This integration replaces the browser's cache system with the normalized relational database schema. The browser now retrieves GTO strategy data from persistent storage with advanced querying capabilities.

## Prerequisites

- Python 3.x with venv activated
- Access to 001-normalized-db-schema implementation
- SQLite database with populated simulation data
- Existing browser components (AoFBrowserDataProvider, AoFBrowserPanel)

## Key Changes

### Before (Cache System)
```python
# Old cache-based approach
provider = AoFBrowserDataProvider(
    cache_enabled=True,
    cache_db_path="python/hopilot/cache/aof_scenario_cache.sqlite3"
)
```

### After (Database Integration)
```python
# New database-integrated approach
from hopilot.gto.database_repository import DatabaseRepository

provider = AoFBrowserDataProvider(
    database_repository=DatabaseRepository(
        db_path="python/hopilot/data/normalized_poker.db"
    )
)
```

## Data Model Mapping

### Position Selection
```python
# Browser context
position = PositionContext.UTG

# Maps to database query
# WHERE s.parameters->>'position' = 'UTG'
```

### Action Selection
```python
# Browser context
action = ActionContext.ALL_IN

# Maps to betting pattern analysis
# WHERE EXISTS (SELECT 1 FROM Bets WHERE action_type = 'raise')
```

### Metric Display
```python
# Browser context
metric = MetricType.EV

# Maps to database column
# SELECT am.jackpot_adjusted_ev FROM AggregatedMetrics am
```

## Usage Examples

### Basic Matrix Retrieval
```python
from hopilot.gto.database_repository import DatabaseRepository

repo = DatabaseRepository(db_path="normalized_poker.db")

# Get complete strategy matrix
matrix = await repo.get_strategy_matrix(
    position=PositionContext.BTN,
    action=ActionContext.FOLD,
    metric=MetricType.EQUITY
)

# Access specific hand
hand_value = matrix[HandKey("AKs")]
print(f"AKs equity: {hand_value.value:.1%}")
```

### Convergence Analysis
```python
# Get convergence data over time
convergence = await repo.get_convergence_data(
    position=PositionContext.SB,
    action=ActionContext.ALL_IN
)

for point in convergence:
    print(f"Simulations: {point.num_simulations}, "
          f"Equity: {point.average_equity:.3f}")
```

## Configuration

### Database Connection
```yaml
# config/gto_defaults.yaml
database:
  path: "python/hopilot/data/normalized_poker.db"
  connection_pool_size: 5
  timeout_ms: 500
```

### Browser Settings
```yaml
# config/gto_defaults.yaml
aof_browser:
  data_source: "database"  # Changed from "cache"
  enable_convergence_analysis: true
  enable_jackpot_adjusted_ev: true
```

## Migration Guide

### Phase 1: Dual Operation
```python
# Run both systems in parallel
provider = AoFBrowserDataProvider(
    cache_enabled=True,  # Keep old system
    database_repository=DatabaseRepository(),  # Add new system
    migration_mode=True  # Enable comparison logging
)
```

### Phase 2: Cutover
```python
# Switch completely to database
provider = AoFBrowserDataProvider(
    database_repository=DatabaseRepository(),
    # cache_enabled=False (default)
)
```

## Performance Expectations

- **Matrix Loading**: <500ms for complete 13x13 matrix
- **Hand Lookup**: <100ms for individual hand queries
- **Concurrent Users**: Supports up to 10 simultaneous users
- **Data Freshness**: Updates reflect latest simulations within 30 seconds

## Troubleshooting

### Common Issues

**Database Connection Failed**
```python
# Check database path and permissions
db_path = Path("python/hopilot/data/normalized_poker.db")
if not db_path.exists():
    raise FileNotFoundError(f"Database not found: {db_path}")
```

**Missing Strategy Data**
```python
# Verify simulation data exists
simulations = await repo.get_simulations_for_context(
    position=PositionContext.UTG,
    action=ActionContext.FOLD
)
if not simulations:
    print("No simulation data found for this context")
```

**Slow Queries**
```python
# Check database indexes
# Ensure AggregatedMetrics.cell_id is indexed
# Ensure Simulations.parameters has JSON index
```

## Testing

### Unit Tests
```bash
# Run database integration tests
pytest tests/test_database_repository.py -v

# Run browser integration tests
pytest tests/test_browser_database_integration.py -v
```

### Performance Tests
```bash
# Test query performance
pytest tests/test_database_performance.py --benchmark

# Test concurrent access
pytest tests/test_concurrent_access.py -k "10_users"
```

## Next Steps

1. Implement DatabaseRepository class
2. Update AoFBrowserDataProvider to use database
3. Add database configuration to YAML files
4. Update browser UI to show convergence/jackpot data
5. Migrate existing cache data to normalized schema