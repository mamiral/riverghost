# Data Model: GTO Analysis Integration in Poker Simulator

**Version**: 1.0
**Date**: 2026-03-03

## Overview

The GTO integration enhances the existing poker simulator data model with GTO-specific parameters and results. All integration leverages existing GTO data models from the core GTO solver implementation.

## Enhanced Simulator State

### Extended Simulation Parameters

```python
class SimulationParameters(BaseModel):
    """Extended simulation parameters including GTO settings."""
    # Existing parameters
    num_simulations: int = 10000
    randomize_unset: bool = True
    
    # New GTO parameters
    enable_gto_analysis: bool = False
    bonus_payouts: BonusPayouts = Field(default_factory=BonusPayouts)
    gto_pot_size: Optional[float] = None  # Uses simulation pot if not set
    gto_bet_amount: Optional[float] = None  # Uses simulation bet if not set
```

## Integration Data Flow

### Simulator to GTO Data Mapping

```
Simulator State → GTO Parameters
├── num_opponents → num_opponents
├── pot_size → pot_size (for GTO analysis)
├── bet_amount → bet_amount (for all-in scenarios)
├── bonus_payouts → bonus_payouts
└── hand_scenario → used for equity context
```

### GTO Results Integration

```python
class IntegratedResults(BaseModel):
    """Combined simulation and GTO results."""
    # Existing simulation results
    equity_results: Dict[str, Any]
    
    # New GTO results
    gto_results: Optional[Dict[str, Any]] = None
    gto_threshold: Optional[float] = None
    optimal_range: Optional[List[str]] = None
    hand_recommendations: Optional[Dict[str, str]] = None  # hand -> 'ALL-IN'/'FOLD'
```

## Validation Rules

### GTO Parameter Validation
- GTO analysis requires at least 2 players (hero + 1 opponent)
- Pot size and bet amount must be positive for GTO calculations
- Bonus multipliers must be non-negative
- GTO analysis only applicable to all-in scenarios

### Integration Validation
- GTO results only displayed when GTO analysis is enabled
- GTO calculations run after successful equity simulation
- Error states in either analysis don't prevent the other from displaying

## Relationships

- **SimulationParameters** extends existing simulator configuration
- **IntegratedResults** combines equity and GTO analysis outputs
- **BonusPayouts** reuses existing GTO configuration model
- Integration maintains separation between equity analysis (existing) and GTO analysis (new)</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\002-gto-simulator-integration\data-model.md