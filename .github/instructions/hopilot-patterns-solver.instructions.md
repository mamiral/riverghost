---
description: "Use when implementing poker analysis features, Monte Carlo simulations, hand evaluation, equity calculations, or working with the solver engine."
applyTo: "**/poker_analyzer.py", "**/hand*.py"
---

# HoPilot Solver Patterns

## Imports
- Import `random` at module level: `import random`
- Don't import inside loops—it's inefficient
- Use `PokerkitDeck.STANDARD` to access full deck
- Use PokerKit library (`StandardHighHand`) for robust hand evaluation
- Always validate hole cards (must be exactly 2) before evaluation
- Board cards can vary (0-5), validate count before processing
- Hand strength returns integer (lower is stronger; higher is weaker)

## Card Conversion
- Implement `card_name_to_pokerkit()` converter for format translation
- Handle invalid card strings gracefully—return None instead of raising
- Log warnings when cards are invalid; filter Nones before processing
- Maintain single source of truth for card format conversion

## Monte Carlo Simulations
- Core method: `_run_monte_carlo_simulation()` accepts:
  - Hero hole cards (PokerKit format)
  - Board cards (PokerKit format, 0-5 cards)
  - Number of simulations
  - Optional: fixed opponent hands OR random opponent count
- Return dictionary always includes:
  ```python
  {
    'win_probability': float,      # Wins / valid_simulations
    'tie_probability': float,      # Ties / valid_simulations
    'loss_probability': float,     # 1 - win - tie
    'valid_simulations': int,      # Count of successful simulations (crucial!)
    'wins': int,                   # Raw count
    'ties': int                    # Raw count
  }
  ```
- See [PokerAnalyzer._run_monte_carlo_simulation](python/hopilot/poker_analyzer.py#L55) for implementation reference

## Known Cards & Deck Management
- Track known cards (hero, board, fixed opponents) to avoid duplicates in deck
- Generate fresh deck for each simulation iteration
- Remove known cards from deck before shuffling
- Validate sufficient deck cards remain before dealing

## Error Handling
- Log warnings for failed simulation iterations (don't abort entire run)
- Return None for invalid inputs (invalid cards, zero simulations, etc.)
- Log error with context: which operation failed and why
- Continue simulations if single iterations fail—report valid_simulations count

## Convergence Tracking
- Monitor convergence metrics: standard deviation of probabilities across batch runs
- Document convergence thresholds in configuration
- Track valid_simulations count to assess sample adequacy

## Solver Output

The solver writes raw `GameState` records via `GameStatePersistence` — one record per simulation iteration. It never computes aggregated metrics. See the **Architecture Constraints** section in `copilot-instructions.md` for the full constraint and rationale.

Schema reference: [GameState](python/hopilot/models/game_state.py), [Player](python/hopilot/models/player.py) (includes `hand_rank`, `hand_class`, `final_strength`).
