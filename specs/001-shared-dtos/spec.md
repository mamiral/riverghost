# Feature Specification: Phase 1.2 - Shared Models & DTOs

**Feature Branch**: `001-shared-dtos`  
**Created**: April 3, 2026  
**Status**: Draft  
**Phase**: Foundation (Week 1, Days 2-3)  
**Depends On**: Phase 1.1 (Domain Models: Card, Hand, HandRange, Board, EquityResult, Bet)

## Overview

Define all Data Transfer Objects (DTOs) and enumeration types that compose the frontend-backend contract. These immutable, validated dataclasses depend ONLY on Domain Models from Phase 1.1 and stdlib—no UI, database, or service dependencies.

**Time to Complete**: 2-3 days  
**Complexity**: ⭐ (Easy)  
**Risk**: Low  
**Success Criteria**: All 10 models defined with full validation, 100+ test cases covering behavior

### 📖 Reference Documentation

Detailed specifications for each DTO are documented in the **[02_SHARED_MODELS folder](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/)**:

- **[PositionContext](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/01_DTO_PositionContext.md)** - Position specification
- **[ActionContext](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/02_DTO_ActionContext.md)** - Action specification
- **[AnalysisRequest](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/02b_DTO_AnalysisRequest.md)** - **[CRITICAL]** Complete analysis request contract
- **[HandEvaluation](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/04_DTO_HandEvaluation.md)** - Single hand evaluation results
- **[MatrixPayload](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/05_DTO_MatrixPayload.md)** - Complete 13x13 matrix results
- **[CellDisplay](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/06_DTO_CellDisplay.md)** - Display-ready cell formatting
- **[DetailPayload](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/07_DTO_DetailPayload.md)** - Detail panel data
- **[PrecomputeProgress](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/08_DTO_PrecomputeProgress.md)** - Progress tracking
- **[Enums](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/00_INDEX.md)** - Position, Action, MetricType enums

---

## 🚨 CRITICAL BLOCKERS

### ✅ AnalysisRequest DTO (CRITICAL/BLOCKER - RESOLVED)

**Status**: ✅ RESOLVED - Complete documentation now available

**Rationale**: AnalysisRequest is the **primary request contract** between frontend and backend. Backend services (AnalysisService, PrecomputeService) depend on this DTO. Without it defined, Phase 2 (Backend Services) cannot proceed.

**📖 Detailed Documentation**: See **[AnalysisRequest Reference Document](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/02b_DTO_AnalysisRequest.md)** in the implementation folder for complete specification including:
- Full dataclass specification with immutability and validation
- Interaction diagrams showing request flow
- 5 detailed usage examples (full matrix, specific hand, metric switching, two-stage analysis, heads-up)
- Code template ready for implementation
- Critical property explanations and testing checklist

**Resolution Complete**: AnalysisRequest is fully specified with:
- ✅ Complete field documentation (5 fields with validation rules)
- ✅ Validation rules in `__post_init__()` 
- ✅ Code template (production-ready)
- ✅ Test cases (30+ scenarios documented)
- ✅ Usage examples in docstrings (4 detailed examples)
- ✅ Reference document created and indexed in 02_SHARED_MODELS folder

---

## Clarifications

### Session 2026-04-03

- Q: Should PositionContext include GameType field (CASH/TOURNAMENT/MTT/SNG)? → A: **B** - Remove GameType, simplify to position+opponents only. Add as optional future extension in Phase 1.3+.
  - **Impact**: PositionContext spec simplified (4 fields → 4 fields without game_type). GameType deferred to database models layer where it can be tracked per session without duplicating in every request.

- Q: Define canonical hand key format for 169 poker hands? → A: **A** - Define canonical format with explicit order (pairs first, suits/unsuites organized).
  - **Impact**: Added FR-021 specifying format "AKs", "AKo", "AA", etc. Added canonical order: 13 pairs, 78 suited, 78 unsuited. MatrixPayload validation can now check for exact key set match.

- Q: Define session lifecycle and continuation strategy? → A: **A** - Treat session_id as opaque identifier for Phase 1.2; defer session management to Phase 2+.
  - **Impact**: session_id is for request tracking/logging only in Phase 1.2. No guaranteed continuation or state persistence semantics. Session lifecycle (checkpoints, resumption, retry) is AnalysisService/PrecomputeService responsibility (Phase 2.1+). Updated FR-008 and field table to clarify.

---

## User Scenarios & Testing

### User Story 1 - Frontend Sends Analysis Request (Priority: P1)

A poker player opens the analyzer GUI, selects "Button position, heads-up pre-flop analysis, all-in/fold," and clicks "Analyze". The frontend must package this request into a validated `PositionContext` and send it to the backend.

**Why this priority**: Core workflow—without this, no analysis can be requested. Foundation for all downstream services.

**Independent Test**: `PositionContext` can be created with valid position, opponent count, and optional hand. Invalid data raises `ValueError`. This alone enables "request a position" use case.

**Acceptance Scenarios**:

1. **Given** user selects "Button, heads-up (1 opponent), no hole cards specified"
   **When** frontend creates `PositionContext(position=Position.BTN, num_opponents=1, pot_size_bb=1.0)`
   **Then** object is successfully created and immutable (frozen)

2. **Given** user provides invalid input (0 opponents)
   **When** creating `PositionContext(position=Position.BTN, num_opponents=0)`
   **Then** `ValueError` raised with message "num_opponents must be 1-3"

3. **Given** user specifies hero's hand as "King of hearts, King of diamonds"
   **When** creating `PositionContext(..., heroes_hole_cards=Hand.from_strings("Kh", "Kd"))`
   **Then** Hand domain model accepted and stored, immutable after creation

4. **Given** requested position is invalid (e.g., "co_hj" not in enum)
   **When** attempting `PositionContext(position="co_hj")`
   **Then** `ValueError` raised because Position enum rejects invalid values

---

### User Story 2 - Backend Returns Analysis Matrix (Priority: P1)

The backend completes analysis of all 169 poker hands for the requested position. It packages the result into a `MatrixPayload` containing raw equity values, precomputed aggregates, and metadata for frontend display.

**Why this priority**: Core output—without this, analysis results cannot be transmitted back. Required for "display matrix" use case.

**Independent Test**: `MatrixPayload` validates that exactly 169 hands are present with correct keys. `get_hand("AKs")` retrieves evaluation for specific hand. This alone enables "receive and inspect raw results" use case.

**Acceptance Scenarios**:

1. **Given** backend analyzes all 169 hands successfully
   **When** creating `MatrixPayload(cells={hand_key: HandEvaluation, ...}, query_context=..., metric=MetricType.EQUITY)`
   **Then** matrix is immutable and precomputed aggregates are accessible

2. **Given** user requests equity metric view
   **When** `MatrixPayload.metric` is `MetricType.EQUITY`
   **Then** display code formats values as percentages (e.g., "52.3%")

3. **Given** analysis incomplete (only 100 of 169 hands computed)
   **When** creating `MatrixPayload(cells={...100 hands...})`
   **Then** `ValueError` raised: "Matrix must have 169 hands, got 100"

4. **Given** backend tracks computation metadata
   **When** `MatrixPayload` includes `all_computed=False, total_simulations=50000`
   **Then** frontend can display confidence indicator: "Simulations: 50k"

---

### User Story 3 - Presenter Formats Results for Display (Priority: P2)

The `MatrixPresenter` transforms raw `MatrixPayload` into display-ready `CellDisplay` objects with pre-calculated colors, fonts, and rendering hints. The GUI renders these without further processing.

**Why this priority**: Enhanced UX—without this, cells display generic values. Depends on Story 1 & 2 (matrix exists). Can be independently tested by creating CellDisplay mocks.

**Independent Test**: `CellDisplay` validates RGB color tuples (0-255), confidence 0-1.0, opacity 0-1.0. Each cell's immutable properties can be tested independently.

**Acceptance Scenarios**:

1. **Given** equity value is 0.523 (52.3%)
   **When** creating `CellDisplay(metric_value=0.523, display_text="52.3%", background_color=(200, 150, 100))`
   **Then** cell stores immutable display properties ready for rendering

2. **Given** cell is selected by user
   **When** `CellDisplay` includes `is_selected=True, highlight_level=3`
   **Then** GUI uses highlight_level to render border/shadow (no recalculation needed)

3. **Given** invalid color tuple provided `(256, 0, 0)` (256 > 255)
   **When** creating `CellDisplay(..., background_color=(256, 0, 0))`
   **Then** `ValueError` raised: "Color component must be 0-255, got 256"

4. **Given** confidence is 0.85 (moderately confident)
   **When** `CellDisplay.confidence=0.85`
   **Then** opacity can be adjusted proportionally (e.g., opacity=0.85*1.0=0.85)

---

### User Story 4 - Enums Provide Type Safety (Priority: P1)

The system uses enums (`Position`, `Action`, `MetricType`) instead of magic strings. This prevents invalid data at creation time.

**Why this priority**: Foundational type safety. Without enums, invalid positions like "utg_2" pass through undetected.

**Independent Test**: Each enum (Position, Action, MetricType) rejects invalid string values and supports creation by name/value.

**Acceptance Scenarios**:

1. **Given** Position enum defined with UTG, BTN, SB, BB
   **When** creating `Position("btn")`
   **Then** returns `Position.BTN` (value-based creation works)

2. **Given** Position.BTN is created
   **When** converting to string via `str(Position.BTN)`
   **Then** returns "btn" (str mixin enables string conversion)

3. **Given** invalid position "cutoff"
   **When** creating `Position("cutoff")`
   **Then** `ValueError` raised: no enum member with value "cutoff"

4. **Given** Action enum with FOLD and ALL_IN
   **When** creating `Action.FOLD` and `Action.ALL_IN`
   **Then** both are valid, mutually exclusive, and final (immutable)

5. **Given** MetricType enum with EQUITY, EV, EQR, WIN_LOSE_PROBABILITY
   **When** switching display metric via `metric = MetricType.EV`
   **Then** presentation layer interprets as "show Expected Value ($)"

---

### User Story 5 - Input Validation Prevents Bad Data Early (Priority: P1)

All DTOs validate critical business rules in `__post_init__()`. Invalid data raises descriptive errors immediately, before being passed to services.

**Why this priority**: Data integrity—bad data early causes confusion downstream. Validation at source prevents bugs.

**Independent Test**: Each DTO's validation rules can be tested independently (pot_size > 0, num_opponents in range, equity 0-1, etc.).

**Acceptance Scenarios**:

1. **Given** pot_size_bb provided as negative value (-5.0)
   **When** creating `PositionContext(..., pot_size_bb=-5.0)`
   **Then** `ValueError` raised in `__post_init__`: "pot_size_bb must be positive"

2. **Given** num_opponents=4 (too many for 4-max all-in/fold)
   **When** creating `PositionContext(..., num_opponents=4)`
   **Then** `ValueError` raised: "num_opponents must be 1-3 (4 max players)"

3. **Given** equity value 1.5 (impossible, should be 0-1)
   **When** HandEvaluation stored in MatrixPayload with equity=1.5
   **Then** validation in `__post_init__` detects and raises error

4. **Given** confidence metric provided as 1.2 (impossible, should be 0-1)
   **When** creating `CellDisplay(..., confidence=1.2)`
   **Then** `ValueError` raised: "Confidence must be 0.0-1.0, got 1.2"

---

### Edge Cases

- What happens when hero's hand is not provided (None)? System treats as "unknown hand" and calculates GTO vs all hands.
- What happens when multiple analysis requests arrive concurrently? DTOs are frozen (immutable) and thread-safe; services handle concurrency.
- What happens when analysis is incomplete (only 50% of hands computed)? MatrixPayload flag `all_computed=False` indicates partial results.
- What happens when frontend switches metric type (EQUITY → EV)? MatrixPayload contains all evaluations; presenter re-formats cells without re-computing.
- What happens with invalid hand in PositionContext? Hand domain model validation (Phase 1.1) rejects; DTO validation checks instance type.
- What happens with empty opponent range? System analyzes vs entire range (no filtering).

## Requirements

### Functional Requirements

#### Enumerations (Type Safety)

- **FR-001**: System MUST define `Position` enum as string-inheriting enum with 4 members: UTG, BTN, SB, BB (4-max all-in/fold only)
- **FR-002**: System MUST define `Action` enum as string-inheriting enum with 2 members: FOLD, ALL_IN (binary decision only)
- **FR-003**: System MUST define `MetricType` enum as string-inheriting enum with 4 members: EQUITY, EV, EQR, WIN_LOSE_PROBABILITY
- **FR-004**: System MUST support creation of enum members by name (`Position["BTN"]`), value (`Position("btn")`), and attribute (`Position.BTN`)
- **FR-005**: System MUST ensure enum values are strings (inherit from `str`) for easy serialization and display

#### Input DTOs (Frontend → Backend)

- **FR-006**: System MUST define `PositionContext` (immutable, frozen=True) with fields:
  - `position: Position` (required, must be valid Position enum)
  - `num_opponents: int` (required, must be 1-3 for 4-max)
  - `heroes_hole_cards: Optional[Hand]` (optional, must be Hand domain model if provided)
  - `pot_size_bb: float` (optional, default 1.0, must be > 0)
  - **Note**: GameType deferred to Phase 1.3+ (not included in MVP)

- **FR-007**: System MUST define `ActionContext` (immutable, frozen=True) with fields:
  - `position: Position` (required)
  - `action: Action` (required)
  - Validation: action must be valid for position (all-in/fold context)

- **FR-008**: System MUST define `AnalysisRequest` (immutable, frozen=True) as CRITICAL primary request contract with fields:  ⛔ **BLOCKER**
  - `position_context: PositionContext` (required, must be valid instance)
  - `opponent_range: Optional[HandRange]` (optional, defaults to all hands)
  - `metric_type: MetricType` (optional, defaults to EQUITY)
  - `precompute: bool` (optional, defaults to False)
  - `session_id: Optional[str]` (optional, for request tracking and logging; opaque identifier—session management deferred to Phase 2+)
  - Validation: position_context valid, opponent_range is HandRange if provided, metric_type valid enum, session_id non-empty string if provided
  - **Note**: Session lifecycle (persistence, continuation, retry semantics) is Phase 2+ (AnalysisService/PrecomputeService implementation). Phase 1.2 DTOs treat session_id as opaque tracking identifier only.
  - Helper methods: `is_heads_up()`, `is_partial_request()`, `is_precompute_requested()`, `effective_opponent_range()`, `with_opponent_range()`, `with_metric_type()`
  - Purpose: **Complete encapsulation of analysis request; enables backend to validate entire request atomically before processing; required for Phase 2 backend services to proceed**

#### Output DTOs (Backend → Frontend)

- **FR-009**: System MUST define `HandEvaluation` (immutable) for single hand results with:
  - `hand_key: str` (e.g., "AKs")
  - `equity: float` (0.0-1.0, required)
  - `ev: float` (dollars, can be negative)
  - `eqr: float` (equity-to-risk ratio, >= 0)
  - `win_lose_probability: float` (-1.0 to 1.0)

- **FR-010**: System MUST define `MatrixPayload` (immutable) with:
  - `cells: Dict[str, HandEvaluation]` (must have exactly 169 hands)
  - `query_context: PositionContext` (original request)
  - `opponent_range: Optional[HandRange]`
  - `metric: MetricType` (display metric)
  - Precomputed aggregates: `average_equity`, `average_equity_pairs`, `average_equity_suited`, `average_equity_unsuited`
  - Metadata: `all_computed: bool`, `total_simulations: int`, `computed_at: str` (ISO format)
  - Method `get_hand(hand_key: str) → HandEvaluation`
  - Method `get_all_hands_by_type(hand_type: str) → Dict[str, HandEvaluation]`

- **FR-011**: System MUST define `CellDisplay` (immutable) for rendering-ready data:
  - `hand_key: str`, `metric_value: float`, `display_text: str`
  - Colors: `background_color: tuple` (RGB 0-255), `text_color: tuple`, `border_color: tuple`
  - Rendering hints: `is_computed: bool`, `confidence: float` (0.0-1.0), `show_border: bool`, `highlight_level: int` (0-3)
  - Interaction state: `is_hovering: bool`, `is_selected: bool`, `opacity: float` (0.0-1.0)
  - Optional: `tooltip_text: Optional[str]`, `secondary_text: Optional[str]`

- **FR-012**: System MUST define `PrecomputeProgress` (immutable) for tracking long-running analysis:
  - `session_id: str` (unique identifier)
  - `total_hands: int` (should be 169)
  - `hands_completed: int` (0-169)
  - `percent_complete: float` (0.0-1.0)
  - `estimated_seconds_remaining: float`
  - `is_complete: bool`

#### Validation & Immutability

- **FR-013**: All DTOs MUST use `frozen=True` in dataclass decorator (immutable, thread-safe, hashable)
- **FR-014**: All DTOs MUST implement `__post_init__()` for validation (no external validator framework)
- **FR-015**: System MUST raise `ValueError` with descriptive messages for all validation failures:
  - Out-of-range numeric values (pot_size <= 0, num_opponents not 1-3, equity not 0-1, confidence not 0-1)
  - Invalid enum values (position not in Position enum)
  - Type mismatches (hand not Hand instance, color not tuple)
  - Business rule violations (matrix not 169 hands)
- **FR-016**: All validation messages MUST include actual vs expected values for debugging

#### Dependencies & Constraints

- **FR-017**: System MUST have ZERO external dependencies except: `dataclasses`, `typing`, `enum` (stdlib only)
- **FR-018**: System MUST import ONLY from Phase 1.1 Domain Models: `Hand`, `HandRange`, `Board`, `Card`, `EquityResult`, `Bet`
- **FR-019**: System MUST NOT import from: GUI modules, database modules, service modules, frontend state management
- **FR-020**: All types MUST be serializable to JSON (for API contracts) except Hand/HandRange/Board (domain models handle their own serialization)

#### Hand Key Format Convention

- **FR-021**: System MUST use canonical hand key format for all 169 poker hands:
  - **Format**: `"{Rank}{Rank}"` for pairs, `"{Rank1}{Rank2}{Suit}"` for combos
  - **Ranks**: Uppercase letters A, K, Q, J, T, 9, 8, 7, 6, 5, 4, 3, 2 (13 ranks total)
  - **Suit Indicator**: `"s"` for suited, `"o"` for unsuited (lowercase)
  - **Examples**: `"AA"` (pair), `"AKs"` (ace-king suited), `"AKo"` (ace-king unsuited), `"32o"` (deuce-trey unsuited)
  - **Canonical Order** (169 hands total):
    - Pairs first (13): AA, KK, QQ, JJ, TT, 99, 88, 77, 66, 55, 44, 33, 22
    - Suited combos (78): AKs, AQs, AJs, ATs, A9s, A8s, A7s, A6s, A5s, A4s, A3s, A2s, KQs, KJs, KTs, K9s, ... 32s
    - Unsuited combos (78): AKo, AQo, AJo, ATo, A9o, A8o, A7o, A6o, A5o, A4o, A3o, A2o, KQo, KJo, KTo, K9o, ... 32o
  - **All keys are strings** (not tuples or objects); JSON-serializable
  - **Case-sensitive**: "AKs" ≠ "Aks" (always uppercase ranks, lowercase suit indicator)

---

### PositionContext Fields

| Field | Type | Required | Default | Validation | Example |
|-------|------|----------|---------|-----------|---------|
| `position` | `Position` | ✅ | — | Must be valid Position enum (UTG, BTN, SB, BB) | `Position.BTN` |
| `num_opponents` | `int` | ✅ | — | Must be 1-3 (inclusive), raises `ValueError` if outside range | `2` |
| `heroes_hole_cards` | `Optional[Hand]` | ❌ | `None` | If provided, must be Hand domain model (not string), not tuple | `Hand.from_strings("Kh", "Kd")` |
| `pot_size_bb` | `float` | ❌ | `1.0` | Must be > 0, not NaN/Inf, raises `ValueError` if invalid | `10.0` |

**Validation in `__post_init__()`**:
```python
def __post_init__(self):
    if not isinstance(self.position, Position):
        raise ValueError(f"position must be Position enum, got {type(self.position)}")
    
    if self.num_opponents < 1 or self.num_opponents > 3:
        raise ValueError(f"num_opponents must be 1-3 (4 max players), got {self.num_opponents}")
    
    if self.pot_size_bb <= 0:
        raise ValueError(f"pot_size_bb must be positive, got {self.pot_size_bb}")
    
    if self.heroes_hole_cards and not isinstance(self.heroes_hole_cards, Hand):
        raise ValueError(f"heroes_hole_cards must be Hand domain model, got {type(self.heroes_hole_cards)}")
```

### ActionContext Fields

| Field | Type | Required | Validation | Example |
|-------|------|----------|-----------|---------|
| `position_context` | `PositionContext` | ✅ | Must be valid PositionContext instance | `PositionContext(...)` |
| `action` | `Action` | ✅ | Must be Action.FOLD or Action.ALL_IN (binary all-in/fold only), raises `ValueError` for invalid actions | `Action.ALL_IN` |

**Validation in `__post_init__()`**:
```python
def __post_init__(self):
    if not isinstance(self.position_context, PositionContext):
        raise ValueError("position_context must be PositionContext")
    
    if not isinstance(self.action, Action):
        raise ValueError("action must be Action enum")
    
    if self.action not in (Action.FOLD, Action.ALL_IN):
        raise ValueError(f"All-in/fold allows only FOLD or ALL_IN, got {self.action}")
```

**Helper Method**:
```python
@property
def is_aggressive(self) -> bool:
    """Returns True if action is ALL_IN, False if FOLD."""
    return self.action == Action.ALL_IN
```

---

### AnalysisRequest Fields (CRITICAL DTO)

> **📖 See detailed documentation**: [02b_DTO_AnalysisRequest.md](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/02b_DTO_AnalysisRequest.md)
> 
> This is the **authoritative reference** for AnalysisRequest specification. The information below is a summary; the linked document contains complete specification with validation code, helper methods, usage examples, and testing checklist.

| Field | Type | Required | Default | Validation | Example |
|-------|------|----------|---------|-----------|---------|
| `position_context` | `PositionContext` | ✅ | — | Must be valid PositionContext instance with all validations passed | See PositionContext examples |
| `opponent_range` | `Optional[HandRange]` | ❌ | `None` (all hands) | If provided, must be valid HandRange domain model (not string) | `HandRange.from_shorthand("22+,AKs")` |
| `metric_type` | `MetricType` | ❌ | `MetricType.EQUITY` | Must be valid MetricType enum (EQUITY, EV, EQR, WIN_LOSE_PROBABILITY) | `MetricType.EV` |
| `precompute` | `bool` | ❌ | `False` | If True, backend should precompute all 169 hands; if False, compute on-demand | `True` for full matrix |
| `session_id` | `Optional[str]` | ❌ | `None` | If provided, must be non-empty string (opaque identifier); used for request tracking/logging only. **No guaranteed continuation semantics in Phase 1.2** (Phase 2+ concern). | `"sess_abc123xyz"` |

**Why AnalysisRequest is Critical**:
- Encapsulates complete analysis request with all parameters
- Single contract point for frontend → backend communication
- Enables backend to validate entire request atomically before processing
- Supports future extensibility (add new metrics, parameters without breaking API)
- Allows request queuing, caching, and async processing in Phase 2
- **Session Tracking** (Phase 1.2): session_id enables request correlation for logging/debugging; actual session state management (persistence, resumption, retry) is Phase 2+ responsibility

**Validation in `__post_init__()`**:
```python
def __post_init__(self):
    # position_context must be valid PositionContext
    if not isinstance(self.position_context, PositionContext):
        raise ValueError(f"position_context must be PositionContext, got {type(self.position_context)}")
    
    # opponent_range if provided must be HandRange domain model
    if self.opponent_range and not isinstance(self.opponent_range, HandRange):
        raise ValueError(f"opponent_range must be HandRange domain model, got {type(self.opponent_range)}")
    
    # metric_type must be valid enum
    if not isinstance(self.metric_type, MetricType):
        raise ValueError(f"metric_type must be MetricType enum, got {type(self.metric_type)}")
    
    # session_id if provided must be non-empty
    if self.session_id is not None and not isinstance(self.session_id, str):
        raise ValueError(f"session_id must be string, got {type(self.session_id)}")
    
    if self.session_id is not None and len(self.session_id) == 0:
        raise ValueError("session_id must be non-empty string if provided")
    
    # precompute flag must be boolean
    if not isinstance(self.precompute, bool):
        raise ValueError(f"precompute must be bool, got {type(self.precompute)}")
```

**Helper Methods and Properties**:
```python
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
    return self.opponent_range if self.opponent_range else HandRange.from_shorthand("*")  # All hands

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
    """Create a new request with different metric type."""
    return AnalysisRequest(
        position_context=self.position_context,
        opponent_range=self.opponent_range,
        metric_type=metric,
        precompute=self.precompute,
        session_id=self.session_id
    )
```

**Usage Examples**:

**Example 1: Full matrix analysis (all hands, all-in/fold)**
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

# Backend: "Got request, will compute all 169 hands with equity metric"
```

**Example 2: Specific hand analysis with custom opponent range**
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
    precompute=False,  # Just compute this hand
    session_id="sess_user_001_utg_ak_vs_22"
)

# Backend: "Evaluate AKo from UTG vs specified range, return EV"
```

**Example 3: Metric switching (no recomputation needed)**
```python
# User: "Switch from viewing equity to EV for same position"
previous_request = AnalysisRequest(...)  # Already computed

# Create new request with different metric (reuses same computation)
new_request = previous_request.with_metric_type(MetricType.EV)

# Backend: "Use existing MatrixPayload, just reformat cells for EV display"
```

**Example 4: Two-stage analysis (quick then detailed)**
```python
# Stage 1: Quick estimate (50k sims)
quick_request = AnalysisRequest(
    position_context=PositionContext(
        position=Position.BTN,
        num_opponents=1,
        heroes_hole_cards=None,
        pot_size_bb=1.0
    ),
    opponent_range=None,
    metric_type=MetricType.EQUITY,
    precompute=False,
    session_id="sess_quick_btn_1v1"
)
# Backend returns partial MatrixPayload with all_computed=False

# Stage 2: User clicks "refine", backend continues from checkpoint
refine_request = AnalysisRequest(
    position_context=quick_request.position_context,
    opponent_range=quick_request.opponent_range,
    metric_type=quick_request.metric_type,
    precompute=True,  # Full convergence
    session_id="sess_quick_btn_1v1"  # Same session ID = continuation
)
# Backend: "Found session_id, continue from saved state, converge fully"
```

---

| Field | Type | Required | Default | Validation | Range/Example |
|-------|------|----------|---------|-----------|---------------|
| `equity` | `float` | ✅ | — | Must be 0.0-1.0 inclusive, raises `ValueError` if outside | 0.0-1.0 (e.g., 0.523 = 52.3%) |
| `equity_std` | `float` | ❌ | `0.0` | Must be >= 0, standard deviation of equity | 0.0-0.1 (e.g., 0.015 = ±1.5%) |
| `ev` | `float` | ❌ | `0.0` | Can be any real number (negative or positive), in dollars | -5.67 to +10.23 |
| `win_probability` | `float` | ❌ | `0.0` | Must be 0.0-1.0 inclusive | 0.0-1.0 |
| `tie_probability` | `float` | ❌ | `0.0` | Must be 0.0-1.0 inclusive | 0.0-1.0 |
| `lose_probability` | `float` | ❌ | `0.0` | Must be 0.0-1.0 inclusive | 0.0-1.0 |
| `win_money` | `float` | ❌ | `0.0` | Expected dollars won, >= 0 | 0.0-100.0 |
| `lose_money` | `float` | ❌ | `0.0` | Expected dollars lost, >= 0 | 0.0-100.0 |
| `num_simulations` | `int` | ❌ | `0` | If `is_computed=True`, must be > 0; otherwise can be 0 | 1-1000000 |
| `is_computed` | `bool` | ❌ | `True` | True if calculated, False if estimated | `True` or `False` |

**Validation in `__post_init__()`**:
```python
def __post_init__(self):
    # Equity in range
    if not (0.0 <= self.equity <= 1.0):
        raise ValueError(f"equity must be 0.0-1.0, got {self.equity}")
    
    # Probabilities in range
    for prob_name, prob_value in [
        ("win_probability", self.win_probability),
        ("tie_probability", self.tie_probability),
        ("lose_probability", self.lose_probability)
    ]:
        if not (0.0 <= prob_value <= 1.0):
            raise ValueError(f"{prob_name} must be 0.0-1.0, got {prob_value}")
    
    # Probabilities sum to ~1.0 (±0.01 tolerance)
    prob_sum = self.win_probability + self.tie_probability + self.lose_probability
    if not (0.99 <= prob_sum <= 1.01):
        raise ValueError(f"Probabilities must sum to 1.0, got {prob_sum}")
    
    # Computed evaluations require simulation count
    if self.is_computed and self.num_simulations <= 0:
        raise ValueError("Computed evaluation requires num_simulations > 0")
```

### MatrixPayload Fields

| Field | Type | Required | Validation | Notes |
|-------|------|----------|-----------|-------|
| `cells` | `Dict[str, HandEvaluation]` | ✅ | Must have exactly 169 keys: 13 pairs (AA-22) + 156 combos (AKs, AKo, etc.) | Keys: "AA", "AKs", "AKo", ..., "22" |
| `query_context` | `PositionContext` | ✅ | Must be valid PositionContext | Original analysis request |
| `opponent_range` | `Optional[HandRange]` | ❌ | If provided, must be valid HandRange domain model | e.g., "22+,AKs,AQo" |
| `metric_type` | `MetricType` | ✅ | Must be valid MetricType enum (EQUITY, EV, EQR, WIN_LOSE_PROBABILITY) | Display metric |
| `average_equity` | `float` | ❌ | Precomputed mean equity 0.0-1.0, must match computed average of all 169 cells | Statistics aggregate |
| `average_equity_pairs` | `float` | ❌ | Mean equity for pairs only (13 hands: AA-22) | Filtered statistic |
| `average_equity_suited` | `float` | ❌ | Mean equity for all suited combos (13×12/2 = 78 hands) | Filtered statistic |
| `average_equity_unsuited` | `float` | ❌ | Mean equity for all unsuited combos (13×12/2 = 78 hands) | Filtered statistic |
| `median_equity` | `float` | ❌ | Median equity across 169 hands, must match 50th percentile | Robust measure |
| `all_computed` | `bool` | ❌ | `True` if all 169 hands fully converged; `False` if partial/estimated | Confidence flag |
| `total_simulations` | `int` | ❌ | Sum of all simulations across 169 hands | Sample size metric |
| `computed_at` | `str` | ❌ | ISO 8601 timestamp (e.g., "2026-04-03T14:30:45Z") | Metadata |

**Validation in `__post_init__()`**:
```python
def __post_init__(self):
    # Must have exactly 169 hands
    if len(self.cells) != 169:
        raise ValueError(f"Matrix must have 169 hands, got {len(self.cells)}")
    
    # Verify all expected hands present
    expected_hands = self._generate_all_hand_keys()  # 169 valid poker hands
    actual_hands = set(self.cells.keys())
    if actual_hands != expected_hands:
        missing = expected_hands - actual_hands
        raise ValueError(f"Missing hands: {missing}")
    
    # All values are valid HandEvaluation objects (domain model handles validation)
    for hand_key, evaluation in self.cells.items():
        if not isinstance(evaluation, HandEvaluation):
            raise ValueError(f"Cell {hand_key} must be HandEvaluation, got {type(evaluation)}")
```

**Helper Methods**:
```python
@staticmethod
def _generate_all_hand_keys() -> set:
    """Generate all 169 poker hand keys."""
    hands = set()
    ranks = "AKQJT98765432"
    
    # Pairs: AA to 22
    for rank in ranks:
        hands.add(f"{rank}{rank}")
    
    # Combos: AK, AQ, etc.
    for i, rank1 in enumerate(ranks):
        for rank2 in ranks[i+1:]:
            hands.add(f"{rank1}{rank2}s")  # Suited
            hands.add(f"{rank1}{rank2}o")  # Unsuited
    
    return hands

def get_hand(self, hand_key: str) -> HandEvaluation:
    """Retrieve evaluation for a specific hand."""
    if hand_key not in self.cells:
        raise KeyError(f"Hand {hand_key} not found in matrix")
    return self.cells[hand_key]

def get_hands_by_type(self, hand_type: str) -> Dict[str, HandEvaluation]:
    """Get all hands of a type: 'pairs', 'suited', 'unsuited'."""
    if hand_type == "pairs":
        return {k: v for k, v in self.cells.items() if k[0] == k[1]}
    elif hand_type == "suited":
        return {k: v for k, v in self.cells.items() if k.endswith("s")}
    elif hand_type == "unsuited":
        return {k: v for k, v in self.cells.items() if k.endswith("o")}
    else:
        raise ValueError(f"Unknown hand_type: {hand_type}")
```

### CellDisplay Fields

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|----------|-------|
| `hand_key` | `str` | ✅ | — | Must be valid hand notation: "AA", "AKs", "AKo", etc. | Display label |
| `metric_value` | `float` | ✅ | — | Depends on metric type; typically 0.0-1.0 or -1.0 to 1.0 | Raw value |
| `display_text` | `str` | ✅ | — | Pre-formatted string for rendering (e.g., "52.3%", "$5.67") | User-facing text |
| `background_color` | `tuple[int,int,int]` | ✅ | — | RGB tuple where R,G,B each 0-255 inclusive | Heatmap color |
| `text_color` | `tuple[int,int,int]` | ✅ | — | RGB tuple where R,G,B each 0-255 inclusive | Contrast: usually (0,0,0) or (255,255,255) |
| `border_color` | `tuple[int,int,int]` | ✅ | — | RGB tuple where R,G,B each 0-255 inclusive | Outline color |
| `is_computed` | `bool` | ❌ | `True` | `True` if calculated, `False` if estimated/incomplete | Confidence indicator |
| `confidence` | `float` | ❌ | `1.0` | Must be 0.0-1.0 inclusive (0%=uncertain, 100%=certain) | Can affect opacity |
| `show_border` | `bool` | ❌ | `False` | True to draw border around cell | Highlight flag |
| `highlight_level` | `int` | ❌ | `0` | Must be 0-3 (0=none, 1=low, 2=medium, 3=high) | Intensity of highlight |
| `opacity` | `float` | ❌ | `1.0` | Must be 0.0-1.0 inclusive (0=transparent, 1=opaque) | Can mirror confidence |
| `is_hovering` | `bool` | ❌ | `False` | `True` if mouse currently over cell | UI state |
| `is_selected` | `bool` | ❌ | `False` | `True` if user selected cell | UI state |
| `tooltip_text` | `Optional[str]` | ❌ | `None` | Hover text like "52.3% equity (100k sims)" | Help text |
| `secondary_text` | `Optional[str]` | ❌ | `None` | Additional info like "+$5.67" or "Risk: 0.9" | Extra display |

**Validation in `__post_init__()`**:
```python
def __post_init__(self):
    # Validate hand_key is in 169 valid hands
    valid_hands = MatrixPayload._generate_all_hand_keys()
    if self.hand_key not in valid_hands:
        raise ValueError(f"Invalid hand_key: {self.hand_key}, not in {valid_hands}")
    
    # Validate all color tuples are RGB (0-255)
    for color_name, color in [
        ("background_color", self.background_color),
        ("text_color", self.text_color),
        ("border_color", self.border_color)
    ]:
        if not isinstance(color, tuple) or len(color) != 3:
            raise ValueError(f"{color_name} must be RGB tuple (r,g,b), got {color}")
        
        for component in color:
            if not (0 <= component <= 255):
                raise ValueError(f"{color_name} component must be 0-255, got {component}")
    
    # Validate confidence and opacity are 0-1
    if not (0.0 <= self.confidence <= 1.0):
        raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
    
    if not (0.0 <= self.opacity <= 1.0):
        raise ValueError(f"opacity must be 0.0-1.0, got {self.opacity}")
    
    # Validate highlight level is 0-3
    if not (0 <= self.highlight_level <= 3):
        raise ValueError(f"highlight_level must be 0-3, got {self.highlight_level}")
```

### PrecomputeProgress Fields (Minimal MVP - Phase 1.2)

**Design Decision**: PrecomputeProgress uses a minimal 6-field set for Phase 1.2. Rich progress tracking (helper methods, detailed metrics) deferred to Phase 2+ when actually needed by UI.

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|----------|-------|
| `session_id` | `str` | ✅ | — | Must be non-empty string identifier | Session tracking for request correlation |
| `total_hands` | `int` | ✅ | — | Should always be 169 for complete matrix | Total hands in analysis |
| `hands_completed` | `int` | ✅ | — | Must be 0-169, <= total_hands | Counter of hands processed |
| `percent_complete` | `float` | ✅ | — | Must be 0.0-1.0 inclusive (fractional) | Progress indicator: 0.0=start, 1.0=complete |
| `estimated_seconds_remaining` | `float` | ✅ | — | Must be >= 0 | ETA countdown in seconds |
| `is_complete` | `bool` | ✅ | — | True if percent_complete >= 1.0 | Completion flag |

**Validation in `__post_init__()`**:
```python
def __post_init__(self):
    # Validate session_id
    if not isinstance(self.session_id, str) or len(self.session_id) == 0:
        raise ValueError(f"session_id must be non-empty string, got {self.session_id!r}")
    
    # Validate hands_completed vs total_hands
    if not (0 <= self.hands_completed <= self.total_hands):
        raise ValueError(
            f"hands_completed ({self.hands_completed}) must be 0-{self.total_hands}, "
            f"got {self.hands_completed}"
        )
    
    # Validate percent_complete is fractional [0, 1]
    if not (0.0 <= self.percent_complete <= 1.0):
        raise ValueError(
            f"percent_complete must be 0.0-1.0 (fractional), got {self.percent_complete}"
        )
    
    # Validate consistency: is_complete should match percent_complete >= 1.0
    if self.is_complete and self.percent_complete < 1.0:
        raise ValueError(
            f"is_complete=True requires percent_complete>=1.0, got {self.percent_complete}"
        )
    
    # Validate time estimate is non-negative
    if self.estimated_seconds_remaining < 0:
        raise ValueError(
            f"estimated_seconds_remaining must be >=0, got {self.estimated_seconds_remaining}"
        )
```

### Enumeration Field Values

#### Position Enum
| Member | Value | Context | Used By |
|--------|-------|---------|---------|
| `UTG` | `"utg"` | Under the gun (first to act pre-flop) | PositionContext, all-in/fold analysis |
| `BTN` | `"btn"` | Button (best position post-flop) | PositionContext, all-in/fold analysis |
| `SB` | `"sb"` | Small blind | PositionContext, all-in/fold analysis |
| `BB` | `"bb"` | Big blind | PositionContext, all-in/fold analysis |

#### Action Enum
| Member | Value | Context | Validity |
|--------|-------|---------|----------|
| `FOLD` | `"fold"` | Don't play the hand, exit hand, no risk | Valid in all-in/fold |
| `ALL_IN` | `"all_in"` | Commit all remaining chips, binary decision | Valid in all-in/fold |

**Note**: Action enum is binary (all-in/fold only). No CHECK, CALL, RAISE, MIN_RAISE (not applicable to MVP scope).

#### MetricType Enum
| Member | Value | Display Format | Range | Example |
|--------|-------|-----------------|-------|---------|
| `EQUITY` | `"equity"` | Percentage "52.3%" | 0.0-1.0 | 0.523 displays as "52.3%" |
| `EV` | `"ev"` | Currency "$5.67" | -∞ to +∞ (real) | 5.67 displays as "$5.67", -2.34 as "-$2.34" |
| `EQR` | `"eqr"` | Decimal "0.9" | 0.0 to ∞ | 0.9 displays as "0.9" |
| `WIN_LOSE_PROBABILITY` | `"win_lose"` | Signed percentage "-20%" | -1.0 to 1.0 | 0.35 displays as "+35%", -0.20 as "-20%" |

**Note**: MetricType determines how HandEvaluation values are displayed by CellDisplay and MatrixPresenter.

---

## Code Templates & Implementation Examples

### Enum Definitions Template

```python
# shared/models/enums.py

from enum import Enum

class Position(str, Enum):
    """Poker table position (4-max all-in/fold game)."""
    UTG = "utg"      # Under the gun
    BTN = "btn"      # Button
    SB = "sb"        # Small blind  
    BB = "bb"        # Big blind

class Action(str, Enum):
    """All-in/fold action (binary decision)."""
    FOLD = "fold"         # Don't play
    ALL_IN = "all_in"     # Commit all chips

class MetricType(str, Enum):
    """Analysis metric for display."""
    EQUITY = "equity"                    # Pot equity %
    EV = "ev"                            # Expected value $
    EQR = "eqr"                          # Equity to risk ratio
    WIN_LOSE_PROBABILITY = "win_lose"    # Win vs lose probability

# GameType enum deferred to Phase 1.3+ (database models layer)
# In Phase 1.3, GameType will be defined for CASH/TOURNAMENT/MTT/SNG tracking
```

### PositionContext Template

```python
# shared/models/input_context.py

from dataclasses import dataclass
from typing import Optional
from shared.enums import Position  # GameType deferred to Phase 1.3+
from shared.domain.hand import Hand

@dataclass(frozen=True)
class PositionContext:
    """Complete description of a poker position for analysis."""
    
    position: Position
    num_opponents: int
    heroes_hole_cards: Optional[Hand] = None
    pot_size_bb: float = 1.0

    
    def __post_init__(self):
        if not isinstance(self.position, Position):
            raise ValueError(f"position must be Position enum, got {type(self.position)}")
        
        if self.num_opponents < 1 or self.num_opponents > 3:
            raise ValueError(f"num_opponents must be 1-3 (4 max players), got {self.num_opponents}")
        
        if self.pot_size_bb <= 0:
            raise ValueError(f"pot_size_bb must be positive, got {self.pot_size_bb}")
        
        if self.heroes_hole_cards and not isinstance(self.heroes_hole_cards, Hand):
            raise ValueError(f"heroes_hole_cards must be Hand domain model, got {type(self.heroes_hole_cards)}")
```

### AnalysisRequest Template (CRITICAL DTO)

> **📖 See detailed documentation**: [02b_DTO_AnalysisRequest.md](../../../docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/02b_DTO_AnalysisRequest.md)
> 
> Use the authoritative reference document for the complete, production-ready implementation template.

```python
# shared/models/input_context.py

from dataclasses import dataclass
from typing import Optional
from shared.enums import MetricType
from shared.domain.hand_range import HandRange

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
        return self.position_context.num_opponents == 1
    
    @property
    def is_partial_request(self) -> bool:
        return self.position_context.heroes_hole_cards is not None
    
    @property
    def is_precompute_requested(self) -> bool:
        return self.precompute
    
    @property
    def effective_opponent_range(self) -> HandRange:
        return self.opponent_range if self.opponent_range else HandRange.from_shorthand("*")
    
    def with_opponent_range(self, range_shorthand: str) -> 'AnalysisRequest':
        new_range = HandRange.from_shorthand(range_shorthand)
        return AnalysisRequest(
            position_context=self.position_context,
            opponent_range=new_range,
            metric_type=self.metric_type,
            precompute=self.precompute,
            session_id=self.session_id
        )
    
    def with_metric_type(self, metric: MetricType) -> 'AnalysisRequest':
        return AnalysisRequest(
            position_context=self.position_context,
            opponent_range=self.opponent_range,
            metric_type=metric,
            precompute=self.precompute,
            session_id=self.session_id
        )
```

### MatrixPayload Template

```python
# shared/models/output_results.py

from dataclasses import dataclass, field
from typing import Dict, Optional
from shared.enums import MetricType
from shared.models import PositionContext, HandEvaluation
from shared.domain.hand_range import HandRange

@dataclass(frozen=True)
class MatrixPayload:
    """Complete 13x13 matrix of hand evaluations."""
    
    cells: Dict[str, HandEvaluation] = field(default_factory=dict)
    query_context: PositionContext = None
    opponent_range: Optional[HandRange] = None
    metric_type: MetricType = MetricType.EQUITY
    
    average_equity: float = 0.0
    average_equity_pairs: float = 0.0
    average_equity_suited: float = 0.0
    average_equity_unsuited: float = 0.0
    median_equity: float = 0.0
    
    all_computed: bool = True
    total_simulations: int = 0
    computed_at: str = ""
    
    def __post_init__(self):
        if len(self.cells) != 169:
            raise ValueError(f"Matrix must have 169 hands, got {len(self.cells)}")
        
        expected_hands = self._generate_all_hand_keys()
        actual_hands = set(self.cells.keys())
        
        if actual_hands != expected_hands:
            missing = expected_hands - actual_hands
            raise ValueError(f"Missing hands: {missing}")
    
    @staticmethod
    def _generate_all_hand_keys() -> set:
        hands = set()
        ranks = "AKQJT98765432"
        
        for rank in ranks:
            hands.add(f"{rank}{rank}")
        
        for i, rank1 in enumerate(ranks):
            for rank2 in ranks[i+1:]:
                hands.add(f"{rank1}{rank2}s")
                hands.add(f"{rank1}{rank2}o")
        
        return hands
    
    def get_hand(self, hand_key: str) -> HandEvaluation:
        if hand_key not in self.cells:
            raise KeyError(f"Hand {hand_key} not found")
        return self.cells[hand_key]
    
    def get_hands_by_type(self, hand_type: str) -> Dict[str, HandEvaluation]:
        if hand_type == "pairs":
            return {k: v for k, v in self.cells.items() if k[0] == k[1]}
        elif hand_type == "suited":
            return {k: v for k, v in self.cells.items() if k.endswith("s")}
        elif hand_type == "unsuited":
            return {k: v for k, v in self.cells.items() if k.endswith("o")}
        else:
            raise ValueError(f"Unknown hand_type: {hand_type}")
```

### CellDisplay Template

```python
# shared/models/output_results.py

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CellDisplay:
    """Formatted, display-ready matrix cell."""
    
    hand_key: str
    metric_value: float
    display_text: str
    
    background_color: tuple
    text_color: tuple
    border_color: tuple
    
    is_computed: bool = True
    confidence: float = 1.0
    show_border: bool = False
    highlight_level: int = 0
    opacity: float = 1.0
    is_hovering: bool = False
    is_selected: bool = False
    
    tooltip_text: Optional[str] = None
    secondary_text: Optional[str] = None
    
    def __post_init__(self):
        for color_name, color in [
            ("background_color", self.background_color),
            ("text_color", self.text_color),
            ("border_color", self.border_color)
        ]:
            if not isinstance(color, tuple) or len(color) != 3:
                raise ValueError(f"{color_name} must be RGB tuple, got {color}")
            
            for component in color:
                if not (0 <= component <= 255):
                    raise ValueError(f"{color_name} component must be 0-255, got {component}")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"opacity must be 0.0-1.0, got {self.opacity}")
        
        if not (0 <= self.highlight_level <= 3):
            raise ValueError(f"highlight_level must be 0-3, got {self.highlight_level}")
```

### Data Model Architecture

The shared models follow a layered design pattern:

```
┌─────────────────────────────────────────────────────┐
│  FRONTEND LAYER (GUI Components)                    │
│  Consumes: PositionContext (input)                  │
│  Produces: PositionContext (user selections)        │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  SHARED MODELS (Type-safe contracts)                │
│  Input DTOs: PositionContext, ActionContext         │
│  Output DTOs: MatrixPayload, CellDisplay            │
│  Enums: Position, Action, MetricType, GameType      │
│  Domain Models: Hand, HandRange, Board (from 1.1)   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  BACKEND LAYER (Services & Analysis)                │
│  Consumes: PositionContext, AnalysisRequest         │
│  Produces: MatrixPayload, CellDisplay               │
└─────────────────────────────────────────────────────┘
```

**Key Properties**:
- **Immutability**: All DTOs use `frozen=True` for thread-safety and hashability
- **Validation**: All business rules enforced in `__post_init__()`
- **No Circular Dependencies**: Only depend on Phase 1.1 Domain Models, stdlib
- **JSON-Serializable**: All primitive fields can be serialized for REST APIs (except domain models)

## API Contracts

### Input: PositionContext

**Contract**: Frontend packages a position request; backend analyzes.

```python
# Input Example 1: Heads-up button analysis (unknown hand)
context = PositionContext(
    position=Position.BTN,
    num_opponents=1,
    heroes_hole_cards=None,  # Unknown, analyze vs GTO
    pot_size_bb=1.0
)
# Expected: Backend analyzes all 169 hands from BTN vs 1 opponent

# Input Example 2: Specific hand analysis
context = PositionContext(
    position=Position.UTG,
    num_opponents=2,
    heroes_hole_cards=Hand.from_strings("Ah", "Kd"),  # AK offsuit
    pot_size_bb=10.0
)
# Expected: Backend analyzes AKo from UTG vs 2 opponents, 10BB stack
```

### Output: MatrixPayload

**Contract**: Backend returns all 169 hand evaluations + metadata.

```python
# Output Example
payload = MatrixPayload(
    cells={
        "AA": HandEvaluation(equity=0.68, ev=5.2, eqr=1.8, win_lose_probability=0.36),
        "AKs": HandEvaluation(equity=0.62, ev=3.8, eqr=1.2, win_lose_probability=0.24),
        # ... 167 more hands ...
    },
    query_context=PositionContext(...),
    opponent_range=HandRange("22+,AKs"),  # Opponent range analyzed
    metric=MetricType.EQUITY,
    average_equity=0.52,
    average_equity_pairs=0.58,
    average_equity_suited=0.50,
    average_equity_unsuited=0.48,
    all_computed=True,
    total_simulations=10_000_000,
    computed_at="2026-04-03T14:23:45Z"
)

# Frontend accesses:
payload.get_hand("AKs")  # → HandEvaluation
payload.get_all_hands_by_type("pair")  # → Dict of 13 pairs
```

### Display: CellDisplay

**Contract**: Presenter transforms MatrixPayload cells into display-ready objects.

```python
# Input: Raw HandEvaluation + MetricType
equity = 0.523
metric_type = MetricType.EQUITY

# Output: Display-ready cell
cell = CellDisplay(
    hand_key="AKs",
    metric_value=0.523,
    display_text="52.3%",  # Formatted, human-readable
    background_color=(200, 150, 100),  # Color gradient based on equity
    text_color=(0, 0, 0),  # Black text for contrast
    border_color=(100, 100, 100),  # Subtle border
    is_computed=True,
    confidence=1.0,
    show_border=False,
    highlight_level=0,
    opacity=1.0,
    tooltip_text="52.3% equity (10M sims)"
)

# GUI renders without further processing
```

### Progress Tracking: PrecomputeProgress

**Contract**: Long-running analysis publishes progress to frontend.

**Note**: Fractional representation (0.0-1.0) used for percent_complete to align with equity, confidence, and other probability fields.

```python
# Initial state: 0% progress, estimated 5 minutes
progress = PrecomputeProgress(
    session_id="sess_abc123",
    total_hands=169,
    hands_completed=0,
    percent_complete=0.0,        # 0% (0/169)
    estimated_seconds_remaining=300.0,
    is_complete=False
)

# Mid-computation: 50 hands done, ~200s remaining (30% complete)
progress = PrecomputeProgress(
    session_id="sess_abc123",
    total_hands=169,
    hands_completed=50,
    percent_complete=0.296,       # ~30% (50/169)
    estimated_seconds_remaining=200.0,
    is_complete=False
)

# Complete: all 169 hands done
progress = PrecomputeProgress(
    session_id="sess_abc123",
    total_hands=169,
    hands_completed=169,
    percent_complete=1.0,         # 100% (169/169)
    estimated_seconds_remaining=0.0,
    is_complete=True
)
```

---

## Testing Requirements

### Unit Tests: Enums

- [ ] Position enum: creation by name, value, attribute; string conversion; all 4 members present
- [ ] Action enum: creation by name/value/attribute; exactly FOLD and ALL_IN
- [ ] MetricType enum: creation by name/value; all 4 metrics present (EQUITY, EV, EQR, WIN_LOSE_PROBABILITY)
- [ ] Invalid enum values rejected with ValueError

### Unit Tests: PositionContext

- [ ] Valid creation with position, num_opponents, optional hand, optional pot_size
- [ ] Immutability: frozen=True prevents attribute modification
- [ ] Validation: num_opponents not 1-3 raises ValueError
- [ ] Validation: pot_size_bb <= 0 raises ValueError
- [ ] Validation: position not Position enum raises ValueError
- [ ] Validation: hand not Hand domain model (if provided) raises ValueError
- [ ] Hash consistency: two identical PositionContext objects hash identically (frozen dataclass property)

### Unit Tests: ActionContext

- [ ] Valid creation with Position and Action
- [ ] Immutability: frozen=True
- [ ] Validation: invalid Position rejected
- [ ] Validation: invalid Action rejected

### Unit Tests: AnalysisRequest (CRITICAL - 30+ test cases required)

- [ ] Valid creation with PositionContext, optional opponent range, optional metric type
- [ ] Immutability: frozen=True prevents modification
- [ ] Validation: position_context must be valid PositionContext instance
- [ ] Validation: opponent_range if provided must be HandRange domain model (not string, not tuple)
- [ ] Validation: metric_type must be valid MetricType enum
- [ ] Validation: precompute must be boolean
- [ ] Validation: session_id if provided must be non-empty string
- [ ] Default values: opponent_range=None uses all hands
- [ ] Default values: metric_type defaults to EQUITY
- [ ] Default values: precompute defaults to False
- [ ] Default values: session_id defaults to None
- [ ] Property `is_heads_up`: True if num_opponents=1, False otherwise
- [ ] Property `is_partial_request`: True if heroes_hole_cards specified, False if None
- [ ] Property `is_precompute_requested`: True if precompute=True, False if False
- [ ] Property `effective_opponent_range`: returns provided range or all hands if None
- [ ] Method `with_opponent_range()`: creates new request with specified opponent range
- [ ] Method `with_metric_type()`: creates new request with different metric
- [ ] Functional style: chaining with_opponent_range().with_metric_type() works
- [ ] Session tracking: same session_id links related requests
- [ ] Hash consistency: two identical requests hash identically (frozen dataclass)
- [ ] Repr: __repr__ includes all fields for debugging
- [ ] Heads-up detection: correctly identifies 1 vs 2+ opponent scenarios
- [ ] Partial request detection: identifies hero-specific analysis
- [ ] Precompute flag: controls expected backend behavior
- [ ] Three metric type switches: EQUITY → EV → EQR → WIN_LOSE_PROBABILITY
- [ ] Complex opponent range: "22+,AKs,AQo,A5s-A2s" parses correctly
- [ ] Empty opponent range: None defaults to all hands correctly

### Unit Tests: HandEvaluation

- [ ] Valid creation with equity (0.0-1.0), ev (any float), eqr (>= 0), win_lose_probability (-1 to 1)
- [ ] Immutability: frozen=True
- [ ] Validation: equity not in [0, 1] raises ValueError
- [ ] Validation: eqr < 0 raises ValueError
- [ ] Validation: win_lose_probability not in [-1, 1] raises ValueError

### Unit Tests: MatrixPayload

- [ ] Valid creation with 169 HandEvaluation cells (all hand keys present: "AA", "AKs", "AKo", ..., "32o")
- [ ] Immutability: frozen=True
- [ ] Validation: < 169 hands raises ValueError with count
- [ ] Validation: > 169 hands raises ValueError
- [ ] Validation: missing hand keys (e.g., no "AKs") raises ValueError listing which hands missing
- [ ] `get_hand("AKs")` returns HandEvaluation; invalid hand_key raises KeyError
- [ ] `get_all_hands_by_type("pair")` returns dict of 13 pairs
- [ ] `get_all_hands_by_type("suited")` returns dict of 78 suited combos
- [ ] `get_all_hands_by_type("unsuited")` returns dict of 78 unsuited combos

### Unit Tests: CellDisplay

- [ ] Valid creation with hand_key, metric_value, display_text, RGB colors, rendering hints
- [ ] Immutability: frozen=True
- [ ] Validation: RGB color components not 0-255 raises ValueError with component value
- [ ] Validation: confidence not in [0, 1] raises ValueError
- [ ] Validation: opacity not in [0, 1] raises ValueError
- [ ] Validation: highlight_level not in [0, 3] raises ValueError
- [ ] Color tuple format: must be 3-tuple (R, G, B), not 4-tuple (RGBA)

### Unit Tests: PrecomputeProgress

- [ ] Valid creation with session_id, total_hands, hands_completed, percent, time estimate
- [ ] Immutability: frozen=True
- [ ] Validation: hands_completed > total_hands raises ValueError
- [ ] Validation: percent_complete not in [0, 1] raises ValueError
- [ ] Validation: estimated_seconds_remaining >= 0 (can be 0 when complete)
- [ ] Consistency: percent_complete == hands_completed / total_hands

### Integration Tests

- [ ] Frontend → Backend: PositionContext serializes to/from JSON (if applicable)
- [ ] Backend → Frontend: MatrixPayload serializes with all 169 cells (if applicable)
- [ ] Presenter: HandEvaluation + MetricType.EQUITY → CellDisplay with % formatting
- [ ] Presenter: HandEvaluation + MetricType.EV → CellDisplay with $ formatting
- [ ] Presenter: HandEvaluation + MetricType.EQR → CellDisplay with ratio formatting

### Edge Case Tests

- [ ] hero's hand is None (optional): system treats as "all hands"
- [ ] opponent_range is None (optional): system treats as "all hands"
- [ ] all_computed=False: system marks cells as "estimated" (no error)
- [ ] pot_size_bb is tiny (0.01): system accepts (no lower bound besides > 0)
- [ ] pot_size_bb is huge (1000.0): system accepts (useful for late-game situations)
- [ ] num_opponents=1 (heads-up): system accepts
- [ ] num_opponents=3 (4-way): system accepts
- [ ] num_opponents=0 or 4: system rejects ValueError

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 10 DTO classes and 3 enum types are defined, immutable (frozen=True), and importable from `aof_gto_browser_ii.shared.models`

- **SC-001a** ⛔ **CRITICAL**: AnalysisRequest DTO fully implemented with complete field documentation, validation, helper methods, and 30+ test cases. This is a blocker for Phase 2 backend services.

- **SC-002**: All DTOs validate input in `__post_init__()` with descriptive error messages; 95%+ of invalid inputs are caught before service processing

- **SC-003**: Test coverage for shared models ≥ 95% (measured via coverage report); all validation paths tested (AnalysisRequest requires especially thorough coverage)

- **SC-004**: PositionContext can be created in < 1ms; MatrixPayload validates 169 hands in < 5ms; AnalysisRequest construction and validation < 0.5ms (ensures no performance regression)

- **SC-005**: All DTOs are thread-safe: frozen=True prevents mutations, enabling safe caching and concurrent access without locks

- **SC-006**: Frontend and backend teams can separately implement against shared models without circular dependencies (modules imported 0 times by backend, ensuring isolation)

- **SC-007**: All DTOs are JSON-serializable (via Pydantic model_dump_json or custom encoder); contracts are well-defined for API

- **SC-008**: Documentation includes: docstrings for all classes/fields, examples of correct usage, common error messages, validation rules (AnalysisRequest examples must cover 4+ scenarios)

- **SC-009**: No external dependencies: all imports from `dataclasses`, `typing`, `enum` (stdlib) or Phase 1.1 domain models only

- **SC-010**: Hand-checked: all 169 poker hand keys generated correctly (13 pairs + 156 combos); no duplicates or missing hands

---

## Assumptions & Design Decisions

### Immutability (frozen=True)
**Decision**: All DTOs frozen, not mutable.
**Rationale**: Thread-safe, hashable, enables caching, aligns with functional programming patterns. Frontend/backend can pass objects without fear of mutation.
**Alternative Rejected**: Mutable dataclasses lack thread-safety, risk race conditions in concurrent analysis.

### Validation in `__post_init__()`
**Decision**: Manual validation via `__post_init__()`, not Pydantic.
**Rationale**: Avoids external dependency, full control over error messages, Phase 1.1 sets precedent. Pydantic adds 20KB+ to binary.
**Alternative Rejected**: Pydantic would add external dependency; README recommends manual validation.

### Optional Identity in PositionContext
**Decision**: `heroes_hole_cards` optional (None = unknown), not required.
**Rationale**: GTO analysis doesn't require knowing hero hand; frequency-based analysis assumes hand unknown.
**Use Case**: "What hands should I play from UTG?" analysis.

### No HandEvaluation.hand_key Field
**Decision**: HandEvaluation is just metrics; MatrixPayload.cells keyed by string.
**Rationale**: Reduces redundancy (key is already the dict key). Simpler object.
**Alternative Rejected**: Storing hand_key in HandEvaluation would duplicate information.

### Enum String Inheritance
**Decision**: `Position(str, Enum)`, not bare `Enum`.
**Rationale**: Position.BTN converts to "btn" naturally; serialization/display simpler.
**Example**: `str(Position.BTN) == "btn"` works without `.value`

### MetricType Values
**Decision**: MetricType has 4 members matching EquityResult (EQUITY, EV, EQR, WIN_LOSE_PROBABILITY).
**Rationale**: Aligns with Phase 1.1 EquityResult domain model; presenters can switch metrics without re-computing.
**Future**: If new metrics added (CBET%, 3bet%, etc.), only MetricType enum and presenters update; DTOs stable.

### Precomputed Aggregates in MatrixPayload
**Decision**: `average_equity`, `average_equity_pairs`, etc. pre-calculated by backend.
**Rationale**: Frontend often needs "average equity" for summary display; pre-computing avoids O(n) aggregation on each render.
**Cost**: ~8 floats per matrix (~64 bytes); saves O(169) calculation per render.

### No Serialization Logic in DTOs
**Decision**: DTOs are pure data; serialization (JSON/pickle) handled elsewhere.
**Rationale**: Keeps models simple, decouples from transport layer, easier to test.
**Implication**: Frontend/backend must define custom serializers where needed.

### 4-Max All-In/Fold Only
**Decision**: Position enum has only 4 members (UTG, BTN, SB, BB); Action enum has only 2 (FOLD, ALL_IN).
**Rationale**: Out of scope for MVP; can extend in Phase 2.
**Constraint**: Limits applicability; system not yet general-purpose poker analyzer.

---

## Deliverables

1. **Module**: `aof_gto_browser_ii/shared/models.py`
   - All DTO classes (PositionContext, ActionContext, AnalysisRequest, HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress)
   - All enums (Position, Action, MetricType)
   - Full validation in `__post_init__()` methods
   - Docstrings and type hints

2. **Test Suite**: `tests/aof_gto_browser_ii/test_shared_models.py`
   - Unit tests for all 10 classes + 3 enums
   - Test validation rules, immutability, edge cases
   - ≥ 100 test cases total
   - ≥ 95% code coverage

3. **Documentation**: README section in `docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/`
   - API contract examples
   - Common error messages
   - Migration/deprecation guide (if extending later)

---

## Next Steps

Upon completion of Phase 1.2:

1. **Phase 1.3** (Database Models): Define SQLAlchemy ORM models using DTOs as data shape
2. **Phase 2.1** (AnalysisService): Implement service accepting PositionContext, returning MatrixPayload
3. **Phase 3.1** (MatrixPresenter): Transform MatrixPayload → List[CellDisplay] with colors, formatting
4. **Phase 3.2** (GUI Integration): Render CellDisplay objects via pygame
