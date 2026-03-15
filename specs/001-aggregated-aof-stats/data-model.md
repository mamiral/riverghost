# Data Model: Aggregated AoF Run Statistics Database

**Date**: March 13, 2026
**Feature**: [specs/001-aggregated-aof-stats/spec.md](specs/001-aggregated-aof-stats/spec.md)

## Entities

### Scenario
Represents a unique poker scenario configuration.

**Fields**:
- `scenario_key` (string, primary key): Deterministic hash of position/action/opponents/pot/bet/mode
- `position` (string): Player position (e.g., "BTN", "SB")
- `action` (string): Current action context
- `opponents` (int): Number of opponents
- `pot` (float): Current pot size
- `bet` (float): Bet amount
- `mode` (string): Game mode (e.g., "cash", "tournament")

**Validation Rules**:
- `scenario_key` must be SHA1 hash of concatenated fields
- All fields required for key generation
- `opponents` > 0
- `pot`, `bet` >= 0

**Relationships**:
- 1:N with Run
- 1:N with Statistics

### Run
Represents a single execution of simulations for a scenario.

**Fields**:
- `run_id` (int, auto-increment primary key)
- `scenario_key` (string, foreign key to Scenario)
- `timestamp` (datetime): When run was executed
- `sim_count` (int): Number of Monte Carlo simulations
- `combo_samples` (int): Range sampling size
- `timeout` (float): Timeout in seconds
- `seed` (int): Random seed used
- `payload` (json): Raw simulation results per hand/metric

**Validation Rules**:
- `sim_count`, `combo_samples` > 0
- `timeout` > 0
- `payload` must contain valid hand/metric data structure

**Relationships**:
- N:1 with Scenario

### Statistics
Per-hand, per-metric aggregated data computed from multiple runs.

**Fields**:
- `stats_id` (int, auto-increment primary key)
- `scenario_key` (string, foreign key to Scenario)
- `hand` (string): Hand identifier (treys format, e.g., "AsKh")
- `metric` (enum): WIN_LOSE_PROBABILITY, EV, EQUITY, EQR
- `aggregated_value` (float): Weighted average value
- `total_samples` (int): Sum of samples across all runs
- `confidence_score` (float): 0-1 confidence indicator

**Validation Rules**:
- `hand` valid poker hand format
- `metric` in allowed enum values
- `total_samples` > 0
- `confidence_score` in [0,1]
- `aggregated_value` in valid range for metric (e.g., probabilities [0,1])

**Relationships**:
- N:1 with Scenario

## State Transitions
None - entities are append-only with aggregation computed on read.

## Data Flow
1. Run executes → inserts Run record
2. Aggregation job → updates/inserts Statistics records
3. Query → reads aggregated Statistics for scenario