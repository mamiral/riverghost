# DTO: AnalysisRequest

## Purpose

**CRITICAL REQUEST CONTRACT** between frontend and backend. Encapsulates a complete analysis request with all parameters needed for the backend to execute analysis.

**Why Critical**: Phase 2 Backend Services (AnalysisService, PrecomputeService) depend on this DTO structure. It enables atomic validation, session tracking, and request queuing.

**Sent By**: Frontend (after user configures position and analysis options)  
**Received By**: AnalysisService, PrecomputeService  
**Triggers**: Complete analysis computation (full matrix or specific hand)  
**Immutable**: Yes (frozen=True)

---

## Specification

```python
from dataclasses import dataclass
from typing import Optional
from shared.models import PositionContext
from shared.domain.hand_range import HandRange
from shared.enums import MetricType

@dataclass(frozen=True)
class AnalysisRequest:
    """Complete analysis request: combines position context with analysis parameters.
    
    This is the PRIMARY REQUEST CONTRACT between frontend and backend.
    It encapsulates everything needed for backend to execute analysis.
    
    Critical for Phase 2: Backend services depend on this DTO structure.
    """
    
    position_context: PositionContext
    opponent_range: Optional[HandRange] = None
    metric_type: MetricType = MetricType.EQUITY
    precompute: bool = False
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate all fields atomically."""
        if not isinstance(self.position_context, PositionContext):
            raise ValueError(
                f"position_context must be PositionContext, got {type(self.position_context)}"
            )
        
        if self.opponent_range and not isinstance(self.opponent_range, HandRange):
            raise ValueError(
                f"opponent_range must be HandRange domain model, got {type(self.opponent_range)}"
            )
        
        if not isinstance(self.metric_type, MetricType):
            raise ValueError(
                f"metric_type must be MetricType enum, got {type(self.metric_type)}"
            )
        
        if not isinstance(self.precompute, bool):
            raise ValueError(f"precompute must be bool, got {type(self.precompute)}")
        
        if self.session_id is not None:
            if not isinstance(self.session_id, str):
                raise ValueError(f"session_id must be string, got {type(self.session_id)}")
            if len(self.session_id) == 0:
                raise ValueError("session_id must be non-empty string if provided")
    
    @property
    def is_heads_up(self) -> bool:
        """Returns True if heads-up (1 opponent)."""
        return self.position_context.num_opponents == 1
    
    @property
    def is_partial_request(self) -> bool:
        """Returns True if only computing for hero's specific hand (not full matrix)."""
        return self.position_context.heroes_hole_cards is not None
    
    @property
    def is_precompute_requested(self) -> bool:
        """Returns True if full matrix precomputation requested."""
        return self.precompute
    
    @property
    def effective_opponent_range(self) -> HandRange:
        """Returns opponent range, defaulting to all hands if not specified."""
        if self.opponent_range:
            return self.opponent_range
        return HandRange.from_shorthand("*")  # All hands
    
    def with_opponent_range(self, range_shorthand: str) -> 'AnalysisRequest':
        """Create a new request with specified opponent range (functional style)."""
        new_range = HandRange.from_shorthand(range_shorthand)
        return AnalysisRequest(
            position_context=self.position_context,
            opponent_range=new_range,
            metric_type=self.metric_type,
            precompute=self.precompute,
            session_id=self.session_id
        )
    
    def with_metric_type(self, metric: MetricType) -> 'AnalysisRequest':
        """Create a new request with different metric type (functional style)."""
        return AnalysisRequest(
            position_context=self.position_context,
            opponent_range=self.opponent_range,
            metric_type=metric,
            precompute=self.precompute,
            session_id=self.session_id
        )
```

---

## Fields

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|-----------|-------|
| `position_context` | `PositionContext` | ✅ | — | Must be valid PositionContext instance | Complete position description |
| `opponent_range` | `Optional[HandRange]` | ❌ | `None` | Must be HandRange domain model if provided | Analyzes vs all hands if None |
| `metric_type` | `MetricType` | ❌ | `MetricType.EQUITY` | Must be valid MetricType enum | Display metric (EQUITY, EV, EQR, WIN_LOSE) |
| `precompute` | `bool` | ❌ | `False` | Must be boolean | Full 169-hand convergence if True |
| `session_id` | `Optional[str]` | ❌ | `None` | Non-empty string if provided | Tracks related requests, enables continuation |

---

## When to Use AnalysisRequest

### ✅ Use When:
- Frontend is ready to send a position analysis to backend
- User has selected position, action, opponent range, metric type
- Starting a precomputation session
- Resuming a previous computation (same session_id)

### ❌ Don't Use:
- Just storing user's position selection (use PositionContext alone)
- Before user has finished configuring analysis parameters

---

## Critical Property: Request Contracts

**AnalysisRequest is the single point of contract** between frontend and backend:
- Frontend knows exactly what to package
- Backend knows exactly what to expect
- Enables validation before computation starts
- Supports async processing, queuing, session resumption

---

## Usage Examples

### Example 1: Full Matrix Analysis (All Hands, All-In/Fold)
```python
# User: "Analyze all hands from button vs 1 opponent, precompute everything"
request = AnalysisRequest(
    position_context=PositionContext(
        position=Position.BTN,
        num_opponents=1,
        heroes_hole_cards=None,  # Unknown hand (GTO)
        pot_size_bb=1.0
    ),
    opponent_range=None,  # Analyze vs all hands
    metric_type=MetricType.EQUITY,
    precompute=True,  # Full precomputation
    session_id="sess_user_001_btn_1v1"
)

# Backend workflow:
# 1. Validate request (all fields valid types, PositionContext valid)
# 2. Save session with session_id
# 3. Spawn precomputation worker
# 4. Compute all 169 hands with equity metric
# 5. Store results in database
# 6. Emit progress updates to frontend

# Frontend displays:
# - Progress bar: 0% → 100%
# - Current hand: "AA" → "32o"
# - ETA countdown
# - Complete matrix when done
```

### Example 2: Specific Hand Analysis with Custom Opponent Range
```python
# User: "Analyze AK from UTG vs 2 tough opponents who play 22+,AKs,AQo"
request = AnalysisRequest(
    position_context=PositionContext(
        position=Position.UTG,
        num_opponents=2,
        heroes_hole_cards=Hand.from_strings("Ah", "Kd"),  # AKo
        pot_size_bb=10.0
    ),
    opponent_range=HandRange.from_shorthand("22+,AKs,AQo"),
    metric_type=MetricType.EV,
    precompute=False,  # Quick computation
    session_id="sess_user_001_utg_ak_vs_22"
)

# Backend workflow:
# 1. Validate request
# 2. Evaluate only AKo (not all 169)
# 3. Compute vs specified opponent range (not all hands)
# 4. Return MatrixPayload with single hand cell
# 5. Frontend displays: "AKo vs 22+,AKs,AQo EV: +$2.34"
```

### Example 3: Metric Switching (No Recomputation)
```python
# User already analyzed position, now wants to switch metric view
# Previous request computed all 169 hands with EQUITY metric
previous_request = AnalysisRequest(
    position_context=PositionContext(...),
    metric_type=MetricType.EQUITY,
    precompute=True,
    session_id="sess_001"
)
# Backend returned MatrixPayload with all evaluations

# Now user clicks "Show EV instead of Equity"
# Frontend creates new request with SAME session but different metric
new_request = previous_request.with_metric_type(MetricType.EV)

# Backend workflow:
# 1. Validate request
# 2. Lookup session_id in database
# 3. Retrieve existing MatrixPayload for same position
# 4. Re-format cells from EQUITY metric to EV metric
# 5. Return reformatted MatrixPayload (NO recomputation!)
# 6. Frontend renders same data, different display format
```

### Example 4: Two-Stage Analysis (Quick Estimate → Full Convergence)
```python
# Stage 1: User wants quick estimate (iterate fast)
quick_request = AnalysisRequest(
    position_context=PositionContext(
        position=Position.BTN,
        num_opponents=1,
        heroes_hole_cards=None,
        pot_size_bb=1.0
    ),
    opponent_range=None,
    metric_type=MetricType.EQUITY,
    precompute=False,  # Quick, not full convergence
    session_id="sess_quick_btn_1v1"
)

# Backend: computes 50k simulations per hand (rough estimate)
# Returns MatrixPayload with all_computed=False, total_simulations=50k
# Frontend displays: "Results estimated (50k sims, not converged)"

# Stage 2: User clicks "Refine for accuracy" 
refine_request = AnalysisRequest(
    position_context=quick_request.position_context,
    opponent_range=quick_request.opponent_range,
    metric_type=quick_request.metric_type,
    precompute=True,  # Full convergence
    session_id="sess_quick_btn_1v1"  # SAME session = continuation
)

# Backend workflow:
# 1. Lookup session_id in database (finds existing results)
# 2. Detect precompute=True (user wants full convergence)
# 3. Load existing state from database
# 4. Continue computation from where we left off (checkpoint)
# 5. Run additional simulations until convergence criteria met
# 6. Update database with final results
# 7. Return MatrixPayload with all_computed=True

# Frontend displays: "Refining... 25% → 50% → 75% → 100%"
```

### Example 5: Heads-Up Detection
```python
# User selects heads-up scenario
request = AnalysisRequest(
    position_context=PositionContext(
        position=Position.BB,
        num_opponents=1,  # Heads-up
        heroes_hole_cards=None,
        pot_size_bb=2.0  # Small blind posted
    )
)

# Code can use helper property:
if request.is_heads_up:
    print("Running heads-up analysis")
    print(f"Request targets {request.position_context.position.value} position")
```

---

## Code Template

```python
# shared/models/input_context.py

from dataclasses import dataclass
from typing import Optional
from shared.enums import MetricType
from shared.domain.hand_range import HandRange
from shared.models import PositionContext

@dataclass(frozen=True)
class AnalysisRequest:
    """Complete analysis request: PRIMARY CONTRACT between frontend and backend.
    
    Attributes:
        position_context: Complete poker position to analyze
        opponent_range: Opponent's hand range (None = all hands)
        metric_type: What metric to display (EQUITY, EV, EQR, WIN_LOSE_PROBABILITY)
        precompute: Whether to fully converge all 169 hands
        session_id: Unique identifier for this request group (enables continuation)
    
    This DTO enables Phase 2 backend services to:
    - Validate entire request atomically
    - Track computation across sessions
    - Support request queuing and async processing
    - Resume interrupted computations
    """
    
    position_context: PositionContext
    opponent_range: Optional[HandRange] = None
    metric_type: MetricType = MetricType.EQUITY
    precompute: bool = False
    session_id: Optional[str] = None
    
    def __post_init__(self):
        if not isinstance(self.position_context, PositionContext):
            raise ValueError(f"position_context must be PositionContext, got {type(self.position_context)}")
        
        if self.opponent_range and not isinstance(self.opponent_range, HandRange):
            raise ValueError(f"opponent_range must be HandRange domain model, got {type(self.opponent_range)}")
        
        if not isinstance(self.metric_type, MetricType):
            raise ValueError(f"metric_type must be MetricType enum, got {type(self.metric_type)}")
        
        if not isinstance(self.precompute, bool):
            raise ValueError(f"precompute must be bool, got {type(self.precompute)}")
        
        if self.session_id is not None:
            if not isinstance(self.session_id, str):
                raise ValueError(f"session_id must be string, got {type(self.session_id)}")
            if len(self.session_id) == 0:
                raise ValueError("session_id must be non-empty string if provided")
    
    @property
    def is_heads_up(self) -> bool:
        """Returns True if heads-up (1 opponent), False otherwise."""
        return self.position_context.num_opponents == 1
    
    @property
    def is_partial_request(self) -> bool:
        """Returns True if analyzing specific hand only (not full matrix)."""
        return self.position_context.heroes_hole_cards is not None
    
    @property
    def is_precompute_requested(self) -> bool:
        """Returns True if full matrix precomputation requested."""
        return self.precompute
    
    @property
    def effective_opponent_range(self) -> HandRange:
        """Returns opponent range, defaulting to all hands if not specified."""
        if self.opponent_range:
            return self.opponent_range
        return HandRange.from_shorthand("*")
    
    def with_opponent_range(self, range_shorthand: str) -> 'AnalysisRequest':
        """Create new request with different opponent range (functional style)."""
        new_range = HandRange.from_shorthand(range_shorthand)
        return AnalysisRequest(
            position_context=self.position_context,
            opponent_range=new_range,
            metric_type=self.metric_type,
            precompute=self.precompute,
            session_id=self.session_id
        )
    
    def with_metric_type(self, metric: MetricType) -> 'AnalysisRequest':
        """Create new request with different metric type (functional style)."""
        return AnalysisRequest(
            position_context=self.position_context,
            opponent_range=self.opponent_range,
            metric_type=metric,
            precompute=self.precompute,
            session_id=self.session_id
        )
```

---

## Interaction Diagram

```
Frontend                          Backend
   │                                 │
   │  User configures position       │
   │  (BTN, 1 opp, AKo, 10BB)       │
   │                                 │
   │  User selects opponent range    │
   │  (all hands, 22+,AKs, custom)   │
   │                                 │
   │  User selects metric            │
   │  (EQUITY, EV, EQR, etc)         │
   │                                 │
   │  User clicks "Analyze"          │
   ├─────────────────────────────────>│
   │  AnalysisRequest                │
   │  {position, range, metric,      │
   │   precompute, session_id}       │
   │                                 │
   │                      Validate   │
   │                    <──────────  │──┐
   │                                 │  │
   │                     Start       │  │
   │                   computation    │  │
   │                    ────────>  ┌──┐ │
   │  PrecomputeProgress (0%)       │  │ │
   │  <──────────────────────────────┤  │
   │  (repeat: 10%, 25%, 50%, etc)   │  │
   │  <──────────────────────────────┤  │
   │  MatrixPayload (100%)           │  │
   │  <──────────────────────────────┘  │
   │                                    │
   │  Display matrix                    │
   │    ✓                               │
```

---

## Why This DTO is Critical

1. **Atomic Validation**: Backend validates entire request at once (position, range, metric) before computation
2. **Session Tracking**: `session_id` enables resuming interrupted computations
3. **Contract Clarity**: Frontend/Backend have explicit, typed interface
4. **Enables Parallelism**: With clear contract, teams can implement independently
5. **Async Processing**: Requests can be queued, cached, processed out-of-order
6. **Extensibility**: Easy to add new request parameters (sampling_intensity, hand_restriction, etc.) without breaking existing code

---

## Relationship to Other DTOs

```
     AnalysisRequest (ENTRY POINT)
            │
            ├─> Contains: PositionContext
            │             ActionContext (optional)
            │
            └─> Returns: MatrixPayload → List[CellDisplay]
                                      ↓
                        PrecomputeProgress (streaming)
```

---

## Testing Checklist

- [ ] Valid creation with all required/optional fields
- [ ] Immutability: frozen=True prevents modification
- [ ] Validation: position_context must be PositionContext instance
- [ ] Validation: opponent_range must be HandRange if provided
- [ ] Validation: metric_type must be MetricType enum
- [ ] Validation: precompute must be boolean
- [ ] Validation: session_id must be non-empty string if provided
- [ ] Properties work: is_heads_up, is_partial_request, is_precompute_requested, effective_opponent_range
- [ ] Functional methods work: with_opponent_range(), with_metric_type()
- [ ] Chaining works: request.with_opponent_range(...).with_metric_type(...)
- [ ] Hash consistency: identical requests hash the same (frozen dataclass)
- [ ] Repr works: __repr__ includes all fields
- [ ] 30+ edge case tests covering all scenarios from examples
