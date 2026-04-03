# Feature Specification: AOF Phase 1 Foundation

**Feature Branch**: `001-aof-phase1-foundation`  
**Created**: April 2, 2026  
**Status**: Draft  
**Input**: User description: "Phase 1, Stage 1.1: Foundation Domain Models - Establish immutable, validated core domain types (Card, Hand, HandRange, Board, EquityResult, Bet) and CardAdapter for PokerKit solver integration, enabling backend analysis engine development"

---

## Overview

Phase 1, Stage 1.1 establishes the architectural foundation for the AOF GTO Browser II application by creating immutable, validated core domain models: Card, Hand, HandRange, Board, EquityResult, and Bet. These foundational types enable backend analysis engine development with strong type safety and runtime validation. The CardAdapter isolates PokerKit solver integration to prevent coupling business logic to library-specific code.

**Key Insight**: Starting with domain models (before DTOs, database, or configuration) enables focused development of the core business logic with minimal dependencies.

---

## Clarifications

### Session 2026-04-03

- Q: What type of test coverage metric should Phase 1 achieve? → A: Line coverage (80% of source code lines executed by tests, measured with tools like `coverage.py`)

---

## User Scenarios & Testing

### User Story 1 - Backend Developer Sets Up Domain Models (Priority: P1)

A backend developer needs immutable, validated domain types for poker positions that can be used throughout the analysis engine without worrying about invalid states. The developer needs types that handle card parsing, hand notation, range expansion, and board representation.

**Why this priority**: Without domain models, the backend cannot be built reliably. These foundational types prevent entire classes of bugs (invalid hands, duplicate cards, malformed ranges).

**Independent Test**: Can be tested by creating instances, parsing from various formats (shorthand, strings), validating constraints, and verifying immutability by attempting mutations.

**Acceptance Scenarios**:

1. **Given** a developer needs to represent cards, **When** they create Card objects using `Card(rank=Rank.ACE, suit=Suit.SPADES)` and `Card.from_string("As")`, **Then** they get immutable Card objects with correct rank/suit enums and can convert to/from strings
2. **Given** a developer parses hand notation, **When** they call `Hand.from_strings("As", "Ks")`, **Then** they get a Hand with `to_shorthand()` returning "AKs", `num_combos()` returning 4, `is_suited()` returning True
3. **Given** a developer needs to represent a range, **When** they parse `HandRange.from_shorthand("AKs+,QQ+,A5s-A2s")`, **Then** the range contains 25+ hands, `size()` returns hand count, `contains(Hand.from_strings("As","Ks"))` returns True, and the range's shorthand round-trips back to input
4. **Given** a developer defines a flop, **When** they create `Board.from_strings(["As", "Kh", "2d"])`, **Then** the Board has 3 cards, `is_flop()` returns True, `get_street()` returns "flop", `get_flop()` returns tuple of 3 cards
5. **Given** a developer attempts to create a Hand with duplicate cards, **When** they call `Hand(Card.from_string("As"), Card.from_string("As"))`, **Then** it raises `ValueError` with message containing "duplicate", preventing invalid Hand objects from existing

---



### User Story 2 - Developer Integrates PokerKit Solver Library (Priority: P2)

A developer needs to evaluate hands using PokerKit solver but wants to keep PokerKit-specific code isolated from the domain layer. The CardAdapter converts between domain Card objects and PokerKit string formats without coupling business logic to the solver library.

**Why this priority**: The adapter pattern isolates PokerKit-specific code from the domain layer, preventing library coupling and enabling future solver extensibility.

**Independent Test**: Can be tested by converting Card objects to PokerKit format and back, verifying round-trip accuracy and O(1) performance.

**Acceptance Scenarios**:

1. **Given** domain Card object with `rank=Rank.ACE, suit=Suit.SPADES`, **When** converted to PokerKit format using `CardAdapter.to_pokerkit()`, **Then** result is string "As", and `CardAdapter.from_pokerkit("As")` round-trips back to original Card perfectly
2. **Given** domain Card `Card(Rank.KING, Suit.HEARTS)`, **When** converted to PokerKit format, **Then** result is string "Kh", and decoding back via `CardAdapter.from_pokerkit("Kh")` gives identical Card
3. **Given** all 52 cards in standard deck, **When** each is converted to PokerKit format and back, **Then** every round-trip preserves the original Card with zero data loss

---

### Edge Cases

**E-001: Invalid HandRange notation** → What happens when a HandRange is parsed from invalid shorthand notation (e.g., "XX+")?
  - System MUST raise a RangeError with descriptive message, not silently ignore invalid parts

**E-002: Duplicate hand cards** → How does the system handle attempting to create a Hand with the same card twice (e.g., "As" and "As")?
  - System MUST raise a ValueError immediately, preventing invalid Hand objects from existing

**E-003: Board/Hand equality comparison** → How are Board and Hand objects compared for equality?
  - Both MUST support equality comparison (==) independent of construction order (e.g., Hand("As", "Ks") == Hand("Ks", "As") if hands are normalized)

**E-004: Floating-point precision** → What happens when float stack/pot values have floating-point precision errors (e.g., 99.99999999)?
  - Bet values MUST round to nearest 0.01 BB (0.01 cents) for consistent storage and comparison using `round(amount_bb, 2)`

**E-005: Whitespace and case sensitivity** → How should parsing handle whitespace and case sensitivity?
  - `Card.from_string()` MUST accept "As", "AS", "as", " As ", "Ace of Spades" with case-insensitivity and whitespace trimming
  - `Hand.from_shorthand()` MUST accept "AKs", "akS", " AKs " with case-insensitivity

---

## Requirements

### Functional Requirements

**FR-001**: System MUST provide immutable Card domain model with:
- **Fields**:
  - `rank: Rank` (Enum: TWO=2, THREE=3, ..., KING=13, ACE=14)
  - `suit: Suit` (Enum: SPADES="s", HEARTS="h", DIAMONDS="d", CLUBS="c")
- **Enums with properties**:
  - `Rank.char` returns single-char representation ("A", "K", "Q", "J", "T", "2"-"9")
  - `Suit.full_name` returns full name ("Spades", "Hearts", "Diamonds", "Clubs")
- **Methods**:
  - `Card.from_string(str)` parses "As", "Kh", "2d", "Tc" (shorthand) or "Ace of Spades", "King of Hearts" (long form), case-insensitive
  - `to_string()` returns normalized shorthand like "As", "Kh"
  - `__str__()` returns shorthand for string conversion
  - `__repr__()` returns full form like "Ace of Spades"
  - `is_ace()` returns bool
- **Immutability**: frozen dataclass, hashable (works in sets/dicts)
- **Validation**: Rank must be 2-14, Suit must be valid enum value

**FR-002**: System MUST provide immutable Hand domain model with:
- **Fields**:
  - `card1: Card` (first hole card)
  - `card2: Card` (second hole card, must differ from card1)
- **Validation in `__post_init__`**:
  - Raises `ValueError` if `card1 == card2` (no duplicate cards)
- **Methods**:
  - `Hand.from_strings(card1_str, card2_str)` parses two card strings, returns Hand or None
  - `Hand.from_tuple((str, str))` parses from tuple
  - `to_strings()` returns `tuple[str, str]` like `("As", "Kd")` for DTO transport
  - `to_shorthand()` returns standardized notation:
    - Pairs: "AA", "KK", "22" (rank×2)
    - Suited: "AKs", "A2s", "QJo" (higher rank + lower rank + 's')
    - Offsuit: "AKo", "K9o" (higher rank + lower rank + 'o')
  - `to_cards()` returns `List[Card]`
  - `__str__()` calls `to_shorthand()`
  - `is_pair()` returns bool (both cards same rank)
  - `is_suited()` returns bool (both cards same suit)
  - `is_offsuit()` returns bool (different suits)
  - `num_combos()` returns int: 6 for pairs, 4 for suited, 12 for offsuit
  - `is_broadway()` returns bool (both ranks ≥ 10)
  - `is_connected()` returns bool (ranks differ by 1)
  - `is_gapped()` returns bool (ranks differ by 2 or 3)
- **Immutability**: frozen dataclass, hashable
- **Note**: Hand("As", "Ks") and Hand("Ks", "As") may have different card1/card2 but represent same shorthand "AKs"

**FR-003**: System MUST provide immutable HandRange domain model with:
- **Fields**:
  - `hands: List[Hand]` (1-1326 possible hands, no duplicates)
  - `notation: str` (original shorthand for round-trip, e.g., "AKs+,QQ+,A5s-A2s")
- **Parsing algorithm** with three phases:
  - **Phase 1 - Parse**: Decompose notation into components by splitting on comma/semicolon
  - **Phase 2 - Expand**: For each component, detect type (single/plus/dash) and expand:
    - Single hand "AKs": Generate 4 combos (one per suit match)
    - Single hand "AKo": Generate 12 combos (all cross-suit combinations)
    - Single hand "AA": Generate 6 combos (unordered suit pairs, C(4,2)=6)
    - Plus notation "22+": Iterate from base (22) to Ace, expand each as single hand → 13×6=78 combos
    - Plus notation "AKs+": Iterate from King down to Two, expand each as single hand
    - Dash range "A5s-A2s": Extract start/end ranks, iterate through them, expand each
    - Dash range "22-99": Iterate through pairs from start to end
  - **Phase 3 - Deduplicate**: Remove duplicate hands, keep order
- **Methods**:
  - `HandRange.from_shorthand(notation: str)` parses complex notation, returns HandRange or raises RangeError
  - `to_shorthand()` returns original notation for serialization
  - `to_strings()` returns `List[tuple[str, str]]` of card pairs for DTO transport
  - `size()` returns number of unique hand types (1-169)
  - `num_combos()` returns total combo count (1-1326)
  - `contains(hand: Hand)` returns bool for membership testing
  - Static methods:
    - `union(range1, range2)` returns new HandRange with combined hands (deduplicated)
    - `intersection(range1, range2)` returns new HandRange with common hands
- **Validation**:
  - Raises `RangeError` for invalid notation (unrecognized ranks, malformed syntax, "XX+", etc.)
  - Raises `ValueError` for duplicate hands in final list
- **Immutability**: frozen dataclass
- **Performance**: Parsing should complete in < 10ms for typical ranges like "AKs+,QQ+,A5s-A2s"

**FR-004**: System MUST provide immutable Board domain model with:
- **Fields**:
  - `cards: List[Card]` (empty list to [0:5] community cards in street order)
- **Validation in `__post_init__`**:
  - Raises `ValueError` if len(cards) > 5
  - Raises `ValueError` if duplicate cards
- **Methods**:
  - `Board.from_strings(card_strings: List[str])` parses list of card strings, returns Board or None
  - `to_strings()` returns `List[str]` of card strings
  - `__str__()` returns space-separated card string like "As Kh 2d Ts"
  - `num_cards()` returns int (0-5)
  - `is_empty()` returns bool (0 cards, preflop)
  - `is_flop()` returns bool (exactly 3 cards)
  - `is_turn()` returns bool (exactly 4 cards)
  - `is_river()` returns bool (exactly 5 cards)
  - `is_complete()` returns bool (5 cards)
  - `get_street()` returns str: "preflop", "flop", "turn", "river", or "unknown"
  - `get_flop()` returns `Optional[tuple[Card, Card, Card]]` (cards 0-2 if available)
  - `get_turn()` returns `Optional[Card]` (card 3 if available)
  - `get_river()` returns `Optional[Card]` (card 4 if available)
  - `contains_card(card: Card)` returns bool
  - `all_board_cards()` returns `List[Card]` copy
- **Immutability**: frozen dataclass
- **Note**: AoF games typically use Board(cards=[]) (empty) since analysis is pre-flop only

**FR-005**: System MUST provide immutable EquityResult domain model with:
- **Fields**:
  - `hand: Hand` - the hand being evaluated
  - `equity: float` - 0.0-1.0, weighted equity vs opponent range
  - `win_prob: float` - 0.0-1.0, probability of winning (excludes draws)
  - `draw_prob: float` - 0.0-1.0, probability of drawing (tie)
  - `loss_prob: float` - 0.0-1.0, probability of losing (excludes draws)
  - `num_simulations: int` - ≥ 1000, Monte Carlo sample count
- **Validation in `__post_init__`**:
  - Each probability field must be 0.0-1.0
  - `win_prob + draw_prob + loss_prob` must equal 1.0 ± 0.01 tolerance (to handle floating-point rounding)
  - Raises `ValueError` with descriptive message for violations
  - `num_simulations` must be ≥ 1000
- **Properties**:
  - `win_percent` returns formatted string like "52.34%"
  - `draw_percent` returns formatted string like "10.50%"
  - `loss_percent` returns formatted string like "36.66%"
  - `equity_percent` returns formatted string like "52.34%"
- **Factory methods**:
  - `from_monte_carlo(hand, wins: int, draws: int, losses: int, total_simulations: int)` creates EquityResult from raw counts
- **Immutability**: frozen dataclass

**FR-006**: System MUST provide immutable Bet value type with:
- **Fields**:
  - `amount_bb: float` - amount in big blinds, must be > 0 and finite, rounded to nearest 0.01 BB
- **Validation in `__post_init__`**:
  - Round amount_bb to nearest 0.01 BB using `round(amount_bb, 2)` for floating-point precision handling
  - Raises `ValueError` if `amount_bb <= 0` (after rounding)
  - Raises `ValueError` if amount is NaN or Infinity
- **Methods**:
  - `is_zero()` returns bool (always False since amount > 0, used for early exit logic)
  - `is_all_in(stack_bb: float)` returns bool if `amount_bb >= stack_bb`
  - `display_value()` formats as string for UI (e.g., "2.5 BB" or "0.50 BB", rounded to 2 decimals)
- **Immutability**: frozen dataclass
- **Semantics**: All monetary values in system use big blinds (stack, pot, bet amounts)

**FR-007**: System MUST provide CardAdapter for PokerKit solver integration with:
- **Purpose**: Convert between domain Card objects and PokerKit string formats without coupling business logic to PokerKit library
- **PokerKit string format conversion**:
  - `to_pokerkit(card: Card) -> str` returns "As", "Kh", "2d", "Tc" (rank char + suit char)
  - `from_pokerkit(s: str) -> Card` parses those strings back to domain Card (delegates to Card.from_string())
  - `to_pokerkit_hand(hand: Hand) -> tuple[str, str]` returns (card1_str, card2_str) for PokerKit hand format
  - `from_pokerkit_hand(c1: str, c2: str) -> Hand` creates domain Hand from PokerKit card strings
- **Performance**: All conversions must be O(1) with < 1 microsecond per conversion (mostly direct passthrough to Card.to_string())
- **Testing**: Round-trip tests for all 52 cards (card → PokerKit string → card must be identical)
- **Future extensibility**: Designed so adding other solvers (Treys, PyPokerEngine) in Phase 2+ only requires adding new adapter methods without changing domain layer



### Key Entities

**Domain Models** (immutable, validated, core business concepts):

- **Card**: Single playing card with:
  - `rank: Rank` enum (2-14 where A=14)
  - `suit: Suit` enum (SPADES, HEARTS, DIAMONDS, CLUBS with values "s", "h", "d", "c")
  - String parsing: `Card.from_string("As")` handles "As", "AS", "Ace of Spades", "A of Spades" variants
  - Hashable: works in sets, dicts, for caching and equality checks
  - Example: `Card(rank=Rank.ACE, suit=Suit.SPADES)` or `Card.from_string("As")`

- **Hand**: Two-card poker hand with:
  - `card1: Card` and `card2: Card` (different cards, validated at construction)
  - Shorthand computation: Hand→"AKs", "22", "QJo" automatically
  - Combo count: 6 for pairs, 4 for suited, 12 for offsuit (critical for equity calculations)
  - String parsing: `Hand.from_strings("As", "Kd")` → Hand with `to_shorthand()=="AKo"`
  - Example: `Hand(As, Ks)` with `num_combos()=4`, `is_suited()=True`, `to_shorthand()="AKs"`

- **HandRange**: Distribution of hands (1-1326 combos) with:
  - `hands: List[Hand]` (unique, no duplicates)
  - `notation: str` (original shorthand for serialization like "AKs+,QQ+,A5s-A2s")
  - Complex shorthand parsing: "22+" expands to all pairs (13×6=78 combos), "A5s-A2s" expands to 4 hands (4×4=16 combos)
  - Set operations: `union()`, `intersection()` for range algebra
  - Example: `HandRange.from_shorthand("AKs+,22+")` → 4+13=17 hand types, 16+78=94 combos

- **Board**: 0-5 community cards in street order with:
  - `cards: List[Card]` (0-5 cards, no duplicates)
  - Street detection: `is_empty()`, `is_flop()`, `is_turn()`, `is_river()`
  - Card accessors: `get_flop()` returns tuple(Card, Card, Card), `get_turn()` returns Card or None
  - Example: `Board.from_strings(["As", "Kh", "2d"])` → `is_flop()=True`, `get_street()="flop"`

- **EquityResult**: Equity computation output with:
  - `hand: Hand` (hand being evaluated)
  - `equity: float` (0.0-1.0, weighted equity vs range)
  - `win_prob, draw_prob, loss_prob: float` (sum to 1.0±0.01)
  - `num_simulations: int` (≥1000 Monte Carlo samples)
  - Properties: `win_percent`, `draw_percent`, `equity_percent` for display formatting
  - Example: EquityResult(hand=AKs, equity=0.625, win_prob=0.625, draw_prob=0.0, loss_prob=0.375, num_simulations=100000)

- **Bet**: Monetary amount in big blinds with:
  - `amount_bb: float` (> 0, finite, not NaN)
  - Methods: `is_all_in(stack_bb)`, `display_value()` for UI formatting
  - Example: `Bet(25.0)` representing 25 big blinds

---

## Success Criteria

### Measurable Outcomes

**SC-001**: All immutable domain models (Card, Hand, HandRange, Board, EquityResult, Bet) can be created, parsed from strings, serialized back to strings, and cannot be mutated after creation (attempt to modify raises AttributeError)

**SC-002**: HandRange parser correctly expands complex shorthand notation like "AKs+, QQ+, A5s-A2s" and contains() method correctly identifies membership for all 1326 possible hands in < 10ms

**SC-003**: EquityResult objects correctly validate that win_prob + draw_prob + loss_prob sums to 1.0 ± 0.01, raising ValueError with descriptive message for violations

**SC-004**: Bet value type validates that amount_bb > 0 and is finite (not NaN/Infinity), raising ValueError for invalid inputs

**SC-005**: CardAdapter converts domain Card objects to PokerKit string format ("As", "Kh", etc.) and back with 100% accuracy for all 52 cards in < 1μs per conversion (round-trip: Card → string → Card equals original)

**SC-006**: All domain model classes are hashable and work correctly in sets and as dictionary keys (e.g., {Card.from_string("As"): ...} or hand_set.add(hand))

**SC-007**: Test coverage for domain models (Card, Hand, HandRange, Board, EquityResult, Bet, CardAdapter) reaches 80% line coverage (measured with `coverage.py` or equivalent) with unit tests for parsing, validation, edge cases, immutability, and round-trip serialization

**SC-008**: All public APIs have docstrings explaining purpose, parameters, return values, and example usage; README documents domain model architecture and design choices

**SC-009**: Domain models integrate with CardAdapter without type errors: CardAdapter methods accept Card objects and return strings; parsing methods handle all valid poker notation formats

**SC-010**: Development team reviews and approves domain model API contracts; no breaking changes expected for Phase 1.2+ development

---

## Code Examples & Usage Patterns

### Example 1: Building a Domain Model

```python
# Card creation (type-safe enum-based)
ace_spades = Card(rank=Rank.ACE, suit=Suit.SPADES)
assert str(ace_spades) == "As"

# Or parse from string (flexible)
king_hearts = Card.from_string("Kh")
assert king_hearts.rank == Rank.KING
assert king_hearts.suit == Suit.HEARTS
```

### Example 2: Hand Shorthand Notation

```python
# Create hand from individual cards
hand = Hand(card1=Card.from_string("As"), card2=Card.from_string("Ks"))
assert hand.to_shorthand() == "AKs"
assert hand.is_suited() == True
assert hand.num_combos() == 4  # All 4 suits

# Another approach
hand2 = Hand.from_strings("As", "Kd")
assert hand2.to_shorthand() == "AKo"  # Offsuit
assert hand2.num_combos() == 12  # All cross-suit combos

# Pair
hand3 = Hand.from_strings("Ac", "Ah")  
assert hand3.to_shorthand() == "AA"
assert hand3.is_pair() == True
assert hand3.num_combos() == 6  # Choose 2 from 4 suits
```

### Example 3: HandRange Parsing with Complex Notation

```python
# Simple range
range1 = HandRange.from_shorthand("AKs")  # 1 hand, 4 combos
assert range1.size() == 1
assert range1.num_combos() == 4

# Plus notation (expanding upward)
range2 = HandRange.from_shorthand("22+")  # All pairs: 22-AA
assert range2.size() == 13     # 13 pairs
assert range2.num_combos() == 78  # 13 × 6

# Dash range (descending)
range3 = HandRange.from_shorthand("A5s-A2s")  # A5s, A4s, A3s, A2s
assert range3.size() == 4
assert range3.num_combos() == 16  # 4 hands × 4 combos each

# Union (multiple components)
range4 = HandRange.from_shorthand("AKs+,QQ+,A5s-A2s")
# AKs+ (2 hands): AKs(4) + AQs(4) = 8 combos
# QQ+ (2 pairs): QQ(6) + KK(6) + AA(6) = 18 combos
# A5s-A2s (4 hands): 16 combos
# Total: 8 + 18 + 16 = 42 combos across 8 hands
assert range4.size() == 8
assert range4.num_combos() == 42
assert range4.contains(Hand.from_strings("As", "Ks")) == True
assert range4.contains(Hand.from_strings("As", "2s")) == True
assert range4.contains(Hand.from_strings("Ks", "Kh")) == True  # KK
assert range4.contains(Hand.from_strings("Js", "Jh")) == False  # JJ not in range
```

### Example 4: Board Representation for Different Streets

```python
# Preflop (empty board)
board1 = Board(cards=[])
assert board1.is_empty() == True
assert board1.num_cards() == 0
assert board1.get_street() == "preflop"

# Flop
board2 = Board.from_strings(["As", "Kh", "2d"])
assert board2.is_flop() == True
assert board2.num_cards() == 3
assert board2.get_flop() == (Card("As"), Card("Kh"), Card("2d"))
assert board2.get_turn() == None  # Turn not available yet

# Turn
board3 = Board.from_strings(["As", "Kh", "2d", "Ts"])
assert board3.is_turn() == True
assert board3.get_turn() == Card.from_string("Ts")
assert board3.get_street() == "turn"

# River (complete)
board4 = Board.from_strings(["As", "Kh", "2d", "Ts", "9c"])
assert board4.is_river() == True
assert board4.is_complete() == True
assert board4.get_river() == Card.from_string("9c")
```

### Example 5: CardAdapter for PokerKit Solver

```python
# Converting between domain and PokerKit formats
card = Card(rank=Rank.ACE, suit=Suit.SPADES)

# Convert to PokerKit string format
pokerkit_str = CardAdapter.to_pokerkit(card)  # "As"
assert pokerkit_str == "As"

# Convert back to domain Card
back_to_domain = CardAdapter.from_pokerkit(pokerkit_str)  # Card(A, S)
assert back_to_domain.rank == Rank.ACE
assert back_to_domain.suit == Suit.SPADES
assert back_to_domain == card  # Round-trip preserves equality

# For Hand objects
hand = Hand.from_strings("As", "Kd")
pokerkit_hand = CardAdapter.to_pokerkit_hand(hand)  # ("As", "Kd")
assert pokerkit_hand == ("As", "Kd")

back_to_hand = CardAdapter.from_pokerkit_hand("As", "Kd")
assert back_to_hand == hand  # Round-trip
```

## Dependency & Data Flow

6. **CardAdapter maintains O(1) conversion performance**: All conversions (Card ↔ PokerKit string) are direct passthrough/lookup operations with negligible overhead.

7. **Immutability via frozen dataclasses**: All domain models use @dataclass(frozen=True) to guarantee immutability at the language level and enable usage as dictionary keys and in sets.

8. **PokerKit is the Phase 1 solver**: CardAdapter supports PokerKit string format only in Phase 1. Additional solvers (Treys, PyPokerEngine) can be added in Phase 2+ by extending CardAdapter without breaking domain models.

---

## Open Questions

None at this time. Phase 1 scope is well-bounded and requires no external clarifications.

---

## Related Documents

- [Implementation Strategy](../00_IMPLEMENTATION_STRATEGY.md) - Overall 4-phase plan; this spec covers Phase 1, Stage 1.1 (Domain Models)
- [Domain Models Index](../01_DOMAIN_MODELS/00_INDEX.md) - Overview of all domain model documentation
- [Card Domain Model](../01_DOMAIN_MODELS/01_DOMAIN_Card.md) - Detailed Card implementation guide
- [Hand Domain Model](../01_DOMAIN_MODELS/02_DOMAIN_Hand.md) - Detailed Hand implementation guide
- [HandRange Domain Model](../01_DOMAIN_MODELS/03_DOMAIN_HandRange.md) - Detailed HandRange implementation guide
- [Board Domain Model](../01_DOMAIN_MODELS/04_DOMAIN_Board.md) - Detailed Board implementation guide
- [EquityResult Domain Model](../01_DOMAIN_MODELS/05_DOMAIN_EquityResult.md) - Detailed EquityResult implementation guide
- [Bet Domain Model](../01_DOMAIN_MODELS/06_DOMAIN_Bet.md) - Detailed Bet implementation guide
