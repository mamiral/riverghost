# Shared Models & DTOs - The Foundation

## Purpose

This is where you start. Shared models are the **contract** between frontend and backend layers. Once defined, both teams can work independently.

**Time to complete**: 2-3 days  
**Complexity**: ⭐ (Easy)  
**Risk**: Low  
**Dependencies**: None

---

## What Are Shared Models?

Shared models are **data structures that cross the frontend/backend boundary**. They define:
- What data flows between layers
- Validation rules
- Naming conventions
- Type safety

They live in a `shared/` package that both frontend AND backend import.

---

## Model Categories

### 1. **Context Models** (Input)
Define what the frontend asks the backend to compute.

```python
# Frontend → Backend: "Analyze this!"
@dataclass(frozen=True)
class PositionContext:
    position: Position
    board: Optional[str]
    pot_size: float
    bet_amount: float
    num_opponents: int
```

### 2. **Result Models** (Output)
Define what the backend returns to the frontend.

```python
# Backend → Frontend: "Here's the result"
@dataclass
class MatrixPayload:
    cells: List[CellDisplay]
    min_value: float
    max_value: float
    mean_value: float
```

### 3. **Enum Definitions**
Shared constants and type definitions.

```python
class Position(Enum):
    UTG = "utg"
    CO = "co"
    BTN = "btn"
    SB = "sb"
    BB = "bb"
```

---

## Shared Models Checklist

### ✅ Context Models
These describe **what to analyze**:

- [ ] `PositionContext` - A specific poker position to analyze (pre-flop only)
- [ ] `ActionContext` - An action at a position

### ✅ Result Models
These describe **analysis results**:

- [ ] `HandEvaluation` - Single hand results (equity, EV, probabilities)
- [ ] `MatrixPayload` - Complete 13x13 matrix
- [ ] `CellDisplay` - Single cell formatted for rendering
- [ ] `DetailPayload` - Details for selected cell

### ✅ Progress Models
These track **ongoing computation**:

- [ ] `PrecomputeProgress` - Computation progress status
- [ ] `PrecomputeSession` - Active computation session info

### ✅ Enums & Types
These are **constants and type definitions**:

- [ ] `Position` - UTG, BTN, SB, BB (4 positions for 4-max only)
- [ ] `Action` - FOLD, ALL_IN (all-in/fold only)
- [ ] `MetricType` - EQUITY, EV, WIN_LOSE, EQR

### ✅ Validators
These enforce **business rules**:

- [ ] Equity must be [0, 1]
- [ ] Percentages must sum to 1 (if applicable)
- [ ] Position must be in valid set
- [ ] Action must be valid for position

---

## Design Decisions to Make

### 1. Immutability
**Question**: Should context models be immutable?

```python
# Option A: Immutable (frozen)
@dataclass(frozen=True)
class PositionContext:
    position: Position
    # Cannot be changed after creation
    # ✅ Good for: Thread safety, caching
    # ❌ Bad for: Flexibility

# Option B: Mutable
@dataclass
class PositionContext:
    position: Position
    # Can be changed
    # ✅ Good for: Flexibility
    # ❌ Bad for: Race conditions
```

**Recommendation**: Make context models **frozen=True** (immutable). This prevents accidental mutations and enables caching.

### 2. Validation Strategy
**Question**: How to validate data?

```python
# Option A: Pydantic (automatic validation)
from pydantic import BaseModel, Field

class PositionContext(BaseModel):
    position: Position
    pot_size: float = Field(gt=0)  # > 0
    # Validates automatically on creation

# Option B: Manual validation
@dataclass
class PositionContext:
    position: Position
    pot_size: float
    
    def __post_init__(self):
        if self.pot_size <= 0:
            raise ValueError("pot_size must be > 0")
```

**Recommendation**: Use **Pydantic** for automatic validation. It's robust and well-tested.

### 3. Optional Fields
**Question**: Use Optional or default values?

```python
# Option A: Optional
@dataclass
class PositionContext:
    board: Optional[str]  # Can be None

# Option B: Default value
@dataclass
class PositionContext:
    board: str = ""  # Empty string instead of None
```

**Recommendation**: Use **Optional** for optional fields. It's more explicit and type-safe.

---

## Expected Shared Models

### Context Models (What frontend asks backend to compute)

```python
@dataclass(frozen=True)
class PositionContext:
    """Specifies a poker position to analyze."""
    position: Position  # BTN, CO, HJ, UTG, SB, BB
    board: Optional[str] = None  # "Qs9h2d" or None for preflop
    pot_size_bb: float  # Pot in big blinds
    bet_amount_bb: float  # What we're betting/calling in BB
    num_opponents: int  # 1-5 typically
    
    def __post_init__(self):
        # Validate fields
        if self.pot_size_bb <= 0:
            raise ValueError("pot_size_bb must be positive")
        if self.num_opponents < 1:
            raise ValueError("Must have at least 1 opponent")
```

### Hand Evaluation Results

```python
@dataclass(frozen=True)
class HandEvaluation:
    """Result of evaluating a single hand."""
    hand_key: str  # "AK", "AKo", "AKs", "AA", etc.
    equity: float  # [0, 1] pot share
    win_probability: float  # [0, 1]
    loss_probability: float  # [0, 1]
    draw_probability: float  # [0, 1]
    ev: float  # Expected value in dollars
    eqr: float  # Equity to Risk Ratio
    
    def __post_init__(self):
        # Validate probabilities sum to 1
        total = self.win_probability + self.loss_probability + self.draw_probability
        if not 0.99 <= total <= 1.01:
            raise ValueError(
                f"Probabilities must sum to 1, got {total}"
            )
        if not 0 <= self.equity <= 1:
            raise ValueError(f"Equity must be [0, 1], got {self.equity}")
```

### Matrix Data for Display

```python
@dataclass
class CellDisplay:
    """Single cell formatted for rendering."""
    hand_key: str  # "AK", "QQ", etc.
    row: int  # 0-12 (matrix position)
    col: int  # 0-12 (matrix position)
    value: str  # Formatted value: "45.2%", "$5.67", etc.
    color_rgb: Tuple[int, int, int]  # RGB tuple
    is_computed: bool  # Has data? Or empty?

@dataclass
class MatrixPayload:
    """Complete 13x13 matrix ready for rendering."""
    cells: List[CellDisplay]  # 169 cells
    metric: MetricType  # EQUITY, EV, WIN_LOSE
    min_value: float  # Min value in matrix
    max_value: float  # Max value in matrix
    mean_value: float  # Average value
    total_computed: int  # How many cells computed?
    legend_colors: Dict[float, Tuple[int, int, int]]  # Value → Color mapping
```

### Precompute Progress

```python
@dataclass
class PrecomputeProgress:
    """Computation progress update."""
    session_id: str  # Unique ID for this computation
    percentage: float  # 0-100
    completed_cells: int  # How many done
    total_cells: int  # How many total
    elapsed_seconds: float  # How long so far
    estimated_remaining_seconds: Optional[float]  # ETA or None
    status: str  # "RUNNING", "PAUSED", "COMPLETED"
```

### Enums

```python
class Position(Enum):
    """Poker table position (4-max all-in/fold only)."""
    UTG = "utg"      # Early position (first to act pre-flop)
    BTN = "btn"      # Button (last to act pre-flop)
    SB = "sb"        # Small blind
    BB = "bb"        # Big blind

class Action(Enum):
    """All-in/fold action."""
    FOLD = "fold"              # Don't play the hand
    ALL_IN = "all_in"         # Commit all chips

class MetricType(Enum):
    """Available display metrics."""
    EQUITY = "equity"           # Pot percentage
    EV = "ev"                   # Expected value
    WIN_LOSE_PROBABILITY = "win_lose"  # P(win) vs P(lose)
    EQR = "eqr"                 # Equity to Risk Ratio
```

---

## Pydantic vs Dataclass Decision

Both are viable. Here's the comparison:

| Feature | Pydantic | Dataclass |
|---------|----------|-----------|
| **Automatic Validation** | ✅ Yes | ❌ No |
| **JSON Serialization** | ✅ Yes | ❌ No |
| **Type Checking** | ✅ Strong | âš ️ Basic |
| **Performance** | Good | Excellent |
| **Learning Curve** | Medium | Easy |
| **File Size** | Medium | Small |

**Recommendation**: Use **Pydantic** for models that cross frontend/backend boundaries (more validation), and **dataclass** for internal models (simpler).

---

## Usage Example

```python
# shared/models/context.py
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Position(str, Enum):
    BTN = "btn"
    CO = "co"
    # ...

class PositionContext(BaseModel):
    position: Position
    pot_size_bb: float = Field(gt=0)
    bet_amount_bb: float = Field(gt=0)
    num_opponents: int = Field(ge=1, le=5)
    board: Optional[str] = None

# Backend uses it
context = PositionContext(
    position=Position.BTN,
    pot_size_bb=50.0,
    bet_amount_bb=10.0,
    num_opponents=3,
    board=None  # Preflop
)

# Frontend uses it
payload = backend_service.query_matrix(context)
```

---

## File Organization

Create these files in `shared/models/`:

```
shared/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── position_context.py     # PositionContext
│   ├── hand_evaluation.py      # HandEvaluation
│   ├── matrix_payload.py       # MatrixPayload, CellDisplay
│   ├── precompute_progress.py  # PrecomputeProgress
│   ├── enums.py                # Position, Action, MetricType
│   └── validators.py           # Custom validation rules
└── config/
    ├── __init__.py
    └── defaults.py             # Default configurations
```

Or alternatively, one file per domain:

```
shared/
├── __init__.py
├── context_models.py           # PositionContext, ActionContext
├── result_models.py            # HandEvaluation, MatrixPayload
├── progress_models.py          # PrecomputeProgress
├── enums.py                    # All enums
├── validators.py               # Validation rules
├── config/
│   ├── __init__.py
│   └── defaults.py
└── types.py                    # Type aliases
```

**Recommendation**: One file per domain. Easier to find things.

---

## Next: Template Code

Here's a template to get started:

```python
# shared/result_models.py

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from enum import Enum

class MetricType(Enum):
    EQUITY = "equity"
    EV = "ev"
    WIN_LOSE_PROBABILITY = "win_lose"
    EQR = "eqr"

@dataclass(frozen=True)
class HandEvaluation:
    """Result of evaluating a single poker hand."""
    hand_key: str
    equity: float
    win_probability: float
    loss_probability: float
    draw_probability: float
    ev: float
    eqr: float
    
    def __post_init__(self):
        total = self.win_probability + self.loss_probability + self.draw_probability
        assert 0.99 <= total <= 1.01, f"Probabilities sum to {total}, not 1"
        assert 0 <= self.equity <= 1, f"Equity {self.equity} not in [0,1]"

@dataclass
class CellDisplay:
    """Single matrix cell formatted for rendering."""
    hand_key: str
    row: int
    col: int
    value: str  # e.g., "45.2%", "$5.67"
    color_rgb: Tuple[int, int, int]
    is_computed: bool

@dataclass
class MatrixPayload:
    """13x13 hand matrix ready for display."""
    cells: List[CellDisplay]
    metric: MetricType
    min_value: float
    max_value: float
    mean_value: float
    total_computed: int
    legend_colors: Dict[float, Tuple[int, int, int]]
```

---

## Testing Shared Models

When you implement these, test them:

```python
# test_shared_models.py
import pytest
from shared.result_models import HandEvaluation

def test_hand_evaluation_validates_probabilities():
    """Probabilities must sum to 1."""
    with pytest.raises(AssertionError):
        HandEvaluation(
            hand_key="AK",
            equity=0.45,
            win_probability=0.4,
            loss_probability=0.4,  # Missing draw
            draw_probability=0.2,  # Sum = 1.0
            ev=2.50,
            eqr=0.9
        )

def test_hand_evaluation_valid():
    """Valid evaluation succeeds."""
    result = HandEvaluation(
        hand_key="AK",
        equity=0.45,
        win_probability=0.4,
        loss_probability=0.4,
        draw_probability=0.2,
        ev=2.50,
        eqr=0.9
    )
    assert result.hand_key == "AK"
    assert result.equity == 0.45
```

---

## Checkpoints

**After designing Shared Models:**

- [ ] All context models defined (PositionContext, ActionContext)
- [ ] All result models defined (HandEvaluation, MatrixPayload)
- [ ] All enums defined (Position, Action, MetricType)
- [ ] Validation rules clear
- [ ] Team agrees on naming conventions
- [ ] Ready to implement backend services

**Time estimate**: 1-2 days

---

## Decision: Pydantic or Dataclass?

**For this project, recommend**:
- Use **dataclass** for simplicity and performance
- Use **Pydantic** only if JSON serialization needed (unlikely for desktop app)
- Add **custom `__post_init__` validation** for business rules

This keeps dependencies minimal and code fast.

---

## Next: Review & Approve

1. Design all models above
2. Get team agreement
3. Create files in `shared/` package
4. Move to Phase 2: Database Layer

Once approved, both frontend and backend teams can start implementation without blocking each other!
