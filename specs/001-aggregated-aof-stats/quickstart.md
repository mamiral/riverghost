# Quickstart: Aggregated AoF Run Statistics Database

**Date**: March 13, 2026
**Feature**: [specs/001-aggregated-aof-stats/spec.md](specs/001-aggregated-aof-stats/spec.md)

## Overview
This feature replaces snapshot caching with cumulative statistics aggregation. Repeated runs of the same scenario now improve estimate accuracy over time.

## Setup
1. Enable aggregation feature flag in `config/gto_defaults.yaml`:
   ```yaml
   aggregation:
     enabled: true
     migration_mode: coexistence
   ```

2. Run the application from `python/` directory:
   ```bash
   python -m hopilot.aof_gto_browser_gui
   ```

## Usage

### Running Scenarios
- Use the precompute runner as usual
- Each run appends evidence to existing data
- No changes to existing workflows

### Viewing Aggregated Results
- Load scenarios in the AoF browser
- Matrix shows aggregated values from all historical runs
- Cell detail panel displays sample counts and confidence indicators

### Monitoring Convergence
- Re-run scenarios multiple times
- Observe metrics stabilize and confidence scores increase
- Higher sample counts = more reliable estimates
- Confidence reaches 1.0 at ~1000 total samples

## Key Behaviors

### Aggregation Rules
- **Weighted averaging**: Runs with more samples have greater influence
- **Confidence indicators**: Based on total sample count across all runs
- **Degraded handling**: Valid data prioritized, samples still counted

### Compatibility
- Existing UI flows unchanged
- Backward compatible with legacy cache
- Feature flag allows gradual rollout

## Troubleshooting

### No Aggregation Visible
- Check feature flag is enabled
- Verify runs are completing successfully
- Check logs for aggregation errors

### Performance Issues
- Monitor database size growth
- Consider periodic cleanup of old runs
- Feature flag can disable if needed

### Data Migration
- Coexistence mode preserves old cache
- Migration validates data integrity
- Rollback possible via feature flag