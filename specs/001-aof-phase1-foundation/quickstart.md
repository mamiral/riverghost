# Quickstart: Phase 1.1 Domain Models Developer Guide

**For**: Backend developers implementing domain models  
**Time**: ~3 days (1 day Card/Hand/HandRange, 1 day Board/EquityResult/Bet, 1 day CardAdapter + tests)

## Setup

### 1. Environment
```powershell
cd c:\Users\U446541\sandbox\riverghost
.venv\Scripts\Activate.ps1
cd python
```

### 2. Project Structure
```
python/aof_gto_browser_ii/
├── __init__.py              # Exports all public domain models
├── domain/
│   ├── __init__.py
│   ├── card.py              # Card, Rank, Suit
│   ├── hand.py              # Hand
│   ├── hand_range.py        # HandRange
│   ├── board.py             # Board
│   ├── equity_result.py     # EquityResult
│   └── bet.py               # Bet
├── adapters/
│   ├── __init__.py
│   └── card_adapter.py      # CardAdapter
└── exceptions/
    ├── __init__.py
    └── validation_errors.py # Custom errors
```

### 3. Test Setup
```
tests/aof_gto_browser_ii/
├── test_card.py             # Card + enums
├── test_hand.py             # Hand
├── test_hand_range.py       # HandRange
├── test_board.py            # Board
├── test_equity_result.py    # EquityResult
├── test_bet.py              # Bet
├── test_card_adapter.py     # CardAdapter
└── conftest.py              # Shared fixtures
```

## Implementation Order

### Phase 1: Card & Related Types (Day 1)

Start with **Card** - simplest and most used by everything else.

#### 1.1 Implement `domain/card.py`

**File**: `python/aof_gto_browser_ii/domain/card.py`

**Requirements** from [data-model.md](data-model.md#entity-card):
- Rank enum (2-14, where A=14)
- Suit enum (s, h, d, c as string values)
- Card dataclass (frozen, hashable, immutable)
- Parsing: `Card.from_string("As")` with case-insensitive support
- Also parse long form "Ace of Spades"
- String conversion: `card.to_string()` returns "As"

**Example Implementation Structure**:
```python
from dataclasses import dataclass
from enum import IntEnum, Enum

class Rank(IntEnum):
    TWO = 2; THREE = 3; FOUR = 4; FIVE = 5; SIX = 6
    SEVEN = 7; EIGHT = 8; NINE = 9; TEN = 10
    JACK = 11; QUEEN = 12; KING = 13; ACE = 14

class Suit(str, Enum):
    SPADES = "s"; HEARTS = "h"; DIAMONDS = "d"; CLUBS = "c"

@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit
    
    @staticmethod
    def from_string(s: str) -> 'Card':
        # Parse "As", "Ace of Spades", case-insensitive
        # Return Card instance
        pass
    
    def to_string(self) -> str:
        # Return "As", "Kh", etc.
        pass
    
    def __str__(self) -> str:
        return self.to_string()
    
    def __repr__(self) -> str:
        return f"Card.from_string('{self.to_string()}')"
    
    def is_ace(self) -> bool:
        return self.rank == Rank.ACE
```

#### 1.2 Test Card Implementation

Create `tests/aof_gto_browser_ii/test_card.py`:

```python
import pytest
from hopilot.shared.domain.card import Card, Rank, Suit

class TestCardConstruction:
    def test_card_enum_construction(self):
        card = Card(rank=Rank.ACE, suit=Suit.SPADES)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES
    
    def test_card_from_string_shorthand(self):
        card = Card.from_string("As")
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES
    
    def test_card_from_string_long_form(self):
        card = Card.from_string("Ace of Spades")
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES
    
    def test_card_case_insensitive(self):
        assert Card.from_string("AS") == Card.from_string("as")
    
    def test_card_to_string(self):
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.to_string() == "As"
        assert str(card) == "As"

class TestCardImmutability:
    def test_card_frozen(self):
        card = Card(Rank.ACE, Suit.SPADES)
        with pytest.raises(AttributeError):
            card.rank = Rank.KING

class TestCardHashable:
    def test_card_in_set(self):
        card1 = Card.from_string("As")
        card2 = Card.from_string("As")
        card_set = {card1, card2}
        assert len(card_set) == 1
    
    def test_card_as_dict_key(self):
        card = Card.from_string("As")
        card_dict = {card: "ace of spades"}
        assert card_dict[card] == "ace of spades"

class TestCardRoundTrip:
    def test_all_52_cards_round_trip(self):
        # Test all combinations of ranks and suits
        for rank in Rank:
            for suit in Suit:
                card = Card(rank, suit)
                serialized = card.to_string()
                deserialized = Card.from_string(serialized)
                assert deserialized == card
```

Run tests: `python -m pytest tests/aof_gto_browser_ii/test_card.py -v`

### Phase 2: Hand (Day 1 afternoon)

#### 2.1 Implement `domain/hand.py`

**Requirements**:
- Two Card fields (card1, card2)
- Validation: no duplicate cards
- `to_shorthand()`: "AKs", "22", "QJo"
- `num_combos()`: 6 (pair), 4 (suited), 12 (offsuit)
- Parsing: `Hand.from_strings("As", "Ks")`

**Key Logic**:
```python
@dataclass(frozen=True)
class Hand:
    card1: Card
    card2: Card
    
    def __post_init__(self):
        if self.card1 == self.card2:
            raise ValueError("Hand cannot have duplicate cards")
    
    def to_shorthand(self) -> str:
        # If pair: "AA", "KK", etc.
        # If suited: "AKs"  (higher rank first)
        # If offsuit: "AKo"
        pass
    
    def num_combos(self) -> int:
        # 6 for pair, 4 for suited, 12 for offsuit
        pass

    @staticmethod
    def from_strings(card1_str: str, card2_str: str) -> 'Hand':
        card1 = Card.from_string(card1_str)
        card2 = Card.from_string(card2_str)
        return Hand(card1, card2)
    
    def is_pair(self) -> bool:
        return self.card1.rank == self.card2.rank
    
    def is_suited(self) -> bool:
        return self.card1.suit == self.card2.suit
    
    def is_offsuit(self) -> bool:
        return not self.is_suited()
```

#### 2.2 Test Hand

Create matching test cases in `tests/test_hand.py` similar to Card tests.

### Phase 3: HandRange (Day 1 evening)

#### 3.1 Implement `domain/hand_range.py`

**Complexity**: HandRange parsing is the most complex. Use 3-phase algorithm:

```python
@dataclass(frozen=True)
class HandRange:
    hands: List[Hand]
    notation: str
    
    @staticmethod
    def from_shorthand(notation: str) -> 'HandRange':
        # Phase 1: Parse by comma
        components = notation.split(',')
        
        all_hands = set()
        for component in components:
            component = component.strip()
            # Phase 2: Expand component
            hands_in_component = expand_component(component)
            all_hands.update(hands_in_component)
        
        # Phase 3: Deduplicate
        hands_list = sorted(list(all_hands))
        return HandRange(hands=hands_list, notation=notation)
    
    def size(self) -> int:
        # Number of unique hand types
        return len(set(h.to_shorthand() for h in self.hands))
    
    def num_combos(self) -> int:
        # Total combos across all hands
        return sum(h.num_combos() for h in self.hands)
    
    def contains(self, hand: Hand) -> bool:
        shorthand = hand.to_shorthand()
        return any(h.to_shorthand() == shorthand for h in self.hands)
```

**Expansion Examples**:
- "AKs" → 4 combos (all AKs combos)
- "22+" → 13 pairs (22 through AA)
- "AKs+" → AKs, AQs (down to As2s if full expansion)
- "A5s-A2s" → A5s, A4s, A3s, A2s

### Phase 4: Board, EquityResult, Bet (Day 2)

These are simpler. Follow same pattern: implement, test, validate immutability, test edge cases.

**Board**: Street detection logic
**EquityResult**: Probability validation (sum to 1.0 ± 0.01)
**Bet**: Amount validation (> 0, finite)

### Phase 5: CardAdapter (Day 2)

Implement PokerKit conversions:

```python
class CardAdapter:
    @staticmethod
    def to_pokerkit(card: Card) -> str:
        return card.to_string()  # "As", "Kh", etc.
    
    @staticmethod
    def from_pokerkit(s: str) -> Card:
        return Card.from_string(s)
    
    @staticmethod
    def to_pokerkit_hand(hand: Hand) -> tuple[str, str]:
        return (hand.card1.to_string(), hand.card2.to_string())
    
    @staticmethod
    def from_pokerkit_hand(c1: str, c2: str) -> Hand:
        return Hand(Card.from_string(c1), Card.from_string(c2))
```

Test round-trip conversions for all 52 cards and hands.

### Phase 6: Complete & Polish (Day 3)

- [ ] Add docstrings to all public methods
- [ ] Create `__init__.py` exports (make domain types accessible)
- [ ] Run coverage: `python -m pytest --cov=hopilot.shared tests/`
- [ ] Target: 80% line coverage
- [ ] Fix any missing edge cases

### Importing & Usage

### Direct Imports (for implementation)
```python
from aof_gto_browser_ii.domain.card import Card, Rank, Suit
from aof_gto_browser_ii.domain.hand import Hand
from aof_gto_browser_ii.domain.hand_range import HandRange
from aof_gto_browser_ii.domain.board import Board
from aof_gto_browser_ii.domain.equity_result import EquityResult
from aof_gto_browser_ii.domain.bet import Bet
from aof_gto_browser_ii.adapters.card_adapter import CardAdapter
```

### Package-Level Imports (for users)
```python
# After __init__.py exports are set up:
from aof_gto_browser_ii import Card, Hand, HandRange, Board, EquityResult, Bet, CardAdapter
```

## Common Patterns

### Pattern 1: Parse from Strings
```python
# Card
card = Card.from_string("As")

# Hand
hand = Hand.from_strings("As", "Ks")

# HandRange
range = HandRange.from_shorthand("AKs+,QQ+")
```

### Pattern 2: Check Properties
```python
# Card
if card.is_ace():
    pass

# Hand
if hand.is_suited():
    combos = hand.num_combos()  # 4

# Board
if board.is_flop():
    flop_cards = board.get_flop()
```

### Pattern 3: Round-Trip Serialization
```python
# Card
card = Card.from_string("As")
serialized = card.to_string()
card_again = Card.from_string(serialized)
assert card == card_again

# Hand
hand = Hand.from_strings("As", "Ks")
notation = hand.to_shorthand()  # "AKs"

# HandRange
range = HandRange.from_shorthand("AKs+,QQ+")
notation_again = range.to_shorthand()
```

### Pattern 4: Validate Edge Cases
```python
# Duplicate cards rejected
try:
    hand = Hand.from_strings("As", "As")
except ValueError:
    pass  # Expected

# Invalid bet amount
try:
    bet = Bet(0)  # amount_bb must be > 0
except ValueError:
    pass  # Expected

# Invalid equity
try:
    result = EquityResult(hand, equity=1.5, ...)  # Out of bounds
except ValueError:
    pass  # Expected
```

## Testing Checklist

- [ ] Unit tests for Card (parsing, immutability, hashing)
- [ ] Unit tests for Hand (validation, shorthand, combos)
- [ ] Unit tests for HandRange (parsing complex notation, performance < 10ms, set operations)
- [ ] Unit tests for Board (street detection, accessors)
- [ ] Unit tests for EquityResult (probability validation, formatting)
- [ ] Unit tests for Bet (amount validation, display)
- [ ] Unit tests for CardAdapter (round-trip conversions, O(1) performance)
- [ ] Integration tests (Card in Hand in HandRange, etc.)
- [ ] Edge case tests (empty range, all 169 hands, floating-point rounding)
- [ ] Coverage report: 80%+ line coverage

## Running Tests

```powershell
# All tests
python -m pytest tests/aof_gto_browser_ii/ -v

# Specific file
python -m pytest tests/aof_gto_browser_ii/test_hand_range.py -v

# With coverage
python -m pytest tests/aof_gto_browser_ii/ --cov=aof_gto_browser_ii --cov-report=html

# Check coverage report
start htmlcov/index.html
```

## Debugging

### Setup Interactive Python
```powershell
python
>>> from aof_gto_browser_ii.domain.card import Card
>>> card = Card.from_string("As")
>>> card
>>> card.to_string()
```

### Check Imports Work
```powershell
python -c "from aof_gto_browser_ii import Card; print(Card.from_string('As'))"
```

### Run Single Test
```powershell
python -m pytest tests/aof_gto_browser_ii/test_card.py::TestCardConstruction::test_card_enum_construction -v
```

## References

- [Data Model Specifications](data-model.md) - Detailed entity design
- [Feature Specification](spec.md) - Requirements and acceptance criteria
- [Domain Model Documentation](../01_DOMAIN_MODELS/00_INDEX.md) - Reference implementation details
- [Project Constitution](../../.github/copilot-instructions.md) - Design principles

## Next Steps (Phase 1.2+)

Once domain models are complete and tested:
1. Phase 1.2: Implement DTOs (PositionContext, CellDisplay, MatrixPayload, PrecomputeProgress, DetailPayload)
2. Phase 1.3: Implement Database Models (AnalysisSession, CellResult, PrecomputeLog)
3. Phase 1.4: Implement Configuration System
4. Phase 2: Implement Backend Services (AnalysisService, PrecomputeService)

Domain models are the foundation - other layers will depend on them.
