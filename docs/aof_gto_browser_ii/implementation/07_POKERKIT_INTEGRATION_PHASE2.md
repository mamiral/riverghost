# PokerKit Integration Strategy - Phase 2

**Document**: PokerKit solver integration architecture  
**Phase**: Phase 2 (Backend Services - not Phase 1.1)  
**Status**: Design Reference for Future Implementation  
**Last Updated**: April 3, 2026

---

## Overview

Phase 1.1 establishes immutable domain models with **zero external dependencies**. Phase 2 will integrate PokerKit for real equity calculation using the **CardAdapter bridge pattern** (designed in Phase 1.1 as string-based).

This document details:
1. How PokerKit.Card is constructed
2. Integration boundaries with domain models
3. Phase 2 implementation strategy

---

## 1. PokerKit Card Construction API

### Direct Constructor

PokerKit.Card accepts **two string arguments** (rank, suit):

```python
from pokerkit.utilities import Card as PokerkitCard

# Construction signature:
pk_card = PokerkitCard(rank: str, suit: str)

# Examples:
pk_card = PokerkitCard("A", "s")  # Ace of Spades
pk_card = PokerkitCard("K", "h")  # King of Hearts
pk_card = PokerkitCard("2", "d")  # Two of Diamonds
pk_card = PokerkitCard("T", "c")  # Ten of Clubs
```

### Rank Format

PokerKit requires **single-character rank strings**:
- Numeric: `"2"` - `"9"`
- Face cards: `"T"` (ten), `"J"` (jack), `"Q"` (queen), `"K"` (king)
- Ace: `"A"`

### Suit Format

PokerKit uses **single-character suit strings**:
- `"s"` = Spades
- `"h"` = Hearts
- `"d"` = Diamonds
- `"c"` = Clubs

### Card Object Properties

Once constructed, PokerKit cards have accessible properties:

```python
pk_card = PokerkitCard("A", "s")

# Attributes:
print(pk_card.rank)  # "A"
print(pk_card.suit)  # "s"

# String representation (for logging/debugging):
print(str(pk_card))  # "As" or similar format
```

---

## 2. Current HoPilot Integration Pattern

The existing `poker_analyzer.py` implements a conversion adapter:

```python
# File: python/hopilot/poker_analyzer.py (Lines 736-802)

def card_name_to_pokerkit(self, card_name: str) -> Optional[PokerkitCard]:
    """Convert card name string to PokerKit Card object."""
    
    # Parse flexible input formats: "As", "AS", "Ace of Spades", etc.
    if ' of ' in card_name or '_of_' in card_name:
        # Long form: "Ace of Spades"
        rank_str, suit_str = card_name.split(' of ')
    else:
        # Short form: "As"
        rank_str = card_name[:-1]
        suit_str = card_name[-1]
    
    # Normalize to PokerKit format
    rank_map = {
        'a': 'A', 'ace': 'A',
        'k': 'K', 'king': 'K',
        # ... other ranks ...
        '2': '2', 'two': '2',
    }
    suit_map = {
        's': 's', 'spades': 's',
        'h': 'h', 'hearts': 'h',
        'd': 'd', 'diamonds': 'd',
        'c': 'c', 'clubs': 'c',
    }
    
    rank = rank_map.get(rank_str.strip().lower())
    suit = suit_map.get(suit_str.strip().lower())
    
    if rank is None or suit is None:
        return None
    
    try:
        return PokerkitCard(rank, suit)  # ← Actual construction
    except Exception:
        return None
```

**Key observation**: The function **maps flexible input → normalized rank/suit → PokerkitCard(rank, suit)**

---

## 3. Phase 1.1 CardAdapter Design (String-Based)

Phase 1.1 implements CardAdapter as a **string conversion interface**:

```python
# File: python/aof_gto_browser_ii/shared/adapters/card_adapter.py

class CardAdapter:
    """Adapter for solver library integration (Phase 1.1: strings only)."""
    
    @staticmethod
    def to_pokerkit(card: Card) -> str:
        """Convert domain Card to PokerKit string format.
        
        Phase 1.1: Returns normalized string "As", "Kh", etc.
        Phase 2: Can be extended to return PokerkitCard objects.
        """
        return card.to_string()  # e.g., "As"
    
    @staticmethod
    def from_pokerkit(s: str) -> Card:
        """Parse PokerKit string format back to domain Card."""
        return Card.from_string(s)
    
    @staticmethod
    def to_pokerkit_hand(hand: Hand) -> tuple[str, str]:
        """Convert Hand to PokerKit format (2-tuple of strings)."""
        return (hand.card1.to_string(), hand.card2.to_string())
    
    @staticmethod
    def from_pokerkit_hand(c1: str, c2: str) -> Hand:
        """Construct Hand from PokerKit card strings."""
        return Hand.from_strings(c1, c2)
```

**Phase 1.1 Output**: Normalized strings like `"As"`, `"Kh"`, `"2d"`, `"Tc"`

---

## 4. Phase 2 Integration Strategy

When Phase 2 adds PokerKit solver support, use **one of three approaches**:

### Option A: Extend CardAdapter with PokerKit Objects (Recommended)

Add Phase 2 methods to CardAdapter without changing Phase 1.1:

```python
# Phase 2 additions to CardAdapter

from pokerkit.utilities import Card as PokerkitCard

class CardAdapter:
    # Keep all Phase 1.1 methods unchanged...
    
    # NEW Phase 2 methods
    @staticmethod
    def to_pokerkit_card_object(card: Card) -> PokerkitCard:
        """Convert domain Card to actual PokerKit Card object (Phase 2+).
        
        Uses Phase 1.1's to_pokerkit() string output as intermediate step.
        """
        string_form = CardAdapter.to_pokerkit(card)  # "As"
        
        # Extract rank and suit from domain Card
        # Domain Card uses Rank enum (2-14) and Suit enum
        rank_char = {
            int(Rank.TWO): '2', int(Rank.THREE): '3', ..., int(Rank.ACE): 'A'
        }[int(card.rank)]
        
        suit_char = card.suit.value  # 's', 'h', 'd', 'c'
        
        # Construct PokerKit Card
        return PokerkitCard(rank_char, suit_char)
    
    @staticmethod
    def to_pokerkit_hand_objects(hand: Hand) -> tuple[PokerkitCard, PokerkitCard]:
        """Convert Hand to tuple of PokerKit Card objects."""
        return (
            CardAdapter.to_pokerkit_card_object(hand.card1),
            CardAdapter.to_pokerkit_card_object(hand.card2)
        )
    
    @staticmethod
    def to_pokerkit_board_objects(board: Board) -> list[PokerkitCard]:
        """Convert Board to list of PokerKit Card objects."""
        return [CardAdapter.to_pokerkit_card_object(c) for c in board.cards]
```

**Advantages**:
- Encapsulates PokerKit coupling in one place
- Phase 1.1 remains unchanged and dependency-free
- Clean separation of string (Phase 1.1) and object (Phase 2) handling
- Easy to extend for other solvers (treys, pypokerengine, etc.)

### Option B: Reuse Existing HoPilot adapter_analyzer

```python
# Phase 2: equity_calculator.py

from hopilot.poker_analyzer import PokerAnalyzer
from aof_gto_browser_ii.shared.domain import Card, Hand, CardAdapter, Board

class EquityCalculator:
    """Phase 2: Real equity calculation using PokerKit."""
    
    def __init__(self):
        self.analyzer = PokerAnalyzer()  # Existing HoPilot adapter
    
    def calculate_hand_equity(self, hand: Hand, board: Board, num_opponents: int):
        """Use existing PokerAnalyzer for equity calculations."""
        
        # Convert domain objects to strings using CardAdapter
        hand_strings = [CardAdapter.to_pokerkit(hand.card1), 
                       CardAdapter.to_pokerkit(hand.card2)]
        board_strings = [CardAdapter.to_pokerkit(c) for c in board.cards]
        
        # Call existing HoPilot analyzer (internally uses card_name_to_pokerkit)
        result = self.analyzer.calculate_odds_random_opponents(
            hero_hole_cards=hand_strings,
            board_cards=board_strings,
            num_opponents=num_opponents,
            num_simulations=10000
        )
        
        # Convert PokerAnalyzer result to domain EquityResult
        return EquityResult.from_monte_carlo(
            hand=hand,
            wins=result['wins'],
            draws=result.get('ties', 0),
            losses=result['valid_simulations'] - result['wins'] - result.get('ties', 0),
            total_simulations=result['valid_simulations']
        )
```

**Advantages**:
- Reuses existing battle-tested HoPilot analyzer
- Minimal Phase 2 code needed
- PokerKit integration already working

**Disadvantage**:
- Couples to HoPilot's specific adapter pattern

### Option C: Direct PokerKit Usage in Equity Service

```python
# Phase 2: equity_service.py (alternative, lower-level approach)

from pokerkit.utilities import Card as PokerkitCard, Deck as PokerkitDeck
from pokerkit.hands import StandardHighHand
from aof_gto_browser_ii.shared.domain import Card, Hand, Board, CardAdapter

class EquityService:
    """Direct PokerKit usage for equity calculation."""
    
    def calculate_equity(self, hand: Hand, board: Board, opponent_range: HandRange):
        """Monte Carlo simulation using PokerKit directly."""
        
        # Convert domain objects to PokerKit objects using CardAdapter
        pk_hand = [
            PokerkitCard(self._card_to_pk_rank(hand.card1), 
                        hand.card1.suit.value),
            PokerkitCard(self._card_to_pk_rank(hand.card2), 
                        hand.card2.suit.value)
        ]
        
        pk_board = [
            PokerkitCard(self._card_to_pk_rank(c), c.suit.value)
            for c in board.cards
        ]
        
        # Monte Carlo
        wins, ties = 0, 0
        for _ in range(num_sims):
            # Generate random opponent hands
            opponent_pks = [...]  # From opponent_range
            
            # Evaluate using PokerKit
            hero_hand = StandardHighHand.from_game(pk_hand, pk_board + random_board)
            opp_hands = [StandardHighHand.from_game(opp, pk_board + random_board)
                        for opp in opponent_pks]
            
            hero_strength = -hero_hand.entry.index
            if all(hero_strength < opp_strength for opp_strength in opp_strengths):
                wins += 1
            elif all(hero_strength == opp_strength for opp_strength in opp_strengths):
                ties += 1
        
        return EquityResult.from_monte_carlo(hand, wins, ties, ...)
    
    @staticmethod
    def _card_to_pk_rank(card: Card) -> str:
        """Map domain Rank to PokerKit rank string."""
        rank_map = {
            Rank.TWO: '2', Rank.THREE: '3', ..., Rank.ACE: 'A'
        }
        return rank_map[card.rank]
```

**Advantages**:
- Full control over Monte Carlo algorithm
- Testable without HoPilot dependency

**Disadvantage**:
- Reinvents logic already in HoPilot

---

## 5. Recommended Phase 2 Implementation

**Use Option A (Extended CardAdapter)** for cleanest architecture:

```
Phase 1.1:
  CardAdapter.to_pokerkit(card: Card) -> str  # "As"
  
Phase 2:
  CardAdapter.to_pokerkit_card_object(card: Card) -> PokerkitCard
  CardAdapter.to_pokerkit_hand_objects(hand: Hand) -> (PokerkitCard, PokerkitCard)
  CardAdapter.to_pokerkit_board_objects(board: Board) -> [PokerkitCard]
  
  EquityCalculator:
    def calculate(hand: Hand, board: Board) -> EquityResult:
      pk_hand = CardAdapter.to_pokerkit_hand_objects(hand)
      pk_board = CardAdapter.to_pokerkit_board_objects(board)
      # Use pk_hand, pk_board with PokerKit
      return EquityResult(...)
```

**Benefits**:
- Phase 1.1 remains pure and independent
- Phase 2 extends cleanly via adapter pattern
- Future solvers (treys, pypokerengine) only require new adapter methods
- Clear separation of concerns

---

## 6. Key Implementation Details for Phase 2

### Rank/Suit Conversion Mapping

```python
# Domain Rank (IntEnum) → PokerKit rank (str)
DOMAIN_TO_PK_RANK = {
    Rank.TWO: '2', Rank.THREE: '3', Rank.FOUR: '4', Rank.FIVE: '5',
    Rank.SIX: '6', Rank.SEVEN: '7', Rank.EIGHT: '8', Rank.NINE: '9',
    Rank.TEN: 'T', Rank.JACK: 'J', Rank.QUEEN: 'Q', Rank.KING: 'K',
    Rank.ACE: 'A'
}

# Domain Suit (str Enum) → PokerKit suit (str)
DOMAIN_TO_PK_SUIT = {
    Suit.SPADES: 's', Suit.HEARTS: 'h', Suit.DIAMONDS: 'd', Suit.CLUBS: 'c'
}

# Or simpler: just use .value property
pk_rank = DOMAIN_TO_PK_RANK[card.rank]
pk_suit = card.suit.value  # Already 's', 'h', 'd', 'c'
```

### Hand Equity Calculation Pattern

```python
# PokerKit evaluation flow (from poker_analyzer.py)

from pokerkit.hands import StandardHighHand

pk_hand = [PokerkitCard('A', 's'), PokerkitCard('K', 'h')]
pk_board = [PokerkitCard('A', 'c'), PokerkitCard('2', 'd'), PokerkitCard('3', 's')]

# Evaluate hand strength
full_hand = StandardHighHand.from_game(pk_hand, pk_board)
strength = -full_hand.entry.index  # Negative index = stronger = lower score
```

---

## 7. Testing Strategy for Phase 2

```python
# tests/aof_gto_browser_ii/test_pokerkit_integration.py

def test_card_roundtrip_through_pokerkit():
    """Verify domain Card ↔ PokerKit Card conversion accuracy."""
    for rank in all_ranks:
        for suit in all_suits:
            domain_card = Card(rank, suit)
            
            # Convert to PokerKit via CardAdapter
            pk_card = CardAdapter.to_pokerkit_card_object(domain_card)
            
            # Verify attributes
            assert pk_card.rank == expected_pk_rank
            assert pk_card.suit == expected_pk_suit
            
            # Round-trip: PokerKit → string → domain
            string_form = CardAdapter.to_pokerkit(domain_card)
            back_to_domain = Card.from_string(string_form)
            assert back_to_domain == domain_card

def test_hand_equity_calculation():
    """Verify equity calculation matches HoPilot baseline."""
    hand = Hand.from_strings("As", "Kh")
    board = Board.from_strings(["Ac", "2d", "3s"])
    
    equity = calc.calculate_equity(hand, board, num_sims=10000)
    
    assert 0 <= equity.win_prob <= 1
    assert 0 <= equity.draw_prob <= 1
    assert 0 <= equity.loss_prob <= 1
    assert abs(equity.win_prob + equity.draw_prob + equity.loss_prob - 1.0) < 0.01
```

---

## 8. References

- **PokerKit Documentation**: Card construction uses `PokerkitCard(rank: str, suit: str)`
- **Current HoPilot**: `python/hopilot/poker_analyzer.py` lines 736-802 (card conversion)
- **Phase 1.1 Design**: Domain models in `python/aof_gto_browser_ii/shared/domain/`
- **CardAdapter Interface**: `python/aof_gto_browser_ii/shared/adapters/card_adapter.py`

---

**Status**: Design reference complete. Ready for Phase 2 implementation.
