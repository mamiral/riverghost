# Research: GTO Analysis Integration in Poker Simulator

**Status**: Complete - Integration approach determined
**Date**: 2026-03-03

## Research Summary

Integration of GTO analysis into the existing poker simulator requires modifying the simulation workflow to include GTO threshold calculations alongside regular equity analysis. The existing architecture supports this through the modular GUI component system.

## Technical Approach

**Integration Strategy**: Enhance the existing `SimulationPanel` component with GTO analysis capabilities rather than maintaining separate panels. This preserves all existing simulator functionality while adding GTO features seamlessly.

**Key Integration Points**:
- Add GTO analysis button to `SimulationPanel`
- Extend parameter inputs to include GTO-specific settings (bonus payouts)
- Display GTO results alongside regular simulation results
- Leverage existing `AllInFoldGTOSolver` with progress tracking and caching

**UI Modifications**:
- Add "Run GTO Analysis" button next to existing "Run Simulation" button
- Add bonus payout configuration inputs in simulation panel
- Extend results display to show GTO threshold, optimal range, and hand recommendations

## Decision Log

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Integrate into SimulationPanel | Maintains single-panel workflow, preserves existing functionality | Keep separate GTO panel (rejected: violates "not be a new panel" requirement) |
| Extend existing parameter inputs | Consistent with current UI patterns | Create separate GTO configuration panel (rejected: adds complexity) |
| Display results alongside equity | Shows both analysis types together | Tabbed results display (rejected: overcomplicates simple workflow) |
| Use existing GTO solver | Leverages proven implementation | Rewrite GTO logic (rejected: unnecessary duplication) |

## Implementation Requirements Confirmed

- **SimulationPanel Enhancement**: Add GTO button and bonus payout inputs
- **Result Display**: Extend to show GTO threshold and recommendations
- **Parameter Integration**: Connect simulator state (opponents, pot) to GTO calculations
- **Progress Handling**: Integrate GTO progress callbacks with existing UI
- **Error Handling**: Maintain existing error display patterns

## Dependencies Confirmed

- PokerAnalyzer: ✅ Existing equity calculations
- AllInFoldGTOSolver: ✅ GTO threshold analysis with bonus payouts
- SimulationPanel: ✅ Existing GUI component to enhance
- CardAssignmentManager: ✅ Provides scenario data for GTO analysis

**No external research required - all components exist and integration approach is clear.**</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\002-gto-simulator-integration\research.md