# Research: All-In-or-Fold GTO Solver with Bonus Payouts

**Status**: Complete - No research required
**Date**: 2026-02-27

## Research Summary

All technical requirements are well understood from existing codebase analysis:

- **GTO Theory**: Equity threshold calculation for binary decisions (all-in vs fold)
- **Monte Carlo Methods**: Existing PokerAnalyzer provides simulation infrastructure
- **Bonus Payout Integration**: Simple multiplier application to EV calculations
- **YAML Persistence**: Existing Pydantic patterns for configuration management
- **GUI Integration**: Pygame component architecture already established

## Decision Log

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Extend existing AllInFoldGTOSolver | Builds on working PoC, maintains consistency | Start fresh (rejected: would duplicate working code) |
| YAML for range storage | Consistent with existing config patterns | JSON (rejected: less human-readable), Database (rejected: overkill for local storage) |
| Pygame for GUI components | Maintains existing UI framework | Web-based UI (rejected: changes platform requirements) |
| Monte Carlo for equity calc | Proven accuracy, existing implementation | Analytical models (rejected: too complex for bonus payouts) |

## Technical Approach

**GTO Algorithm**: Simple threshold finding - calculate EV for all hands, find equity where EV crosses zero.

**Bonus Integration**: Apply multipliers to pot size in EV calculations: `EV = equity * (pot * bonus_multiplier) - (1-equity) * bet`

**Range Optimization**: Extend solver to handle hero vs villain range matchups using Nash equilibrium approximation.

**Performance**: Target <30 seconds through simulation count optimization and result caching.

## Dependencies Confirmed

- PokerKit: Hand evaluation ✓
- Pygame: GUI components ✓  
- PyYAML: Configuration ✓
- pytest: Testing framework ✓
- Existing Monte Carlo infrastructure ✓

**No external research required - all components leverage existing proven technologies.**