# Quickstart: GTO Analysis Integration in Poker Simulator

**Version**: 1.0
**Last Updated**: 2026-03-03

## Overview

The poker simulator now includes integrated GTO analysis capabilities. Use all your existing simulation features while adding optimal all-in strategy recommendations for tournament scenarios with bonus payouts.

## Prerequisites

- HoPilot poker simulator running
- Basic understanding of poker hands and ranges
- Familiarity with all-in tournament scenarios

## Quick Start (5 minutes)

### 1. Enable GTO Analysis

1. Launch the poker simulator (it opens by default)
2. In the simulation panel, check "Enable GTO Analysis"
3. Configure bonus payouts for your tournament (optional - defaults provided)

### 2. Set Up Your Scenario

1. **Assign hero hand/range**: Click on the hero seat to set specific cards or a range
2. **Add opponents**: Use the simulation panel to add villain seats
3. **Set board cards**: Click board positions to assign community cards
4. **Configure all-in parameters**: Set pot size and bet amount for the all-in decision

### 3. Run Integrated Analysis

1. Click "Run Simulation" as usual - this now runs both equity analysis AND GTO analysis
2. Wait for both analyses to complete (GTO may take 15-30 seconds)
3. View combined results showing both equity and GTO recommendations

## Understanding Results

### Combined Display

**Equity Results** (existing):
- Win probability, equity percentages
- Range analysis if using hand ranges

**GTO Results** (new):
- **GTO Threshold**: Minimum equity needed to profitably go all-in
- **Optimal Range**: Hands that should be played in this scenario
- **Hand Recommendations**: For specific cards - "ALL-IN" or "FOLD"

### Example Output

```
Equity Analysis:
Hero Equity: 35.2%
Win Probability: 38.1%

GTO Analysis (All-In Decision):
GTO Threshold: 0.312
Optimal Hands: 156/1326 (11.8%)
Recommendation for As Kh: ALL-IN (equity: 0.671 > threshold: 0.312)
```

## Common Scenarios

### Tournament Bubble Play

**Setup**:
- Hero: Premium range (AA, KK, QQ, AKs, etc.)
- Opponents: 8 (bubble pressure)
- Pot: $50 (bubble pot)
- Bet: $25 (all-in amount)

**Bonus Payouts**:
```yaml
royal_flush: 500
straight_flush: 100
four_of_a_kind: 50
full_house: 10
flush: 5
```

**Analysis**: GTO will show which hands to shove vs the bubble pressure and bonus payouts.

### Cash Game with Bonuses

**Setup**:
- Hero: Specific hand (e.g., pocket Jacks)
- Opponents: 5
- Pot: $30
- Bet: $15

**Analysis**: See if JJ should be played all-in considering bonus payouts for made hands.

## Configuration Options

### Bonus Payout Settings

Configure multipliers for special hands:
- **Royal Flush**: 500x (very rare, high payout)
- **Straight Flush**: 100x
- **Four of a Kind**: 50x
- **Full House**: 10x
- **Flush/Straight**: 5x-4x
- **Three of a Kind/Two Pair**: 3x-2x
- **One Pair**: 1x

### GTO Parameters

- **Pot Size**: Current pot before all-in bet
- **Bet Amount**: Size of the all-in bet
- **Opponents**: Number of remaining players (automatically counted from simulator setup)

## Advanced Usage

### Range vs Range Analysis

1. Assign ranges to both hero and villains
2. Run analysis to see GTO recommendations across the entire range
3. Useful for studying opening ranges or calling ranges

### Progressive Analysis

1. Start with flop analysis
2. Add turn card
3. Add river card
4. See how GTO recommendations change as board develops

## Troubleshooting

### GTO Analysis Not Showing

**Issue**: GTO results don't appear after simulation
**Solution**: Ensure "Enable GTO Analysis" is checked and bonus payouts are configured

### Slow Performance

**Issue**: GTO calculation takes too long
**Solution**: Reduce number of simulations or use specific hands instead of ranges

### Invalid Parameters

**Issue**: "GTO analysis failed" error
**Solution**: Check that pot size > 0, bet amount > 0, and at least 2 players

## Integration Benefits

- **Seamless Workflow**: No switching between different tools
- **Context Preservation**: GTO analysis uses your exact simulation setup
- **Combined Insights**: See both equity and optimal strategy together
- **Tournament Ready**: Bonus payout support for realistic tournament analysis

## Next Steps

1. **Experiment** with different bonus payout structures
2. **Analyze real hands** from your tournament sessions
3. **Study optimal ranges** for various stack depths
4. **Compare strategies** across different opponent counts

The integrated GTO analysis transforms your poker simulator into a comprehensive tournament analysis tool while maintaining all existing functionality.</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\002-gto-simulator-integration\quickstart.md