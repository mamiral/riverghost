# Architecture A - Implementation Strategy

## Overview

This folder (`implementation/`) contains detailed component designs for implementing **Architecture A: Layered Backend-Frontend**.

The documents are ordered by implementation sequence, not by folder organization.

---

## 🎯 Recommended Implementation Order

### Phase 1: Foundation (Week 1)
**Goal**: Establish the interfaces and contracts between layers

1. **Domain Models** ← **START HERE** ⭐
   - Card (Rank + Suit enums)
   - Hand (2 Card objects)
   - HandRange (from shorthand notation)
   - Board (0-5 community cards)
   - These are immutable, validated, core business concepts
   - No external dependencies
   
2. **Shared Models & DTOs (depend on Domain Models)**
   - Define all data transfer objects
   - PositionContext (uses Hand)
   - MatrixPayload (uses HandRange)
   - Enums and type definitions
   - Validation rules
   - No dependencies on backend or frontend
   
3. **Database Models & Connection**
   - SQLAlchemy ORM models
   - Connection factory
   - Migration setup

### Phase 2: Backend Services (Week 2-3)
**Goal**: Pure business logic, testable, no UI dependencies

3. **Repository Pattern**
   - Data access layer
   - Query methods
   - Persistence methods
   - Uses: Shared models, DB models

4. **Analysis & Solver Services**
   - AnalysisService (facade)
   - PrecomputeService (orchestration)
   - **CardAdapter** (solver library bridge)
   - EquityCalculator (PokerKit integration)
   - Uses: Shared models, Repository
   - See: [07_POKERKIT_INTEGRATION_PHASE2.md](07_POKERKIT_INTEGRATION_PHASE2.md) for solver details

### Phase 3: Frontend Layer (Week 4-5)
**Goal**: GUI and state management

5. **State Management**
   - StateManager (view state)
   - Store/subscription patterns
   - Event handling
   - Uses: Shared models, Services

6. **Presenters & Formatting**
   - MatrixPresenter
   - DetailPresenter
   - Value formatters
   - Uses: Shared models, Services

7. **GUI Components**
   - pygame components
   - Event handling
   - Rendering logic
   - Uses: StateManager, Presenters

### Phase 4: Integration & Polish (Week 6)
**Goal**: Connect everything, test, document

8. **Dependency Injection & Composition**
   - Application bootstrap
   - Service wiring
   - Configuration loading

9. **Testing & Validation**
   - Integration tests
   - Database tests
   - Full workflow tests

---

## 💡 Why This Foundation Order?

```
┌────────────────────────────────────────┐
│  Domain Models (immutable foundation)  │
│  Card, Hand, HandRange, Board          │
└──────────────┬─────────────────────────┘
               │
┌──────────────▼─────────────────────────┐
│  Shared Models / DTOs (use domain)     │
│  PositionContext, MatrixPayload, etc   │
└──────────────┬─────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
    Backend      Frontend
   (uses DTOs)  (uses DTOs)
```

### Benefits of Starting with Domain Models → DTOs:

1. **Type Safety** - Domain models provide immutable, validated types
2. **Decouples layers** - Once defined, teams can work independently
3. **Clear contracts** - Frontend/Backend have explicit interface with no strings
4. **No dependencies** - Domain models depend on nothing; DTOs depend only on domain models
5. **Easy to test** - Can iterate quickly with immutable objects
6. **Enables parallel work** - Backend and Frontend teams don't block each other
7. **Minimal risk** - Just dataclasses and enums, easy to change
8. **Consumer safety** - No string parsing scattered throughout codebase

### Example DTOs to Define First:

```python
# These are the "API" between frontend and backend

@dataclass(frozen=True)
class PositionContext:
    """Frontend tells backend: analyze this position."""
    position: Position
    board: Optional[str]
    pot_size: float
    bet_amount: float
    num_opponents: int

@dataclass
class MatrixPayload:
    """Backend tells frontend: here's the matrix data."""
    cells: List[CellDisplay]
    min_value: float
    max_value: float
    mean_value: float

@dataclass
class PrecomputeProgress:
    """Backend tells frontend: computation progress."""
    percentage: float
    completed_cells: int
    total_cells: int
    estimated_remaining_seconds: float
```

Once these are defined, both layers know exactly what to expect from each other.

---

## � Phase 1: Foundation Deliverables (Week 1)

### Stage 1.1: Domain Models (Days 1-2)

**What to Deliver**:
- ✅ `shared/domain/card.py` - Card, Rank, Suit classes with:
  - Enum-based Rank (2-A with values 2-14)
  - Enum-based Suit (s, h, d, c with symbols)
  - `Card.from_string()` parser supporting "As", "Kh", "2d", "Tc" formats
  - `Card.__str__()` for string conversion
  - Helper methods: `is_ace()`, `is_face()`, `is_broadway()`, `is_same_rank()`, `is_same_suit()`
  - Card is frozen (immutable), hashable, works in sets/dicts

- ✅ `shared/domain/hand.py` - Hand class with:
  - Two Card objects (card1, card2)
  - Validation: no duplicate cards
  - `Hand.from_strings("As", "Ks")` factory
  - `Hand.from_shorthand("AKs")` factory parsing shorthand to all combos
  - `hand.to_strings()` → tuple of card strings
  - Helper methods: `is_pair()`, `is_suited()`, `is_broadway()`, `num_combos()`
  - Frozen and immutable

- ✅ `shared/domain/hand_range.py` - HandRange class with:
  - List of Hand objects (no duplicates)
  - Original shorthand notation stored for round-trip
  - `HandRange.from_shorthand("AKs+", "22+", "A5s-A2s", etc)` parsing engine
  - Support for: single hands, pairs, plus notation (+), dash ranges (-), unions
  - `range.size()` → number of hand types
  - `range.num_combos()` → total combos across all hands
  - `range.contains(hand)` → check membership
  - `range.to_strings()` → list of card tuples for transport
  - Static methods: `union()`, `intersection()` for range operations
  - Frozen and immutable

- ✅ `shared/domain/board.py` - Board class with:
  - 0-5 Card objects
  - Validation: no duplicates, only 0-5 cards
  - `Board.from_shorthand("AsKhQd")` parser
  - `board.to_strings()` → list of card strings
  - Street detection: `is_preflop()`, `is_flop()`, `is_turn()`, `is_river()`
  - Card accessors: `get_flop()`, `get_turn()`, `get_river()`
  - Frozen and immutable

- ✅ `shared/domain/equity_result.py` - EquityResult domain model:
  - `hand: Hand` - the hand being evaluated
  - `equity: float` - 0.0-1.0 equity vs opponent range
  - `win_prob: float` - probability of winning
  - `draw_prob: float` - probability of drawing
  - `loss_prob: float` - probability of losing
  - `num_simulations: int` - Monte Carlo sample count for this result
  - Properties: `win_percent`, `draw_percent`, `loss_percent` (for display)
  - Validation: probabilities sum to 1.0 ± 0.01
  - Frozen and immutable

- ✅ `shared/domain/bet.py` - Bet/Amount value type:
  - `amount_bb: float` - amount in big blinds
  - Validation: amount > 0, not NaN/Inf
  - Properties: `is_zero()`, `is_all_in(stack: float) -> bool`
  - Operations: round to nearest cent for display
  - Frozen and immutable

- ✅ `shared/domain/card_adapter.py` - CardAdapter class for solver library integration:
  - Abstract library-specific conversions behind adapter pattern
  - `to_pokerkit(card: Card) -> str` / `from_pokerkit(str) -> Card`
    - PokerKit uses string format ("As", "Kh", etc.)
    - Direct passthrough, O(1) conversion
  - `to_treys(card: Card) -> int` / `from_treys(int) -> Card`
    - Treys uses integer index 0-51
    - Formula: `suit * 13 + rank` where suit∈[0,3], rank∈[0,12]
    - O(1) arithmetic conversion
  - `to_pypoker(card: Card) -> tuple` / `from_pypoker(str, str) -> Card`
    - PyPokerEngine uses ('A', 'S') tuples
    - Dictionary lookup, O(1) conversion
  - `to_json(card: Card) -> Dict` / `from_json(Dict) -> Card`
    - JSON serialization format with rank/suit keys
    - For REST APIs and storage
  - Support for custom solver adapters via inheritance
  - Library compatibility chart documentation
  - Performance notes: all conversions O(1), no penalty vs direct use

**Testing**: Unit tests for all conversions, round-trip tests, library format validation
**File Count**: 7 files (card.py, hand.py, hand_range.py, board.py, equity_result.py, bet.py, card_adapter.py)
**Code Lines**: ~1300-1500 LOC total
**Time**: 1-2 days

---

### Stage 1.2: Shared DTOs (Days 2-3)

**What to Deliver**:
- ✅ `shared/models/enums.py` - All enumeration types:
  - `Position(str, Enum)`: UTG, HJ, CO, BTN, SB, BB values
  - `Action(str, Enum)`: FOLD, CALL, RAISE, ALL_IN, CHECK values
  - `MetricType(str, Enum)`: EQUITY, EV, WIN_LOSE_DRAW, EQR values
  - `GameType(str, Enum)`: CASH, TOURNAMENT, MTT, SNG values

- ✅ `shared/models/input_context.py` - Input DTOs:
  - `PositionContext(dataclass, frozen)` with:
    - `position: Position` - enum
    - `num_opponents: int` - validation: 1-5
    - `stack_bb: float` - validation: > 0
    - `pot_bb: float` - validation: > 0
    - `heroes_hole_cards: Optional[Hand]` - uses Hand domain model
    - `board: Optional[Board]` - uses Board domain model (0-5 cards)
    - `game_type: GameType` - enum
    - `__post_init__()` validation
    
  - `ActionContext(dataclass)` with:
    - Context for where action happens
    - Street, action sequence, betting round info
    
  - `AnalysisRequest(dataclass)` with:
    - `context: PositionContext`
    - `metric_type: MetricType`
    - `opponent_range: Optional[HandRange]`
    - `precompute: bool` flag

- ✅ `shared/models/output_results.py` - Output DTOs:
  - `CellDisplay(dataclass)` with:
    - `hand_notation: str` - "AKs", "KQo", "77", etc
    - `equity: float` - 0.0-1.0
    - `ev: float` - expected value
    - `win_prob: float`
    - `draw_prob: float`
    - `combos: int` - 4, 6, or 12
    - `color: tuple[int,int,int]` - RGB for display
    - `selected: bool` - if highlighted
    
  - `MatrixPayload(dataclass)` with:
    - `cells: Dict[str, CellDisplay]` - keyed by hand notation
    - `position: Position` - what this matrix is for
    - `num_opponents: int`
    - `metric_type: MetricType`
    - `opponent_range: HandRange` - what was analyzed against
    - `statistics: Dict[str, float]` - min, max, mean, median equity
    - `timestamp: datetime` - when computed
    - `is_complete: bool` - fully converged or partial?
    
  - `PrecomputeProgress(dataclass)` with:
    - `session_id: str` - unique ID for this computation
    - `position: Position`
    - `num_opponents: int`
    - `percentage: float` - 0-100
    - `completed_cells: int`
    - `total_cells: int` - 169
    - `elapsed_seconds: float`
    - `estimated_remaining_seconds: float`
    - `status: str` - "running", "paused", "completed", "error"
    - `message: str` - status message
    
  - `DetailPayload(dataclass)` with:
    - `hand_notation: str`
    - `equity: float`
    - `ev: float`
    - `vs_range: HandRange` - opponent range used
    - `recommendation: str` - "FOLD", "CALL", "RAISE", "JAM"
    - `reason: str` - why this action
    - `sample_matchups: List[Dict]` - equity vs specific hands

- ✅ `shared/models/validation.py` - Validation rules:
  - `validate_position(pos: Position) -> bool`
  - `validate_stack(stack: float) -> bool`
  - `validate_hand(hand: Optional[Hand]) -> bool`
  - `validate_board(board: Optional[Board]) -> bool`
  - `validate_equity(eq: float) -> bool`
  - Custom exceptions: `PositionError`, `ValidationError`, `RangeError`

**Testing**: Unit tests for all DTO creation, validation, edge cases
**File Count**: 5 files (enums.py, input_context.py, output_results.py, validation.py, __init__.py)
**Code Lines**: ~600-800 LOC total
**Time**: 1-2 days

---

### Stage 1.3: Database Layer (Day 3)

**What to Deliver**:
- ✅ `db/models.py` - SQLAlchemy ORM models:
  - `AnalysisSession(Base)` table with:
    - `id: int` primary key
    - `session_id: str` unique
    - `position: str` (enum)
    - `num_opponents: int`
    - `created_at: datetime`
    - `updated_at: datetime`
    - `is_complete: bool`
    - Relationships to CellResult
    
  - `CellResult(Base)` table with:
    - `id: int` primary key
    - `session_id: int` foreign key
    - `hand_notation: str` - "AKs", "KQo", etc
    - `equity: float`
    - `ev: float`
    - `win_prob: float`
    - `draw_prob: float`
    - `combos: int` - 4, 6, 12
    - `iterations: int` - Monte Carlo samples
    - `opponent_range: str` - JSON encoded
    - `updated_at: datetime`
    - Index on (session_id, hand_notation)
    
  - `PrecomputeLog(Base)` for tracking precomputation:
    - `id: int` primary key
    - `session_id: int` foreign key
    - `started_at: datetime`
    - `paused_at: datetime`
    - `resumed_at: datetime`
    - `completed_at: datetime`
    - `error_message: str`
    - `elapsed_seconds: float`

- ✅ `db/connection.py` - Database connection factory:
  - `class DatabaseConnection`:
    - `__init__(connection_string)` - SQLite or PostgreSQL
    - `create_session() -> Session` - SQLAlchemy session factory
    - `create_tables()` - Alembic migrations
    - `get_engine() -> Engine`
    - `__enter__/__exit__` - context manager support
  - Singleton pattern or factory function
  - Connection pooling for production

- ✅ `db/alembic/` - Database migrations:
  - Initial migration creating all tables
  - Version tracking

**Testing**: Database tests with test fixtures
**File Count**: 3 files (models.py, connection.py, plus alembic/)
**Code Lines**: ~400-500 LOC
**Time**: 0.5-1 day

---

### Stage 1.4: Configuration & Integration (Days 3)

**What to Deliver**:
- ✅ `config.yaml` - Application configuration:
  ```yaml
  database:
    type: sqlite  # or postgresql
    path: ./data/analysis.db
    
  solver:
    max_iterations: 100000
    convergence_threshold: 0.001
    
  logging:
    level: INFO
    file: ./logs/app.log
    
  positions:
    precompile: [BTN, CO, HJ]  # Pre-compute these positions
    default: BTN
  ```

- ✅ `shared/config.py` - Configuration loader:
  - `load_config(path: str) -> Config`
  - Pydantic model or dataclass for type-safe access
  - Environment variable overrides
  - Validation on load
  - Singleton or dependency injection

- ✅ `shared/__init__.py` - Package initialization:
  - Export all domain models (Card, Hand, HandRange, Board)
  - Export all DTOs (PositionContext, MatrixPayload, etc)
  - Export all enums (Position, Action, MetricType)

**Testing**: Config loading tests with fixtures
**File Count**: 3 files
**Code Lines**: ~200 LOC
**Time**: 0.5 day

---

### Stage 1 Acceptance Criteria

**Phase 1 is COMPLETE when**:

1. ✅ **All deliverables exist and are documented**
   - Every file has docstrings
   - Every class/method has type hints
   - README explains architecture

2. ✅ **Domain models are immutable and validated**
   - Card, Hand, HandRange, Board all frozen
   - All parsing methods work correctly
   - Edge cases handled

3. ✅ **DTOs work correctly with domain models**
   - PositionContext can hold optional Hand
   - MatrixPayload can hold HandRange
   - No strings leak into DTO fields (except for display)

4. ✅ **Database models align with DTOs**
   - Can save/load AnalysisSession
   - Can save/load CellResult
   - Queries work efficiently

5. ✅ **Configuration system works**
   - Can load from YAML
   - Can override with environment variables
   - Config is type-safe

6. ✅ **Test coverage ≥ 80% for domain models and DTOs**
   - Unit tests for all parsing
   - Unit tests for validation
   - Integration tests for dataclass creation

7. ✅ **Documentation is complete**
   - Each module has docstrings
   - README explains design choices
   - Examples of usage patterns

8. ✅ **Team agrees on API contracts**
   - Frontend and Backend have signed off on DTOs
   - No more breaking changes expected
   - Ready to parallelize Phase 2

**Estimated Time**: 3-4 days for experienced developer
**Risk**: Low (just dataclasses, simple domain logic)
**Parallel Work**: Phase 1 is sequential (each stage depends on previous)

---
## 📅 CardAdapter Delivery & Usage Timeline

### When is CardAdapter Delivered?
**Phase 1, Stage 1.1 (Days 1-2 of Week 1)**
- Delivered alongside other domain models (Card, Hand, HandRange, Board)
- Fully implemented and tested
- Documentation complete with library compatibility chart
- All conversion methods O(1) performance

### When is CardAdapter Used?
**Phase 2, Backend Services (Week 2-3)**
- `AnalysisService` imports CardAdapter
- `PrecomputeService` uses CardAdapter to convert between:
  - Domain Card objects → Solver library formats
  - Example: cardAdapter.to_pokerkit(card) in solver evaluation loops
- `Repository` saves/loads Card objects using to_json/from_json

**Phase 3 and Beyond**:
- Frontend uses CardAdapter if needs solver integration
- Custom solvers extend CardAdapter base class
- Enables swapping between PokerKit, Treys, PyPokerEngine without code changes

### Delivery vs Usage Summary

| Component | Delivered | Used From | Status |
|-----------|-----------|-----------|--------|
| **CardAdapter** | Phase 1, Week 1, Days 1-2 | Phase 2, Week 2-3 | Ready to go |
| PokerKit Integration | Phase 1 (spec) | Phase 2 (code) | Documented |
| Treys Integration | Phase 1 (spec) | Phase 2 (code) | Documented |
| PyPokerEngine Integration | Phase 1 (spec) | Phase 2 (code) | Documented |
| Custom Solver Pattern | Phase 1 (spec) | On-demand | Extensible |

---
## �📋 Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create shared models package
  - [ ] Context models (PositionContext, ActionContext)
  - [ ] DTO models (MatrixPayload, CellDisplay, PrecomputeProgress)
  - [ ] Enum definitions (Position, Action, MetricType)
  - [ ] Validation rules
- [ ] Create database models
  - [ ] Reuse existing SQLAlchemy models
  - [ ] Set up connection factory
  - [ ] Configuration loading
- [ ] **Estimated time**: 2-3 days
- [ ] **Test coverage**: Not critical yet (DTOs are simple)

### Phase 2: Backend Services (Week 2-3)
- [ ] Repository implementation
  - [ ] query_matrix() method
  - [ ] query_cell() method
  - [ ] persist_results() method
  - [ ] get_aggregates() method
- [ ] AnalysisService facade
  - [ ] evaluate_hand() method
  - [ ] start_precompute_session() method
  - [ ] get_progress() method
- [ ] PrecomputeService orchestration
  - [ ] start() - spawn threads
  - [ ] pause() - pause computation
  - [ ] cancel() - stop computation
  - [ ] _poll_progress() - get status
- [ ] **Estimated time**: 4-5 days
- [ ] **Test coverage**: 80%+ (pure logic, easy to test)

### Phase 3: Frontend Layer (Week 4-5)
- [ ] StateManager
  - [ ] Holds ViewState (position, action, metric, etc.)
  - [ ] select_position_action() method
  - [ ] start_precompute() method
  - [ ] Observer pattern for updates
- [ ] EventHandler
  - [ ] handle_event() dispatcher
  - [ ] Event to state mutation routing
- [ ] Presenters
  - [ ] MatrixPresenter (cells → display format)
  - [ ] DetailPresenter (cell data → formatted display)
  - [ ] Color computation
  - [ ] Value formatting
- [ ] GUI Components
  - [ ] Base component class
  - [ ] MatrixPanel
  - [ ] DetailPanel
  - [ ] ControlPanel
  - [ ] PlotPanel
- [ ] **Estimated time**: 5-7 days
- [ ] **Test coverage**: 60%+ (harder to test with pygame)

### Phase 4: Integration & Polish (Week 6)
- [ ] Dependency injection / composition
  - [ ] Service factory
  - [ ] Component wiring
  - [ ] Configuration loading
- [ ] Integration tests
- [ ] Documentation
- [ ] **Estimated time**: 3-4 days

**Total**: ~4-6 weeks for experienced developer

---

## 📂 Implementation Folder Structure

This `implementation/` folder has:

```
implementation/
├── 00_IMPLEMENTATION_STRATEGY.md  ← You are here
│
├── 01_DOMAIN_MODELS/              ← START HERE! (Foundation)
│   ├── 00_INDEX.md                # Overview & architecture
│   ├── 01_DOMAIN_Card.md          # Card + Rank + Suit enums
│   ├── 02_DOMAIN_Hand.md          # Hand (2 Card objects)
│   ├── 03_DOMAIN_HandRange.md     # HandRange (from shorthand)
│   └── 04_DOMAIN_Board.md         # Board (0-5 community cards)
│
├── 04_INTEGRATION_DTOs_and_DomainModels.md  # API boundaries (read before coding!)
│
├── 02_SHARED_MODELS/              ← Then here (depends on domain models)
│   ├── 00_INDEX.md
│   ├── 01_DTO_PositionContext.md  # Input DTO (uses Hand)
│   ├── 02_DTO_ActionContext.md
│   ├── 03_DTO_BoardState.md       # DEPRECATED
│   ├── 04_DTO_HandEvaluation.md
│   ├── 05_DTO_MatrixPayload.md    # Output DTO (uses HandRange)
│   ├── 06_DTO_CellDisplay.md
│   ├── 07_DTO_DetailPayload.md
│   ├── 08_DTO_PrecomputeProgress.md
│   ├── 09_ENUM_Position.md
│   ├── 10_ENUM_Action.md
│   ├── 11_ENUM_MetricType.md
│   └── 12_COMPONENT_ARCHITECTURE_WITH_DTOs.md
│
├── 02_DATABASE_LAYER/             ← Week 1-2 (after DTOs)
│   ├── README.md
│   ├── models_design.md           # SQLAlchemy models
│   ├── connection_setup.md        # DatabaseConnection factory
│   └── schema_design.md           # Database schema diagrams
│
├── 03_BACKEND_SERVICES/           ← Week 2-3
│   ├── README.md
│   ├── repository_pattern.md      # Repository interface & impl
│   ├── analysis_service.md        # AnalysisService facade
│   ├── precompute_service.md      # PrecomputeService orchestration
│   └── solver_integration.md      # How to use AllInFoldGTOSolver
│
├── 04_FRONTEND_STATE/
│   ├── README.md
│   ├── state_manager.md           # StateManager implementation
│   ├── event_handler.md           # EventHandler routing
│   └── store_pattern.md           # Observer/subscriber pattern
│
├── 05_FRONTEND_PRESENTERS/
│   ├── README.md
│   ├── presenter_pattern.md       # Presenter base class
│   ├── matrix_presenter.md        # Format cells
│   ├── detail_presenter.md        # Format details
│   └── color_mapping.md           # Equity to color computation
│
├── 06_FRONTEND_COMPONENTS/
│   ├── README.md
│   ├── component_architecture.md  # Component hierarchy
│   ├── matrix_panel.md            # 13x13 grid implementation
│   ├── detail_panel.md            # Cell details
│   ├── control_panel.md           # Position/action selectors
│   └── plot_panel.md              # Convergence plot
│
├── 07_DEPENDENCY_INJECTION/
│   ├── README.md
│   ├── composition_root.md        # Application bootstrap
│   ├── service_factory.md         # Service creation
│   └── config_loading.md          # YAML config loading
│
└── 08_INTEGRATION/
    ├── README.md
    ├── testing_strategy.md        # Unit/integration/E2E tests
    ├── api_contracts.md           # Frontend-Backend contracts
    └── deployment_checklist.md    # Release checklist
```

---

## 🚀 Getting Started Now

### Today (Decision Point):
- [ ] Review this strategy
- [ ] Decide on Shared Models design
- [ ] Create `02_SHARED_MODELS/` documents

### Tomorrow (Week 1):
- [ ] Design all shared models/DTOs
- [ ] Design database schema
- [ ] Start implementation

### Next Week (Week 2):
- [ ] Implement repository
- [ ] Implement services
- [ ] 80% test coverage

### Week 3-4:
- [ ] Frontend state management
- [ ] GUI components
- [ ] Integration tests

---

## 📌 Key Principles for Implementation

1. **Start with contracts** - Define shared models before implementation
2. **Test backend first** - Services are easier to test than UI
3. **Mock backend in GUI tests** - Presenter and StateManager tests don't need real DB
4. **Reuse existing code** - From aof_gto_browser_gui where possible
5. **Small components** - Each component under 200 LOC
6. **Clear naming** - What you see is what you get
7. **Document as you go** - Add docstrings, type hints

---

## 🎯 Success Criteria

### Week 1 (Foundation)
- ✅ All shared models defined and documented
- ✅ Database models prepared
- ✅ Team agrees on contracts

### Week 2-3 (Backend)
- ✅ Repository fully implemented
- ✅ AnalysisService working
- ✅ PrecomputeService orchestrating
- ✅ 80%+ test coverage
- ✅ Can run precomputation end-to-end

### Week 4-5 (Frontend)
- ✅ StateManager manages view correctly
- ✅ EventHandler routes events
- ✅ Presenters format data
- ✅ GUI renders matrix
- ✅ User can interact with controls

### Week 6 (Integration)
- ✅ Full workflow works (select → query → precompute → display)
- ✅ Configuration system integrated
- ✅ Logging working
- ✅ Can migrate data from old browser
- ✅ All tests passing

---

## 📖 Next Steps

1. **Read**: [02_SHARED_MODELS/README.md](02_SHARED_MODELS/README.md) (to be created)
2. **Design**: Complete shared models specification
3. **Approve**: Get team agreement on models
4. **Implement**: Start with repository and services
5. **Test**: 80%+ coverage before frontend

The rest of the documents will fill in implementation details for each layer.

---

## Questions to Answer Before Starting

- [ ] Which Python version? (3.9+, 3.11+, 3.12+?)
- [ ] Which Pydantic version? (v1 or v2?)
- [ ] Reuse existing database or fresh schema?
- [ ] Keep pygame or consider alternatives later?
- [ ] Single process or threaded architecture?
- [ ] How to handle old browser data migration?

Document answers in `configuration_decisions.md` when ready.
