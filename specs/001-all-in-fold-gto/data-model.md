# Data Model: All-In-or-Fold GTO Solver with Bonus Payouts

**Version**: 1.0
**Date**: 2026-02-27

## Overview

The GTO solver feature introduces several new data models for representing poker ranges, GTO analysis results, and bonus payout configurations. All models follow Pydantic validation patterns consistent with existing HoPilot configuration management.

## Core Data Models

### Range Definition

```python
class PokerRange(BaseModel):
    """Represents a collection of poker hands with metadata."""
    name: str
    description: Optional[str] = None
    hands: List[str]  # List of shorthand hand notations (e.g., ["AA", "AKs", "QQ"])
    tags: Optional[List[str]] = None  # e.g., ["broadway", "premium", "suited"]
    created: datetime = Field(default_factory=datetime.now)
    modified: datetime = Field(default_factory=datetime.now)

    @validator('hands')
    def validate_hands(cls, v):
        """Ensure all hands are valid poker hand notations."""
        for hand in v:
            if not HandRange.is_valid_shorthand(hand):
                raise ValueError(f"Invalid hand notation: {hand}")
        return v

    def expand_to_cards(self) -> List[List[str]]:
        """Expand range to all possible card combinations."""
        return HandRange.expand_range_to_hands(self.hands)
```

### Bonus Payout Configuration

```python
class BonusPayouts(BaseModel):
    """Configuration for bonus payouts on special hands."""
    royal_flush: float = 500.0
    straight_flush: float = 100.0
    four_of_a_kind: float = 50.0
    full_house: float = 10.0
    flush: float = 5.0
    straight: float = 4.0
    three_of_a_kind: float = 3.0
    two_pair: float = 2.0
    one_pair: float = 1.0

    def get_multiplier(self, hand_category: str) -> float:
        """Get bonus multiplier for a hand category."""
        return getattr(self, hand_category, 0.0)
```

### GTO Analysis Parameters

```python
class GTOParameters(BaseModel):
    """Parameters for GTO analysis calculations."""
    num_opponents: int = Field(ge=1, le=9)  # 1-9 opponents
    pot_size: float = Field(gt=0)  # Current pot size
    bet_amount: float = Field(gt=0)  # All-in bet amount
    num_simulations: int = Field(ge=100, le=10000)  # Monte Carlo samples
    bonus_payouts: BonusPayouts = Field(default_factory=BonusPayouts)
    random_seed: Optional[int] = None  # For reproducible results
```

### GTO Analysis Result

```python
class GTOHandResult(BaseModel):
    """Result for a single hand in GTO analysis."""
    hand: List[str]  # The hole cards
    shorthand: str   # Shorthand notation
    equity: float    # Win probability vs random
    ev: float        # Expected value including bonuses
    hand_category: str  # Best hand category achieved
    bonus_multiplier: float  # Applied bonus multiplier

class GTOResult(BaseModel):
    """Complete GTO analysis result."""
    parameters: GTOParameters
    threshold_equity: float  # Minimum equity for profitable all-in
    optimal_hands: int       # Number of hands that should be played
    total_hands: int         # Total hands analyzed
    optimal_range: List[str] # List of optimal hand shorthands
    hand_results: List[GTOHandResult]
    calculation_time: float  # Time taken in seconds
    valid_simulations: int   # Total simulations run

class NashEquilibriumResult(BaseModel):
    """Result of push-fold Nash equilibrium calculation for range vs range optimization."""
    hero_range: PokerRange      # Original hero range
    villain_range: PokerRange   # Original villain range
    hero_shove_frequencies: Dict[str, float]    # Hand -> shove frequency (0.0-1.0)
    villain_call_frequencies: Dict[str, float]  # Hand -> call frequency (0.0-1.0)
    hero_ev: float             # Expected value for hero in equilibrium
    villain_ev: float          # Expected value for villain in equilibrium (should be 0)
    exploitability: float      # How far from true Nash (0 = perfect Nash)
    convergence_iterations: int # Iterations needed for convergence
    calculation_time: float    # Time taken in seconds
```

## Data Flow

### Range Management Flow

```
YAML File → RangeManager.load_range() → PokerRange (validated) → GUI Display
PokerRange → RangeManager.save_range() → YAML File
```

### GTO Analysis Flow

```
GTOParameters + HeroRange → GTOSolver.analyze_range() → GTOResult → GUI Visualization
```

### Range vs Range Optimization Flow

```
HeroRange + VillainRange + GTOParameters → GTOOptimizer.optimize_push_fold_nash() → NashEquilibriumResult
```

## Storage Schema

### YAML Range File Format

```yaml
# example_range.yaml
name: "Premium Pairs"
description: "High pocket pairs for tournament play"
hands:
  - "AA"
  - "KK"
  - "QQ"
  - "JJ"
  - "TT"
tags:
  - "premium"
  - "pairs"
created: "2026-02-27T10:00:00Z"
modified: "2026-02-27T10:00:00Z"
```

### Bonus Configuration File Format

```yaml
# gto_defaults.yaml
bonus_payouts:
  royal_flush: 500
  straight_flush: 100
  four_of_a_kind: 50
  full_house: 10
  flush: 5
  straight: 4
  three_of_a_kind: 3
  two_pair: 2
  one_pair: 1
```

## Validation Rules

### Range Validation
- All hand notations must be valid poker shorthand
- No duplicate hands in a single range
- Range names must be unique within storage location
- Maximum 1000 hands per range (performance constraint)

### GTO Parameter Validation
- Opponents: 1-9 (table size constraints)
- Pot size: > 0
- Bet amount: > 0 and ≤ pot size * 3 (reasonability check)
- Simulations: 100-10,000 (balance between accuracy and performance)

### Bonus Validation
- All multipliers must be ≥ 0
- Royal flush multiplier should be highest (business rule)
- Multipliers can be 0 (disable bonus for that category)

## Relationships

- `PokerRange` contains multiple hand specifications
- `GTOParameters` references `BonusPayouts` configuration
- `GTOResult` contains multiple `GTOHandResult` instances
- `GTOOptimizer` works with two `PokerRange` instances to produce `NashEquilibriumResult`
- `NashEquilibriumResult` contains optimized shove/call frequencies for both players

## Migration Notes

- Existing hand range data can be imported into new `PokerRange` format
- Bonus payouts default to common tournament values but are fully configurable
- GTO results are computed on-demand and not persisted (can be large)