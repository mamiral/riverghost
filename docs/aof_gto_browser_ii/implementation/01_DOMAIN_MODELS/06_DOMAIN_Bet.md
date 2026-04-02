# Domain Model: Bet

## Purpose

Represents a **monetary amount in terms of big blinds** - a value type for game-specific amounts that need validation and consistency.

**Depends on**: Nothing (primitive value type)

Critical for GTO analysis:
- ✅ Standardizes amount representation across app (always big blinds)
- ✅ Validates amounts (no zero, negative, NaN, or infinity)
- ✅ Enables safe arithmetic with monetary values
- ✅ Immutable to prevent accidental mutation
- ✅ Simplifies display formatting

---

## Class Definition

### Bet

Represents an amount in big blinds with validation.

```python
@dataclass(frozen=True)
class Bet:
    """
    Immutable monetary amount in big blinds.
    
    All amounts in the system use big blinds for consistency:
    - Pot size: 2.5 BB
    - Stack: 100 BB
    - Bet: 1.0 BB (= 1 big blind)
    
    Attributes:
        amount_bb: Amount in big blinds (must be > 0, not NaN/Inf)
    """
    amount_bb: float  # > 0
```

---

## Attributes & Types

| Attribute | Type | Valid Range | Purpose | Notes |
|-----------|------|-------------|---------|-------|
| `amount_bb` | float | > 0.0 | Amount in big blinds | Must be positive, finite, not NaN |

---

## Validation Rules

### Constraint 1: Positive Amount
Amount must be strictly greater than zero.

```python
if self.amount_bb <= 0:
    raise ValueError(f"amount_bb must be > 0, got {self.amount_bb}")
```

### Constraint 2: Finite (No NaN or Infinity)
Amount must be a valid finite number.

```python
import math

if math.isnan(self.amount_bb) or math.isinf(self.amount_bb):
    raise ValueError(f"amount_bb must be finite, got {self.amount_bb}")
```

### Full Validation

```python
@dataclass(frozen=True)
class Bet:
    amount_bb: float
    
    def __post_init__(self):
        """Validate amount constraints."""
        import math
        
        # Check for NaN/Inf
        if math.isnan(self.amount_bb) or math.isinf(self.amount_bb):
            raise ValueError(
                f"amount_bb must be finite, got {self.amount_bb}"
            )
        
        # Check for positive
        if self.amount_bb <= 0:
            raise ValueError(
                f"amount_bb must be > 0, got {self.amount_bb}"
            )
```

---

## Methods

### Properties

#### `is_zero() -> bool`
Check if amount is zero (convenience method).

```python
@property
def is_zero(self) -> bool:
    """Check if amount is zero (for early exit logic)"""
    return self.amount_bb == 0.0
```

#### `is_all_in(stack_bb: float) -> bool`
Check if this bet would be an all-in given a stack.

```python
def is_all_in(self, stack_bb: float) -> bool:
    """
    Check if this bet amount equals or exceeds stack.
    
    Args:
        stack_bb: Stack size in big blinds
    
    Returns:
        True if bet >= stack (all-in)
    
    Example:
        >>> bet = Bet(25.0)
        >>> bet.is_all_in(25.0)
        True
        >>> bet.is_all_in(26.0)
        False
    """
    if stack_bb <= 0:
        raise ValueError(f"stack_bb must be > 0, got {stack_bb}")
    
    return self.amount_bb >= stack_bb
```

#### `display_value() -> str`
Format amount for display (handles cents, currency).

```python
@property
def display_value(self) -> str:
    """
    Format as display string with appropriate precision.
    
    Rules:
    - < 1 BB: Show to 2 decimal places (e.g., "0.50 BB")
    - >= 1 BB: Show to 1 decimal place (e.g., "2.5 BB")
    
    Returns:
        Formatted string ready for display
    
    Example:
        >>> Bet(0.50).display_value
        "0.50 BB"
        >>> Bet(25.0).display_value
        "25.0 BB"
        >>> Bet(0.3333).display_value
        "0.33 BB"  # Rounded
    """
    if self.amount_bb < 1.0:
        return f"{self.amount_bb:.2f} BB"
    else:
        return f"{self.amount_bb:.1f} BB"
```

---

## Factories & Constructors

### Default Constructor
Create bet by passing amount.

```python
# Usage
bet = Bet(25.0)  # 25 big blinds
bet_small = Bet(0.5)  # Half big blind
```

### `from_cents(cents: int, big_blind_cents: int) -> Bet`
Create bet from monetary amounts (cents).

```python
@staticmethod
def from_cents(bet_cents: int, big_blind_cents: int) -> "Bet":
    """
    Create Bet from monetary amounts.
    
    Args:
        bet_cents: Bet amount in cents (e.g., 2500 for $25.00)
        big_blind_cents: Big blind amount in cents (e.g., 100 for $1.00)
    
    Returns:
        Bet with amount_bb calculated
    
    Raises:
        ValueError: If big_blind_cents <= 0
    
    Example:
        >>> Bet.from_cents(bet_cents=2500, big_blind_cents=100)
        Bet(amount_bb=25.0)  # $25 / $1 = 25 BB
        
        >>> Bet.from_cents(bet_cents=50, big_blind_cents=100)
        Bet(amount_bb=0.5)  # $0.50 / $1.00 = 0.5 BB
    """
    if big_blind_cents <= 0:
        raise ValueError(f"big_blind_cents must be > 0, got {big_blind_cents}")
    
    amount_bb = bet_cents / big_blind_cents
    return Bet(amount_bb)
```

### `from_dollars(bet_dollars: float, big_blind_dollars: float) -> Bet`
Create bet from dollars.

```python
@staticmethod
def from_dollars(bet_dollars: float, big_blind_dollars: float) -> "Bet":
    """
    Create Bet from dollar amounts.
    
    Args:
        bet_dollars: Bet amount in dollars (e.g., 25.00)
        big_blind_dollars: Big blind in dollars (e.g., 1.00)
    
    Returns:
        Bet with amount_bb calculated
    
    Raises:
        ValueError: If big_blind_dollars <= 0
    
    Example:
        >>> Bet.from_dollars(bet_dollars=25.00, big_blind_dollars=1.00)
        Bet(amount_bb=25.0)
        
        >>> Bet.from_dollars(bet_dollars=0.50, big_blind_dollars=1.00)
        Bet(amount_bb=0.5)
    """
    if big_blind_dollars <= 0:
        raise ValueError(f"big_blind_dollars must be > 0, got {big_blind_dollars}")
    
    amount_bb = bet_dollars / big_blind_dollars
    return Bet(amount_bb)
```

---

## Invariants & Constraints

### Amount Invariant
Always true:
```python
assert bet.amount_bb > 0
assert not math.isnan(bet.amount_bb)
assert not math.isinf(bet.amount_bb)
```

### Immutability
Bet is frozen (immutable):

```python
bet = Bet(25.0)
bet.amount_bb = 30.0  # ❌ FrozenInstanceError - cannot modify
```

---

## Usage Examples

### Example 1: Basic Creation

```python
from shared.domain import Bet

# Create directly
bet = Bet(25.0)  # 25 big blinds
print(f"Bet: {bet.display_value}")  # "25.0 BB"

# Check if all-in
is_allin = bet.is_all_in(25.0)  # True (20 >= 25)
is_allin = bet.is_all_in(30.0)  # False (25 < 30)
```

### Example 2: Creating from Monetary Values

```python
# From dollars
bet = Bet.from_dollars(bet_dollars=25.00, big_blind_dollars=1.00)
# Result: Bet(amount_bb=25.0)

# From cents (useful for precise calculations)
bet = Bet.from_cents(bet_cents=2500, big_blind_cents=100)
# Result: Bet(amount_bb=25.0)

# Half-big blind
bet = Bet.from_dollars(0.50, 1.00)
# Result: Bet(amount_bb=0.5)
```

### Example 3: Position Context with Bets

```python
from shared.domain import Bet
from shared.dto import PositionContext

# Analysis request with bet amounts
context = PositionContext(
    position="BTN",
    stack=Bet(100.0),  # 100 BB stack
    pot=Bet(2.5),      # 2.5 BB pot
    bet_to_call=Bet(10.0),  # 10 BB to call
)
```

### Example 4: Database Persistence

```python
from sqlalchemy import Float, Column
from shared.domain import Bet

class ActionModel(Base):
    __tablename__ = "actions"
    
    bet_amount_bb = Column(Float)
    stack_bb = Column(Float)
    
    def to_domain_bet(self) -> Bet:
        """Convert ORM to domain"""
        return Bet(amount_bb=self.bet_amount_bb)
    
    @staticmethod
    def from_domain_bet(bet: Bet) -> "ActionModel":
        """Convert domain to ORM"""
        return ActionModel(
            bet_amount_bb=bet.amount_bb
        )
```

### Example 5: All-In Detection

```python
def is_all_in_scenario(hero_bet: Bet, hero_stack: Bet) -> bool:
    """Check if hero's bet is all-in"""
    return hero_bet.is_all_in(hero_stack.amount_bb)

# Usage
hero_action = Bet(100.0)
hero_stack = Bet(100.0)

if is_all_in_scenario(hero_action, hero_stack):
    print("Hero is all-in!")
```

---

## Testing Expectations

### Test 1: Validation on Construction

```python
def test_bet_zero_amount():
    """Should reject zero amount"""
    with pytest.raises(ValueError, match="must be > 0"):
        Bet(0.0)

def test_bet_negative_amount():
    """Should reject negative amount"""
    with pytest.raises(ValueError, match="must be > 0"):
        Bet(-5.0)

def test_bet_nan_amount():
    """Should reject NaN"""
    import math
    with pytest.raises(ValueError, match="must be finite"):
        Bet(math.nan)

def test_bet_infinity_amount():
    """Should reject infinity"""
    import math
    with pytest.raises(ValueError, match="must be finite"):
        Bet(math.inf)

def test_bet_valid_amounts():
    """Should accept positive finite amounts"""
    assert Bet(0.5).amount_bb == 0.5
    assert Bet(1.0).amount_bb == 1.0
    assert Bet(100.5).amount_bb == 100.5
```

### Test 2: Factory Methods

```python
def test_from_dollars():
    """Should calculate BB from dollars"""
    bet = Bet.from_dollars(25.00, big_blind_dollars=1.00)
    assert bet.amount_bb == pytest.approx(25.0)
    
    bet = Bet.from_dollars(0.50, big_blind_dollars=1.00)
    assert bet.amount_bb == pytest.approx(0.5)

def test_from_cents():
    """Should calculate BB from cents"""
    bet = Bet.from_cents(2500, big_blind_cents=100)
    assert bet.amount_bb == pytest.approx(25.0)
    
    bet = Bet.from_cents(50, big_blind_cents=100)
    assert bet.amount_bb == pytest.approx(0.5)

def test_from_dollars_invalid_bb():
    """Should reject zero or negative BB"""
    with pytest.raises(ValueError, match="big_blind_dollars must be > 0"):
        Bet.from_dollars(25.0, big_blind_dollars=0.0)
```

### Test 3: All-In Detection

```python
def test_is_all_in():
    """Should correctly identify all-in"""
    bet = Bet(25.0)
    
    assert bet.is_all_in(25.0) is True  # Exact stack
    assert bet.is_all_in(24.0) is True  # Bet > stack
    assert bet.is_all_in(26.0) is False  # Bet < stack

def test_is_all_in_fraction():
    """Should work with fractional amounts"""
    bet = Bet(0.75)
    
    assert bet.is_all_in(0.75) is True
    assert bet.is_all_in(0.5) is True
    assert bet.is_all_in(1.0) is False
```

### Test 4: Display Formatting

```python
def test_display_value_under_1bb():
    """Should show 2 decimals for amounts < 1 BB"""
    assert Bet(0.5).display_value == "0.50 BB"
    assert Bet(0.33).display_value == "0.33 BB"

def test_display_value_over_1bb():
    """Should show 1 decimal for amounts >= 1 BB"""
    assert Bet(1.0).display_value == "1.0 BB"
    assert Bet(25.0).display_value == "25.0 BB"
    assert Bet(100.5).display_value == "100.5 BB"
```

### Test 5: Immutability

```python
def test_bet_frozen():
    """Should not allow modification after construction"""
    bet = Bet(25.0)
    
    with pytest.raises(FrozenInstanceError):
        bet.amount_bb = 30.0
```

---

## Implementation Checklist

- [ ] Define Bet dataclass with frozen=True
- [ ] Implement `__post_init__()` validation (positive, finite)
- [ ] Add `is_all_in(stack_bb: float)` method
- [ ] Add `display_value` property
- [ ] Add `from_dollars()` factory
- [ ] Add `from_cents()` factory
- [ ] Add to shared.domain.__init__.py exports
- [ ] Write comprehensive unit tests (95%+ coverage)
- [ ] Document in API reference
- [ ] Add to integration examples (DTOs, database)

---

## Related Domain Models

- **Hand** - Used with Bet in action contexts
- **Board** - Used with Bet in game state
- **EquityResult** - Often paired with Bet for bet/equity analysis

---

## Related DTOs

- **PositionContext** - Contains Bet amounts (stack, pot, bet_to_call)
- **ActionContext** - Contains action Bet amounts
- **AnalysisRequest** - May contain Bet parameters
