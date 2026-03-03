# Quickstart: All-In-or-Fold GTO Solver

**Version**: 1.0
**Last Updated**: 2026-02-27

## Overview

The All-In-or-Fold GTO Solver helps you find optimal strategies for simplified poker games where players can only fold or go all-in preflop. This guide gets you started with basic usage and common scenarios.

## Prerequisites

- HoPilot installed and running
- Basic understanding of poker equity and expected value (EV)
- Familiarity with poker hand ranges

## Quick Start (5 minutes)

### 1. Access the GTO Solver

1. Launch HoPilot
2. Navigate to the new "GTO Solver" panel in the main interface
3. The panel will open with default tournament parameters

### 2. Run Your First Analysis

1. **Set Game Parameters:**
   - Opponents: 8 (9-handed table)
   - Pot Size: $20
   - Bet Amount: $10
   - Keep default bonus payouts

2. **Click "Calculate GTO"**
   - Wait ~15-30 seconds for analysis
   - View results in the strategy display

3. **Interpret Results:**
   - **Threshold Equity**: Minimum win probability needed to profitably all-in
   - **Optimal Range**: Hands that should be played
   - **EV Breakdown**: Expected value for each hand type

## Common Scenarios

### Tournament Bubble Play

**Situation**: You're on the tournament bubble with 8 opponents left.

```yaml
# Game Parameters
opponents: 8
pot_size: 50
bet_amount: 25
bonus_payouts:
  royal_flush: 500
  straight_flush: 100
  # ... other bonuses
```

**Key Insight**: With bonus payouts, suited connectors become more valuable due to flush/straight potential.

### Cash Game with Bonus

**Situation**: Online cash game with bonus payouts for made hands.

```yaml
# Game Parameters
opponents: 5
pot_size: 30
bet_amount: 15
bonus_payouts:
  full_house: 10
  flush: 5
  straight: 4
```

**Key Insight**: Pocket pairs become more valuable due to full house potential.

## Range Management

### Creating a Range

1. Click "Range Editor" in the GTO panel
2. Enter range name: "My Premium Hands"
3. Add hands:
   - AA, KK, QQ, JJ, TT
   - AKs, AQs, AJs
   - AKo, AQO
4. Save as YAML file

### Loading a Range

1. Click "Load Range" in the GTO panel
2. Select your saved YAML file
3. Range appears in the analysis interface

### Example Range File

```yaml
name: "Tournament Steal"
description: "Hands to open-raise from late position"
hands:
  - "AA"
  - "KK"
  - "QQ"
  - "AKs"
  - "AQs"
  - "AJs"
  - "KQs"
  - "AKo"
tags:
  - "steal"
  - "late-position"
```

## Understanding Results

### Equity Threshold
- **Above threshold**: All-in profitable
- **Below threshold**: Fold profitable
- **Example**: 0.35 threshold means you need >35% equity to all-in

### EV Calculations
- **Positive EV**: Profitable to all-in
- **Negative EV**: Better to fold
- **Bonus Impact**: Multipliers increase EV for made hands

### Range Optimization
- Compare your range vs opponent's range
- Find optimal frequencies for each hand
- Adjust for stack sizes and positions

## Advanced Usage

### Custom Bonus Payouts

```yaml
bonus_payouts:
  royal_flush: 1000    # Very high bonus
  straight_flush: 200
  four_of_a_kind: 100
  full_house: 20
  flush: 10
  straight: 8
  three_of_a_kind: 6
  two_pair: 4
  one_pair: 2
```

### Range vs Range Analysis

1. Load your hero range
2. Load opponent's villain range
3. Run optimization
4. See adjusted strategies for both players

## Troubleshooting

### Common Issues

**"Calculation taking too long"**
- Reduce simulation count (try 1000 instead of 5000)
- Close other applications
- Analysis is CPU-intensive

**"Invalid range file"**
- Check YAML syntax
- Verify hand notations (AA, AKs, etc.)
- Ensure no duplicate hands

**"No profitable hands found"**
- Check bonus payouts are reasonable
- Verify pot size vs bet amount
- Consider if game parameters make sense

### Performance Tips

- Use 1000-2000 simulations for quick analysis
- Save frequently-used ranges for reuse
- Close unnecessary GUI panels during calculations

## Next Steps

1. **Experiment** with different bonus payout structures
2. **Create custom ranges** for specific game types
3. **Compare strategies** across different stack sizes
4. **Analyze real hands** from your sessions

## Support

- Check the main HoPilot documentation for detailed API reference
- Review the data model documentation for advanced configuration
- Use the built-in help in the GTO solver panel

---

*This quickstart covers the most common use cases. For advanced features like range optimization and custom analysis, refer to the full documentation.*