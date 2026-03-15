# Research Findings: Aggregated AoF Run Statistics Database

**Date**: March 13, 2026
**Feature**: [specs/001-aggregated-aof-stats/spec.md](specs/001-aggregated-aof-stats/spec.md)

## Research Tasks Completed

### RT-001: Aggregation Math for Monte Carlo Results
**Task**: Research best practices for aggregating Monte Carlo simulation results using weighted totals (not average-of-averages).

**Decision**: Use weighted average where each run's contribution is weighted by its sample count. For probabilities: `aggregated_prob = sum(run_prob * run_samples) / total_samples`. For EVs: `aggregated_ev = sum(run_ev * run_samples) / total_samples`.

**Rationale**: Ensures runs with more samples have proportional influence. Avoids bias from varying run sizes.

**Alternatives considered**: Simple average (rejected: doesn't account for sample size differences), geometric mean (rejected: not appropriate for additive metrics).

### RT-002: Confidence Indicator Calculation
**Task**: Research how to compute confidence indicators from sample counts for Monte Carlo estimates.

**Decision**: Use coefficient of variation as confidence proxy: `confidence = sqrt(total_samples) / (mean_estimate * sqrt(total_samples))` or simplified `confidence_score = min(1.0, sqrt(total_samples) / 1000)` for 0-1 scale.

**Rationale**: Higher sample counts provide more reliable estimates. Provides intuitive 0-1 scale for UI display.

**Alternatives considered**: Standard error (too complex for UI), p-value (not applicable), fixed thresholds (less adaptive).

### RT-003: Runtime Parameter Keying Policy
**Task**: Define how runtime parameters (sim count, combo samples, timeout, seed) affect scenario keying - merge or partition evidence.

**Decision**: Merge evidence across all runtime parameters for same scenario semantics key. Runtime parameters do not partition - they are metadata, not identity.

**Rationale**: Scenario identity is defined by poker situation (position/action/etc.), not execution details. Allows combining results from different run configurations.

**Alternatives considered**: Partition by sim count (rejected: would fragment evidence), partition by seed (rejected: defeats purpose of aggregation).

### RT-004: Database Migration Strategy
**Task**: Research migration strategies from snapshot table to cumulative statistics storage.

**Decision**: Use coexistence with fallback: new aggregation table alongside old snapshot table. Feature flag controls which to use. Gradual migration with data validation.

**Rationale**: Zero-downtime rollout, allows rollback, preserves existing data integrity.

**Alternatives considered**: One-time migration (riskier), drop old table immediately (breaks compatibility).

### RT-005: Degraded Status Aggregation Rules
**Task**: Research how to handle degraded statuses (timeout/error/missing/no_contest) in aggregation.

**Decision**: Prioritize available data over degraded. For cells: if any run has valid data, aggregate from valid runs only. Sample counts accumulate regardless. Degraded cells show as degraded if no valid data exists.

**Rationale**: Maximizes available information while maintaining data quality indicators.

**Alternatives considered**: Exclude entire runs with degraded cells (loses valid data), average degraded values (inappropriate).

## Resolved Technical Context Updates

- Aggregation math: Weighted averages by sample count
- Confidence calculation: sqrt(sample_count) normalized scale
- Keying policy: Runtime parameters merged, scenario semantics only
- Migration: Coexistence with feature flag
- Degraded handling: Prioritize valid data, accumulate samples

All NEEDS CLARIFICATION resolved. Ready for Phase 1 design.