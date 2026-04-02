# Feature Specification: AOF Phase 1 Foundation

**Feature Branch**: `001-aof-phase1-foundation`  
**Created**: April 2, 2026  
**Status**: Draft  
**Input**: User description: "Phase 1: Foundation - Establish interfaces and contracts between layers including Domain Models (Card, Hand, HandRange, Board, EquityResult, Bet, CardAdapter), Shared DTOs (PositionContext, MatrixPayload, PrecomputeProgress, DetailPayload), Database Models and Connection Factory, and Configuration System with YAML support and Environment Variable overrides"

---

## Overview

Phase 1 establishes the architectural foundation for the AOF GTO Browser II application by creating immutable, validated domain models and type-safe data transfer objects. This layer decouples the backend analysis engine from the frontend GUI, enabling parallel development and providing clear contracts between layers. The foundation includes database models, a connection factory, and a configuration system that supports environment-specific settings.

**Key Insight**: By starting with domain models and DTOs (rather than UI or backend services), we enable both frontend and backend teams to work independently once these contracts are signed off.

---

## User Scenarios & Testing

### User Story 1 - Backend Developer Sets Up Domain Models (Priority: P1)

A backend developer needs immutable, validated domain types for poker positions that can be used throughout the analysis engine without worrying about invalid states. The developer needs types that handle card parsing, hand notation, range expansion, and board representation.

**Why this priority**: Without domain models, the backend cannot be built reliably. These foundational types prevent entire classes of bugs (invalid hands, duplicate cards, malformed ranges).

**Independent Test**: Can be tested by creating instances, parsing from various formats (shorthand, strings), validating constraints, and verifying immutability by attempting mutations.

**Acceptance Scenarios**:

1. **Given** a developer needs to represent a card, **When** they create a Card from "As" (Ace of spades), **Then** they get an immutable Card object with rank=Ace and suit=Spades
2. **Given** a developer needs to represent a hand, **When** they create a Hand from shorthand "AKs", **Then** they get all 4 AKs combinations ([As, Ks], [Ah, Kh], [Ad, Kd], [Ac, Kc])
3. **Given** a developer has a HandRange parsed from shorthand "AKs+, QQ+, A5s-A2s", **When** they check if "KK" is in the range, **Then** they get False
4. **Given** a developer needs to represent a flop, **When** they create a Board with "AsKhQd", **Then** they have a Board with 3 cards in correct order
5. **Given** a developer attempts to create a Card with duplicate suits in a Hand, **When** they try to construct it, **Then** they get a validation error, not a silent failure

---

### User Story 2 - API Consumer Uses Data Transfer Objects (Priority: P1)

A frontend developer needs type-safe, validated DTOs to send analysis requests to the backend and receive results. The DTOs must clearly specify what data is expected, with all fields typed and validated, eliminating runtime string parsing throughout the frontend code.

**Why this priority**: DTOs define the contract between frontend and backend. Without them, both teams work with implicit assumptions, leading to mismatches and integration bugs.

**Independent Test**: Can be tested by creating valid DTOs, attempting to create invalid ones (missing required fields, invalid values), serializing/deserializing, and verifying all fields are typed.

**Acceptance Scenarios**:

1. **Given** a frontend needs to request analysis, **When** it creates a PositionContext with position=BTN, num_opponents=3, stack_bb=100, pot_bb=10, and board=None (preflop), **Then** the backend knows exactly what to analyze
2. **Given** the backend computes analysis results, **When** it creates a MatrixPayload with cells, statistics, opponent_range, and timestamp, **Then** the frontend can display all 169 hands with equity values and styling
3. **Given** long-running precomputation is happening, **When** the backend sends PrecomputeProgress with percentage=45, completed_cells=76, total_cells=169, **Then** the frontend can show accurate progress bars
4. **Given** a user clicks on a hand to see details, **When** the backend creates a DetailPayload with recommendation, reason, and sample_matchups, **Then** the frontend can display educational information

---

### User Story 3 - Database Developer Persists Analysis Results (Priority: P1)

A database developer needs database models that correspond to DTOs and can efficiently store analysis sessions and results. The models must support querying by session, pagination, and tracking computation state.

**Why this priority**: Persistence of analysis results enables precomputation caching and historical analysis review, core features of the application.

**Independent Test**: Can be tested by creating sessions, inserting results, querying by hand notation and session, updating progress, and verifying round-trip serialization.

**Acceptance Scenarios**:

1. **Given** an analysis is computed, **When** an AnalysisSession is created with position=BTN, num_opponents=3, and persisted, **Then** it can be retrieved by session_id with created_at timestamp
2. **Given** multiple CellResult rows are inserted, **When** querying by (session_id, hand_notation), **Then** retrieval is fast due to composite index
3. **Given** precomputation is running, **When** PrecomputeLog is updated with started_at, paused_at, resumed_at, **Then** elapsed_seconds is calculated correctly across pause/resume cycles

---

### User Story 4 - System Admin Configures Application (Priority: P2)

A system administrator needs to configure database connection, solver parameters, logging level, and positions to precompute, using YAML files and environment variable overrides. The configuration must be type-safe and validated on load.

**Why this priority**: Configuration flexibility is essential for deployment across development, staging, and production environments with different resource constraints.

**Independent Test**: Can be tested by loading config from YAML, overriding with environment variables, validating required fields, and verifying values are type-safe.

**Acceptance Scenarios**:

1. **Given** a config.yaml with database.type=sqlite, **When** it's loaded in development, **Then** it connects to ./data/analysis.db
2. **Given** the same config in production with DATABASE_URL environment variable set, **When** environment overrides are applied, **Then** it connects to the PostgreSQL URL instead
3. **Given** invalid config values (negative stack size, unknown position), **When** config is loaded, **Then** validation errors are raised immediately, not at runtime

---

### User Story 5 - Developer Integrates External Solver Library (Priority: P3)

A developer needs to evaluate hands using an external solver (PokerKit, Treys, or PyPokerEngine) but wants to keep solver-specific code isolated. The CardAdapter converts between domain Card objects and solver library formats without coupling business logic to solver choice.

**Why this priority**: Solver integration happens in Phase 2, but the adapter pattern enables clean separation. This reduces risk of solver library changes breaking the domain layer.

**Independent Test**: Can be tested by converting Card objects to each solver format and back, verifying round-trip accuracy and O(1) performance.

**Acceptance Scenarios**:

1. **Given** domain Card object "As", **When** converted to PokerKit format, **Then** result is string "As"
2. **Given** domain Card "Kh", **When** converted to Treys integer format, **Then** result is integer 39 (suit=3, rank=12, formula: suit * 13 + rank)
3. **Given** PokerKit string "2d", **When** converted back to domain Card, **Then** result correctly represents deuce of diamonds

---

### Edge Cases

- What happens when a HandRange is parsed from invalid shorthand notation (e.g., "XX+")?
  - System MUST raise a RangeError with descriptive message, not silently ignore invalid parts
- How does the system handle attempting to create a Hand with the same card twice (e.g., "As" and "As")?
  - System MUST raise a ValidationError immediately, preventing invalid Hand objects from existing
- What happens when the configuration file is missing required fields?
  - System MUST raise a ConfigurationError on load with list of missing fields, enabling quick debugging
- How are Board and Hand objects compared for equality?
  - Both MUST support equality comparison (==) independent of construction order (e.g., Hand("As", "Ks") == Hand("Ks", "As") if hands are normalized)
- What happens when float stack/pot values have floating-point precision errors (e.g., 99.99999999)?
  - Bet values MUST round to nearest cent (0.01 BB) for consistent display and comparison

---

## Requirements

### Functional Requirements

**FR-001**: System MUST provide immutable Card domain model with:
- Rank enum (2-14 with A=14)
- Suit enum (s, h, d, c with Unicode symbols)
- `Card.from_string("As")` parser supporting multiple formats ("As", "AS", "as")
- `card.to_string()` returning normalized format
- Equality and hashing so Cards work in sets/dicts
- Helper methods: `is_ace()`, `is_face()`, `is_broadway()`

**FR-002**: System MUST provide immutable Hand domain model with:
- Two Card objects (card1, card2)
- Validation: no duplicate cards, cards not None
- `Hand.from_strings("As", "Ks")` factory
- `Hand.from_shorthand("AKs")` parser expanding to all suited combos
- `hand.to_strings()` returning tuple of card strings
- Helper methods: `is_pair()`, `is_suited()`, `is_broadway()`
- Equality, hashing, immutability

**FR-003**: System MUST provide immutable HandRange domain model with:
- List of Hand objects (165-169 combos possible, max 1326 if all hands)
- `HandRange.from_shorthand(...)` parser supporting:
  - Single hands: "AKs", "88"
  - Plus notation: "AA+", "AKs+"
  - Dash ranges: "A5s-A2s", "JJ-99"
  - Unions: "AKs+, QQ+, A5s-A2s, 88"
- `range.size()` returning number of hand types (1-169)
- `range.num_combos()` returning total combos (1-1326)
- `range.contains(hand)` checking membership
- `range.to_strings()` returning list of card tuples for transfer
- Static methods: `union()`, `intersection()` for range operations
- Validation: no duplicate hands in range
- Frozen and immutable

**FR-004**: System MUST provide immutable Board domain model with:
- 0-5 Card objects in order (preflop, flop, turn, river sequentially)
- Validation: no duplicate cards, only 0-5 cards allowed
- `Board.from_shorthand("AsKhQd")` parser for 2-10 card string
- `board.to_strings()` returning list of card strings
- Street detection: `is_preflop()`, `is_flop()`, `is_turn()`, `is_river()`
- Card accessors: `get_flop()`, `get_turn()`, `get_river()` returning Cards or None
- Frozen and immutable

**FR-005**: System MUST provide immutable EquityResult domain model with:
- `hand: Hand` - hand being evaluated
- `equity: float` (0.0-1.0) - equity vs opponent range
- `win_prob: float`, `draw_prob: float`, `loss_prob: float` - probabilities for each outcome
- `num_simulations: int` - Monte Carlo sample count
- Properties: `win_percent`, `draw_percent`, `loss_percent` (multiply by 100 for display)
- Validation: probabilities sum to 1.0 ± 0.01 tolerance
- Frozen and immutable

**FR-006**: System MUST provide immutable Bet value type with:
- `amount_bb: float` - amount in big blinds (e.g., 2.5 = 2.5x BB)
- Validation: amount > 0, not NaN/Infinity
- `is_zero()` method
- `is_all_in(stack: float) -> bool` comparing bet size to stack
- Frozen and immutable

**FR-007**: System MUST provide CardAdapter for solver library integration with:
- `to_pokerkit(Card) -> str` and `from_pokerkit(str) -> Card` for PokerKit format
- `to_treys(Card) -> int` and `from_treys(int) -> Card` for Treys integer format (0-51)
- `to_pypoker(Card) -> tuple` and `from_pypoker(str, str) -> Card` for PyPokerEngine format
- `to_json(Card) -> Dict` and `from_json(Dict) -> Card` for REST API and storage
- All conversions O(1) with no penalty vs direct solver library usage
- Support for custom solver adapters via inheritance
- Documentation of all supported solvers and their formats

**FR-008**: System MUST provide Position enumeration with values: UTG, HJ, CO, BTN, SB, BB

**FR-009**: System MUST provide Action enumeration with values: FOLD, CALL, RAISE, ALL_IN, CHECK

**FR-010**: System MUST provide MetricType enumeration with values: EQUITY, EV, WIN_LOSE_DRAW, EQR

**FR-011**: System MUST provide GameType enumeration with values: CASH, TOURNAMENT, MTT, SNG

**FR-012**: System MUST provide immutable PositionContext DTO with:
- `position: Position` (enum) - seat position
- `num_opponents: int` - 1-5 active opponents
- `stack_bb: float` - hero stack in big blinds (> 0)
- `pot_bb: float` - current pot in big blinds (> 0)
- `heroes_hole_cards: Optional[Hand]` - None for ranges, specified Hand for single-hand analysis
- `board: Optional[Board]` - None for preflop, 0-5 cards for postflop
- `game_type: GameType` (enum) - cash/tournament context
- Validation in `__post_init__`: position valid, num_opponents in 1-5, stacks/pots > 0
- Frozen dataclass

**FR-013**: System MUST provide immutable CellDisplay DTO with:
- `hand_notation: str` - "AKs", "KQo", "77" (normalized)
- `equity: float` (0.0-1.0) - equity vs opponent range
- `ev: float` - expected value in big blinds
- `win_prob: float`, `draw_prob: float` - draw/win probabilities
- `combos: int` - 4 (pairs), 6 (offsuit), or 12 (suited)
- `color: tuple[int, int, int]` - RGB color for heatmap display
- `selected: bool` - if currently highlighted by user

**FR-014**: System MUST provide immutable MatrixPayload DTO with:
- `cells: Dict[str, CellDisplay]` - all 169 hands keyed by notation
- `position: Position` (enum) - what position this matrix analyzes
- `num_opponents: int` - opponent count
- `metric_type: MetricType` (enum) - EQUITY, EV, etc.
- `opponent_range: HandRange` - what range was evaluated against
- `statistics: Dict[str, float]` - contains min_equity, max_equity, mean_equity, median_equity
- `timestamp: datetime` - when this was computed
- `is_complete: bool` - fully converged or partial?
- Frozen dataclass

**FR-015**: System MUST provide immutable PrecomputeProgress DTO with:
- `session_id: str` - unique ID for computation session
- `position: Position` (enum)
- `num_opponents: int`
- `percentage: float` (0-100) - completion percentage
- `completed_cells: int` - number of cells finished
- `total_cells: int` - always 169
- `elapsed_seconds: float` - wall-clock time elapsed
- `estimated_remaining_seconds: float` - ETA to completion
- `status: str` - "running", "paused", "completed", "error"
- `message: str` - status update message
- Frozen dataclass

**FR-016**: System MUST provide immutable DetailPayload DTO with:
- `hand_notation: str` - "AKs", etc.
- `equity: float` - vs opponent range
- `ev: float` - expected value
- `vs_range: HandRange` - opponent range used
- `recommendation: str` - "FOLD", "CALL", "RAISE", "JAM" (action annotation)
- `reason: str` - explanation of recommendation
- `sample_matchups: List[Dict]` - equity vs specific opponent hands (e.g., AA, AK, 99)
- Frozen dataclass

**FR-017**: System MUST provide AnalysisSession ORM model with:
- `id: int` primary key
- `session_id: str` unique identifier
- `position: str` - stored enumeration value
- `num_opponents: int` - 1-5
- `created_at: datetime` - auto-set on insert
- `updated_at: datetime` - auto-updated
- `is_complete: bool` - whether precomputation finished
- Foreign key relationship to CellResult rows

**FR-018**: System MUST provide CellResult ORM model with:
- `id: int` primary key
- `session_id: int` foreign key to AnalysisSession
- `hand_notation: str` - "AKs", "77", etc.
- `equity: float` - computed equity
- `ev: float` - expected value
- `win_prob: float`, `draw_prob: float`
- `combos: int` - 4, 6, or 12
- `iterations: int` - Monte Carlo samples
- `opponent_range: str` - JSON-encoded HandRange for reproducibility
- `updated_at: datetime`
- Composite index on (session_id, hand_notation) for fast queries

**FR-019**: System MUST provide PrecomputeLog ORM model for tracking computation lifecycle with:
- `id: int` primary key
- `session_id: int` foreign key to AnalysisSession
- `started_at: datetime` - when computation began
- `paused_at: datetime` - when user paused (nullable)
- `resumed_at: datetime` - when resumed (nullable)
- `completed_at: datetime` - when finished (nullable)
- `error_message: str` - if error occurred (nullable)
- `elapsed_seconds: float` - total wall-clock time including pauses

**FR-020**: System MUST provide DatabaseConnection factory class with:
- `__init__(connection_string: str)` - accepts SQLite path or PostgreSQL URL
- `create_session() -> Session` - SQLAlchemy session factory (thread-safe)
- `create_tables()` - runs migrations via Alembic
- `get_engine() -> Engine` - gets underlying SQLAlchemy engine
- Context manager support (`__enter__`, `__exit__`)
- Connection pooling configured for production scale

**FR-021**: System MUST support configuration via YAML file (`config.yaml`) with sections:
- `database`: type (sqlite/postgresql), path/url, connection_string
- `solver`: max_iterations, convergence_threshold
- `logging`: level (DEBUG/INFO/WARNING), file path
- `positions`: list of positions to precompute, default position
- All values validated on load

**FR-022**: System MUST provide configuration loader with:
- `load_config(path: str) -> Config` function
- Support for environment variable overrides (e.g., DATABASE_URL overrides database.url)
- Type-safe configuration object (Pydantic model or frozen dataclass)
- Validation errors raised on load with list of issues

**FR-023**: System MUST export domain models, DTOs, and enums from `shared/__init__.py`:
- `from hopilot.shared import Card, Hand, HandRange, Board`
- `from hopilot.shared import PositionContext, MatrixPayload, PrecomputeProgress`
- `from hopilot.shared import Position, Action, MetricType, GameType`
- All imports at package level for ease of use

**FR-024**: System MUST provide validation rules with custom exceptions:
- `PositionError` - invalid position value
- `ValidationError` - general validation failure
- `RangeError` - invalid range notation or operations
- `ConfigurationError` - config loading or value error
- All exceptions with descriptive messages

### Key Entities

**Domain Models** (immutable, validated, core business concepts):
- **Card**: Represents a single playing card (rank + suit). Hashable, works in sets/dicts.
- **Hand**: Represents two hole cards. Frozen, no duplicate cards allowed.
- **HandRange**: Represents 1-1326 poker hand combos. Supports range notation parsing and set operations.
- **Board**: Represents 0-5 community cards in sequence. Validated for street progression (flop → turn → river).
- **EquityResult**: Represents equity computation output for one hand vs range. Immutable probability snapshot.
- **Bet**: Value type for monetary amounts in big blinds. Prevents invalid/NaN amounts.

**Data Transfer Objects** (contracts between layers):
- **PositionContext**: Request DTO - frontend tells backend "analyze this position"
- **CellDisplay**: Response DTO - single hand in matrix with equity/color/action
- **MatrixPayload**: Response DTO - all 169 hands for a position/opponent config
- **PrecomputeProgress**: Streaming DTO - backend tells frontend computation progress
- **DetailPayload**: Response DTO - educational detail for selected hand

**Database Models** (persistent storage):
- **AnalysisSession**: Groups related CellResult rows, tracks completion
- **CellResult**: Individual computed hand equity, indexed for fast queries
- **PrecomputeLog**: Tracks computation lifecycle, elapsed time, pause/resume cycles

**Adapter Pattern** (isolation of solver dependencies):
- **CardAdapter**: Converts domain Card ↔ solver library formats (PokerKit, Treys, PyPokerEngine, JSON)

---

## Success Criteria

### Measurable Outcomes

**SC-001**: All immutable domain models (Card, Hand, HandRange, Board) can be created, parsed from strings, serialized back to strings, and cannot be mutated after creation (attempt to modify raises AttributeError)

**SC-002**: HandRange parser correctly expands complex shorthand notation like "AKs+, QQ+, A5s-A2s" and contains() method correctly identifies membership for all 1326 possible hands in < 10ms

**SC-003**: All DTOs (PositionContext, MatrixPayload, PrecomputeProgress, DetailPayload) can be created with valid data, raise TypeError for missing required fields, and can be serialized/deserialized for transport

**SC-004**: Database models (AnalysisSession, CellResult, PrecomputeLog) can persist to SQLite in development and PostgreSQL in production with composite index on (session_id, hand_notation) returning < 10ms for a full session

**SC-005**: Configuration system loads from YAML, environment variables override file values, validation occurs on load with descriptive error messages for invalid configs (missing fields, wrong types, out-of-range values)

**SC-006**: CardAdapter converts domain Card objects to all supported solver formats (PokerKit string, Treys int, PyPokerEngine tuple, JSON) and back with 100% accuracy for all 52 cards in < 1μs per conversion

**SC-007**: Test coverage for domain models and DTOs reaches 80%+ with unit tests for parsing, validation, edge cases, immutability, and serialization

**SC-008**: All public APIs have docstrings explaining purpose, parameters, return values, and example usage; README documents architecture and design choices

**SC-009**: Integration between domain models and DTOs works without type errors: PositionContext accepts Hand objects, MatrixPayload accepts HandRange, CellDisplay embeds equity floats, all without manual string conversion

**SC-010**: Development team reviews and approves API contracts (domain models, DTOs, database schema); no breaking changes expected for Phase 2 backend development

---

## Assumptions

1. **No external dependencies for domain models**: Domain models (Card, Hand, HandRange, Board) depend only on Python standard library, no third-party libraries.

2. **Range notation is expanded at parse time**: HandRange.from_shorthand() produces all individual hands, not lazy evaluation. This trades memory for simplicity and predictable performance.

3. **Float precision for equity**: Equity values are floats (0.0-1.0) with 4 decimal places (10,000 distinct equity values). No decimal.Decimal needed for game logic.

4. **Hand equality is order-independent**: Hand("As", "Ks") == Hand("Ks", "As") if both hands represent the same cards, improving usability.

5. **Board is strictly ordered by street**: Board.from_shorthand() parses cards in address order (flop = first 3, turn = 4th, river = 5th). No validation of actual poker legality (e.g., can't have Flop + Turn without community cards between them).

6. **Configuration is immutable after load**: Config object is frozen/immutable to prevent accidental runtime changes. Environment overrides happen only at startup.

7. **Database migrations are managed by Alembic**: SQLAlchemy ORM models are source of truth; Alembic generates/applies migrations automatically.

8. **Solver integration is optional for Phase 1**: CardAdapter is specified but not tested with actual solvers until Phase 2. Phase 1 tests focus on format conversion logic.

9. **DTO serialization format-agnostic**: DTOs work with JSON, MessagePack, or other formats via @dataclass decorator and explicit to_dict()/from_dict() methods (not relying on dataclass.__dict__ which may change).

10. **Enum string values are stable identifiers**: Position, Action, MetricType enums use str values (e.g., Position.BTN.value == "BTN") for database/API consistency, not position indices. This allows enum reordering without migration.

---

## Open Questions

None at this time. Phase 1 scope is well-bounded and requires no external clarifications.

---

## Related Documents

- [Implementation Strategy](../00_IMPLEMENTATION_STRATEGY.md) - Overall 4-phase plan
- [Architecture Decision Record](../architecture/) - Design rationale
- [Phase 2: Backend Services](../phase-2-backend/spec.md) - Will use domain models from Phase 1
- [Phase 3: Frontend Layer](../phase-3-frontend/spec.md) - Will use DTOs from Phase 1
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
