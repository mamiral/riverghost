# Data Model: Phase 1.2 - Shared Models & DTOs

**Status**: Design Definition (Phase 1)  
**Last Updated**: April 3, 2026

## Entity Overview

Phase 1.2 defines 13 data model classes:
- **3 Enumerations** (value types): Position, Action, MetricType
- **3 Input DTOs** (frontend → backend): PositionContext, ActionContext, AnalysisRequest
- **4 Output DTOs** (backend → frontend): HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress
- **3 Domain Model references** (from Phase 1.1): Hand, HandRange, Board

---

## Enumerations

### Position
**Purpose**: Identify seat position at the poker table (4-max, all-in/fold)  
**Values**: UTG, BTN, SB, BB  
**Inheritance**: `str, Enum` (string-inheriting for serialization)  
**Canonical Order**: [UTG, BTN, SB, BB]

```python
class Position(str, Enum):
    UTG = "utg"
    BTN = "btn"
    SB = "sb"
    BB = "bb"
```

**Validation**:
- Must be one of 4 members
- Lowercase string values for serialization
- Support creation by name (`Position["BTN"]`), value (`Position("btn")`), attribute (`Position.BTN`)

---

### Action
**Purpose**: Binary decision at a position (all-in or fold)  
**Values**: FOLD, ALL_IN  
**Inheritance**: `str, Enum`

```python
class Action(str, Enum):
    FOLD = "fold"
    ALL_IN = "all_in"
```

**Validation**: Only FOLD or ALL_IN allowed; no other actions.

---

### MetricType
**Purpose**: Display metric for analysis results  
**Values**: EQUITY, EV, EQR, WIN_LOSE_PROBABILITY  
**Inheritance**: `str, Enum`  
**Alignment**: Matches Phase 1.1 EquityResult metrics

```python
class MetricType(str, Enum):
    EQUITY = "equity"
    EV = "ev"
    EQR = "eqr"
    WIN_LOSE_PROBABILITY = "win_lose_probability"
```

**Validation**: Must be valid MetricType member.

---

## Input DTOs (Frontend → Backend)

### PositionContext
**Purpose**: Describe a poker position to analyze  
**Lifecycle**: Created by frontend when user selects position; sent to backend in AnalysisRequest  
**Immutability**: frozen=True (immutable, thread-safe, hashable)

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|-----------|-------|
| `position` | `Position` | ✅ | — | Must be valid Position enum | UTG, BTN, SB, BB |
| `num_opponents` | `int` | ✅ | — | Must be 1-3 (4-max), raises ValueError | 1=HU, 2=3-way, 3=4-way |
| `heroes_hole_cards` | `Optional[Hand]` | ❌ | `None` | If provided, Hand domain model only | None = GTO analysis |
| `pot_size_bb` | `float` | ❌ | `1.0` | Must be > 0, not NaN/Inf | Blind units |

**Relationships**:
- Depends on Phase 1.1 Hand domain model (if heroes_hole_cards provided)
- Used by ActionContext (wraps PositionContext)
- Used by AnalysisRequest (as position_context field)

**Helper Methods**: None (data container only)

---

### ActionContext
**Purpose**: Specify an action at a position  
**Lifecycle**: Optional; used when analyzing specific action decisions  
**Immutability**: frozen=True

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| `position_context` | `PositionContext` | ✅ | Must be valid PositionContext instance |
| `action` | `Action` | ✅ | Must be Action.FOLD or Action.ALL_IN |

**Relationships**:
- Wraps PositionContext (composition)
- Optional in AnalysisRequest (not required for MVP)

**Helper Method**:
```python
@property
def is_aggressive(self) -> bool:
    """Returns True if action is ALL_IN, False if FOLD."""
    return self.action == Action.ALL_IN
```

---

### AnalysisRequest ⛔ **CRITICAL**
**Purpose**: Complete analysis request contract between frontend and backend  
**Status**: BLOCKER for Phase 2 (AnalysisService, PrecomputeService depend on this)  
**Lifecycle**: Frontend creates after user finishes configuration; backend validates atomically before processing  
**Immutability**: frozen=True  
**Documented At**: [02b_DTO_AnalysisRequest.md](../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/02b_DTO_AnalysisRequest.md) (authoritative reference)

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|-----------|-------|
| `position_context` | `PositionContext` | ✅ | — | Must be valid PositionContext | Core position definition |
| `opponent_range` | `Optional[HandRange]` | ❌ | `None` | If provided, HandRange domain model only | None = all hands |
| `metric_type` | `MetricType` | ❌ | `MetricType.EQUITY` | Must be valid MetricType enum | Display metric |
| `precompute` | `bool` | ❌ | `False` | Must be boolean | Full convergence if True |
| `session_id` | `Optional[str]` | ❌ | `None` | Non-empty string if provided | Opaque tracking ID (Phase 2+ handles continuity) |

**Relationships**:
- Wraps PositionContext
- Optionally references HandRange (Phase 1.1)
- References MetricType enum
- Returned by helpers: with_opponent_range(), with_metric_type()

**Helper Properties**:
```python
@property
def is_heads_up(self) -> bool:
    """True if 1 opponent, False for 2+."""

@property
def is_partial_request(self) -> bool:
    """True if analyzing hero's specific hand, False if GTO (hand unknown)."""

@property
def is_precompute_requested(self) -> bool:
    """True if full matrix precomputation requested."""

@property
def effective_opponent_range(self) -> HandRange:
    """Returns provided range or all hands if None."""
```

**Helper Methods** (functional style):
```python
def with_opponent_range(self, range_shorthand: str) -> 'AnalysisRequest':
    """Create new request with specified opponent range."""

def with_metric_type(self, metric: MetricType) -> 'AnalysisRequest':
    """Create new request with different metric type."""
```

**Critical Properties**:
- Enables atomic validation before backend processing
- Single contract point between frontend/backend teams
- session_id for request tracking/logging (Phase 2+ implements continuity)
- Immutability enables caching and thread-safety

---

## Output DTOs (Backend → Frontend)

### HandEvaluation
**Purpose**: Metrics for a single poker hand  
**Lifecycle**: Created by backend during analysis; aggregated into MatrixPayload  
**Immutability**: frozen=True

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|-----------|-------|
| `hand_key` | `str` | ✅ | — | Must match canonical format (see FR-021) | e.g., "AKs", "AKo", "AA" |
| `equity` | `float` | ✅ | — | Must be 0.0-1.0 | Probability of winning |
| `equity_std` | `float` | ❌ | `0.0` | Must be ≥ 0 | Standard deviation |
| `ev` | `float` | ❌ | `0.0` | Any real number (negative OK) | Expected value in dollars |
| `win_probability` | `float` | ❌ | `0.0` | Must be 0.0-1.0 | P(win) |
| `tie_probability` | `float` | ❌ | `0.0` | Must be 0.0-1.0 | P(tie) |
| `lose_probability` | `float` | ❌ | `0.0` | Must be 0.0-1.0 | P(lose); sum ≈ 1.0 |
| `win_money` | `float` | ❌ | `0.0` | Must be ≥ 0 | Expected winnings |
| `lose_money` | `float` | ❌ | `0.0` | Must be ≥ 0 | Expected losses |
| `num_simulations` | `int` | ❌ | `0` | If is_computed=True, must be > 0 | Sample size |
| `is_computed` | `bool` | ❌ | `True` | Must be boolean | True if calculated, False if estimated |

**Relationships**:
- No dependencies on other DTOs (standalone metrics)
- Used by MatrixPayload (dict of 169 HandEvaluation objects)
- Used by CellDisplay (formatted version)

**Helper Methods**: None (raw metrics container)

---

### MatrixPayload
**Purpose**: Complete 13x13 matrix of all 169 hands for a position  
**Lifecycle**: Returned by backend after analysis; contains all raw evaluations  
**Immutability**: frozen=True  
**Critical Validation**: Exactly 169 hands with correct keys (FR-021)

| Field | Type | Required | Validation | Notes |
|-------|------|----------|-----------|-------|
| `cells` | `Dict[str, HandEvaluation]` | ✅ | Must have exactly 169 keys (all poker hands) | Main payload |
| `query_context` | `PositionContext` | ✅ | Must be valid PositionContext | Original request |
| `opponent_range` | `Optional[HandRange]` | ❌ | If provided, HandRange domain model | Opponent constraints |
| `metric_type` | `MetricType` | ✅ | Must be valid MetricType | Display metric |
| `average_equity` | `float` | ❌ | Must match average of all 169 cells | Mean equity |
| `average_equity_pairs` | `float` | ❌ | Mean of 13 pair hands | Filtered stat |
| `average_equity_suited` | `float` | ❌ | Mean of 78 suited combos | Filtered stat |
| `average_equity_unsuited` | `float` | ❌ | Mean of 78 unsuited combos | Filtered stat |
| `median_equity` | `float` | ❌ | Must match 50th percentile | Robust measure |
| `all_computed` | `bool` | ❌ | `True` if fully converged, `False` if partial | Confidence flag |
| `total_simulations` | `int` | ❌ | Sum of simulations across 169 hands | Sample size |
| `computed_at` | `str` | ❌ | ISO 8601 timestamp (e.g., "2026-04-03T14:30:45Z") | Metadata |

**Relationships**:
- Wraps 169 HandEvaluation objects
- References PositionContext (original request)
- References optional HandRange (Phase 1.1)
- Referenced by MetricType enum

**Hand Key Format** (FR-021):
- **Pairs**: AA, KK, QQ, JJ, TT, 99, 88, 77, 66, 55, 44, 33, 22 (13 total)
- **Suited**: AKs, AQs, AJs, ATs, A9s, ... down to 32s (78 total)
- **Unsuited**: AKo, AQo, AJo, ATo, A9o, ... down to 32o (78 total)
- **Total**: 13 + 78 + 78 = 169 hands

**Helper Methods**:
```python
@staticmethod
def _generate_all_hand_keys() -> set:
    """Generate all 169 canonical hand keys."""

def get_hand(self, hand_key: str) -> HandEvaluation:
    """Retrieve evaluation for specific hand, raises KeyError if not found."""

def get_hands_by_type(self, hand_type: str) -> Dict[str, HandEvaluation]:
    """Get hands by type: 'pairs', 'suited', 'unsuited'."""
```

---

### CellDisplay
**Purpose**: Display-ready cell for rendering in 13x13 matrix GUI  
**Lifecycle**: Created by Presenter (Phase 3.1) from MatrixPayload and MetricType  
**Immutability**: frozen=True

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|-----------|-------|
| `hand_key` | `str` | ✅ | — | Must match FR-021 format | e.g., "AKs" |
| `metric_value` | `float` | ✅ | — | Depends on metric type | Raw metric |
| `display_text` | `str` | ✅ | — | Formatted metric string | e.g., "52.3%", "+$2.34" |
| `background_color` | `tuple[int,int,int]` | ✅ | — | RGB 0-255 each component | Cell background |
| `text_color` | `tuple[int,int,int]` | ✅ | — | RGB 0-255 | Text color |
| `border_color` | `tuple[int,int,int]` | ✅ | — | RGB 0-255 | Border color |
| `is_computed` | `bool` | ❌ | `True` | Boolean | True if converged |
| `confidence` | `float` | ❌ | `0.5` | Must be 0.0-1.0 | Convergence confidence |
| `show_border` | `bool` | ❌ | `False` | Boolean | Draw border if True |
| `highlight_level` | `int` | ❌ | `0` | Must be 0-3 | Highlight intensity |
| `is_hovering` | `bool` | ❌ | `False` | Boolean | Hover state |
| `is_selected` | `bool` | ❌ | `False` | Boolean | Selected state |
| `opacity` | `float` | ❌ | `1.0` | Must be 0.0-1.0 | Transparency |
| `tooltip_text` | `Optional[str]` | ❌ | `None` | String if provided | On-hover hint |
| `secondary_text` | `Optional[str]` | ❌ | `None` | String if provided | Additional display |

**Relationships**:
- Created from HandEvaluation + MetricType
- Used by GUI rendering (Phase 3.2)
- No dependency on other DTOs

**Rendering Hints**:
- `is_computed=False`: Show "estimated" indicator
- `highlight_level`: 0=none, 1=subtle, 2=medium, 3=strong
- `confidence` correlates with opacity for convergence visualization

---

### PrecomputeProgress
**Purpose**: Track long-running precomputation progress  
**Lifecycle**: Streamed from backend to frontend during precomputation (WebSocket/polling)  
**Immutability**: frozen=True

| Field | Type | Required | Validation | Notes |
|-------|------|----------|-----------|-------|
| `session_id` | `str` | ✅ | Non-empty string | Links to parent AnalysisRequest |
| `total_hands` | `int` | ✅ | Must be 169 (or 1 for single hand analysis) | Total work units |
| `hands_completed` | `int` | ✅ | Must be 0-total_hands | Progress |
| `percent_complete` | `float` | ✅ | Must equal hands_completed/total_hands | Progress percentage |
| `estimated_seconds_remaining` | `float` | ✅ | Must be ≥ 0 | ETA |
| `is_complete` | `bool` | ✅ | True if percent_complete=1.0 | Completion flag |

**Relationships**:
- References session_id from AnalysisRequest
- Streamed during matrix computation (Phase 2.1)

**Validation Rules**:
- `percent_complete` must equal `hands_completed / total_hands`
- `is_complete` ⇔ `percent_complete == 1.0`
- `estimated_seconds_remaining` must be consistent with rate

---

## Entity Relationship Diagram

```
┌──────────────────┐
│  Enumerations    │
├──────────────────┤
│ - Position       │
│ - Action         │
│ - MetricType     │
└─────────┬────────┘
          │ uses
          │
     ┌────▼──────────────────┐
     │  Input DTOs           │
     ├─────────────────────  │
     │ PositionContext ─────┐│  (references Hand from Phase 1.1)
     │   - position         ││
     │   - num_opponents    ││
     │   - heroes_hole_cards││
     │   - pot_size_bb      ││
     │                      ││
     │ ActionContext        ││  (wraps PositionContext)
     │   - position_context ││
     │   - action           ││
     │                      ││
     │ AnalysisRequest ⛔   ││  CRITICAL/BLOCKER
     │   - position_context ││
     │   - opponent_range   ││  (references HandRange from Phase 1.1)
     │   - metric_type      ││
     │   - precompute       ││
     │   - session_id       ││
     └────┬─────────────────┘│
          │ sent to          │
          │                  │
     ┌────▼──────────────────┐
     │  Backend Services     │ (Phase 2.1+)
     │ (AnalysisService)    │
     └────┬──────────────────┘
          │ returns
          │
     ┌────▼──────────────────┐
     │  Output DTOs          │
     ├──────────────────────  │
     │ HandEvaluation        │  (single hand metrics)
     │   - hand_key          │
     │   - equity            │
     │   - ev, eqr, ...      │
     │   - num_simulations   │
     │                       │
     │ MatrixPayload         │  (all 169 hands)
     │   - cells: Dict[str, HandEvaluation]
     │   - query_context     │  (references PositionContext)
     │   - opponent_range    │  (references HandRange)
     │   - metric_type       │
     │   - precomputed stats │
     │                       │
     │ PrecomputeProgress    │  (streamed during computation)
     │   - session_id        │
     │   - hands_completed   │
     │   - percent_complete  │
     │   - estimated_seconds │
     │                       │
     │ CellDisplay           │  (formatted for rendering)
     │   - hand_key          │
     │   - metric_value      │
     │   - display_text      │
     │   - colors, hints     │
     │   - interaction state │
     └──────────────────────┘
              │ sent to
              │
         ┌────▼─────────────┐
         │  Frontend GUI    │ (Phase 3.2+)
         │  (pygame render) │
         └──────────────────┘
```

---

## Data Flow

```
Frontend                          Backend
   │                                 │
User configures position ────────► AnalysisRequest
   │                                 │
   │◄─────────────● Validate atomically
   │              │ - PositionContext valid
   │              │ - HandRange valid
   │              │ - MetricType valid
   │              │ - session_id trackable
   │              │
   │              ├─► AnalysisService creates job
   │              │
   │              ├─► For each of 169 hands:
   │              │   - Simulate vs opponent_range
   │              │   ├─► HandEvaluation
   │              │   └─► emit PrecomputeProgress
   │              │
   │◄─────────────● PrecomputeProgress (10%, 25%, ...)
   │  Display     │ (streamed updates)
   │  progress bar│
   │              │
   │              ├─► Aggregate 169 HandEvaluations
   │              │
   │◄─────────────● MatrixPayload (all cells)
   │              │ (query_context, metric_type, aggregates)
   │              │
   ├─► Presenter ─┤
   │   (Phase 3.1)│ HandEvaluation + MetricType
   │              │        ↓
   │              │    CellDisplay (formatted)
   │
   ├─► Render ───┤
   │   (pygame)   │ 13x13 matrix with colors
```

---

## Validation Rules Summary

**All DTOs validate in `__post_init__()` with no external dependencies:**

| Field | Validation Rule |
|-------|-----------------|
| Position enum | Must be UTG, BTN, SB, or BB |
| MetricType enum | Must be EQUITY, EV, EQR, or WIN_LOSE_PROBABILITY |
| num_opponents | 1 ≤ num_opponents ≤ 3 |
| pot_size_bb | pot_size_bb > 0 (not NaN/Inf) |
| heroes_hole_cards | Either None or Hand domain model (type check) |
| opponent_range | Either None or HandRange domain model (type check) |
| equity (HandEvaluation) | 0.0 ≤ equity ≤ 1.0 |
| Probabilities | 0.0 ≤ prob ≤ 1.0; sum ≈ 1.0 (±0.01 tolerance) |
| cells (MatrixPayload) | Exactly 169 keys; all from FR-021 hand format |
| Colors (CellDisplay) | 0 ≤ R, G, B ≤ 255 each |
| confidence (CellDisplay) | 0.0 ≤ confidence ≤ 1.0 |
| opacity (CellDisplay) | 0.0 ≤ opacity ≤ 1.0 |
| session_id | Non-empty string if provided |
| percent_complete | Must equal hands_completed / total_hands |

---

## Testing Strategy

**Unit Tests** (by entity):
- Each enum: creation, conversion, invalid values
- Each DTO: valid creation, immutability, each validation rule, edge cases
- Total: 100+ test cases

**Integration Tests**:
- PositionContext + HandRange combination (valid/invalid)
- AnalysisRequest with various opponent ranges
- MatrixPayload with all 169 hands (hand key validation)
- CellDisplay color validation with MatrixPayload values
- PrecomputeProgress consistency checks

**Edge Cases**:
- heroes_hole_cards = None (GTO analysis)
- opponent_range = None (all hands)
- all_computed = False (partial results)
- pot_size_bb = 0.01 (tiny pot)
- pot_size_bb = 1000.0 (large pot)
- num_opponents variations (1, 2, 3)
- Metric switching (EQUITY → EV without recomputation)

---

## Success Criteria

- [ ] All 13 classes defined, frozen=True, immutable
- [ ] All validation paths tested (100+ cases)
- [ ] ≥95% code coverage
- [ ] Hand key format FR-021 implemented (all 169 keys)
- [ ] AnalysisRequest complete with 30+ tests (BLOCKER)
- [ ] Docstrings complete with usage examples
- [ ] No external dependencies (stdlib + Phase 1.1)
- [ ] JSON-serializable (domain models handle their own)
