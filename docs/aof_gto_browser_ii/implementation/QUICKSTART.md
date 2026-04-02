# 🚀 Architecture A - Quick Start Guide

## Where You Are Now

✅ Design phase complete  
🎯 **Architecture A selected**  
📂 Implementation structure created  
👉 **Ready to start building**

---

## The Most Logical Starting Point: Domain Models First, Then DTOs

### Why This Order?

```
Domain Models (Card, Hand, HandRange)  ← Start Here
    ↓ [Foundation]
Shared Models/DTOs (depend on domain models)
    ↓ [Type-safe, immutable]
Both Frontend AND Backend depend on these
    ↓ [Once defined, teams work independently]
No risk of rework
```

### What to Do This Week

1. **Understand** domain models:
   - Read [01_DOMAIN_MODELS/00_INDEX.md](01_DOMAIN_MODELS/00_INDEX.md) (10 min)
   - Review [01_DOMAIN_MODELS/01_DOMAIN_Card.md](01_DOMAIN_MODELS/01_DOMAIN_Card.md) (15 min)
   - Review [01_DOMAIN_MODELS/02_DOMAIN_Hand.md](01_DOMAIN_MODELS/02_DOMAIN_Hand.md) (15 min)
   - Review [01_DOMAIN_MODELS/03_DOMAIN_HandRange.md](01_DOMAIN_MODELS/03_DOMAIN_HandRange.md) (15 min)

2. **Understand** integration boundaries:
   - Read [04_INTEGRATION_DTOs_and_DomainModels.md](04_INTEGRATION_DTOs_and_DomainModels.md) (20 min)
   - How strings convert to domain models at API boundary
   - How domain models stay immutable in business logic

3. **Design** all DTOs using domain models:
   - `PositionContext` - uses **Hand** domain model
   - `HandEvaluation` - primitive values
   - `MatrixPayload` - uses **HandRange** domain model
   - `PrecomputeProgress` - simple progress tracking
   - Enums: `Position`, `Action`, `MetricType`

4. **Create** files in your project:
   ```
   aof_gto_browser_ii_v2/
   ├── shared/
   │   ├── domain/
   │   │   ├── __init__.py
   │   │   ├── card.py          ← Card + Rank + Suit enums
   │   │   ├── hand.py          ← Hand (2 Card objects)
   │   │   ├── hand_range.py    ← HandRange (from shorthand)
   │   │   └── board.py         ← Board (0-5 cards)
   │   ├── models/
   │   │   ├── __init__.py
   │   │   ├── context.py       ← PositionContext (uses Hand)
   │   │   ├── result.py        ← HandEvaluation, MatrixPayload (uses HandRange)
   │   │   ├── progress.py      ← PrecomputeProgress
   │   │   └── enums.py         ← Position, Action, MetricType
   ```

---

## The Implementation Path

```
Week 1: Shared Models ✅ (You start here)
    ↓
Week 2-3: Backend Services (Pure logic, testable)
    ↓
Week 4-5: Frontend State & Components (GUI)
    ↓
Week 6: Integration & Polish
```

---

## Key Files in `implementation/` Folder

| Document | Purpose | Read When |
|----------|---------|-----------|
| **00_IMPLEMENTATION_STRATEGY.md** | Overall roadmap | Orientation (gives you big picture) |
| **01_DOMAIN_MODELS/** | Domain model definitions | This week (foundation for DTOs) |
| **01_DOMAIN_MODELS/00_INDEX.md** | Domain model overview | Now |
| **01_DOMAIN_MODELS/01_DOMAIN_Card.md** | Card type (Rank + Suit) | Now |
| **01_DOMAIN_MODELS/02_DOMAIN_Hand.md** | Hand type (2 Card objects) | Now |
| **01_DOMAIN_MODELS/03_DOMAIN_HandRange.md** | HandRange type (from shorthand) | Now |
| **01_DOMAIN_MODELS/01_DOMAIN_Card.md** *(Solver Integration section)* | **CardAdapter** for poker solver libraries (PokerKit, Treys, etc.) | When using solvers |
| **CARD_AND_HAND_ABSTRACTION.md** *(Section 6.5)* | **Solver Library Integration** best practices | When integrating new solvers |
| **04_INTEGRATION_DTOs_and_DomainModels.md** | API boundaries explained | Now (critical!) |
| **02_SHARED_MODELS/** | DTOs that depend on domain models | This week (your main task) |
| **02_SHARED_MODELS/00_INDEX.md** | DTO overview | Next (after domain models) |
| **02_SHARED_MODELS/01_DTO_PositionContext.md** | Input DTO (uses Hand) | Next |
| **02_SHARED_MODELS/05_DTO_MatrixPayload.md** | Output DTO (uses HandRange) | Next |
| (Future) **03_DATABASE_LAYER/** | Database design | Later (supports shared models) |
| (Future) **04_BACKEND_SERVICES/** | Business logic | Week 2 |
| (Future) **05_FRONTEND_STATE/** | GUI state | Week 3 |

---

## Decision: Dataclass or Pydantic?

For shared models, **use dataclass + manual validation**:

```python
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

class Position(Enum):
    BTN = "btn"
    CO = "co"

@dataclass(frozen=True)  # Immutable (safe for threading)
class PositionContext:
    position: Position
    pot_size_bb: float
    bet_amount_bb: float
    num_opponents: int
    board: Optional[str] = None
    
    def __post_init__(self):
        """Validate constraints."""
        if self.pot_size_bb <= 0:
            raise ValueError("pot_size_bb must be positive")
        if not 1 <= self.num_opponents <= 5:
            raise ValueError("num_opponents must be 1-5")

@dataclass
class HandEvaluation:
    hand_key: str
    equity: float
    win_probability: float
    loss_probability: float
    draw_probability: float
    ev: float
    eqr: float
    
    def __post_init__(self):
        """Validate probabilities."""
        total = (self.win_probability + self.loss_probability + 
                 self.draw_probability)
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Probabilities sum to {total}, not 1.0")
```

**Why**:
- ✅ Simple (just dataclass + validation)
- ✅ Small dependencies
- ✅ Fast
- ✅ Type-safe with Python 3.9+
- ❌ Not auto-validated on creation

---

## Reusable Code from Existing App

You can reuse from `python/hopilot/`:

```python
# From existing app, can extract/reuse:
✅ AllInFoldGTOSolver (core solver)
✅ PokerAnalyzer (hand evaluation)
✅ DatabaseConnection (DB setup)
✅ SQLAlchemy models (or adapt)
✅ Configuration loading

❌ AoFBrowserPanel (too entangled)
❌ pygame components (will rewrite cleaner)
❌ State machine logic (will simplify)
```

---

## Today's Tasks

### ✅ Do This Now

1. **Navigate to** `docs/aof_gto_browser_ii/implementation/`
2. **Read** `00_IMPLEMENTATION_STRATEGY.md` (15 min)
3. **Read** `02_SHARED_MODELS/README.md` (20 min)
4. **Identify** what shared models you need
5. **Create** `shared/` package structure in your repo

### 📝 Create This Week

```python
# shared/enums.py
class Position(Enum):
    UTG, HJ, CO, BTN, SB, BB

class Action(Enum):
    FOLD, CALL, RAISE, MIN_RAISE, etc.

class MetricType(Enum):
    EQUITY, EV, WIN_LOSE, EQR

# shared/context_models.py
@dataclass(frozen=True)
class PositionContext:
    position: Position
    pot_size_bb: float
    bet_amount_bb: float
    num_opponents: int
    board: Optional[str] = None

# shared/result_models.py
@dataclass(frozen=True)
class HandEvaluation:
    hand_key: str
    equity: float
    win_probability: float
    loss_probability: float
    draw_probability: float
    ev: float
    eqr: float

@dataclass
class CellDisplay:
    hand_key: str
    row: int
    col: int
    value: str
    color_rgb: Tuple[int, int, int]
    is_computed: bool

@dataclass
class MatrixPayload:
    cells: List[CellDisplay]
    metric: MetricType
    min_value: float
    max_value: float
    mean_value: float
    total_computed: int
    legend_colors: Dict[float, Tuple[int, int, int]]

# shared/progress_models.py
@dataclass
class PrecomputeProgress:
    session_id: str
    percentage: float
    completed_cells: int
    total_cells: int
    elapsed_seconds: float
    estimated_remaining_seconds: Optional[float]
    status: str
```

### ✅ By End of Week 1

- [ ] All shared models defined
- [ ] Team reviewed and approved
- [ ] Ready for backend team to implement services
- [ ] Ready for frontend team to use in state management

---

## The Big Picture

```
Phase 1: Week 1 (Foundation)
├── Shared Models ← YOU START HERE
└── Database Setup

Phase 2: Weeks 2-3 (Backend Logic)
├── Repository (data access)
├── AnalysisService (facade)
└── PrecomputeService (orchestration)
    ↓ [BACKEND TEAM DELIVERS WORKING SERVICES]

Phase 3: Weeks 4-5 (Frontend UI)
├── StateManager (view state)
├── EventHandler (input routing)
├── Presenters (data formatting)
└── GUI Components (pygame)
    ↓ [FRONTEND TEAM DELIVERS WORKING GUI]

Phase 4: Week 6 (Integration)
├── Wire services + GUI
├── Test end-to-end
├── Configure & deploy
└── Done!
```

---

## Success Looks Like

**At the end of Week 1:**
```
✅ shared/enums.py - all position/action/metric types
✅ shared/context_models.py - what we ask backend to compute
✅ shared/result_models.py - what backend returns
✅ shared/progress_models.py - computation progress
✅ Docstrings and validation rules defined
✅ Team aligned on interfaces
```

**At the end of Week 2-3:**
```
✅ Backend services fully implemented
✅ Repository working (queries DB)
✅ AnalysisService callable
✅ PrecomputeService running
✅ 80%+ test coverage
```

**By end of Week 6:**
```
✅ Full application working
✅ User can click to query matrix
✅ User can start precompute
✅ Results display and update
✅ Configuration system integrated
```

---

## Files Structure You'll Create

```
aof_gto_browser_ii/  (new project folder)
│
├── shared/                     ← Start here (Week 1)
│   ├── __init__.py
│   ├── enums.py
│   ├── context_models.py
│   ├── result_models.py
│   └── progress_models.py
│
├── backend/                    ← Week 2-3
│   ├── solver/
│   ├── analysis/
│   ├── database/
│   └── config/
│
├── frontend/                   ← Week 4-5
│   ├── gui/
│   ├── components/
│   ├── presenters/
│   └── services/
│
├── tests/                      ← Throughout
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── main.py                     ← Integration point
├── config.yaml                 ← Configuration
└── requirements.txt            ← Dependencies
```

---

## Next: Create First File

```bash
# Create the project
mkdir aof_gto_browser_ii_v2
cd aof_gto_browser_ii_v2
mkdir -p shared tests

# Create shared models
touch shared/__init__.py
touch shared/enums.py
touch shared/context_models.py
touch shared/result_models.py
touch shared/progress_models.py
```

Then fill them in based on [02_SHARED_MODELS/README.md](02_SHARED_MODELS/README.md).

---

## Questions Before Starting?

1. **Project location?** Where should new `aof_gto_browser_ii` live? (Sibling to existing app?)
2. **Python version?** Which Python version to target? (3.9, 3.10, 3.11, 3.12?)
3. **Reuse database?** Keep existing database schema or start fresh?
4. **Team size?** How many developers working on this?
5. **Timeline?** 6 weeks realistic for your team?

Document your answers in `implementation_decisions.md` when ready.

---

## 🎯 Recommended Reading Order

1. **RIGHT NOW**: This file (5 min)
2. **This morning**: `00_IMPLEMENTATION_STRATEGY.md` (15 min)
3. **This afternoon**: `02_SHARED_MODELS/README.md` (20 min)
4. **Start designing**: Shared models
5. **Get approval**: From team leads
6. **Begin implementation**: Week 2

---

**You're ready to start! Go design those shared models.** 🚀

Questions? Refer to `02_SHARED_MODELS/README.md` which has templates and examples.
