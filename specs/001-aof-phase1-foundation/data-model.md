# Data Model: AOF Phase 1.1 Domain Models

**Purpose**: Detailed entity specifications and design decisions for Phase 1.1 domain models.  
**Reference**: [Feature Specification](spec.md) | [Domain Documentation](../01_DOMAIN_MODELS/00_INDEX.md)

## Entity: Card

**File**: `python/aof_gto_browser_ii/shared/domain/card.py`

### Purpose
Immutable representation of a single playing card with rank and suit. Supports parsing from multiple formats and conversion for solver libraries.

### Structure
```python
from dataclasses import dataclass
from enum import IntEnum, Enum

class Rank(IntEnum):
    """Card rank as integer quasi-enum (2-14, where A=14)"""
    TWO = 2
    THREE = 3
    # ... up to ...
    KING = 13
    ACE = 14

class Suit(str, Enum):
    """Card suit with string values for database/API stability"""
    SPADES = "s"
    HEARTS = "h"
    DIAMONDS = "d"
    CLUBS = "c"

@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit
    
    # Fields:
    # - rank: Rank (2-14)
    # - suit: Suit (s/h/d/c)
```

### Key Methods
- `Card.from_string(s: str) -> Card` - Parse "As", "Kh", "2d", "Tc", case-insensitive
- `Card.from_string()` also accepts long form "Ace of Spades", "King of Hearts"
- `to_string() -> str` - Normalized shorthand like "As", "Kh"
- `__str__()` - Shorthand representation
- `__repr__()` - Full form like "Ace of Spades"
- `__hash__()` - Implicit via frozen dataclass (hashable for sets/dicts)
- `__eq__()` - Equality via dataclass
- `is_ace() -> bool`
- Immutability: frozen dataclass prevents any mutation

### Validation
- Rank must be 2-14 (enforced by IntEnum)
- Suit must be valid enum value (enforced by Enum)
- No custom `__post_init__` validation needed (enum + int constraints sufficient)

### Example Usage
```python
# Enum-based construction
card1 = Card(rank=Rank.ACE, suit=Suit.SPADES)

# String parsing
card2 = Card.from_string("As")
card3 = Card.from_string("KING OF HEARTS")  # case-insensitive

# String conversion
assert str(card1) == "As"
assert card1 == card2

# Hashable
card_set = {card1, card2, card3}
card_dict = {card1: "ace spades"}
```

---

## Entity: Hand

**File**: `python/aof_gto_browser_ii/shared/domain/hand.py`

### Purpose
Immutable representation of a 2-card poker hand. Computes shorthand notation (AKs, 22, QJo) and combos automatically. Validates that both cards are different.

### Structure
```python
@dataclass(frozen=True)
class Hand:
    card1: Card
    card2: Card
    
    def __post_init__(self):
        if self.card1 == self.card2:
            raise ValueError("Hand cannot have duplicate cards")
```

### Key Methods
- `Hand.from_strings(card1_str, card2_str) -> Hand` - Parse two card strings
- `Hand.from_tuple((card1_str, card2_str)) -> Hand` - Parse from tuple
- `to_strings() -> tuple[str, str]` - For DTO transport  
- `to_shorthand() -> str` - Returns "AKs", "22", "QJo", etc.
- `to_cards() -> List[Card]`
- `__str__()` - Calls `to_shorthand()`
- `is_pair() -> bool` - Both cards same rank
- `is_suited() -> bool` - Both cards same suit
- `is_offsuit() -> bool` - Different suits
- `num_combos() -> int` - 6 for pairs, 4 for suited, 12 for offsuit
- `is_broadway() -> bool` - Both ranks ≥ 10
- `is_connected() -> bool` - Ranks differ by 1
- `is_gapped() -> bool` - Ranks differ by 2 or 3
- Immutability: frozen dataclass

### Validation
- `__post_init__`: Raises `ValueError` if `card1 == card2`
- Does NOT validate construction order (Hand("As", "Ks") allowed; normalizes to AKs on `to_shorthand()`)

### Example Usage
```python
# From card strings
hand1 = Hand.from_strings("As", "Ks")
assert hand1.to_shorthand() == "AKs"
assert hand1.num_combos() == 4
assert hand1.is_suited() == True

# From Card objects
hand2 = Hand(Card.from_string("2c"), Card.from_string("2h"))
assert hand2.is_pair() == True
assert hand2.num_combos() == 6

# Duplicate cards rejected
try:
    hand3 = Hand.from_strings("As", "As")
except ValueError as e:
    assert "duplicate" in str(e).lower()
```

---

## Entity: HandRange

**File**: `python/aof_gto_browser_ii/shared/domain/hand_range.py`

### Purpose
Immutable representation of 1-1326 possible poker hands as a range. Supports complex shorthand notation parsing (AKs+, 22+, A5s-A2s) and set operations.

### Structure
```python
@dataclass(frozen=True)
class HandRange:
    hands: List[Hand]  # 1-1326, no duplicates
    notation: str      # original shorthand for round-trip ("AKs+,QQ+,A5s-A2s")
    
    def __post_init__(self):
        if len(set(hand.to_shorthand() for hand in self.hands)) != len(self.hands):
            raise ValueError("HandRange cannot have duplicate hands")
```

### Parsing Algorithm (3-phase)

**Phase 1 - Parse**: Decompose notation by comma/semicolon  
**Phase 2 - Expand**: For each component, detect type and expand:
- Single hand "AKs": 4 combos (one per suit match)
- Single hand "AKo": 12 combos  
- Single hand "AA": 6 combos
- Plus notation "22+": 13×6=78 combos (all pairs)
- Plus notation "AKs+": Iterate down from AK to as  
- Dash range "A5s-A2s": 4 hands × 4 combos = 16 combos
- Dash range "22-99": 8 pairs x 6 combos = 48 combos

**Phase 3 - Deduplicate**: Remove duplicates, keep order

### Key Methods
- `HandRange.from_shorthand(notation: str) -> HandRange` - Parse complex notation
- `to_shorthand() -> str` - Return original notation
- `to_strings() -> List[tuple[str, str]]` - Card pairs for DTO transport
- `size() -> int` - Number of unique hand types (1-169)
- `num_combos() -> int` - Total combos (1-1326)
- `contains(hand: Hand) -> bool` - Membership test
- `union(range1, range2) -> HandRange` (static) - Combined hands
- `intersection(range1, range2) -> HandRange` (static) - Common hands
- Immutability: frozen dataclass
- Performance: Parsing < 10ms for typical ranges

### Validation
- Raises `RangeError` for invalid notation (unrecognized ranks,"XX+", malformed syntax)
- Raises `ValueError` for duplicate hands in final list

### Example Usage
```python
# Simple notation
range1 = HandRange.from_shorthand("AKs")
assert range1.size() == 1
assert range1.num_combos() == 4

# Plus notation
range2 = HandRange.from_shorthand("22+")
assert range2.size() == 13
assert range2.num_combos() == 78  # 13 pairs × 6 combos each

# Complex notation
range3 = HandRange.from_shorthand("AKs+,QQ+,A5s-A2s")
assert range3.size() == 8  # AKs, AQs, QQ, KK, AA, A5s, A4s, A3s, A2s
assert range3.num_combos() == 42

# Round-trip
assert range3.to_shorthand() == "AKs+,QQ+,A5s-A2s"

# Set operations
range4 = HandRange.union(range1, range2)
range5 = HandRange.intersection(range1, range2)  # Empty
```

---

## Entity: Board

**File**: `python/aof_gto_browser_ii/shared/domain/board.py`

### Purpose
Immutable representation of 0-5 community cards in street order. Supports street detection and card accessors.

### Structure
```python
@dataclass(frozen=True)
class Board:
    cards: List[Card]  # 0-5 cards, no duplicates, in street order
    
    def __post_init__(self):
        if len(self.cards) > 5:
            raise ValueError("Board cannot have more than 5 cards")
        if len(set(self.cards)) != len(self.cards):
            raise ValueError("Board cannot have duplicate cards")
```

### Key Methods
- `Board.from_strings(card_strings: List[str]) -> Board` - Parse from strings
- `to_strings() -> List[str]` - Return card strings
- `__str__()` - Space-separated cards like "As Kh 2d Ts"
- `num_cards() -> int` - 0-5
- `is_empty() -> bool` - 0 cards (preflop)
- `is_flop() -> bool` - Exactly 3 cards
- `is_turn() -> bool` - Exactly 4 cards
- `is_river() -> bool` - Exactly 5 cards
- `is_complete() -> bool` - 5 cards
- `get_street() -> str` - "preflop", "flop", "turn", "river", or "unknown"
- `get_flop() -> Optional[tuple[Card, Card, Card]]` - Cards 0-2 if available
- `get_turn() -> Optional[Card]` - Card 3 if available
- `get_river() -> Optional[Card]` - Card 4 if available
- `contains_card(card: Card) -> bool`
- `all_board_cards() -> List[Card]` - Copy of all cards
- Immutability: frozen dataclass

### Validation
- `__post_init__`: len(cards) ≤ 5, no duplicates
- Does NOT validate poker legality

### Example Usage
```python
# Preflop (empty)
board1 = Board(cards=[])
assert board1.is_empty() == True
assert board1.get_street() == "preflop"

# Flop
board2 = Board.from_strings(["As", "Kh", "2d"])
assert board2.is_flop() == True
assert board2.get_flop() == (Card("As"), Card("Kh"), Card("2d"))

# Turn
board3 = Board.from_strings(["As", "Kh", "2d", "Ts"])
assert board3.is_turn() == True
assert board3.get_turn() == Card.from_string("Ts")

# River
board4 = Board.from_strings(["As", "Kh", "2d", "Ts", "9c"])
assert board4.is_river() == True
assert board4.is_complete() == True
```

---

## Entity: EquityResult

**File**: `python/aof_gto_browser_ii/shared/domain/equity_result.py`

### Purpose
Immutable result of poker hand equity calculation. Stores win/draw/loss probabilities and validates they sum to 1.0.

### Structure
```python
@dataclass(frozen=True)
class EquityResult:
    hand: Hand
    equity: float          # 0.0-1.0
    win_prob: float        # 0.0-1.0
    draw_prob: float       # 0.0-1.0
    loss_prob: float       # 0.0-1.0
    num_simulations: int   # ≥ 1000
    
    def __post_init__(self):
        # Validate each probability is 0.0-1.0
        if not (0.0 <= self.equity <= 1.0):
            raise ValueError("equity must be 0.0-1.0")
        # ... validate others ...
        
        # Validate probabilities sum to 1.0 ± 0.01 (floating-point tolerance)
        prob_sum = self.win_prob + self.draw_prob + self.loss_prob
        if not (0.99 <= prob_sum <= 1.01):
            raise ValueError(f"probabilities must sum to 1.0 ± 0.01, got {prob_sum}")
        
        if self.num_simulations < 1000:
            raise ValueError("num_simulations must be >= 1000")
```

### Key Methods
- `win_percent -> str` - Formatted string like "52.34%"
- `draw_percent -> str`
- `loss_percent -> str`
- `equity_percent -> str`
- `from_monte_carlo(hand, wins: int, draws: int, losses: int, total_simulations: int) -> EquityResult` (static) - Factory from raw counts
- Immutability: frozen dataclass

### Validation
- Each probability field must be 0.0-1.0
- `win_prob + draw_prob + loss_prob` must equal 1.0 ± 0.01
- `num_simulations >= 1000`
- Raises `ValueError` with descriptive message for violations

### Example Usage
```python
hand = Hand.from_strings("As", "Ks")

# From probabilities
result1 = EquityResult(
    hand=hand,
    equity=0.625,
    win_prob=0.625,
    draw_prob=0.0,
    loss_prob=0.375,
    num_simulations=100000
)

# From Monte Carlo counts
result2 = EquityResult.from_monte_carlo(
    hand=hand,
    wins=62500,
    draws=0,
    losses=37500,
    total_simulations=100000
)

# Display formatting
print(f"{hand.to_shorthand()}: {result1.equity_percent} equity")  # "AKs: 62.5% equity"
```

---

## Entity: Bet

**File**: `python/aof_gto_browser_ii/shared/domain/bet.py`

### Purpose
Immutable monetary amount in big blinds. Validates amount > 0 and finite.

### Structure
```python
@dataclass(frozen=True)
class Bet:
    amount_bb: float  # Big blinds, must be > 0 and finite
    
    def __post_init__(self):
        if self.amount_bb <= 0:
            raise ValueError("amount_bb must be > 0")
        if not math.isfinite(self.amount_bb):
            raise ValueError("amount_bb must be finite (not NaN/Inf)")
```

### Key Methods
- `is_zero() -> bool` - Always False (since amount > 0)
- `is_all_in(stack_bb: float) -> bool` - True if amount >= stack
- `display_value() -> str` - Formats for UI (e.g., "2.5 BB", "0.50 BB")
- Immutability: frozen dataclass

### Validation
- `__post_init__`: Raises `ValueError` if `amount_bb <= 0`
- `__post_init__`: Raises `ValueError` if amount is NaN or Infinity

### Example Usage
```python
# Valid bets
bet1 = Bet(25.0)
bet2 = Bet(0.5)

# Invalid bets
try:
    bet_invalid = Bet(0)
except ValueError:
    pass

try:
    bet_invalid = Bet(float('nan'))
except ValueError:
    pass

# Formatting
print(bet1.display_value())  # "25.0 BB"
print(bet2.display_value())  # "0.5 BB"

# Comparison
assert bet1.is_all_in(stack_bb=20.0) == True
assert bet1.is_all_in(stack_bb=30.0) == False
```

---

## Adapter: CardAdapter

**File**: `python/aof_gto_browser_ii/shared/adapters/card_adapter.py`

### Purpose
Convert between domain Card objects and solver library formats. Isolates PokerKit coupling to adapter layer.

### Structure
```python
class CardAdapter:
    """Adapter for PokerKit solver library conversions"""
    
    @staticmethod
    def to_pokerkit(card: Card) -> str:
        """Card → PokerKit string format"""
        # Returns "As", "Kh", "2d", "Tc"
        # O(1) direct passthrough to card.to_string()
    
    @staticmethod
    def from_pokerkit(s: str) -> Card:
        """PokerKit string format → Card"""
        # Delegates to Card.from_string()
    
    @staticmethod
    def to_pokerkit_hand(hand: Hand) -> tuple[str, str]:
        """Hand → PokerKit hand format (card1_str, card2_str)"""
    
    @staticmethod
    def from_pokerkit_hand(c1: str, c2: str) -> Hand:
        """PokerKit hand format (card1_str, card2_str) → Hand"""
```

### Performance
- All conversions O(1) with < 1 microsecond per call
- Direct passthrough to Card.to_string() / Card.from_string()
- No lookups or complex logic

### Testing
- Round-trip tests for all 52 cards
- Card → PokerKit → Card must be identical
- Hand → PokerKit → Hand must be identical

### Future Extensibility
- Phase 2+ can add `to_treys()`, `from_treys()`, `to_pypokerengine()`, etc.
- Without modifying Card, Hand, or domain layer

### Example Usage
```python
card = Card(rank=Rank.ACE, suit=Suit.SPADES)

# Card conversion
pokerkit_str = CardAdapter.to_pokerkit(card)  # "As"
back_to_card = CardAdapter.from_pokerkit(pokerkit_str)
assert back_to_card == card

# Hand conversion
hand = Hand.from_strings("As", "Kd")
pokerkit_hand = CardAdapter.to_pokerkit_hand(hand)  # ("As", "Kd")
back_to_hand = CardAdapter.from_pokerkit_hand("As", "Kd")
assert back_to_hand == hand
```

---

## Supporting Types

### Custom Exceptions

**File**: `python/aof_gto_browser_ii/exceptions/validation_errors.py`

```python
class ValidationError(Exception):
    """General validation failure"""
    pass

class RangeError(ValidationError):
    """Invalid range notation or operations"""
    pass

class PositionError(ValidationError):
    """Invalid position value"""
    pass
```

---

## Architectural Decisions

1. **Frozen Dataclasses**: All domain types use `@dataclass(frozen=True)` for immutability and hashability
2. **Enum Types**: Rank (IntEnum), Suit (str, Enum) for type safety and database stability
3. **Factory Methods**: `from_string()`, `from_shorthand()` for flexible parsing
4. **Validation in `__post_init__`**: Prevents invalid objects from existing (no invalid state possible)
5. **Round-Trip Serializability**: All types can serialize → string and recover using inverse factory
6. **Single Responsibility**: Each class has one clear purpose
7. **No External Dependencies**: Only Python standard library (Phase 1.1)
8. **Adapter Pattern**: CardAdapter abstracts solver-specific conversions

## Testing Strategy

See [spec.md § Success Criteria](spec.md#success-criteria) for 10 measurable outcomes:
- **SC-001**: Immutability via frozen dataclass
- **SC-002**: HandRange parsing performance (< 10ms)
- **SC-003 through SC-006**: Type-specific validation
- **SC-007**: 80% line coverage with pytest
- **SC-008 through SC-010**: Documentation and approval

**Test Categories**:
- **Unit Tests**: Each class independently (create, parse, validate, exception cases)
- **Integration Tests**: Cross-class usage (Card in Hand, Hand in HandRange, etc.)
- **Performance Tests**: HandRange parsing < 10ms, CardAdapter < 1μs
- **Immutability Tests**: Attempt mutations, expect AttributeError
- **Serialization Tests**: Round-trip conversions maintain equality

**Test Files**:
- `tests/aof_gto_browser_ii/test_card.py`
- `tests/aof_gto_browser_ii/test_hand.py`
- `tests/aof_gto_browser_ii/test_hand_range.py`
- `tests/aof_gto_browser_ii/test_board.py`
- `tests/aof_gto_browser_ii/test_equity_result.py`
- `tests/aof_gto_browser_ii/test_bet.py`
- `tests/aof_gto_browser_ii/test_card_adapter.py`
- `tests/aof_gto_browser_ii/conftest.py`
