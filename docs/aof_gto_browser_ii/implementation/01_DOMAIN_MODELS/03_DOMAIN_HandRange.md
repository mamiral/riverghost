# Domain Model: HandRange

## Purpose

Represents a **distribution of hands** parsed from shorthand notation (e.g., "AKs+", "22+", "A5s-A2s", "AKs+AQo+22").

**Depends on**: Hand (which depends on Card)

Critical for GTO analysis:
- ✅ Parses professional poker notation
- ✅ Represents opponent strategy ("UTG opens 22+,A2s+,...")
- ✅ Enables range vs range equity calculations
- ✅ Foundation of 13×13 matrix analysis

---

## Shorthand Notation Reference

| Notation | Meaning | Count | Example |
|----------|---------|-------|---------|
| `"AKs"` | Single hand, all 4 suited combos | 4 | A♠K♠, A♥K♥, A♦K♦, A♣K♣ |
| `"AKo"` | Single hand, all 12 offsuit combos | 12 | A♠K♥, A♠K♦, ... (all cross-suit) |
| `"AA"` | Pocket pair, all 6 combos | 6 | A♠A♥, A♠A♦, ... |
| `"22+"` | Range of pairs (22 through AA) | 78 | 22, 33, 44, ..., KK, AA |
| `"AKs+"` | Connected suited (AKs, AQs) | 8 | AKs (4) + AQs (4) |
| `"A5s-A2s"` | Descending range (A5s down to A2s) | 16 | A5s, A4s, A3s, A2s (4 combos each) |
| `"AKs+AQo+22"` | Union notation (union of multiple) | Variable | Union of three ranges |
| `"AKs,AQo,22"` | Alternative union syntax | Variable | Same as above |

---

## Hand Expansion Algorithm (Parsing & Combinatorial)

### Overview

Converting shorthand notation to Hand objects involves **three phases**:

1. **Parsing Phase**: Decompose notation string into components (single, range, plus)
2. **Expansion Phase**: Generate individual hands with all suit combinations
3. **Deduplication Phase**: Remove duplicates and validate

### Phase 1: Parsing Strategy

The parser identifies which type of notation and delegates to the appropriate sub-parser:

```
Input: "A5s-A2s,22+,AKo"
         ↓
Split on comma → ["A5s-A2s", "22+", "AKo"]
         ↓
For each component:
  "A5s-A2s"  → Detect '-' → _parse_range()
  "22+"      → Detect '+' → _parse_plus()
  "AKo"      → No special chars → _parse_single()
         ↓
Combine all hands → Deduplicate → HandRange object
```

### Phase 2: Expansion - Single Hand

When parsing a single hand like "AKs" or "22", expand to all suit combinations:

#### Pocket Pairs (2 characters: "AA", "22", etc.)

**Structure**: Same rank, all different suits

**Combos Generated**: **6 unique combos** (unordered pairs)

```
Pair "AA":
  Suits: [Spades, Hearts, Diamonds, Clubs]
  
  Generate pairs from 4 suits (unordered, so order matters):
  1. As Ah  (Spades, Hearts)
  2. As Ad  (Spades, Diamonds)
  3. As Ac  (Spades, Clubs)
  4. Ah Ad  (Hearts, Diamonds)
  5. Ah Ac  (Hearts, Clubs)
  6. Ad Ac  (Diamonds, Clubs)
  
  Algorithm: 4 choose 2 = 6 combos
  
  Python loop:
    for i, suit1 in enumerate(suits):
        for suit2 in suits[i+1:]:  # Start after suit1 to avoid duplicates
            pair = (suit1, suit2)
```

#### Suited Hands (3 characters ending in 's': "AKs", "QJo", etc.)

**Structure**: Two different ranks, **same suit** for all pairs

**Combos Generated**: **4 combos** (one per suit)

```
"AKs" (Ace-King suited):
  Generate all 4 suit matches (As-Ks, Ah-Kh, Ad-Kd, Ac-Kc):
  1. As Ks  (both Spades)
  2. Ah Kh  (both Hearts)
  3. Ad Kd  (both Diamonds)
  4. Ac Kc  (both Clubs)
  
  Algorithm: 4 suits = 4 combos
  
  Python loop:
    for suit in [Spades, Hearts, Diamonds, Clubs]:
        combo = (Rank1(suit), Rank2(suit))
```

**Note**: "AKs" and "KAs" are the **same hand** - suit matching determines suitedness, not rank order.

#### Offsuit Hands (3 characters ending in 'o': "AKo", "QJo", etc.)

**Structure**: Two different ranks, **different suits** (any except both same)

**Combos Generated**: **12 combos** (all cross-suit pairs)

```
"AKo" (Ace-King offsuit):
  Generate all suit combinations except matching suits:
  1. As Kh   2. As Kd   3. As Kc
  4. Ah Ks   5. Ah Kd   6. Ah Kc
  7. Ad Ks   8. Ad Kh   9. Ad Kc
  10. Ac Ks  11. Ac Kh  12. Ac Kd
  
  Algorithm: 4 × 4 - 4 (excluding matching suits) = 12 combos
  
  Python loop:
    for suit1 in [Spades, Hearts, Diamonds, Clubs]:
        for suit2 in [Spades, Hearts, Diamonds, Clubs]:
            if suit1 != suit2:  # Different suits only
                combo = (Rank1(suit1), Rank2(suit2))
```

**Critical Insight**: Order matters for offsuit! (As Kh ≠ Kh As in our internal representation, but they map to the same hand type in shorthand)

### Phase 3: Expansion - Range Notation

#### Dash Range (descending pairs or connecting cards)

**Notation**: "A5s-A2s" or "22-99"

**Algorithm**:
1. Split on '-': start, end
2. Identify pattern type (high-card match vs pair)
3. Iterate through ranks from end to start
4. For each rank, expand as single hand

```
"A5s-A2s" expansion:
  Start: "A5s", End: "A2s"
  
  Pattern: Both start with 'A' → high-card pattern
  Ranks to include: [5, 4, 3, 2] (descending from 5 to 2)
  Suited: yes (detected from 's')
  
  For each rank:
    "A5s" → Expand to 4 combos
    "A4s" → Expand to 4 combos
    "A3s" → Expand to 4 combos
    "A2s" → Expand to 4 combos
  
  Total: 16 combos
  
  Result hands:
    [Hand(As, 5s), Hand(Ah, 5h), Hand(Ad, 5d), Hand(Ac, 5c),
     Hand(As, 4s), Hand(Ah, 4h), Hand(Ad, 4d), Hand(Ac, 4c),
     Hand(As, 3s), Hand(Ah, 3h), Hand(Ad, 3d), Hand(Ac, 3c),
     Hand(As, 2s), Hand(Ah, 2h), Hand(Ad, 2d), Hand(Ac, 2c)]
```

```
"22-99" expansion:
  Start: "22", End: "99"
  
  Pattern: Pair range
  Pairs to include: [22, 33, 44, 55, 66, 77, 88, 99]
  
  For each pair:
    "22" → Expand to 6 combos
    "33" → Expand to 6 combos
    ...
    "99" → Expand to 6 combos
  
  Total: 8 pairs × 6 combos = 48 combos
```

#### Plus Notation (expanding upward)

**Notation**: "22+" (all pairs) or "AKs+" (broadway suited hands)

**Algorithm**:
1. Extract base hand
2. Determine range end (Ace for pairs, Ace for high cards)
3. Iterate from base up to max rank
4. For each, expand as single hand

```
"22+" expansion (all pocket pairs):
  Base: "22"
  Range: [22, 33, 44, 55, 66, 77, 88, 99, TT, JJ, QQ, KK, AA]
  
  For each pair:
    "22" → 6 combos
    "33" → 6 combos
    ...
    "AA" → 6 combos
  
  Total: 13 pairs × 6 combos = 78 combos
```

```
"AKs+" expansion (broadway connectors):
  Base: "AK"
  Suited: yes
  Range: [K, Q, J, T] (descending from K)
  
  For each rank:
    "AKs" → 4 combos
    "AQs" → 4 combos
    "AJs" → 4 combos
    "ATs" → 4 combos
  
  Total: 4 hands × 4 combos = 16 combos
```

### Phase 4: Deduplication & Union Handling

When multiple components are combined (e.g., "AKs+AQo+22"):

```
Components: ["AKs+", "AQo+", "22"]

Expand each:
  "AKs+"  → [AKs(4), AQs(4), AJs(4), ATs(4)] = 16 combos
  "AQo+"  → [AQo(12), AJo(12), ATo(12), A9o(12)] = 48 combos
  "22"    → [22(6)] = 6 combos

Combined list: [... 16 AKs/AQs/AJs/ATs combos ..., 
                ... 48 AQo/AJo/ATo/A9o combos ...,
                ... 6 pairs of 22 ...]

Deduplication: Keep only unique hands
  - Sets help: set(all_hands) removes duplicates automatically
  - list(dict.fromkeys(hands)) maintains order for Python < 3.7
  
Final HandRange:
  - hands: List[Hand] with ~70 unique hands (70 × average combos)
  - shorthand: "AKs+AQo+22" (for round-trip serialization)
```

### Expansion Examples - Complete Walkthrough

#### Example: "A5s-A2s"

```
Input: "A5s-A2s"

Step 1: Detect '-' → _parse_range()
Step 2: Split → start="A5s", end="A2s"
Step 3: Extract pattern → first_rank='A', suited=True
Step 4: Determine rank range → [5, 4, 3, 2]
Step 5: For each rank, expand:
  
  rank=5:
    "A5s" → _parse_single()
    Generate As 5s, Ah 5h, Ad 5d, Ac 5c (4 combos)
  
  rank=4:
    "A4s" → _parse_single()
    Generate As 4s, Ah 4h, Ad 4d, Ac 4c (4 combos)
  
  rank=3:
    "A3s" → _parse_single()
    Generate As 3s, Ah 3h, Ad 3d, Ac 3c (4 combos)
  
  rank=2:
    "A2s" → _parse_single()
    Generate As 2s, Ah 2h, Ad 2d, Ac 2c (4 combos)

Step 6: Combine all
  hands = [As5s, Ah5h, Ad5d, Ac5c, 
           As4s, Ah4h, Ad4d, Ac4c,
           As3s, Ah3h, Ad3d, Ac3c,
           As2s, Ah2h, Ad2d, Ac2c]
  
Step 7: Create HandRange
  HandRange(hands=hands, shorthand="A5s-A2s")
  
Result:
  - size() = 16 (four A-X combos)
  - num_combos() = 16 (4 combos each hand)
```

#### Example: "22+"

```
Input: "22+"

Step 1: Detect '+' at end → _parse_plus()
Step 2: Extract base → "22"
Step 3: Extract start_rank → Rank.TWO
Step 4: Build rank range → All ranks from TWO to ACE
Step 5: For each rank, generate pair:
  
  Rank.TWO:   "22" → 6 combos
  Rank.THREE: "33" → 6 combos
  ...
  Rank.ACE:   "AA" → 6 combos

Step 6: Combine
  hands = [all combos of 22, 33, 44, 55, 66, 77, 88, 99, TT, JJ, QQ, KK, AA]
  Total: 78 hands × 6 combos = 468 combos (but hands.size() = 78)

Step 7: Create HandRange
  HandRange(hands=hands, shorthand="22+")

Result:
  - size() = 78 (78 pocket pair types)
  - num_combos() = 468 (13 pairs × 6 combos each)
```

### Key Design Decisions

1. **Combo Counts Are Fixed**:
   - Pairs: always 6
   - Suited: always 4
   - Offsuit: always 12
   - This is mathematical and immutable

2. **Order Preservation**:
   - Hands kept in expansion order (not alphabetically sorted)
   - Helps for debugging and consistency with source notation

3. **Shorthand Preservation**:
   - Original notation stored for round-trip serialization
   - `to_shorthand()` can recover notation if needed

4. **Deduplication Strategy**:
   - Used when parsing unions (same hand might appear in multiple parts)
   - Example: "AKs+AQs" would include AQs twice if not deduplicated

---

## Specification

```python
from dataclasses import dataclass, field
from typing import Optional, List, Set
from shared.domain.hand import Hand

@dataclass(frozen=True)
class HandRange:
    """Distribution of poker hands (immutable, validated)."""
    
    hands: List[Hand] = field(default_factory=list)
    shorthand: Optional[str] = None  # Original notation for round-trip
    
    def __post_init__(self):
        """Validate range has no duplicates."""
        if len(set(self.hands)) != len(self.hands):
            raise ValueError("HandRange cannot contain duplicate hands")
        if not self.hands:
            raise ValueError("HandRange must contain at least one hand")
    
    def __str__(self) -> str:
        """String representation (shorthand if available)."""
        if self.shorthand:
            return self.shorthand
        return self.to_shorthand()
    
    def size(self) -> int:
        """Number of hand types in range."""
        return len(self.hands)
    
    def num_combos(self) -> int:
        """Total combos across all hands."""
        return sum(hand.num_combos() for hand in self.hands)
    
    def contains(self, hand: Hand) -> bool:
        """Check if hand is in this range."""
        return hand in self.hands
    
    def to_strings(self) -> List[tuple[str, str]]:
        """Convert to list of card string tuples for transport."""
        return [hand.to_strings() for hand in self.hands]
    
    def to_shorthand(self) -> str:
        """Convert to shorthand notation string.
        
        Returns best-effort notation (may not round-trip if constructed manually).
        """
        if self.shorthand:
            return self.shorthand
        
        # Group hands by type
        pairs = []
        suited = []
        offsuit = []
        
        for hand in self.hands:
            if hand.is_pair():
                pairs.append(hand)
            elif hand.is_suited():
                suited.append(hand)
            else:
                offsuit.append(hand)
        
        components = []
        
        # Format pairs
        if pairs:
            pairs_shorthand = ",".join(h.to_shorthand() for h in pairs)
            components.append(pairs_shorthand)
        
        # Format suited
        if suited:
            suited_shorthand = ",".join(h.to_shorthand() for h in suited)
            components.append(suited_shorthand)
        
        # Format offsuit
        if offsuit:
            offsuit_shorthand = ",".join(h.to_shorthand() for h in offsuit)
            components.append(offsuit_shorthand)
        
        return "+".join(components)
    
    @staticmethod
    def from_shorthand(notation: str) -> Optional['HandRange']:
        """Parse shorthand notation into HandRange.
        
        Supports:
        - "AKs" - single hand
        - "22+" - pair range
        - "A5s-A2s" - descending range
        - "AKs+AQo+22" - union of multiple
        
        Returns None if notation is invalid.
        """
        if not notation:
            return None
        
        try:
            hands = HandRange._parse_notation(notation)
            if not hands:
                return None
            
            # Remove duplicates, maintain order
            unique_hands = list(dict.fromkeys(hands))
            
            return HandRange(hands=unique_hands, shorthand=notation)
        except Exception:
            return None
    
    @staticmethod
    def _parse_notation(notation: str) -> Optional[List[Hand]]:
        """Parse notation string into list of Hand objects.
        
        Internal method - handles:
        - Union: "AKs+AQo+22"
        - Single: "AKs", "22", "AKo"
        - Range: "A5s-A2s", "22-99"
        - Plus: "AKs+", "22+"
        """
        all_hands = []
        
        # Split by '+' for union (careful: also used for plus notation)
        # Strategy: identify components by looking for range indicators
        components = notation.replace(',', '+').split('+')
        
        for component in components:
            component = component.strip()
            if not component:
                continue
            
            if '-' in component:
                # Range notation: "A5s-A2s" or "22-99"
                hands = HandRange._parse_range(component)
            else:
                # Single hand or plus notation
                if component.endswith('+'):
                    # Plus notation: "AKs+" or "22+"
                    hands = HandRange._parse_plus(component)
                else:
                    # Single hand: "AKs", "22", "AKo"
                    hands = HandRange._parse_single(component)
            
            if hands:
                all_hands.extend(hands)
        
        return all_hands if all_hands else None
    
    @staticmethod
    def _parse_single(component: str) -> Optional[List[Hand]]:
        """Parse single hand or hand type like 'AKs', '22', 'AKo'."""
        component = component.strip()
        
        if len(component) == 2:
            # Pocket pair: "22", "AA"
            # Generate all 6 combos
            hands = []
            rank_str = component[0]
            
            from shared.domain.card import Rank, Suit
            rank = _rank_from_char(rank_str)
            if not rank:
                return None
            
            suits = list(Suit)
            for i, suit1 in enumerate(suits):
                for suit2 in suits[i+1:]:
                    from shared.domain.card import Card
                    card1 = Card(rank=rank, suit=suit1)
                    card2 = Card(rank=rank, suit=suit2)
                    hand = Hand(card1=card1, card2=card2)
                    hands.append(hand)
            return hands
        
        elif len(component) == 3 and component[2] in 'so':
            # Two-card hand: "AKs", "AKo"
            rank1_str = component[0]
            rank2_str = component[1]
            suited = component[2] == 's'
            
            from shared.domain.card import Rank, Card, Suit
            rank1 = _rank_from_char(rank1_str)
            rank2 = _rank_from_char(rank2_str)
            
            if not rank1 or not rank2:
                return None
            
            hands = []
            suits = list(Suit)
            
            if suited:
                # All 4 suited combos
                for suit in suits:
                    card1 = Card(rank=rank1, suit=suit)
                    card2 = Card(rank=rank2, suit=suit)
                    hand = Hand(card1=card1, card2=card2)
                    hands.append(hand)
            else:
                # All 12 offsuit combos
                for suit1 in suits:
                    for suit2 in suits:
                        if suit1 != suit2:
                            card1 = Card(rank=rank1, suit=suit1)
                            card2 = Card(rank=rank2, suit=suit2)
                            hand = Hand(card1=card1, card2=card2)
                            hands.append(hand)
            
            return hands
        
        return None
    
    @staticmethod
    def _parse_range(component: str) -> Optional[List[Hand]]:
        """Parse range like 'A5s-A2s' or '22-99'."""
        parts = component.split('-')
        if len(parts) != 2:
            return None
        
        start_str, end_str = parts[0].strip(), parts[1].strip()
        
        # Handle A5s-A2s style
        if start_str[0] == end_str[0]:  # Same first rank
            first_rank = start_str[0]
            start_rank = _rank_from_char(start_str[1] if len(start_str) > 1 else start_str[0])
            end_rank = _rank_from_char(end_str[1] if len(end_str) > 1 else end_str[0])
            suited = start_str.endswith('s') if len(start_str) > 2 else False
            
            if not start_rank or not end_rank:
                return None
            
            all_hands = []
            from shared.domain.card import Rank
            ranks = [r for r in Rank if end_rank.value <= r.value <= start_rank.value]
            
            for rank in ranks:
                # Generate combos for each
                hand_type = f"{first_rank}{_char_from_rank(rank)}{'s' if suited else 'o'}"
                hands = HandRange._parse_single(hand_type)
                if hands:
                    all_hands.extend(hands)
            
            return all_hands
        
        return None
    
    @staticmethod
    def _parse_plus(component: str) -> Optional[List[Hand]]:
        """Parse plus notation like 'AKs+' or '22+'."""
        base = component[:-1]  # Remove '+'
        
        # AKs+ means AKs, AQs
        if len(base) == 3 and base[2] in 'so':
            rank1 = _rank_from_char(base[0])
            rank2 = _rank_from_char(base[1])
            suited = base[2] == 's'
            
            if not rank1 or not rank2:
                return None
            
            all_hands = []
            from shared.domain.card import Rank
            
            # Generate AKs, AQs, AAs
            for r in Rank:
                if r.value >= rank2.value:
                    hand_type = f"{base[0]}{_char_from_rank(r)}{'s' if suited else 'o'}"
                    hands = HandRange._parse_single(hand_type)
                    if hands:
                        all_hands.extend(hands)
            
            return all_hands
        
        # 22+ means all pairs
        elif len(base) == 2:
            all_hands = []
            from shared.domain.card import Rank
            
            start_rank = _rank_from_char(base[0])
            if not start_rank:
                return None
            
            for r in Rank:
                if r.value >= start_rank.value:
                    pair_str = f"{r.char}{r.char}"
                    hands = HandRange._parse_single(pair_str)
                    if hands:
                        all_hands.extend(hands)
            
            return all_hands
        
        return None
    
    @staticmethod
    def union(*ranges: 'HandRange') -> 'HandRange':
        """Create union of multiple ranges (remove duplicates)."""
        all_hands = []
        for r in ranges:
            all_hands.extend(r.hands)
        
        unique_hands = list(dict.fromkeys(all_hands))
        return HandRange(hands=unique_hands, shorthand=None)
    
    @staticmethod
    def intersection(*ranges: 'HandRange') -> 'HandRange':
        """Create intersection of multiple ranges."""
        if not ranges:
            raise ValueError("Must provide at least one range")
        
        hand_sets = [set(r.hands) for r in ranges]
        common = hand_sets[0]
        for hand_set in hand_sets[1:]:
            common &= hand_set
        
        if not common:
            raise ValueError("Ranges have no intersection")
        
        return HandRange(hands=list(common), shorthand=None)
    
    def get_subrange(self, shorthand: str) -> Optional['HandRange']:
        """Get specific hands from range.
        
        Example: range.get_subrange("AKs") returns just AKs hands
        """
        subrange = HandRange.from_shorthand(shorthand)
        if not subrange:
            return None
        
        filtered = [h for h in subrange.hands if h in self.hands]
        if not filtered:
            return None
        
        return HandRange(hands=filtered, shorthand=shorthand)

# Helper functions
def _rank_from_char(char: str) -> Optional['Rank']:
    """Convert char to Rank."""
    from shared.domain.card import Rank
    
    char = char.upper()
    map_ = {
        '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
        '6': Rank.SIX, '7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE,
        'T': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN, 'K': Rank.KING, 'A': Rank.ACE
    }
    return map_.get(char)

def _char_from_rank(rank: 'Rank') -> str:
    """Convert Rank to char."""
    return rank.char
```

---

## Fields

| Field | Type | Notes |
|-------|------|-------|
| `hands` | `List[Hand]` | All Hand objects in range (no duplicates) |
| `shorthand` | `Optional[str]` | Original notation (for round-trip serialization) |

---

## Factory Methods

| Method | Input | Returns | Notes |
|--------|-------|---------|-------|
| `HandRange.from_shorthand()` | `"AKs+"`, `"22+"`, `"A5s-A2s"` | `HandRange` or `None` | Robust parsing |
| `to_shorthand()` | — | `str` | Best-effort notation |
| `to_strings()` | — | `List[tuple[str,str]]` | For DTO transport |

---

## Helper Methods

| Method | Returns | Examples |
|--------|---------|----------|
| `size()` | `int` | Number of hand types |
| `num_combos()` | `int` | Total combos (sum of all hands) |
| `contains(hand)` | `bool` | Is hand in range? |
| `union(other_ranges)` | `HandRange` | Combine multiple ranges |
| `intersection(other_ranges)` | `HandRange` | Common hands only |
| `get_subrange(shorthand)` | `HandRange` | Extract subset |

---

## Usage Examples

### Example 1: Parse Simple Notation
```python
# Single hand: 4 combos
ak_suited = HandRange.from_shorthand("AKs")
assert ak_suited.size() == 4
assert ak_suited.num_combos() == 4

# Pocket pair: 6 combos
aces = HandRange.from_shorthand("AA")
assert aces.size() == 6
assert aces.num_combos() == 6
```

### Example 2: Parse Plus Notation
```python
# All pairs: 78 combos
all_pairs = HandRange.from_shorthand("22+")
assert all_pairs.size() == 78

# Broadway pairs: AKs, AQs, AJs, ATs, KQs, KJs, KTs
broadway = HandRange.from_shorthand("AKs+")
assert broadway.size() == 4  # AKs, AQs
```

### Example 3: Parse Range Notation
```python
# A5s down to A2s: 16 combos
ax_suited = HandRange.from_shorthand("A5s-A2s")
assert ax_suited.size() == 16
assert ax_suited.num_combos() == 16
```

### Example 4: Hand Expansion Details
```python
# See step-by-step expansion
range_obj = HandRange.from_shorthand("A5s-A2s")

# Inspect first few hands
first_hand = range_obj.hands[0]  # As 5s
print(f"First hand: {first_hand.to_shorthand()}")  # "A5s"

# Get all hands at specific rank pair
as_hands = [h for h in range_obj.hands if h.card1.rank == Rank.ACE and h.card2.rank == Rank.FIVE]
print(f"A5 combos: {len(as_hands)}")  # 4 (one per suit)

# All ace-x suited hands
ace_suited = [h for h in range_obj.hands if h.card1.rank == Rank.ACE]
print(f"Ace-suited combos: {len(ace_suited)}")  # 16 (A5s, A4s, A3s, A2s × 4 suits)

# Convert back to shorthand
original = range_obj.to_shorthand()  # "A5s-A2s" (preserved)
```

### Example 5: Union Notation (GTO Strategy)
```python
# UTG opening range: pairs + broadway + A5s+
utg_range = HandRange.from_shorthand("22+,A5s+,A9o+,K9s+,KTo+,QTs+,JTs+")
assert utg_range.size() > 30  # Many hands

# BTN opening range (wider)
btn_range = HandRange.from_shorthand("22+,A2s+,K8s+,Q9s+,J9s+,T9s,A8o+,K9o+,QTo+,JTo")
assert btn_range.size() > utg_range.size()
```

### Example 6: Range vs Range Analysis
```python
def calc_matrix_equity(
    hero_range: HandRange,
    villain_range: HandRange,
    solver: PokerSolver
) -> Dict[str, float]:
    """Calculate equity for range vs range.
    
    Each cell is weighted by combo count.
    """
    total_equity = 0
    total_combos = 0
    
    for hero_hand in hero_range.hands:
        for villain_hand in villain_range.hands:
            equity = solver.calculate_hand_equity(hero_hand, villain_hand)
            combos = hero_hand.num_combos() * villain_hand.num_combos()
            
            total_equity += equity * combos
            total_combos += combos
    
    return {
        "overall_equity": total_equity / total_combos,
        "hero_range_size": hero_range.size(),
        "villain_range_size": villain_range.size(),
        "total_combos": total_combos
    }

# Example
btn_opens = HandRange.from_shorthand("22+,A2s+,K8s+,Q9s+,J9s+,T9s")
bb_defends = HandRange.from_shorthand("22+,A2s+,K8s+,Q9s+,JTs+")

equity = calc_matrix_equity(btn_opens, bb_defends, solver)
```

### Example 6: GTO Strategy Representation
```python
# Instead of: "play these specific hands"
# Use: "play this range"

class GTOStrategy:
    position: Position
    action: str  # "open", "defend", "3bet"
    range: HandRange  # Type-safe range representation
    
    def __str__(self):
        return f"{self.position} {self.action}: {self.range}"

# Example
utg_open = GTOStrategy(
    position=Position.UTG,
    action="open",
    range=HandRange.from_shorthand("22+,A5s+,A9o+,K9s+,KTo+,QTs+,JTs+")
)

print(utg_open)  # "UTG open: 22+,A5s+,A9o+,K9s+,KTo+,QTs+,JTs+"
```

---

## Data Flow: Notation to Expanded Hands

```
User Input String
    ↓
"A5s-A2s,22+,AKo"
    ↓
Split by comma (union)
    ↓
["A5s-A2s"] ["22+"] ["AKo"]
    ↓ ↓ ↓
Identify notation type (-, +, or single)
    ↓ ↓ ↓
Range←┘ Plus←┘ Single←┘
    ↓
Call appropriate parser method
    ↓
←─ _parse_range() ─→ [A5s(4 combos), A4s(4), A3s(4), A2s(4)]
←─ _parse_plus()  ─→ [22(6), 33(6), 44(6), ..., AA(6)]
←─ _parse_single()─→ [AKo(12 combos)]
    ↓
Combine all hands (496 combos total)
    ↓
Deduplicate using dict.fromkeys()
    ↓
Create HandRange object
    ├─ hands: List[Hand] (496 combos, 34 types)
    ├─ size(): 34
    ├─ num_combos(): 496
    └─ shorthand: "A5s-A2s,22+,AKo" (original)
    ↓
Ready for GTO analysis
```

---

## Important Implementation Notes

### Suit Representation in Expansion

When expanding "A5s", the HandRange creates Hand objects with concrete Card objects:

```python
# Input: "A5s"
# Expansion creates these Hand objects:

Hand(Card(Rank.ACE, Suit.SPADES), Card(Rank.FIVE, Suit.SPADES))
Hand(Card(Rank.ACE, Suit.HEARTS), Card(Rank.FIVE, Suit.HEARTS))
Hand(Card(Rank.ACE, Suit.DIAMONDS), Card(Rank.FIVE, Suit.DIAMONDS))
Hand(Card(Rank.ACE, Suit.CLUBS), Card(Rank.FIVE, Suit.CLUBS))

# Each is a unique Hand object with:
# - card1: Rank=ACE, Suit=(SPADES|HEARTS|DIAMONDS|CLUBS)
# - card2: Rank=FIVE, Suit=same as card1
```

**Key Point**: Not abstract hands, but concrete cards with suits for equity calculations.

### Combo Counts Are Fixed

- **Pocket Pairs** (e.g., "AA"): 6 combos (C(4,2) = 6)
- **Suited** (e.g., "AKs"): 4 combos (one per suit)
- **Offsuit** (e.g., "AKo"): 12 combos (4 ranks × 3 other ranks)

These are mathematical truths, never variable.

### Why This Matters for GTO

1. **Equity Lookup**: Monte Carlo needs actual card combos with suits, not abstract hands
2. **Board Blocking**: Must know specific suits to determine which combos are blocked
3. **Strategy Storage**: Shorthand is compact; expansion is computational requirement
4. **Round-trip**: Original notation preserved for serialization and display

---

## Integration with Other Domain Models

### Dependency Chain
```
HandRange
    ↓ (contains List of)
Hand (exactly 2 cards)
    ↓ (each card is)
Card (Rank + Suit)
    ├─ Rank (2-A, enum)
    └─ Suit (♠♥♦♣, enum)

Board (independent, used with HandRange in analysis)
    └─ contains 0-5 Cards
```

### Real-World Pattern: Board Blocking

```python
# Create board
board = Board.from_shorthand("AsKhQd")  # Three cards

# Create range
hero_range = HandRange.from_shorthand("AK")  # All AK combos

# Filter combos blocked by board
available_hands = [
    h for h in hero_range.hands
    if h.card1 not in board.cards and h.card2 not in board.cards
]

# Result: AK combos involving As or Kh are blocked
# Available: AhKs, AhKd, AhKc, AdKs, etc.
# Blocked: AsKh, AsKd, AsKc (all have As from board)
```

### Real-World Pattern: Range vs Range Equity

```python
def analyze_range_matchup(
    hero: HandRange,
    villain: HandRange,
    board: Board
) -> AnalysisResult:
    """Equity calculation needs expanded hands.
    
    - Hero has 40+ hand types, each with multiple combos
    - Villain has 30+ hand types, each with multiple combos
    - Board has specific cards with specific suits
    - Each combo's equity depends on exact cards and board cards
    """
    
    total_equity = 0.0
    combo_weight = 0
    
    # Iterate through explicit combos
    for hero_combo in hero.hands:
        for villain_combo in villain.hands:
            # Check for blocking
            if hero_combo.blocks
(villain_combo, board):
                continue
            
            # Calculate equity for this specific matchup
            equity = montecarlo_equity(hero_combo, villain_combo, board)
            
            # Weight by combo count (all combos have same weight)
            total_equity += equity
            combo_weight += 1
    
    return AnalysisResult(
        avg_equity=total_equity / combo_weight,
        hero_range_size=hero.size(),
        combo_count=combo_weight
    )

# Example
btn_opens = HandRange.from_shorthand("22+,A2s+")
bb_defends = HandRange.from_shorthand("22+,A2s+")
board = Board.from_shorthand("KhQhJh")

result = analyze_range_matchup(btn_opens, bb_defends, board)
```

---

## Algorithm Optimizations & Design Improvements

### Critical Issues to Fix

#### Issue 1: Pocket Pair Expansion Generates Duplicates ❌

**Current Problem**:
```python
def _expand_pair(rank: str) -> List[Tuple[str, str]]:
    cards = []
    for suit1 in SUITS:
        for suit2 in SUITS:
            if suit1 != suit2:  # Only prevents same suit
                cards.append((rank + suit1, rank + suit2))
    return cards
```

**Result**: Generates 12 combos when should be **6**
- (As,Ah), (As,Ad), (As,Ac), (Ah,As), (Ah,Ad), (Ah,Ac), ... ← **Duplicates!**
- (As,Ah) and (Ah,As) are the same hand

**Optimized Algorithm**:
```python
def _expand_pair(rank: str) -> List[Tuple[str, str]]:
    """Expand pocket pair to 6 unique combos using combinations."""
    cards = []
    # Only generate pairs where suit1_index < suit2_index
    for i, suit1 in enumerate(SUITS):
        for suit2 in SUITS[i+1:]:  # Only j > i
            cards.append((rank + suit1, rank + suit2))
    return cards
    # Cost: O(6) = C(4,2), no duplicates
```

**Impact**: Fixes 2x memory waste on pair ranges like "22+" (78 pairs × 6 combos, not 12)

---

#### Issue 2: Plus Notation Not Implemented ❌

**Current Problem**:
```python
def _parse_plus_range(range_str: str) -> List[Tuple[str, str]]:
    base_hand = range_str[:-1]  # Remove '+'
    base_hands = HandRange._parse_single_hand(base_hand)
    logger.warning(f"Plus ranges not fully implemented: {range_str}")
    return base_hands  # ← Only returns base, ignores '+'!
```

**Result**: "22+" returns 6 combos (only AA), not 78 (all pairs)

**Optimized Algorithm**:
```python
def _parse_plus_range(range_str: str) -> List[Tuple[str, str]]:
    """Parse plus notation: expand upward to Ace."""
    base_hand = range_str[:-1]  # Remove '+'
    
    if len(base_hand) == 2:
        # Pair notation: "22+" → all pairs 22,33,44,...,AA
        base_rank = base_hand[0]
        start_idx = RANK_VALUES[base_rank]
        result = []
        for idx in range(start_idx, len(RANKS)):
            rank = RANKS[idx]
            result.extend(_expand_pair(rank))
        return result
    
    elif len(base_hand) == 3:
        # Two-card notation: "AKs+" → AKs, AQs, AJs
        rank1 = base_hand[0]
        rank2 = base_hand[1]
        suited = base_hand[2] == 's'
        start_idx = RANK_VALUES[rank2]
        result = []
        for idx in range(start_idx, len(RANKS)):
            if idx != RANK_VALUES[rank1]:  # Don't create pair
                rank = RANKS[idx]
                result.extend(_expand_two_cards(rank1, rank, suited))
        return result
    
    return []
```

**Coverage**: 
- "22+" → [22(6), 33(6), ..., AA(6)] = 78 hands
- "AKs+" → [AKs(4), AQs(4), AJs(4), ATs(4)] = 16 combos
- "KTs+" → [KTs, KJs, KQs, KAs] = 16 combos

---

#### Issue 3: Dash Range Limited to "Axy-Axz" Pattern ❌

**Current Problem**:
```python
# Only handles "A5s-A2s" pattern
if start_rank1 != 'A' or end_rank1 != 'A' or start_rank2 == end_rank2:
    logger.warning(f"Unsupported range format: {range_str}")
    return []
```

**Cannot Parse**:
- "22-99" (pair range)
- "KTs-K9s" (connector pattern)
- "J9s-J7s" (broadway pattern)

**Optimized Algorithm**:
```python
def _parse_dash_range(range_str: str) -> List[Tuple[str, str]]:
    """Parse descending range for any pattern."""
    parts = range_str.split('-')
    if len(parts) != 2:
        return []
    
    start_hand, end_hand = parts[0].strip(), parts[1].strip()
    
    # Parse start and end
    start_parsed = _parse_single_hand(start_hand)
    end_parsed = _parse_single_hand(end_hand)
    if not start_parsed or not end_parsed:
        return []
    
    start_rank1 = start_parsed[0][0][0]
    start_rank2 = start_parsed[0][1][0]
    end_rank1 = end_parsed[0][0][0]
    end_rank2 = end_parsed[0][1][0]
    
    # Handle pair ranges: "22-99"
    if start_rank1 == start_rank2 and end_rank1 == end_rank2:
        start_idx = RANK_VALUES[start_rank1]
        end_idx = RANK_VALUES[end_rank1]
        if start_idx <= end_idx:
            return []  # Invalid order
        result = []
        for idx in range(end_idx, start_idx + 1):
            rank = RANKS[idx]
            result.extend(_expand_pair(rank))
        return result
    
    # Handle high-card ranges: "A5s-A2s" or "KTs-K9s"
    if start_rank1 == end_rank1:  # Same high card
        high_rank = start_rank1
        start_idx = RANK_VALUES[start_rank2]
        end_idx = RANK_VALUES[end_rank2]
        if start_idx <= end_idx:
            return []  # Invalid order
        
        # Detect suitedness
        suited = 's' in start_hand.lower()
        
        result = []
        for idx in range(end_idx, start_idx + 1):
            rank = RANKS[idx]
            if rank != high_rank:  # Don't create pair
                result.extend(_expand_two_cards(high_rank, rank, suited))
        return result
    
    return []
```

**Coverage**:
- "A5s-A2s" → [A5s, A4s, A3s, A2s] = 16 combos ✅
- "22-99" → [22, 33, 44, 55, 66, 77, 88, 99] = 48 combos ✅
- "KTs-K9s" → [KTs, KJs, KQs] = 12 combos ✅

---

### Performance Optimizations

#### Optimization 1: Memoization (Caching)

**Problem**: Repeated parses of same notation recompute combos

```python
# Without cache:
for _ in range(1000):
    hands = HandRange.parse_shorthand("AKs+")  # Recomputes 16 combos each time
```

**Solution - Cache Common Ranges**:
```python
class HandRange:
    _EXPANSION_CACHE: Dict[str, List[Hand]] = {}
    _CACHE_MAX_SIZE = 500  # LRU cache of most common ranges
    
    @classmethod
    def from_shorthand(cls, notation: str) -> Optional['HandRange']:
        """Parse with automatic memoization."""
        if notation in cls._EXPANSION_CACHE:
            cached_hands = cls._EXPANSION_CACHE[notation]
            return HandRange(hands=cached_hands, shorthand=notation)
        
        # Parse normally
        hands = cls._parse_notation(notation)
        
        # Cache if under limit
        if len(cls._EXPANSION_CACHE) < cls._CACHE_MAX_SIZE:
            cls._EXPANSION_CACHE[notation] = hands
        
        return HandRange(hands=hands, shorthand=notation)
    
    @classmethod
    def clear_cache(cls):
        """Clear cache (for testing or memory management)."""
        cls._EXPANSION_CACHE.clear()
```

**Impact**:
- Common ranges ("22+", "AKs+", "UTG standard") cached after first parse
- **1000x faster** for repeated notation (cache lookup vs full parse)
- Memory: ~500 cached notations × 1KB average = 500KB overhead

---

#### Optimization 2: Lazy Evaluation (Deferred Expansion)

**Problem**: Always expands all combos, even if only need count

```python
# Without lazy eval:
range = HandRange.from_shorthand("22+,A2s+,KQs+")  # ~ 200+ combos generated
if range.size() > 100:  # Only wanted to know size!
    ...
```

**Solution - Lazy Expansion**:
```python
class LazyHandRange:
    """Defers hand expansion until needed."""
    
    def __init__(self, notation: str):
        self.notation = notation
        self._hands = None  # Lazy-loaded
        self._hand_types = self._parse_components()  # Fast: just parse notation
    
    def _parse_components(self) -> List[Tuple[str, str]]:
        """Fast path: parse into components without expanding."""
        # Examples: ["22", "A2s", "KQs+"]
        import re
        components = re.findall(r'[A-Z]{1,2}[so+\-]?(?:[A-Z0-9][so]?)?', 
                               self.notation.upper())
        return components
    
    @property
    def hands(self) -> List[Hand]:
        """Lazy load: expand only when accessed."""
        if self._hands is None:
            self._hands = self._expand_all()
        return self._hands
    
    def size(self) -> int:
        """Fast path: count without full expansion."""
        total = 0
        for component in self._hand_types:
            combos = self._get_combo_count(component)
            total += combos // self._get_combos_per_hand(component)
        return total
    
    def num_combos(self) -> int:
        """Fast path: count total combos without creating objects."""
        return sum(
            self._get_combo_count(component)
            for component in self._hand_types
        )
    
    def _get_combo_count(self, component: str) -> int:
        """Get combo count for single component (no object creation)."""
        # Pair: 6, Suited: 4, Offsuit: 12
        if len(component) == 2:
            return 6  # Pair
        elif component.endswith('s'):
            return 4  # Suited (or calculate from range)
        else:
            return 12  # Offsuit (or calculate from range)
    
    def expand(self) -> List[Hand]:
        """Explicit expansion (fallback to eager if needed)."""
        return self.hands
```

**Usage**:
```python
# Fast queries don't expand
range = LazyHandRange("22+,A2s+")
count = range.num_combos()  # O(components), no expansion!
size = range.size()         # O(components), no expansion!

# Expansion only when needed
hands = range.expand()      # O(combos) - full expansion
for hand in range.hands:    # O(combos) - triggers expansion once
    ...
```

**Impact**:
- **1000x faster** for queries like `size()` and `num_combos()`
- Only expands when iterating hands or accessing combos
- Perfect for GTO analysis where we often just need counts

---

### Robust Tokenization Strategy

**Current Problem**: Simple string detection is fragile

```python
if '+' in shorthand:  # Detects wrong '+' in "AKs+AQo+22"!
    return _parse_plus_range(shorthand)
```

**Optimized Approach - Regex-Based Tokenization**:
```python
import re

def _tokenize(notation: str) -> List[str]:
    """Split notation into clear components using regex.
    
    Examples:
    - "AKs+AQo+22" → ["AKs+", "AQo+", "22"]
    - "A5s-A2s,22+" → ["A5s-A2s", "22+"]
    - "AKs,AQo" → ["AKs", "AQo"]
    """
    # Pattern: 2-3 char hand + optional (+|-) modifier
    pattern = r'[A-Z]{1,2}[so]?(?:[+\-][A-Z0-9][so]?)?'
    tokens = re.findall(pattern, notation.upper())
    return tokens

def _parse_component(token: str) -> List[Hand]:
    """Parse single component (handles all notations)."""
    if '-' in token:
        return _parse_dash_range(token)
    elif token.endswith('+'):
        return _parse_plus_range(token)
    else:
        return _parse_single_hand(token)

def from_shorthand(notation: str) -> Optional['HandRange']:
    """Parse with robust tokenization."""
    tokens = _tokenize(notation)
    all_hands = []
    for token in tokens:
        hands = _parse_component(token)
        all_hands.extend(hands)
    
    return HandRange(hands=all_hands, shorthand=notation)
```

**Benefits**:
- Clear separation of tokenization and parsing
- Handles all syntaxes: "+", "-", and combinations
- Easy to extend with new notations
- Testable in isolation

---

### Summary of Improvements

| Item | Current | Optimized | Impact |
|------|---------|-----------|--------|
| **Pair Expansion** | 12 combos (6 dup) | 6 combos | Memory/speed 2x |
| **Plus Notation** | Not implemented | Full support | Correctness |
| **Dash Range** | Only "Axy-Axz" | All patterns | Feature complete |
| **Repeated Parses** | Recompute each time | Cached (500 notations) | Speed 1000x |
| **Count-Only Queries** | Full expansion | Lazy evaluation | Speed 1000x |
| **Tokenization** | String detection | Regex-based | Robust |

---

## Code Template

```python
# shared/domain/hand_range.py

# (Full implementation as shown in Specification)
```

---

## Validation Rules

```python
# Valid ranges
HandRange.from_shorthand("AKs")              # ✅ Single hand
HandRange.from_shorthand("22+")              # ✅ Plus notation
HandRange.from_shorthand("A5s-A2s")          # ✅ Range notation
HandRange.from_shorthand("AKs+AQo+22")       # ✅ Union notation
HandRange.from_shorthand("AKs,AQo,22")       # ✅ Comma syntax

# Invalid
HandRange.from_shorthand("")                 # ❌ Empty
HandRange.from_shorthand("XYZ")              # ❌ Invalid notation
HandRange([])                                # ❌ Must have hands
HandRange([hand1, hand1])                    # ❌ No duplicates
```

---

## Interactions with Other Models

```mermaid
graph LR
    Hand["Hand<br/>(foundation)"]
    HandRange["HandRange<br/>(parsed from shorthand)"]
    MatrixPayload["MatrixPayload<br/>(opponent strategy)"]
    Analyzer["RangeAnalyzer<br/>(range vs range)"]
    
    Hand -->|used by| HandRange
    HandRange -->|used in| MatrixPayload
    HandRange -->|analyzed by| Analyzer
    
    style Hand fill:#e8f5e9
    style HandRange fill:#e8f5e9
    style MatrixPayload fill:#fff3e0
    style Analyzer fill:#e3f2fd
```

---

## Testing

```python
import pytest
from shared.domain.hand_range import HandRange

def test_parse_single_hand():
    """Parse single hand."""
    ak_suited = HandRange.from_shorthand("AKs")
    assert ak_suited.size() == 4

def test_parse_pocket_pair():
    """Parse pocket pair."""
    aces = HandRange.from_shorthand("AA")
    assert aces.num_combos() == 6

def test_parse_plus_pairs():
    """Parse all pairs."""
    all_pairs = HandRange.from_shorthand("22+")
    assert all_pairs.size() == 78

def test_parse_range():
    """Parse range notation."""
    ax = HandRange.from_shorthand("A5s-A2s")
    assert ax.size() == 16

def test_parse_union():
    """Parse union notation."""
    range_ = HandRange.from_shorthand("AKs+AQo+22")
    assert range_.size() > 0

def test_round_trip():
    """Shorthand round-trip."""
    notation = "AKs+AQo+22"
    range_ = HandRange.from_shorthand(notation)
    assert range_.shorthand == notation

def test_num_combos():
    """Calculate total combos."""
    range_ = HandRange.from_shorthand("AKs,AKo")
    # AKs: 4, AKo: 12
    assert range_.num_combos() == 16

def test_contains():
    """Check hand membership."""
    ak_range = HandRange.from_shorthand("AKs+")
    ak_hand = Hand.from_strings("As", "Ks")
    assert ak_range.contains(ak_hand)

def test_union():
    """Combine ranges."""
    pairs = HandRange.from_shorthand("22+")
    aks = HandRange.from_shorthand("AKs")
    combined = HandRange.union(pairs, aks)
    assert combined.size() == pairs.size() + 4
```

---

## Best Practices

1. **Use from_shorthand() at API boundaries**
   ```python
   # ✅ Good - parse at entry point
   @app.post("/analyze")
   def analyze(data: dict):
       opponent_range = HandRange.from_shorthand(data["range_notation"])
   
   # ❌ Bad - deep in business logic
   def estimate_equity(range_str: str):
       opponent_range = HandRange.from_shorthand(range_str)
   ```

2. **Store shorthand for round-trip**
   ```python
   # ✅ Good - preserves original notation
   range_ = HandRange.from_shorthand("22+,A2s+")
   assert range_.shorthand == "22+,A2s+"
   
   # Can serialize back to JSON as string
   ```

3. **Weight by combos in calculations**
   ```python
   # ✅ Good - accounts for likelihood
   for hand in some_range.hands:
       equity_weighted = equity_value * hand.num_combos()
   
   # ❌ Bad - treats all hands equally
   equity_avg = sum(equity_values) / len(some_range.hands)
   ```

---

**Next**: Read [04_DOMAIN_Board.md](04_DOMAIN_Board.md) (uses Card)

