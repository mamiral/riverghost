# Quickstart: Using Phase 1.2 Shared DTOs

**For**: Frontend developers, backend developers, analysis service implementers  
**Phase**: 1.2 (Shared Models & DTOs)  
**Updated**: April 3, 2026

---

## Installation & Imports

Once Phase 1.2 is complete, import DTOs from the shared models package:

```python
# All imports from the same package
from aof_gto_browser_ii.shared.models import (
    # Enumerations
    Position, Action, MetricType,
    # Input DTOs
    PositionContext, ActionContext, AnalysisRequest,
    # Output DTOs
    HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress,
)

# If you need domain models from Phase 1.1
from aof_gto_browser_ii.shared.domain import Hand, HandRange, Board
```

---

## Common Use Cases

### 1. Frontend: User Selects a Position

```python
# User clicks "Button, heads-up (1 opp), no hand specified"
position_context = PositionContext(
    position=Position.BTN,           # User selected button
    num_opponents=1,                 # Heads-up
    heroes_hole_cards=None,          # Not specified (GTO)
    pot_size_bb=1.0                  # Default 1 big blind
)

# This object is immutable and thread-safe
print(position_context.position)  # Position.BTN
print(position_context.num_opponents)  # 1

# # Try to modify (will fail)
# position_context.position = Position.SB  # 🚫 AttributeError: frozen dataclass
```

**Validation Examples**:
```python
# ✅ Valid: Position must be enum
ctx = PositionContext(Position.BTN, num_opponents=1)

# ❌ Invalid: Wrong position type
try:
    ctx = PositionContext("btn", num_opponents=1)  # String, not Position
except ValueError as e:
    print(e)  # "position must be Position enum, got <class 'str'>"

# ❌ Invalid: num_opponents out of range
try:
    ctx = PositionContext(Position.BTN, num_opponents=4)
except ValueError as e:
    print(e)  # "num_opponents must be 1-3 (4 max players), got 4"
```

---

### 2. Frontend: Send Analysis Request to Backend

```python
from aof_gto_browser_ii.shared.domain import HandRange

# User configured position (from step 1 above)
position_context = PositionContext(Position.BTN, num_opponents=1)

# User optionally specified opponent range and metric
opponent_range = HandRange.from_shorthand("22+,AKs,AQo")  # Phase 1.1 domain model
metric_type = MetricType.EQUITY

# Create the complete analysis request
request = AnalysisRequest(
    position_context=position_context,
    opponent_range=opponent_range,
    metric_type=metric_type,
    precompute=False,  # Quick analysis, don't converge
    session_id="sess_user_001_btn_1v1"  # Track this request
)

# Send to backend (serialized via JSON or gRPC)
# Backend will validate atomically in its handler
print(request.is_heads_up)  # True
print(request.is_partial_request)  # False (no hero hand specified)
print(request.effective_opponent_range)  # HandRange (provided range)
```

**Using Functional Methods**:
```python
# User clicks "Switch metric to EV"
new_request = request.with_metric_type(MetricType.EV)
# Now metric_type=EV but all other fields unchanged (functional style)
print(new_request.metric_type)  # MetricType.EV

# User clicks "Analyze vs all hands instead"
all_hands_request = request.with_opponent_range("*")
# Now opponent_range=all hands

# Chain methods (fluent interface)
refined = request.with_opponent_range("TT+,AKs").with_metric_type(MetricType.EQR)
```

---

### 3. Backend: Validate Incoming Request

```python
def analyze_position(request_json: dict) -> MatrixPayload:
    """
    Backend handler receives JSON payload.
    First step: Deserialize and validate.
    """
    
    # Deserialize from JSON (framework handles this)
    # Assume request_json looks like:
    # {
    #   "position_context": {
    #       "position": "btn",
    #       "num_opponents": 1,
    #       "heroes_hole_cards": null,
    #       "pot_size_bb": 1.0
    #   },
    #   "opponent_range": "22+,AKs,AQo",
    #   "metric_type": "equity",
    #   "precompute": false,
    #   "session_id": "sess_001"
    # }
    
    # Reconstruct DTOs from JSON (framework handles, or manual mapping)
    try:
        position_ctx = PositionContext(
            position=Position(request_json["position_context"]["position"]),
            num_opponents=request_json["position_context"]["num_opponents"],
            # ... etc
        )
        request = AnalysisRequest(
            position_context=position_ctx,
            # ... other fields
        )
    except ValueError as e:
        # Validation failed; return error to frontend
        return {"error": str(e)}
    
    # Now request is valid; proceed with analysis
    return compute_analysis(request)
```

---

### 4. Backend: Compute and Return Results

```python
from aof_gto_browser_ii.shared.domain import Hand

def compute_analysis(request: AnalysisRequest) -> MatrixPayload:
    """
    Backend analysis engine.
    Returns typed MatrixPayload to frontend.
    """
    
    cells = {}
    
    # Generate all 169 poker hands
    for hand_key in MatrixPayload._generate_all_hand_keys():
        # Evaluate this hand
        equity = simulate_hand_vs_range(
            hand=hand_key,
            position_context=request.position_context,
            opponent_range=request.effective_opponent_range
        )
        
        # Create HandEvaluation for this hand
        cells[hand_key] = HandEvaluation(
            hand_key=hand_key,
            equity=equity,
            ev=equity * request.position_context.pot_size_bb * 2,
            # ... other metrics
        )
    
    # Compute aggregates
    all_equities = [ev.equity for ev in cells.values()]
    
    # Return typed payload
    return MatrixPayload(
        cells=cells,
        query_context=request.position_context,
        opponent_range=request.opponent_range,
        metric_type=request.metric_type,
        average_equity=sum(all_equities) / len(all_equities),
        all_computed=True,
        total_simulations=sum(ev.num_simulations for ev in cells.values()),
        computed_at="2026-04-03T14:30:45Z"
    )
    
    # MatrixPayload is immutable and validates 169 hands during creation
    # If any hand missing or invalid key → ValueError raised
```

---

### 5. Backend: Stream Progress Updates

```python
# During long-running precomputation
def precompute_full_matrix(request: AnalysisRequest, session_id: str):
    """
    Precompute all 169 hands with full convergence.
    Stream PrecomputeProgress updates to frontend.
    """
    
    total_hands = 169
    hands_completed = 0
    
    for i, hand_key in enumerate(MatrixPayload._generate_all_hand_keys()):
        # Simulate this hand until convergence (more sims than quick analysis)
        simulate_hand_fully(hand_key, request)
        
        hands_completed += 1
        
        # Create progress update
        progress = PrecomputeProgress(
            session_id=session_id,
            total_hands=total_hands,
            hands_completed=hands_completed,
            percent_complete=hands_completed / total_hands,
            estimated_seconds_remaining=estimate_remaining(hands_completed, total_hands),
            is_complete=(hands_completed == total_hands)
        )
        
        # Send to frontend (WebSocket, polling, etc.)
        websocket.send(progress.to_json())
        
        # progress object is frozen and guaranteed consistent
        # (percent_complete always equals hands_completed / total_hands)
```

---

### 6. Frontend: Receive and Format Results

```python
def display_matrix_results(payload: MatrixPayload):
    """
    Backend returned MatrixPayload.
    Transform into GUI-ready CellDisplay objects.
    """
    
    cells_to_display = []
    
    # Iterate all 169 hands
    for hand_key, hand_eval in payload.cells.items():
        # Format metric value based on MetricType
        if payload.metric_type == MetricType.EQUITY:
            display_text = f"{hand_eval.equity * 100:.1f}%"
            metric_value = hand_eval.equity
        elif payload.metric_type == MetricType.EV:
            display_text = f"${hand_eval.ev:.2f}"
            metric_value = hand_eval.ev
        else:
            display_text = str(hand_eval.equity)  # Default
            metric_value = hand_eval.equity
        
        # Choose color based on value
        if metric_value > 0.55:
            bg_color = (50, 200, 50)  # Green: strong
        elif metric_value > 0.45:
            bg_color = (200, 200, 50)  # Yellow: marginal
        else:
            bg_color = (200, 50, 50)  # Red: weak
        
        # Create display-ready cell
        cell_display = CellDisplay(
            hand_key=hand_key,
            metric_value=metric_value,
            display_text=display_text,
            background_color=bg_color,
            text_color=(0, 0, 0),
            border_color=(100, 100, 100),
            is_computed=payload.all_computed,
            confidence=0.95 if payload.all_computed else 0.50,
            show_border=False,
            highlight_level=0,
            is_hovering=False,
            is_selected=False,
            opacity=1.0,
            tooltip_text=f"{hand_key}: {display_text}"
        )
        
        cells_to_display.append(cell_display)
    
    # Render cells (pygame or web framework)
    render_matrix(cells_to_display)
```

---

## Instantiation Checklists

### PositionContext

**Required Fields**:
- [ ] `position: Position` — UTG, BTN, SB, or BB
- [ ] `num_opponents: int` — 1, 2, or 3

**Optional Fields**:
- [ ] `heroes_hole_cards: Optional[Hand]` — Hand.from_strings("Ah", "Kd") or None
- [ ] `pot_size_bb: float` — Positive number (default 1.0)

```python
# Minimal valid creation
ctx = PositionContext(position=Position.BTN, num_opponents=1)

# Fully specified
ctx = PositionContext(
    position=Position.UTG,
    num_opponents=2,
    heroes_hole_cards=Hand.from_strings("Ah", "Kd"),  # From Phase 1.1
    pot_size_bb=10.0
)
```

---

### AnalysisRequest ⛔ **CRITICAL**

**Required Fields**:
- [ ] `position_context: PositionContext` — Fully valid PositionContext

**Optional Fields** (with sensible defaults):
- [ ] `opponent_range: Optional[HandRange]` — None (all hands) or "22+,AKs,..."
- [ ] `metric_type: MetricType` — Default MetricType.EQUITY
- [ ] `precompute: bool` — Default False (quick analysis)
- [ ] `session_id: Optional[str]` — Tracking ID (default None)

```python
# Minimal (quick analysis of all hands, equity metric)
request = AnalysisRequest(
    position_context=PositionContext(Position.BTN, num_opponents=1)
)

# Fully specified
request = AnalysisRequest(
    position_context=PositionContext(Position.UTG, num_opponents=2),
    opponent_range=HandRange.from_shorthand("22+,AKs"),
    metric_type=MetricType.EV,
    precompute=True,  # Full convergence
    session_id="sess_user_001_utg"
)
```

---

### MatrixPayload

**Required Fields**:
- [ ] `cells: Dict[str, HandEvaluation]` — Exactly 169 hands
- [ ] `query_context: PositionContext` — Invalid PositionContext raises error
- [ ] `metric_type: MetricType` — Valid MetricType enum

**Optional Aggregates**:
- [ ] `opponent_range: Optional[HandRange]`
- [ ] `average_equity`, `average_equity_pairs`, etc. — Auto-calculated if not provided
- [ ] `all_computed: bool` — Default True
- [ ] `total_simulations: int` — Sum of all sims
- [ ] `computed_at: str` — ISO 8601 timestamp

```python
# Validation: must have exactly 169 keys
cells = {hand_key: HandEvaluation(...) for hand_key in all_169_hands}
payload = MatrixPayload(
    cells=cells,
    query_context=position_context,
    metric_type=MetricType.EQUITY
)
# If cells has 168 or 170 hands → ValueError raised
```

---

## Common Pitfalls

❌ **Don't**: Import domain models within Phase 1.2 implementation
```python
# WRONG: Phase 1.1 models should not appear in shared.models
from shared.models import Hand  # Hand is in domain, not models
```

✅ **Do**: Reference Phase 1.1 models by type hint only
```python
from shared.domain import Hand, HandRange

class PositionContext:
    heroes_hole_cards: Optional[Hand]  # Type hint only
```

---

❌ **Don't**: Mutate DTOs
```python
request = AnalysisRequest(...)
request.metric_type = MetricType.EV  # 🚫 FrozenInstanceError
```

✅ **Do**: Use functional methods
```python
new_request = request.with_metric_type(MetricType.EV)
```

---

❌ **Don't**: Assume session continuation in Phase 1.2
```python
# Phase 1.2 DTOs only carry session_id for tracking
# Implementation of checkpoints, state restoration is Phase 2+
session_id = request.session_id  # Opaque identifier for logging
```

✅ **Do**: Defer session handling to AnalysisService (Phase 2.1)
```python
# Phase 2.1 backend will implement:
# - Session state persistence
# - Checkpoint resumption
# - Retry semantics
```

---

## API Contracts

### Frontend → Backend

```json
POST /api/analysis
Content-Type: application/json

{
  "position_context": {
    "position": "btn",
    "num_opponents": 1,
    "heroes_hole_cards": null,
    "pot_size_bb": 1.0
  },
  "opponent_range": "22+,AKs,AQo",
  "metric_type": "equity",
  "precompute": false,
  "session_id": "sess_001"
}

→ Response (MatrixPayload)
{
  "cells": {
    "AA": {"hand_key": "AA", "equity": 0.523, "ev": 0.523, ...},
    "AKs": {"hand_key": "AKs", "equity": 0.495, ...},
    ...  // 169 total
  },
  "query_context": { ... },
  "metric_type": "equity",
  "average_equity": 0.490,
  "all_computed": false,
  "total_simulations": 50000,
  "computed_at": "2026-04-03T14:30:45Z"
}
```

### Backend → Frontend (WebSocket Progress)

```json
{
  "session_id": "sess_001",
  "total_hands": 169,
  "hands_completed": 42,
  "percent_complete": 0.2486,
  "estimated_seconds_remaining": 285,
  "is_complete": false
}
```

---

## Next Steps

1. **Phase 1.2 Implementation**: Build the 10 DTOs + 3 enums per `plan.md`
2. **Testing**: 100+ tests covering validation, immutability, hand key validation
3. **Phase 2.1**: Implement AnalysisService consuming AnalysisRequest
4. **Phase 3.1**: Implement MatrixPresenter transforming MatrixPayload → CellDisplay
5. **Phase 3.2**: Render CellDisplay objects in GUI (pygame)

---

## References

- **Spec**: [spec.md](spec.md) — Full functional + non-functional requirements
- **Plan**: [plan.md](plan.md) — Implementation timeline and delivery checklist
- **Data Model**: [data-model.md](data-model.md) — Entity definitions and relationships
- **AnalysisRequest Docs**: [02b_DTO_AnalysisRequest.md](../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/02b_DTO_AnalysisRequest.md) — Detailed reference
- **Phase 1.1**: Domain Models (Card, Hand, HandRange, Board, EquityResult, Bet)
