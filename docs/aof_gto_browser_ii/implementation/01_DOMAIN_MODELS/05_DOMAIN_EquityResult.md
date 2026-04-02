# Domain Model: EquityResult

## Purpose

Represents the **result of hand equity analysis** - the outcome of comparing a specific hand against an opponent range in a preflop all-in scenario.

**Depends on**: Hand

Critical for GTO analysis:
- ✅ Captures win/loss/draw probabilities
- ✅ Stores equity value (0.0-1.0)
- ✅ Tracks simulation count for convergence
- ✅ Immutable result object returned from analysis
- ✅ Foundation of 13×13 matrix display

---

## Class Definition

### EquityResult

Represents hand equity against a range, with detailed probability breakdown.

```python
@dataclass(frozen=True)
class EquityResult:
    """
    Immutable result of hand equity analysis.
    
    Attributes:
        hand: The hand being evaluated
        equity: Overall equity 0.0-1.0 vs opponent range
        win_prob: Probability of winning (no draw)
        draw_prob: Probability of drawing (tie)
        loss_prob: Probability of losing
        num_simulations: Number of Monte Carlo iterations
    """
    hand: Hand
    equity: float  # 0.0-1.0
    win_prob: float  # 0.0-1.0
    draw_prob: float  # 0.0-1.0
    loss_prob: float  # 0.0-1.0
    num_simulations: int  # > 0
```

---

## Attributes & Types

| Attribute | Type | Range | Purpose | Notes |
|-----------|------|-------|---------|-------|
| `hand` | Hand | - | The hand being evaluated | Immutable Hand object, e.g., AKs |
| `equity` | float | 0.0-1.0 | Weighted equity vs range | Decimal form: 0.52 = 52% |
| `win_prob` | float | 0.0-1.0 | Probability of winning | Excludes draws |
| `draw_prob` | float | 0.0-1.0 | Probability of drawing | Tie scenario |
| `loss_prob` | float | 0.0-1.0 | Probability of losing | Excludes draws |
| `num_simulations` | int | ≥ 1000 | MC sample count | For convergence tracking |

---

## Probability Validation

**Invariant**: `win_prob + draw_prob + loss_prob ≈ 1.0`

**Tolerance**: ±0.01 (1%) to account for floating-point rounding

```python
@dataclass(frozen=True)
class EquityResult:
    # ... attributes ...
    
    def __post_init__(self):
        """Validate probability constraints."""
        # Check individual probabilities in range
        if not (0.0 <= self.win_prob <= 1.0):
            raise ValueError(f"win_prob must be 0.0-1.0, got {self.win_prob}")
        if not (0.0 <= self.draw_prob <= 1.0):
            raise ValueError(f"draw_prob must be 0.0-1.0, got {self.draw_prob}")
        if not (0.0 <= self.loss_prob <= 1.0):
            raise ValueError(f"loss_prob must be 0.0-1.0, got {self.loss_prob}")
        if not (0.0 <= self.equity <= 1.0):
            raise ValueError(f"equity must be 0.0-1.0, got {self.equity}")
        
        # Check sum constraint
        total_prob = self.win_prob + self.draw_prob + self.loss_prob
        expected = 1.0
        if not (expected - 0.01 <= total_prob <= expected + 0.01):
            raise ValueError(
                f"Probabilities must sum to 1.0±0.01: "
                f"{self.win_prob} + {self.draw_prob} + {self.loss_prob} = {total_prob}"
            )
        
        # Check simulation count
        if self.num_simulations < 1000:
            raise ValueError(f"num_simulations must be ≥ 1000, got {self.num_simulations}")
```

---

## Methods

### Properties

#### `win_percent() -> float`
Returns win probability as percentage string for display.

```python
@property
def win_percent(self) -> str:
    """Format win probability as percentage (e.g., '52.34%')"""
    return f"{self.win_prob * 100:.2f}%"

@property
def draw_percent(self) -> str:
    """Format draw probability as percentage"""
    return f"{self.draw_prob * 100:.2f}%"

@property
def loss_percent(self) -> str:
    """Format loss probability as percentage"""
    return f"{self.loss_prob * 100:.2f}%"

@property
def equity_percent(self) -> str:
    """Format equity as percentage"""
    return f"{self.equity * 100:.2f}%"
```

---

## Factories & Constructors

### `from_monte_carlo()`
Create result from Monte Carlo simulation output.

```python
@staticmethod
def from_monte_carlo(
    hand: Hand,
    wins: int,
    draws: int,
    losses: int,
    total_simulations: int
) -> "EquityResult":
    """
    Create EquityResult from raw Monte Carlo counts.
    
    Args:
        hand: The hand being evaluated
        wins: Number of winning scenarios
        draws: Number of draw scenarios
        losses: Number of losing scenarios
        total_simulations: Total Monte Carlo iterations
    
    Returns:
        EquityResult with calculated probabilities
    
    Example:
        >>> result = EquityResult.from_monte_carlo(
        ...     hand=Hand.from_shorthand("AKs")[0],
        ...     wins=520,
        ...     draws=20,
        ...     losses=460,
        ...     total_simulations=1000
        ... )
        >>> result.equity
        0.53  # (wins + 0.5*draws) / total
    """
    win_prob = wins / total_simulations
    draw_prob = draws / total_simulations
    loss_prob = losses / total_simulations
    
    # Equity includes half the draws
    equity = (wins + 0.5 * draws) / total_simulations
    
    return EquityResult(
        hand=hand,
        equity=equity,
        win_prob=win_prob,
        draw_prob=draw_prob,
        loss_prob=loss_prob,
        num_simulations=total_simulations
    )
```

### `from_solver_output()`
Create result from solver library output (PokerKit, Treys, etc.).

```python
@staticmethod
def from_solver_output(
    hand: Hand,
    solver_result: Dict[str, float],
    num_simulations: int = 100000
) -> "EquityResult":
    """
    Create EquityResult from solver library output.
    
    Args:
        hand: The hand being evaluated
        solver_result: Dict with 'equity', 'win', 'draw', 'loss' keys
                      Values should be probabilities (0.0-1.0) or percentages
        num_simulations: Sample count for this result
    
    Returns:
        EquityResult validated and normalized
    
    Example:
        >>> result = EquityResult.from_solver_output(
        ...     hand=Hand.from_shorthand("AKs")[0],
        ...     solver_result={
        ...         'equity': 0.52,
        ...         'win': 0.50,
        ...         'draw': 0.04,
        ...         'loss': 0.46
        ...     },
        ...     num_simulations=100000
        ... )
    """
    # Normalize percentages to probabilities if needed
    win = solver_result.get('win', 0.0)
    draw = solver_result.get('draw', 0.0)
    loss = solver_result.get('loss', 0.0)
    equity = solver_result.get('equity', 0.0)
    
    # Convert percentages to decimals if > 1.0
    if win > 1.0:
        win, draw, loss = win / 100, draw / 100, loss / 100
    if equity > 1.0:
        equity = equity / 100
    
    return EquityResult(
        hand=hand,
        equity=equity,
        win_prob=win,
        draw_prob=draw,
        loss_prob=loss,
        num_simulations=num_simulations
    )
```

---

## Invariants & Constraints

### Probability Invariant

Always true: `win_prob + draw_prob + loss_prob = 1.0 ± tolerance`

```python
assert abs((result.win_prob + result.draw_prob + result.loss_prob) - 1.0) <= 0.01
```

### Equity Relationship

Equity includes half of draws:

```python
expected_equity = result.win_prob + 0.5 * result.draw_prob
assert abs(result.equity - expected_equity) <= 0.01
```

### Immutability

EquityResult is frozen (immutable):

```python
result = EquityResult(...)
result.equity = 0.60  # ❌ FrozenInstanceError - cannot modify
```

---

## Usage Examples

### Example 1: Creating from Monte Carlo Output

```python
from shared.domain import Hand, EquityResult

# Simulate AKs vs random range, 1000 iterations
hand = Hand.from_shorthand("AKs")[0]  # First AKs combo
result = EquityResult.from_monte_carlo(
    hand=hand,
    wins=520,
    draws=20,
    losses=460,
    total_simulations=1000
)

print(f"Hand: {hand}")
print(f"Equity: {result.equity_percent}")  # "53.00%"
print(f"Win: {result.win_percent}, Draw: {result.draw_percent}, Loss: {result.loss_percent}")
# Output: Win: 52.00%, Draw: 2.00%, Loss: 46.00%
```

### Example 2: Storing in Database

```python
# ORM mapping for database persistence
class CellResult(Base):
    __tablename__ = "cell_results"
    
    id = Column(Integer, primary_key=True)
    hand_notation = Column(String(10), index=True)
    equity = Column(Float)
    win_prob = Column(Float)
    draw_prob = Column(Float)
    loss_prob = Column(Float)
    num_simulations = Column(Integer)
    
    def to_domain(self) -> EquityResult:
        """Convert ORM to domain model"""
        hand = Hand.from_shorthand(self.hand_notation)[0]  # Simplified
        return EquityResult(
            hand=hand,
            equity=self.equity,
            win_prob=self.win_prob,
            draw_prob=self.draw_prob,
            loss_prob=self.loss_prob,
            num_simulations=self.num_simulations
        )
    
    @staticmethod
    def from_domain(result: EquityResult) -> "CellResult":
        """Convert domain model to ORM"""
        return CellResult(
            hand_notation=str(result.hand),
            equity=result.equity,
            win_prob=result.win_prob,
            draw_prob=result.draw_prob,
            loss_prob=result.loss_prob,
            num_simulations=result.num_simulations
        )
```

### Example 3: Matrix Cell Display

```python
# Using in DTO conversion for display
from shared.dto import CellDisplay

def equity_result_to_display(result: EquityResult) -> CellDisplay:
    """Convert domain result to display DTO"""
    return CellDisplay(
        hand=str(result.hand),
        equity_percent=result.equity_percent,
        win_percent=result.win_percent,
        draw_percent=result.draw_percent,
        loss_percent=result.loss_percent,
        color_code=get_equity_color(result.equity),
        simulation_count=result.num_simulations
    )
```

### Example 4: Weighted Average Equity

```python
# Computing average equity across multiple hands
def weighted_average_equity(results: List[EquityResult]) -> float:
    """Calculate equity-weighted average"""
    total_weight = sum(r.hand.num_combos() for r in results)
    weighted_sum = sum(
        r.equity * r.hand.num_combos()
        for r in results
    )
    return weighted_sum / total_weight

# Usage
range_results = [result1, result2, result3]  # Multiple EquityResult objects
avg_equity = weighted_average_equity(range_results)
print(f"Range equity: {avg_equity * 100:.2f}%")
```

---

## Testing Expectations

### Test 1: Validation on Construction

```python
def test_equity_result_invalid_probability_sum():
    """Should reject probabilities that don't sum to 1.0"""
    with pytest.raises(ValueError, match="must sum to 1.0"):
        EquityResult(
            hand=Hand.from_shorthand("AKs")[0],
            equity=0.50,
            win_prob=0.60,  # Sum = 1.10, invalid
            draw_prob=0.30,
            loss_prob=0.20,
            num_simulations=1000
        )

def test_equity_result_out_of_range_equity():
    """Should reject equity outside 0.0-1.0"""
    with pytest.raises(ValueError, match="equity must be 0.0-1.0"):
        EquityResult(
            hand=Hand.from_shorthand("AKs")[0],
            equity=1.50,  # > 1.0, invalid
            win_prob=0.50,
            draw_prob=0.00,
            loss_prob=0.50,
            num_simulations=1000
        )

def test_equity_result_insufficient_simulations():
    """Should reject num_simulations < 1000"""
    with pytest.raises(ValueError, match="num_simulations must be ≥ 1000"):
        EquityResult(
            hand=Hand.from_shorthand("AKs")[0],
            equity=0.50,
            win_prob=0.50,
            draw_prob=0.00,
            loss_prob=0.50,
            num_simulations=500  # < 1000, invalid
        )
```

### Test 2: Factory Methods

```python
def test_from_monte_carlo():
    """Should correctly calculate probabilities from counts"""
    result = EquityResult.from_monte_carlo(
        hand=Hand.from_shorthand("AKs")[0],
        wins=520,
        draws=20,
        losses=460,
        total_simulations=1000
    )
    
    assert result.win_prob == pytest.approx(0.52)
    assert result.draw_prob == pytest.approx(0.02)
    assert result.loss_prob == pytest.approx(0.46)
    assert result.equity == pytest.approx(0.53)  # 0.52 + 0.5*0.02

def test_from_solver_output():
    """Should handle solver library output formats"""
    result = EquityResult.from_solver_output(
        hand=Hand.from_shorthand("AKs")[0],
        solver_result={
            'equity': 52.5,  # Percentage format
            'win': 52.0,
            'draw': 1.0,
            'loss': 47.0
        },
        num_simulations=100000
    )
    
    assert result.equity == pytest.approx(0.525)
    assert result.win_prob == pytest.approx(0.52)
```

### Test 3: Immutability

```python
def test_equity_result_frozen():
    """Should not allow modification after construction"""
    result = EquityResult(
        hand=Hand.from_shorthand("AKs")[0],
        equity=0.50,
        win_prob=0.50,
        draw_prob=0.00,
        loss_prob=0.50,
        num_simulations=1000
    )
    
    with pytest.raises(FrozenInstanceError):
        result.equity = 0.60
    
    with pytest.raises(FrozenInstanceError):
        result.win_prob = 0.55
```

### Test 4: Percentage Formatting

```python
def test_equity_percent_formatting():
    """Should format probabilities as percentage strings"""
    result = EquityResult(
        hand=Hand.from_shorthand("AKs")[0],
        equity=0.5234,
        win_prob=0.5012,
        draw_prob=0.0122,
        loss_prob=0.4866,
        num_simulations=1000
    )
    
    assert result.equity_percent == "52.34%"
    assert result.win_percent == "50.12%"
    assert result.draw_percent == "1.22%"
    assert result.loss_percent == "48.66%"
```

---

## Implementation Checklist

- [ ] Define EquityResult dataclass with frozen=True
- [ ] Implement `__post_init__()` validation
- [ ] Add `from_monte_carlo()` factory
- [ ] Add `from_solver_output()` factory
- [ ] Implement `*_percent` properties for display formatting
- [ ] Add to shared.domain.__init__.py exports
- [ ] Write comprehensive unit tests (95%+ coverage)
- [ ] Document in API reference
- [ ] Add to integration examples (DTOs, ORM, display)

---

## Related Domain Models

- **Hand** - The specific hand being evaluated
- **HandRange** - Multiple hands evaluated together
- **Board** - Community cards (always 0 in preflop all-in scenarios)

---

## Related DTOs

- **CellDisplay** - Frontend representation of EquityResult
- **MatrixPayload** - Multiple results in 13×13 matrix format
- **DetailPayload** - Detailed analysis of single EquityResult
