---
description: "Use when working with card representation, detection, and format conversion in HoPilot. Covers card formats, naming conventions, and poker-specific patterns."
applyTo: ["**/card*.py", "**/poker_analyzer.py"]
---

# HoPilot Card Patterns

## Card Representation
- Use short treys format exclusively: `"As"` (Ace of spades), `"Kh"` (King of hearts)
- Format specification: `[rank][suit]`
  - Ranks: 2-9, T (10), J, Q, K, A
  - Suits: s (spades), h (hearts), d (diamonds), c (clubs)
- Example: `"Ts"` = Ten of spades, `"Ac"` = Ace of clubs

## Board Positions
- Use semantic position names for consistency:
  - Flop: `"flop_1"`, `"flop_2"`, `"flop_3"`
  - Turn: `"turn"`
  - River: `"river"`
- Always reference board positions by name, not index—improves readability

## Card Format Conversion
- Use `PokerAnalyzer.card_name_to_treys()` for cross-format conversion
- Never manually convert between formats—use the helper method
- Document the input/output format when accepting card data from external sources

## Card Detection Specifics
- Log confidence scores when detecting cards
- Track detection fallback decisions (if template match fails, what's the fallback?)
- Validate card detection before using in analysis
- Include unrecognized cards in logs for debugging template issues

## Hand & Range Representation
- Hands: tuple of two card strings, e.g., `("As", "Kh")`
- Ranges: use consistent notation from `treys` library
- When logging ranges, include notation (e.g., "AK+", "22-88")
