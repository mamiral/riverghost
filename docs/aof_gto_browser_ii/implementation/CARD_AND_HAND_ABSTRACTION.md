# Card & Hand Abstraction Layer Design

## Problem Statement

Using raw `str` objects for cards and hands in DTOs is architecturally weak because:

1. **No type safety**: "As", "AS", "ace spade" all compile but fail at runtime
2. **Tight coupling to solver**: DTOs would need to change if swapping PokerKit → treys
3. **No validation**: Invalid card formats pass type checking
4. **Low discoverability**: No IDE hints for valid card formats
5. **Mixing concerns**: Network transport format (string) leaks into domain model

## Current HoPilot Architecture

Original app uses a **conversion pattern**:
```python
# Data layer (strings from UI/network)
card_string = "As"

# Conversion at boundary
card_obj = PokerAnalyzer.card_name_to_pokerkit(card_string)  # PokerkitCard

# Domain models use Card objects
def calculate_odds(hero: List[PokerkitCard], board: List[PokerkitCard])
```

## Proposed Solution: Domain-Driven Design

Create abstraction layer:
- `Card` class (domain model, not string)
- `Hand` class (represents 2 cards)
- `Board` class (represents 0-5 cards)
- `SolverAdapter` pattern for pluggable libraries

---

## 1. Card Domain Model

```python
from enum import Enum
from typing import Optional

class Rank(Enum):
    """Poker ranks (Ace high)."""
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

class Suit(Enum):
    """Card suits."""
    SPADES = "s"
    HEARTS = "h"
    DIAMONDS = "d"
    CLUBS = "c"

@dataclass(frozen=True)
class Card:
    """Immutable card representation (domain model)."""
    rank: Rank
    suit: Suit
    
    def __str__(self) -> str:
        """Convert to shorthand: 'As', 'Kh', '2d'."""
        rank_char = {
            Rank.TWO: '2', Rank.THREE: '3', Rank.FOUR: '4', Rank.FIVE: '5',
            Rank.SIX: '6', Rank.SEVEN: '7', Rank.EIGHT: '8', Rank.NINE: '9',
            Rank.TEN: 'T', Rank.JACK: 'J', Rank.QUEEN: 'Q', Rank.KING: 'K',
            Rank.ACE: 'A'
        }
        return f"{rank_char[self.rank]}{self.suit.value}"
    
    @staticmethod
    def from_string(card_str: str) -> Optional['Card']:
        """Parse card from string: 'As', 'Kh', etc.
        
        Returns None if invalid.
        """
        if not card_str or len(card_str) != 2:
            return None
        
        rank_map = {
            '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
            '6': Rank.SIX, '7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE,
            'T': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN, 'K': Rank.KING,
            'A': Rank.ACE
        }
        suit_map = {'s': Suit.SPADES, 'h': Suit.HEARTS, 'd': Suit.DIAMONDS, 'c': Suit.CLUBS}
        
        rank = rank_map.get(card_str[0].upper())
        suit = suit_map.get(card_str[1].lower())
        
        if rank is None or suit is None:
            return None
        
        return Card(rank=rank, suit=suit)
```

**Benefits**:
- ✅ Type-safe: Only valid cards can be created
- ✅ Validation at construction time (no false positives)
- ✅ Enum-based: IDE hints for valid ranks/suits
- ✅ Immutable: Safe to use in sets/dicts
- ✅ Easy conversion: `str(card)` → `"As"`, `Card.from_string("As")` → Card object

---

## 1.5 Hand Range Domain Model (Critical for GTO)

Hand ranges represent **distributions of hands**, not individual hands. This is essential for AoF analysis.

```python
@dataclass(frozen=True)
class HandRange:
    """Represents a collection of hands (e.g., 'AKs', 'QJo', '22+')."""
    
    hands: List[Hand]  # All concrete hands in this range
    shorthand: Optional[str] = None  # Original notation ("AKs+", "A5s-A2s")
    
    def __post_init__(self):
        """Ensure all hands are unique."""
        if len(set(self.hands)) != len(self.hands):
            raise ValueError("HandRange cannot contain duplicate hands")
    
    def size(self) -> int:
        """Number of hands in range."""
        return len(self.hands)
    
    def to_strings(self) -> List[tuple[str, str]]:
        """Convert to list of card string tuples for transport."""
        return [hand.to_strings() for hand in self.hands]
    
    @staticmethod
    def from_shorthand(notation: str) -> Optional['HandRange']:
        """Parse shorthand notation into HandRange.
        
        Examples:
        - "AKs" → 4 suited AK combos
        - "22" → 6 pocket pair combos  
        - "AKo" → 12 offsuit AK combos
        - "AKs+AQs+22" → union of multiple components
        - "A5s-A2s" → range from A5s down to A2s (4 hands)
        - "22+" → all pairs from 22 to AA (13 hands)
        
        Returns None if notation is invalid.
        """
        try:
            # Use original HandRange.parse_shorthand()
            card_tuples = HandRange._parse_shorthand_internal(notation)
            hands = [Hand.from_strings(c1, c2) for c1, c2 in card_tuples]
            hands = [h for h in hands if h is not None]
            
            if not hands:
                return None
            
            return HandRange(hands=hands, shorthand=notation)
        except Exception:
            return None
    
    @staticmethod
    def union(*ranges: 'HandRange') -> 'HandRange':
        """Create union of multiple ranges (remove duplicates)."""
        all_hands = []
        for r in ranges:
            all_hands.extend(r.hands)
        
        unique_hands = list(dict.fromkeys(all_hands))  # Remove duplicates, preserve order
        return HandRange(hands=unique_hands, shorthand=None)
    
    @staticmethod
    def intersection(*ranges: 'HandRange') -> 'HandRange':
        """Create intersection of multiple ranges."""
        if not ranges:
            return HandRange(hands=[])
        
        hand_sets = [set(r.hands) for r in ranges]
        common_hands = hand_sets[0]
        for hand_set in hand_sets[1:]:
            common_hands &= hand_set
        
        return HandRange(hands=list(common_hands))
    
    def contains(self, hand: Hand) -> bool:
        """Check if range contains specific hand."""
        return hand in self.hands
```

**Shorthand Notation** (must support):

| Notation | Means | Count |
|----------|-------|-------|
| `"AKs"` | Ace-King suited all 4 combos | 4 |
| `"AKo"` | Ace-King offsuit all 12 combos | 12 |
| `"AA"` | Pocket aces all 6 combos | 6 |
| `"22"` | Pocket deuces all 6 combos | 6 |
| `"22+"` | All pocket pairs (2-2 through A-A) | 78 |
| `"A5s-A2s"` | Suited aces from A5 down to A2 (4 hands) | 16 |
| `"AKs+AQs"` | Union: AKs + AQs | 8 |
| `"AKs+KKs"` | ❌ Invalid (different ranks) |  |

**Integration with Card/Hand**:

```python
# Parse shorthand → get concrete Hand objects
hero_range = HandRange.from_shorthand("AKs+AQo+22")

# Equity calculations operate on ranges
def calculate_range_equity(hero_range: HandRange, villain_range: HandRange, board: Board):
    """Get equity distribution for hero range vs villain range."""
    result = {}
    for hero_hand in hero_range.hands:
        for villain_hand in villain_range.hands:
            equity = solver.calculate_hand_equity(hero_hand, villain_hand, board)
            result[(hero_hand, villain_hand)] = equity
    
    return result
```

---

## 2. Hand Domain Model

```python
@dataclass(frozen=True)
class Hand:
    """Two-card poker hand (domain model)."""
    card1: Card
    card2: Card
    
    def __post_init__(self):
        """Validate hand has exactly 2 different cards."""
        if self.card1 == self.card2:
            raise ValueError(f"Hand cannot have duplicate cards: {self.card1}")
    
    def to_cards(self) -> List[Card]:
        """Get cards as list."""
        return [self.card1, self.card2]
    
    def to_strings(self) -> tuple[str, str]:
        """Convert to string tuple for transport."""
        return (str(self.card1), str(self.card2))
    
    @staticmethod
    def from_strings(card1_str: str, card2_str: str) -> Optional['Hand']:
        """Parse hand from two card strings."""
        c1 = Card.from_string(card1_str)
        c2 = Card.from_string(card2_str)
        
        if c1 is None or c2 is None:
            return None
        
        try:
            return Hand(card1=c1, card2=c2)
        except ValueError:
            return None
    
    @staticmethod
    def from_tuple(cards: tuple[str, str]) -> Optional['Hand']:
        """Parse hand from tuple of strings."""
        return Hand.from_strings(cards[0], cards[1])
```

**Benefits**:
- ✅ Prevents duplicate cards in hand (validation)
- ✅ Bidirectional conversion (domain ↔ string)
- ✅ Type-safe: Can't accidentally pass single card
- ✅ Works with existing HandRange for shorthand ("AKs") conversion

---

## 3. Board Domain Model

```python
@dataclass(frozen=True)
class Board:
    """0-5 community cards (domain model)."""
    cards: List[Card] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate board state."""
        if not 0 <= len(self.cards) <= 5:
            raise ValueError(f"Board must have 0-5 cards, got {len(self.cards)}")
        
        # Check for duplicates
        card_set = set(self.cards)
        if len(card_set) != len(self.cards):
            raise ValueError("Board cannot have duplicate cards")
    
    def to_strings(self) -> List[str]:
        """Convert to string list for transport."""
        return [str(card) for card in self.cards]
    
    @staticmethod
    def from_strings(card_strings: List[str]) -> Optional['Board']:
        """Parse board from list of card strings."""
        cards = []
        for card_str in card_strings:
            card = Card.from_string(card_str)
            if card is None:
                return None
            cards.append(card)
        
        try:
            return Board(cards=cards)
        except ValueError:
            return None
```

---

## 4. Solver Adapter Pattern

**Create interface abstraction** (independent of PokerKit):

```python
from abc import ABC, abstractmethod
from typing import Dict, List

class PokerSolver(ABC):
    """Abstraction for poker solvers (pluggable)."""
    
    @abstractmethod
    def evaluate_hand(self, hand: Hand, board: Board) -> Optional[int]:
        """Evaluate hand strength (lower = stronger)."""
        pass
    
    @abstractmethod
    def calculate_equity(
        self, 
        hand: Hand, 
        opponent_hands: List[Hand], 
        board: Board
    ) -> Optional[Dict[str, float]]:
        """Calculate equity vs opponent hands."""
        pass
```

**PokerKit Adapter**:

```python
class PokerkitAdapter(PokerSolver):
    """Adapter to use PokerKit library."""
    
    def __init__(self):
        from pokerkit.hands import StandardHighHand
        self.evaluator = StandardHighHand
    
    def evaluate_hand(self, hand: Hand, board: Board) -> Optional[int]:
        """Delegate to PokerKit."""
        pokerkit_hand = [self._to_pokerkit(c) for c in hand.to_cards()]
        pokerkit_board = [self._to_pokerkit(c) for c in board.cards]
        
        # ... PokerKit logic ...
    
    @staticmethod
    def _to_pokerkit(card: Card) -> PokerkitCard:
        """Convert domain Card → PokerKit Card."""
        return PokerkitCard(rank=card.rank.name[0], suit=card.suit.value)
```

**Treys Adapter** (future):

```python
class TreysAdapter(PokerSolver):
    """Adapter to use treys library."""
    
    def __init__(self):
        import treys
        self.evaluator = treys.Evaluator()
    
    def evaluate_hand(self, hand: Hand, board: Board) -> Optional[int]:
        """Delegate to treys."""
        treys_hand = [self._to_treys(c) for c in hand.to_cards()]
        treys_board = [self._to_treys(c) for c in board.cards]
        
        # ... treys logic ...
    
    @staticmethod
    def _to_treys(card: Card) -> int:
        """Convert domain Card → treys card int."""
        return treys.Card.new(str(card))
```

**Benefits**:
- ✅ No DTO changes needed when swapping solvers
- ✅ Easy to test (mock PokerSolver)
- ✅ Library changes are isolated to adapter

---

## 4.5 Range Equity Analysis (Core to GTO)

Hand ranges are **essential** to AoF GTO analysis. The 13×13 matrix analysis uses ranges at scale:

```python
class RangeAnalyzer:
    """Analyzes equity for entire hand ranges."""
    
    def __init__(self, solver: PokerSolver):
        self.solver = solver
    
    def analyze_matrix(
        self, 
        position: Position, 
        num_opponents: int,
        board: Board
    ) -> Dict[str, Dict[str, float]]:
        """
        Analyze complete 13×13 hand matrix.
        
        Returns dict mapping each hand (AKs, KQo, 77, etc.) to:
        {
            "equity": float,
            "ev": float,
            "win_probability": float,
            "combos": int  # Number of ways to make this hand
        }
        
        Used to:
        - Fill matrix cells
        - Display color-coded strength
        - Generate optimal GTO strategy
        """
        ALL_HANDS = self._generate_all_hands()  # 169 unique hands
        result = {}
        
        for hand in ALL_HANDS:
            # For each hand, calculate equity vs optimal opponent range
            opponent_range = self._get_opponent_range(position, num_opponents)
            
            equity = self.solver.calculate_hand_equity(
                hand=hand,
                opponent_range=opponent_range,
                board=board
            )
            
            if equity:
                result[hand.shorthand()] = {
                    "equity": equity['equity'],
                    "ev": equity['ev'],
                    "win_probability": equity['win_prob'],
                    "combos": hand.num_combos()  # 6 for pairs, 4 for suited, 12 for offsuit
                }
        
        return result
    
    @staticmethod
    def _generate_all_hands() -> List[Hand]:
        """Generate all 169 possible two-card combinations.
        
        Structure:
        - 13 pocket pairs (AA, KK, ... 22)
        - 78 unpaired hands (AKs, AKo, AQs, AQo, ..., 32o)
        - Total: 169 unique matrix cells
        
        Each cell represents multiple combo variations:
        - Pairs: 6 combos each (e.g., AA = AsAh, AsAd, AsAc, AhAd, AhAc, AdAc)
        - Suited: 4 combos each (e.g., AKs = AsKs, AhKh, AdKd, AcKc)
        - Offsuit: 12 combos each (e.g., AKo = all 12 cross-suit combos)
        """
        all_hands = []
        
        # Generate all combinations
        for rank1_idx in range(13):
            for rank2_idx in range(13):
                rank1 = RANKS[rank2_idx]
                rank2 = RANKS[rank2_idx]
                
                if rank1_idx == rank2_idx:
                    # Pocket pair
                    for suit1_idx in range(4):
                        for suit2_idx in range(suit1_idx + 1, 4):
                            card1 = Card(rank=rank1, suit=SUITS[suit1_idx])
                            card2 = Card(rank=rank2, suit=SUITS[suit2_idx])
                            all_hands.append(Hand(card1, card2))
                elif rank1_idx > rank2_idx:
                    # Only consider higher rank first to avoid duplicates
                    # Generate both suited and offsuit
                    for suit in [True, False]:  # True=suited, False=offsuit
                        hands = self._generate_rank_combination(rank1, rank2, suited=suit)
                        all_hands.extend(hands)
        
        return all_hands
    
    def get_solver_range(self, position: Position, num_opponents: int) -> HandRange:
        """Get opponent range based on position and game theory.
        
        Example outputs:
        - BTN vs 1 opponent: "22+,A2s+,A9o+,K9s+,QTs+"
        - SB vs 3 opponents: "22+,A5s+,A9o+,K9s+,QTs+,J8s+,97s"
        """
        # Lookup from pre-computed GTO charts
        gto_ranges = {
            (Position.UTG, 1): "22+,A2s+,A9o+,K9s+,KTo+,QTs+,JTs,AJo+",
            (Position.UTG, 2): "22+,A2s+,A8o+,K9s+,KJo+,QTs+,J9s+",
            (Position.UTG, 3): "22+,A3s+,A8o+,K9s+,KJo+,QTs+,J9s+,T8s+",
            (Position.BTN, 1): "22+,A2s+,A7o+,K8s+,KJo+,Q9s+,J8s+,T7s+,96s+,85s+,74s+,64s,53s",
            # More position/opponent combinations...
        }
        
        range_notation = gto_ranges.get((position, num_opponents), "22+,A2s+")
        return HandRange.from_shorthand(range_notation)
```

**Why HandRange is Critical**:

| Feature | Single Hand | Full Range |
|---------|-------------|-----------|
| **Analysis scope** | One specific combo (As, Kh) | All 1,326 possible combos |
| **GTO strategy** | "Does 3♠ 2♥ open UTG?" | "What % of hands open UTG?" |
| **Matrix size** | Single cell | 13×13 = 169 cells |
| **Opponent modeling** | Doesn't make sense | "Opponent opens 22+,A2s+" |
| **Range vs Range equity** | Not applicable | "AKs vs {22+,A5s+}" |
| **Computational cost** | 1 evaluation | 1,326 × opponent_combos evaluations |

---

## 5. Updated DTO Design

**PositionContext with Card/Hand abstraction**:

```python
from dataclasses import dataclass
from typing import Optional
from shared.enums import Position
from shared.models import Card, Hand, Board

@dataclass(frozen=True)
class PositionContext:
    """Pre-flop AoF position analysis."""
    
    position: Position
    num_opponents: int  # 1-3
    heroes_hole_cards: Optional[Hand] = None  # ✅ Hand object, not tuple[str,str]
    pot_size_bb: float = 1.0
```

**Transport Layer** (at API boundary):

```python
# HTTP request comes in as JSON with string cards
@app.post("/analyze")
def analyze(data: dict):
    # Parse strings into domain models
    hand = Hand.from_strings(
        data["heroes_hole_cards"][0], 
        data["heroes_hole_cards"][1]
    )
    
    position_ctx = PositionContext(
        position=Position[data["position"]],
        num_opponents=data["num_opponents"],
        heroes_hole_cards=hand
    )
    
    # Backend uses strong types
    solver = PokerkitAdapter()
    result = solver.evaluate_hand(hand, board)
    
    # Convert back to strings for JSON response
    return {
        "cards": hand.to_strings(),
        "result": result
    }
```

---

## 6. HandRange Integration with DTO Models

**PositionContext Analysis Workflow**:

```python
# 1. User selects position/opponents (PositionContext)
context = PositionContext(
    position=Position.BTN,
    num_opponents=2,  # 3-way
    heroes_hole_cards=None  # Not selected yet
)

# 2. Backend generates opponent range based on GTO
opponent_range = gto_analyzer.get_opponent_range(
    position=Position.UTG,  # Opponent's position
    num_opponents=2,
    action="open"  # UTG opens/folds
)
# opponent_range = HandRange.from_shorthand("22+,A2s+,A9o+,K9s+,...")

# 3. Generate 13×13 matrix 
matrix = {}
for hand_notation in ALL_169_HANDS:
    hand = Hand.from_shorthand(hand_notation)
    equity_vs_range = solver.calculate_hand_equity(
        hand=hand,
        opponent_range=opponent_range,
        board=board
    )
    matrix[hand_notation] = equity_vs_range

# 4. User clicks cell (selects specific hand)
selected_hand = Hand.from_strings("As", "Kd")  # Ace spade, King diamond

# 5. Backend returns detailed analysis for that hand
detail = {
    "hand": selected_hand,
    "vs_opponent_range": opponent_range,
    "equity": 0.65,
    "ev": 2.45,
    "recommendation": "SHOVE"
}
```

**MatrixPayload Integration**:

```python
@dataclass
class MatrixPayload:
    """Complete 13×13 matrix analysis (with range info)."""
    
    hands: Dict[str, HandEvaluation]  # Keys: "AKs", "KQo", "77", etc.
    opponent_range: HandRange  # The range assumed for opponents
    averages: Dict[str, float]  # Average equity, EV across all hands
    metadata: Dict[str, Any]
    
    def get_hand_breakdown(self) -> Dict[str, float]:
        """Get equity breakdown by hand type."""
        pairs = {h: hands[h].equity for h in hands if len(h) == 2 and h[0] == h[1]}
        suited = {h: hands[h].equity for h in hands if 's' in h}
        offsuit = {h: hands[h].equity for h in hands if 'o' in h}
        
        return {
            "pair_avg": sum(pairs.values()) / len(pairs),
            "suited_avg": sum(suited.values()) / len(suited),
            "offsuit_avg": sum(offsuit.values()) / len(offsuit)
        }
```

**Range vs Range Analysis**:

```python
# Advanced GTO analysis
def solve_game(
    hero_position: Position,
    villain_position: Position,
    stack_depth: float,
    blinds: dict
) -> Dict[str, HandRange]:
    """
    Solve for optimal ranges at each position.
    
    Returns:
    {
        "hero_open_range": HandRange,
        "villain_defense_range": HandRange,
        "mutual_equilibrium": bool
    }
    """
    # This is how the original app should compute GTO
    hero_range = HandRange.from_shorthand("22+,A2s+,A9o+,K9s+,...")
    villain_range = HandRange.from_shorthand("22+,A5s+,A8o+,...")
    
    # Compute mutual best responses iteratively
    # (simplified - actual solver is complex)
    for iteration in range(100):
        hero_range = compute_best_response(hero_range, villain_range)
        villain_range = compute_best_response(villain_range, hero_range)
    
    return {
        "hero_open_range": hero_range,
        "villain_defense_range": villain_range,
        "mutual_equilibrium": check_equilibrium(hero_range, villain_range)
    }
```

---

## 6.5 Solver Library Abstraction Layer

The domain model Card is **library-agnostic**. To integrate with different poker solver libraries (PokerKit, Treys, PyPokerEngine, custom solvers), use the **CardAdapter** pattern.

### Why This Matters

Different libraries use different card formats:
```python
# Domain Model (consistent across codebase)
card = Card(rank=Rank.ACE, suit=Suit.SPADES)

# PokerKit format
pokerkit_str = "As"  # String format

# Treys format  
treys_int = 12  # Integer 0-51 index

# PyPokerEngine format
pypoker_tuple = ('A', 'S')  # Tuple of rank/suit

# Without abstraction layer:
# - Solver-specific code scattered throughout domain logic
# - Hard to swap libraries
# - Type conversions leak into business logic
#
# With CardAdapter:
# - Single point of conversion
# - Libraries isolated behind adapter
# - Easy to add new solvers
```

### CardAdapter Implementation

See **01_DOMAIN_MODELS/01_DOMAIN_Card.md** for complete `CardAdapter` class including:
- `to_pokerkit()` / `from_pokerkit()` - Direct string format
- `to_treys()` / `from_treys()` - Integer index (0-51)
- `to_pypoker()` / `from_pypoker()` - Tuple format  
- `to_json()` / `from_json()` - Serialization
- Custom solver adapters

### Usage Patterns

**Pattern 1: Hand Conversion to Solver**
```python
from shared.domain.hand import Hand
from shared.domain.card import CardAdapter

# Domain hand
hand = HandRange.from_shorthand("AKs")

# For each combo, convert to solver format
for combo in hand.to_strings():  # [('As', 'Ks'), ...]
    card1_str, card2_str = combo
    card1 = Card.from_string(card1_str)  
    card2 = Card.from_string(card2_str)
    
    # Use adapter for library-specific format
    solver_hand = [
        CardAdapter.to_treys(card1),
        CardAdapter.to_treys(card2)
    ]
    equity = treys_solver.evaluate(solver_hand)
```

**Pattern 2: Range Conversion for Analysis**
```python
def analyze_range_with_solver(
    range_obj: HandRange,
    board: Board,
    solver_type: str = "pokerkit"
) -> Dict[str, float]:
    """Converts entire range to solver format for analysis."""
    
    result = {}
    
    # Create adapter based on solver type
    if solver_type == "pokerkit":
        adapter = CardAdapter
    elif solver_type == "custom":
        adapter = CustomSolverAdapter
    else:
        raise ValueError(f"Unknown solver: {solver_type}")
    
    # Convert all hands to board and combos
    board_strs = [adapter.convert(c) for c in board.cards]
    
    for hand in range_obj.hands:
        card1_str, card2_str = hand.to_strings()
        hand_strs = [
            adapter.convert(Card.from_string(card1_str)),
            adapter.convert(Card.from_string(card2_str))
        ]
        
        # Call solver with converted format
        equity = solver.evaluate(hand_strs, board_strs)
        result[hand.shorthand()] = equity
    
    return result
```

**Pattern 3: Custom Solver Adapter**
```python
class CustomSolverAdapter(CardAdapter):
    """Adapter for custom poker solver with unique format."""
    
    @staticmethod
    def convert(card: Card) -> str:
        """Convert to custom format: 'ASPAD', 'KHEART', etc."""
        suit_map = {
            Suit.SPADES: 'PAD',
            Suit.HEARTS: 'HEART',
            Suit.DIAMONDS: 'DIAMOND',
            Suit.CLUBS: 'CLUB'
        }
        return f"{card.rank.char}{suit_map[card.suit]}"

# Usage
adapter = CustomSolverAdapter()
for hand in range_obj.hands:
    card1, card2 = hand.to_strings()
    custom_format = [
        adapter.convert(Card.from_string(card1)),
        adapter.convert(Card.from_string(card2))
    ]
    equity = custom_solver.evaluate(custom_format)
```

### Library Compatibility Chart

| Library | Format | Adapter | Speed | Notes |
|---------|--------|---------|-------|-------|
| **PokerKit** | String `"As"` | O(1) - passthrough | ⚡ Fast | Already what we use |
| **Treys** | Integer 0-51 | O(1) - arithmetic | ⚡⚡ Fastest | Popular in bots |
| **PyPokerEngine** | Tuple `('A','S')` | O(1) - map | ⚡ Fast | Good for simulation |
| **Custom** | Varies | Custom adapter | 🟡 Varies | Client-defined |

### Performance Notes

- **Conversion cost**: O(1) per card (arithmetic or map lookup)
- **Batch conversion**: O(n) where n = number of cards
- **No performance penalty** vs direct library usage
- **Benefit**: Can swap libraries without rewriting domain logic

---

## 7. Migration Path

### Phase 1: Add abstraction (non-breaking)
```
PositionContext:
  - Keep heroes_hole_cards as tuple[str,str] (backward compat)
  - Add heroes_hand: Optional[Hand] (new field)
```

### Phase 2: Update backend
```
- Analyzer accepts both Hand and tuple[str,str]
- Adapters handle conversion
```

### Phase 3: Deprecate strings
```
- Mark tuple[str,str] as deprecated
- Recommend Hand objects
```

### Phase 4: Remove strings
```
- Only Hand objects in DTOs
- Solvers work with strong types
```

---

## Comparison: Before vs After

### ❌ Before (Current)
```python
heroes_hole_cards: tuple[str, str]  # No validation
board_state: Optional[BoardState]   # Mutable, no type safety

# Backend
def evaluate(hole_cards: List[str], board: List[str]):
    hero = [card_name_to_pokerkit(c) for c in hole_cards]
    board = [card_name_to_pokerkit(c) for c in board]  # Manual conversion
    # ...
```

### ✅ After (Proposed)
```python
heroes_hole_cards: Optional[Hand]   # Type-safe, validated at construction
board: Optional[Board]               # Validated, immutable

# Backend
def evaluate(hand: Hand, board: Board):
    # Use domain models directly
    result = solver.evaluate_hand(hand, board)  # Solver handles conversion
    # ...
```

---

## Summary

| Aspect | Current | Proposed |
|--------|---------|----------|
| Card type | `str` | `Card` (enum-based) |
| Hand type | `tuple[str,str]` | `Hand` (validated) |
| Hand range type | List of tuples | `HandRange` (parsed from shorthand) |
| Board type | `BoardState` (mutable) | `Board` (immutable) |
| Range parsing | Ad-hoc string split | Declarative shorthand ("AKs+", "22+") |
| Matrix generation | Manual loop over hands | `RangeAnalyzer.analyze_matrix()` |
| Solver coupling | Tight (PokerKit strings) | Loose (Adapter pattern) |
| Range vs Range equity | Not supported | Built-in via `solver.calculate_range_equity()` |
| GTO strategy export | Strings | `HandRange` objects with shorthand |
| Solver swap cost | Rewrite DTOs + backend | Change adapter only |

---

## Critical Insight: Hand Ranges as Core Domain Model

**Initial Oversight**: My first design focused on individual cards (`Card`) and hands (`Hand`), but **hand ranges** are the true core abstraction for poker GTO analysis.

**Why Hand Ranges Matter**:

1. **GTO is about distributions, not specifics**
   - Question: "Is AK good?" → No, meaningless for GTO
   - Real question: "What % of AK combos should I play?" → GTO answer

2. **13×13 Matrix is fundamentally a range analysis**
   ```
   Matrix cell (e.g., "AKs") = 4 combo variations = 1 hand in range notation
   Complete 13×13 = 169 cells = all hands = complete range
   ```

3. **Opponent modeling requires ranges**
   - Single hand: "Opponent has AK" → incomplete
   - Range: "Opponent has {22+,A2s+,A9o+,...}" → complete strategy

4. **EV calculations are range-based**
   - My hand equity vs one opponent hand = easy
   - My hand equity vs opponent's RANGE = Monte Carlo across their hands

**Implementation Priority**:
```
1. ✅ Card (already planned)
2. ✅ Hand (already planned)  
3. ❌ ERROR: Forgot HandRange (CRITICAL!)
4. Board (secondary)

Corrected:
1. ✅ Card (immutable, enum-based)
2. ✅ HandRange (shorthand notation parsing)
   - "AKs", "22+", "A5s-A2s", "AKs+AQo+22"
   - Expands to all concrete Hand objects
3. ✅ Hand (represents 2 cards, part of range)
4. Board (board state, if needed)
```

**HandRange is the Bridge**:
- **Domain**: Represents poker strategy (shorthand notation)
- **Solver interface**: `solver.calculate_range_equity(hand, opponent_range, board)`
- **DTOs**: `MatrixPayload` includes `opponent_range: HandRange`
- **GTO output**: Optimal strategies as `HandRange` objects

**Example: Why HandRange Design Matters**:

```python
# ❌ Without HandRange (current DTOs):
matrix_payload = {
    "AKs": {"equity": 0.68, ...},
    "KQo": {"equity": 0.45, ...},
    # ... 169 more cells
    "opponent_assumed": "RFI 22+ AK AQ"  # Unstructured string!
}

# ✅ With HandRange (proposed):
matrix_payload = MatrixPayload(
    hands={
        "AKs": HandEvaluation(...),
        "KQo": HandEvaluation(...),
        # ... 169 more
    },
    opponent_range=HandRange.from_shorthand("22+,A2s+,A9o+,K9s+,..."),
    # Type-safe, parseable, structured
)

# Usage:
for hand_in_range in matrix_payload.opponent_range.hands:
    # Can iterate opponent range hands
    # Can export range as string: "22+,A2s+,..."
    # Can compute range statistics
    pass
```

**Answer to "Why did you miss this?"**: 
Ranges are so fundamental to poker that the original `hand_range.py` module was already implemented. I focused on individual card representation without realizing that **HandRange should be a first-class domain model**, not just a utility function. The real insight is that GTO analysis is about computing strategies as `HandRange` objects, not about evaluating single hands.
| Solver swap cost | Rewrite DTOs + backend | Change adapter only |
| Type safety | ❌ Low | ✅ High |
| IDE hints | ❌ None | ✅ Enum values |
| Validation | ❌ Runtime | ✅ Construction time |
| Test mocking | ❌ Hard | ✅ Easy |

