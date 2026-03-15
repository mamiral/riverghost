# Contract: Aggregation Service API

**Date**: March 13, 2026
**Feature**: [specs/001-aggregated-aof-stats/spec.md](specs/001-aggregated-aof-stats/spec.md)

## Overview
Internal contract for the aggregation service that handles storing runs and computing aggregated statistics.

## Interface: AggregationService

### Methods

#### store_run(scenario_key: str, run_data: RunData) -> None
Stores a new run for aggregation.

**Parameters**:
- `scenario_key`: Deterministic scenario identifier
- `run_data`: Structured run results

**Preconditions**:
- Valid scenario_key format
- run_data contains complete simulation results

**Postconditions**:
- Run persisted in database
- Aggregation triggered asynchronously

#### get_aggregated_stats(scenario_key: str) -> AggregatedResults
Retrieves aggregated statistics for a scenario.

**Parameters**:
- `scenario_key`: Scenario identifier

**Returns**:
- AggregatedResults with per-hand, per-metric data

**Preconditions**:
- scenario_key exists (or returns empty results)

**Postconditions**:
- Results computed from all matching runs
- Includes confidence metadata

## Data Structures

### RunData
```python
@dataclass
class RunData:
    timestamp: datetime
    sim_count: int
    combo_samples: int
    timeout: float
    seed: int
    results: dict[str, dict[str, float]]  # hand -> metric -> value
```

### AggregatedResults
```python
@dataclass
class AggregatedResults:
    scenario_key: str
    statistics: dict[str, dict[str, Statistic]]  # hand -> metric -> stats

@dataclass
class Statistic:
    value: float
    sample_count: int
    confidence: float
```

## Error Handling
- Invalid scenario_key: ValueError
- Database errors: DatabaseError
- Aggregation failures: AggregationError