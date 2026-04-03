# Tasks: AOF Phase 1.1 - Foundation Domain Models

**Input**: Specification and planning documents from `/specs/001-aof-phase1-foundation/`  
**Feature**: Phase 1, Stage 1.1 - Establish immutable domain models (Card, Hand, HandRange, Board, EquityResult, Bet) with CardAdapter for PokerKit integration  
**Scope**: 7 domain models + 1 adapter, ~1300-1500 LOC, 80% line coverage target  
**Estimated Duration**: 3 days following quickstart.md roadmap

---

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: User story (US1=domain models, US2=CardAdapter)
- File paths use project structure: `python/aof_gto_browser_ii/shared/domain/`, `shared/adapters/`, `shared/exceptions/` and `tests/aof_gto_browser_ii/`

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and infrastructure

- [ ] T001 Create project structure per plan.md: `python/aof_gto_browser_ii/shared/` with `domain/`, `adapters/`, `exceptions/` subdirectories
- [ ] T002 [P] Create test directory structure: `tests/aof_gto_browser_ii/` with subdirs for test files
- [ ] T003 [P] Create `python/aof_gto_browser_ii/__init__.py` (placeholder for package exports)
- [ ] T004 [P] Create `python/aof_gto_browser_ii/shared/domain/__init__.py` (placeholder for domain exports)
- [ ] T005 [P] Create `python/aof_gto_browser_ii/shared/adapters/__init__.py` (placeholder for adapter exports)
- [ ] T006 [P] Create `python/aof_gto_browser_ii/shared/exceptions/__init__.py` (placeholder for exception exports)
- [ ] T007 [P] Create `tests/aof_gto_browser_ii/conftest.py` with shared fixtures (Card, Hand, Board instances for reuse)

---

## Phase 2: Foundational (Shared Infrastructure)

**Purpose**: Exception types and infrastructure used by all domain models

**⚠️ CRITICAL**: Must complete before domain model implementation

- [ ] T008 Create `python/aof_gto_browser_ii/shared/exceptions/validation_errors.py` with custom exception classes:
  - `ValidationError` (base for all domain validation errors)
  - `RangeError` (for HandRange parsing failures)
  - `PositionError` (for board/position validation failures)
  - Add docstrings explaining each exception's use cases

**Checkpoint**: Shared exception infrastructure complete - can now implement domain models

---

## Phase 3: User Story 1 - Backend Developer Sets Up Domain Models (Priority: P1) 🎯

**Goal**: Implement all 6 core domain models (Card, Hand, HandRange, Board, EquityResult, Bet) with immutability, validation, and parsing support  
**Independent Test**: Developer can create instances, parse from strings, validate constraints, serialize back to strings, and verify immutability by attempting mutations  
**Acceptance Scenarios**: 5 scenarios covering Card creation/parsing → Hand shorthand → HandRange expansion → Board street detection → Hand duplicate validation

### Domain Model 1: Card (FR-001)

**File**: `python/aof_gto_browser_ii/shared/domain/card.py`

**Requirements**: Immutable Card with Rank/Suit enums, parsing from shorthand/long form, string conversion, hashable for sets/dicts

- [ ] T009 [P] [US1] Implement Rank enum (IntEnum, 2-14 where A=14) with properties: `char` for single-char representation ("A", "K", "Q", "J", "T", "2"-"9")
- [ ] T010 [P] [US1] Implement Suit enum (str Enum, s/h/d/c) with property: `full_name` for full names ("Spades", "Hearts", "Diamonds", "Clubs")
- [ ] T011 [US1] Implement Card frozen dataclass with `rank: Rank` and `suit: Suit` fields in `python/aof_gto_browser_ii/shared/domain/card.py`
- [ ] T012 [US1] Implement `Card.from_string(s: str) -> Card` parser accepting:
  - Shorthand: "As", "Kh", "2d", "Tc" (case-insensitive)
  - Long form: "Ace of Spades", "King of Hearts" (case-insensitive)
  - Whitespace trimming: " As " → Card(A, S)
  - Raise ValueError for invalid formats
- [ ] T013 [US1] Implement `Card.to_string() -> str` returning normalized shorthand like "As", "Kh"
- [ ] T014 [US1] Implement `Card.__str__()` and `Card.__repr__()` for string representation
- [ ] T015 [US1] Implement `Card.is_ace() -> bool` helper method
- [ ] T016 [P] [US1] Create `tests/aof_gto_browser_ii/test_card.py` with comprehensive tests:
  - Test enum construction (Rank/Suit values correct)
  - Test from_string parsing (shorthand, long form, case-insensitive, whitespace handling)
  - Test to_string() returns normalized shorthand
  - Test immutability (frozenzen dataclass prevents mutations, AttributeError on attempt)
  - Test hashability (Card works in sets and as dict keys)
  - Test equality comparison (same rank/suit == equal)
  - Test is_ace() returns True/False correctly
  - Test all 52 cards can be created and round-trip (Card → string → Card is identical)

**SC-001 Progress**: ✅ Card immutable with frozen dataclass

### Domain Model 2: Hand (FR-002)

**File**: `python/aof_gto_browser_ii/shared/domain/hand.py`

**Requirements**: Immutable 2-card Hand, validates no duplicate cards, computes shorthand notation (AKs/22/QJo), computes combos (6/4/12), hashable

- [ ] T017 [P] [US1] Implement Hand frozen dataclass with `card1: Card` and `card2: Card` fields in `python/aof_gto_browser_ii/shared/domain/hand.py`
- [ ] T018 [US1] Implement `Hand.__post_init__()` validation raising ValueError if card1 == card2 (no duplicate cards)
- [ ] T019 [US1] Implement `Hand.from_strings(card1_str: str, card2_str: str) -> Hand` parser delegating to Card.from_string()
- [ ] T020 [US1] Implement `Hand.from_tuple((str, str)) -> Hand` parser for tuple input
- [ ] T021 [US1] Implement `Hand.to_strings() -> tuple[str, str]` returning ("As", "Kd") format for DTO transport
- [ ] T022 [US1] Implement `Hand.to_shorthand() -> str` returning standardized notation:
  - Pairs: "AA", "KK", "22" (both cards same rank)
  - Suited hands: "AKs", "A2s", "QJs" (higher rank + lower rank + 's', same suit)
  - Offsuit hands: "AKo", "K9o", "QJo" (higher rank + lower rank + 'o', different suits)
  - Algorithm: normalize to higher/lower ranks, check if suited, return notation
- [ ] T023 [US1] Implement hand classification methods:
  - `Hand.is_pair() -> bool` (both cards same rank)
  - `Hand.is_suited() -> bool` (both cards same suit)
  - `Hand.is_offsuit() -> bool` (different suits)
  - `Hand.num_combos() -> int` (6 for pairs, 4 for suited, 12 for offsuit)
  - `Hand.is_broadway() -> bool` (both ranks >= 10, inclusive of 10)
  - `Hand.is_connected() -> bool` (ranks differ by exactly 1)
  - `Hand.is_gapped() -> bool` (ranks differ by 2 or 3)
- [ ] T024 [US1] Implement `Hand.__str__()` returning to_shorthand(), `Hand.__repr__()` returning clear representation
- [ ] T025 [P] [US1] Create `tests/aof_gto_browser_ii/test_hand.py` with comprehensive tests:
  - Test construction and parsing (from_strings, from_tuple)
  - Test to_strings() for DTO serialization
  - Test to_shorthand() for all hand types (pairs, suited, offsuit)
  - Test duplicate card validation (raises ValueError on card1 == card2)
  - Test immutability (frozen dataclass prevents mutations)
  - Test hashability (Hand works in sets and dicts)
  - Test classification methods (is_pair, is_suited, is_offsuit, num_combos, etc.)
  - Test edge cases (Hand("As", "Ks") vs Hand("Ks", "As") - should both be "AKs" for shorthand)
  - Test all 1326 possible hands can be created without errors (sanity check)

**SC-001 Progress**: ✅ Hand immutable with frozen dataclass, SC-006 ✅ hashable

### Domain Model 3: HandRange (FR-003)

**File**: `python/aof_gto_browser_ii/shared/domain/hand_range.py`

**Requirements**: Immutable HandRange with complex notation parser (AKs+, 22+, A5s-A2s, etc.), set operations (union/intersection), performance < 10ms, hashable

- [ ] T026 [P] [US1] Implement HandRange frozen dataclass with:
  - `hands: List[Hand]` field (1-1326 unique hands, no duplicates)
  - `notation: str` field (original shorthand for round-trip serialization, e.g., "AKs+,QQ+,A5s-A2s")
- [ ] T027 [US1] Implement `HandRange.from_shorthand(notation: str) -> HandRange` parser with 3-phase algorithm:
  - **Phase 1 - Parse**: Split notation on comma/semicolon into components, strip whitespace
  - **Phase 2 - Expand**: For each component, detect type (single/plus/dash) and expand:
    - Single hand "AKs": Generate matching Hand from Rank.ACE downto Rank.TWO
    - Plus notation "22+": Iterate from base rank (22) to Rank.ACE, expand each rank as single hand
    - Plus notation "AKs+": Iterate from Rank.KING downto Rank.TWO, expand each as single hand with suited constraint
    - Dash range "A5s-A2s": Extract start/end ranks, iterate through range, expand each as suited hand
    - Dash range "22-99": Iterate through pair ranks from start to end
  - **Phase 3 - Deduplicate**: Remove duplicate hands, preserve order
  - Raise RangeError with descriptive message for invalid notation (unrecognized ranks, malformed syntax, "XX+", etc.)
- [ ] T028 [US1] Implement `HandRange.to_shorthand() -> str` returning original notation for serialization
- [ ] T029 [US1] Implement `HandRange.to_strings() -> List[tuple[str, str]]` returning card pair list for DTO transport
- [ ] T030 [US1] Implement HandRange query methods:
  - `HandRange.size() -> int` (number of unique hand types, 1-169)
  - `HandRange.num_combos() -> int` (total combo count, 1-1326)
  - `HandRange.contains(hand: Hand) -> bool` (membership testing)
- [ ] T031 [US1] Implement `HandRange.union(other: HandRange) -> HandRange` static method combining ranges and deduplicating
- [ ] T032 [US1] Implement `HandRange.intersection(other: HandRange) -> HandRange` static method returning common hands
- [ ] T033 [US1] Implement `HandRange.__str__()` and `HandRange.__repr__()` for representation
- [ ] T034 [P] [US1] Create `tests/aof_gto_browser_ii/test_hand_range.py` with comprehensive tests:
  - Test from_shorthand parsing (single hands, plus notation, dash ranges, complex notation)
  - Test expansion correctness ("22+" expands to 13 pairs × 6 combos = 78 total, "AKs+" expands correctly with suit constraint)
  - Test to_shorthand() round-trips back to original notation
  - Test size() and num_combos() calculations
  - Test contains() membership for various hands
  - Test union() and intersection() set operations
  - Test immutability (frozen dataclass)
  - Test hashability (HandRange works in sets)
  - Test performance: parsing complex ranges like "AKs+,QQ+,A5s-A2s" completes in < 10ms
  - Test error handling (RangeError for invalid notation like "XX+", "ABC", etc.)
  - Test edge cases (empty notation, single hand vs range, overlapping ranges in union)

**SC-001 Progress**: ✅ HandRange immutable, SC-002 ✅ parsing < 10ms

---

## Phase 4: User Story 1 Continued - Remaining Domain Models (Priority: P1)

### Domain Model 4: Board (FR-004)

**File**: `python/aof_gto_browser_ii/shared/domain/board.py`

**Requirements**: Immutable Board with 0-5 cards in street order, street detection (preflop/flop/turn/river), no duplicate cards, hashable

- [ ] T035 [P] [US1] Implement Board frozen dataclass with `cards: List[Card]` field (0-5 cards in street order) in `python/aof_gto_browser_ii/shared/domain/board.py`
- [ ] T036 [US1] Implement `Board.__post_init__()` validation:
  - Raise ValueError if len(cards) > 5
  - Raise ValueError if duplicate cards detected
- [ ] T037 [US1] Implement `Board.from_strings(card_strings: List[str]) -> Board` parser delegating to Card.from_string()
- [ ] T038 [US1] Implement `Board.to_strings() -> List[str]` returning card string list
- [ ] T039 [US1] Implement street detection methods:
  - `Board.num_cards() -> int` (0-5)
  - `Board.is_empty() -> bool` (0 cards)
  - `Board.is_flop() -> bool` (exactly 3 cards)
  - `Board.is_turn() -> bool` (exactly 4 cards)
  - `Board.is_river() -> bool` (exactly 5 cards)
  - `Board.is_complete() -> bool` (5 cards)
  - `Board.get_street() -> str` (returns "preflop", "flop", "turn", "river", or "unknown")
- [ ] T040 [US1] Implement card accessors:
  - `Board.get_flop() -> Optional[tuple[Card, Card, Card]]` (cards 0-2 if available, else None)
  - `Board.get_turn() -> Optional[Card]` (card 3 if available, else None)
  - `Board.get_river() -> Optional[Card]` (card 4 if available, else None)
  - `Board.contains_card(card: Card) -> bool` (membership test)
  - `Board.all_board_cards() -> List[Card]` (copy of cards list)
- [ ] T041 [US1] Implement `Board.__str__()` returning space-separated cards, `Board.__repr__()` for representation
- [ ] T042 [P] [US1] Create `tests/aof_gto_browser_ii/test_board.py` with comprehensive tests:
  - Test construction and parsing (from_strings)
  - Test to_strings() for serialization
  - Test validation (len > 5 raises ValueError, duplicate cards raise ValueError)
  - Test immutability
  - Test hashability
  - Test street detection (is_empty, is_flop, is_turn, is_river, is_complete, get_street)
  - Test card accessors (get_flop, get_turn, get_river with/without cards)
  - Test contains_card() and all_board_cards()
  - Test edge cases (empty board, single card, flop, turn, river)

**SC-001 Progress**: ✅ Board immutable

### Domain Model 5: EquityResult (FR-005)

**File**: `python/aof_gto_browser_ii/shared/domain/equity_result.py`

**Requirements**: Immutable EquityResult with probability validation (sum to 1.0±0.01), simulations >= 1000, display formatting, hashable

- [ ] T043 [P] [US1] Implement EquityResult frozen dataclass with fields in `python/aof_gto_browser_ii/shared/domain/equity_result.py`:
  - `hand: Hand`
  - `equity: float` (0.0-1.0)
  - `win_prob: float` (0.0-1.0)
  - `draw_prob: float` (0.0-1.0)
  - `loss_prob: float` (0.0-1.0)
  - `num_simulations: int` (>= 1000)
- [ ] T044 [US1] Implement `EquityResult.__post_init__()` validation:
  - Verify each probability is 0.0-1.0, raise ValueError if not
  - Verify win_prob + draw_prob + loss_prob sums to 1.0 ± 0.01 (allows floating-point rounding), raise ValueError if not
  - Verify num_simulations >= 1000, raise ValueError if not
  - Raise ValueError with descriptive messages explaining which validation failed and why
- [ ] T045 [US1] Implement display properties:
  - `EquityResult.win_percent -> str` (formatted like "52.34%")
  - `EquityResult.draw_percent -> str` (formatted like "10.50%")
  - `EquityResult.loss_percent -> str` (formatted like "36.66%")
  - `EquityResult.equity_percent -> str` (formatted like "52.34%", same as equity * 100)
- [ ] T046 [US1] Implement `EquityResult.from_monte_carlo(hand: Hand, wins: int, draws: int, losses: int, total_simulations: int) -> EquityResult` factory method:
  - Compute probabilities from raw counts: win_prob = wins / total_simulations, etc.
  - Create EquityResult instance (validation in __post_init__ will catch errors)
  - Return EquityResult
- [ ] T047 [US1] Implement `EquityResult.__str__()` and `EquityResult.__repr__()` for representation
- [ ] T048 [P] [US1] Create `tests/aof_gto_browser_ii/test_equity_result.py` with comprehensive tests:
  - Test construction with valid probabilities
  - Test probability validation (each 0.0-1.0, sum to 1.0±0.01)
  - Test simulations validation (>= 1000)
  - Test immutability
  - Test hashability
  - Test display properties (formatted percentages)
  - Test from_monte_carlo() factory with various win/draw/loss counts
  - Test edge cases (exactly 1000 simulations, 0 wins/draws/losses, floating-point precision errors)

**SC-001 Progress**: ✅ EquityResult immutable, SC-003 ✅ probability validation

### Domain Model 6: Bet (FR-006)

**File**: `python/aof_gto_browser_ii/shared/domain/bet.py`

**Requirements**: Immutable Bet with amount > 0 and finite validation, all-in checking, display formatting, hashable

- [ ] T049 [P] [US1] Implement Bet frozen dataclass with `amount_bb: float` field (amount in big blinds) in `python/aof_gto_browser_ii/shared/domain/bet.py`
- [ ] T050 [US1] Implement `Bet.__post_init__()` validation:
  - Round amount_bb to nearest 0.01 BB using `round(amount_bb, 2)` to handle floating-point precision errors (E-004)
  - Raise ValueError if amount_bb <= 0 (after rounding)
  - Raise ValueError if amount_bb is NaN or Infinity (math.isnan and math.isinf checks)
  - Raise ValueError with descriptive message explaining which constraint failed
- [ ] T051 [US1] Implement `Bet.is_zero() -> bool` returning False (always, since amount > 0)
- [ ] T052 [US1] Implement `Bet.is_all_in(stack_bb: float) -> bool` returning True if amount_bb >= stack_bb
- [ ] T053 [US1] Implement `Bet.display_value() -> str` formatting amount as "2.5 BB" or "0.50 BB" for UI display
- [ ] T054 [US1] Implement `Bet.__str__()` and `Bet.__repr__()` for representation
- [ ] T055 [P] [US1] Create `tests/aof_gto_browser_ii/test_bet.py` with comprehensive tests:
  - Test construction with valid amounts
  - Test validation (> 0, not NaN, not Infinity)
  - Test floating-point rounding: `Bet(99.99999999)` rounds to `100.00` BB (E-004)
  - Test immutability
  - Test hashability
  - Test is_zero() always returns False
  - Test is_all_in() for various stack sizes
  - Test display_value() formatting with rounded values
  - Test edge cases (very small amounts like 0.01 BB, very large amounts, floating-point values)

**SC-001 Progress**: ✅ Bet immutable, SC-004 ✅ amount validation

**Checkpoint**: All 6 domain models complete, immutable, validated, and tested

---

## Phase 5: User Story 2 - Developer Integrates PokerKit Solver (Priority: P2)

**Goal**: Implement CardAdapter to isolate PokerKit solver integration using adapter pattern  
**Independent Test**: Convert Card objects to/from PokerKit format, verify 100% round-trip accuracy and O(1) < 1μs performance  
**Acceptance Scenarios**: 3 scenarios covering round-trip conversions for individual cards and all 52 cards

### Domain Model 7: CardAdapter (FR-007)

**File**: `python/aof_gto_browser_ii/shared/adapters/card_adapter.py`

**Requirements**: Adapter for PokerKit conversion, O(1) < 1μs per conversion, round-trip accuracy, extensible for future solvers

- [ ] T056 [P] [US2] Implement CardAdapter class in `python/aof_gto_browser_ii/shared/adapters/card_adapter.py` with:
  - Purpose: Convert between domain Card objects and PokerKit string format without coupling domain layer to PokerKit library
  - Design: Static methods for conversion (no state needed)
  - Note: This is adapter pattern - future Phase 2 can add to_treys(), to_pypokerengine() without touching domain layer
- [ ] T057 [US2] Implement `CardAdapter.to_pokerkit(card: Card) -> str`:
  - Convert domain Card to PokerKit string format ("As", "Kh", "2d", "Tc")
  - Delegate to Card.to_string() internally (O(1) implementation)
  - Return string directly
  - **IMPORTANT**: Do NOT import PokerKit library; CardAdapter is string-based only (Phase 1.1 has zero PokerKit imports)
- [ ] T058 [US2] Implement `CardAdapter.from_pokerkit(s: str) -> Card`:
  - Parse PokerKit string format ("As", "Kh", etc.) back to domain Card
  - Delegate to Card.from_string() internally
  - Return Card object
- [ ] T059 [US2] Implement `CardAdapter.to_pokerkit_hand(hand: Hand) -> tuple[str, str]`:
  - Convert domain Hand to PokerKit hand format (tuple of 2 card strings)
  - Return (card1_string, card2_string)
- [ ] T060 [US2] Implement `CardAdapter.from_pokerkit_hand(c1: str, c2: str) -> Hand`:
  - Parse 2 PokerKit card strings back to domain Hand
  - Delegate to Hand.from_strings() internally
  - Return Hand object
- [ ] T061 [P] [US2] Create `tests/aof_gto_browser_ii/test_card_adapter.py` with comprehensive tests:
  - Test to_pokerkit() for individual cards (As→"As", Kh→"Kh", 2d→"2d", Tc→"Tc")
  - Test from_pokerkit() for individual cards (round-trip: Card → string → Card is identical)
  - Test round-trip for ALL 52 cards (sanity check that all ranks/suits work)
  - Test to_pokerkit_hand() for various hands (AKs, 22, QJo)
  - Test from_pokerkit_hand() round-trip for hands
  - Test performance: single conversion < 1μs (measure with timeit or similar)
  - Test error handling (invalid strings should raise ValueError from Card.from_string)

**SC-001 Progress**: ✅ CardAdapter is stateless/immutable pattern, SC-005 ✅ O(1) < 1μs conversion performance

**Checkpoint**: CardAdapter complete and integrated with PokerKit conversion

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize implementation, testing, and documentation

### Package Exports & Documentation

- [ ] T062 Update `python/aof_gto_browser_ii/__init__.py` to export all public API:
  - Domain models: Card, Rank, Suit, Hand, HandRange, Board, EquityResult, Bet
  - Adapter: CardAdapter
  - Example: `from hopilot.shared import Card, Hand, HandRange, Board, EquityResult, Bet, CardAdapter`
- [ ] T063 Update `python/aof_gto_browser_ii/shared/domain/__init__.py` to export domain classes
- [ ] T064 Update `python/aof_gto_browser_ii/shared/adapters/__init__.py` to export CardAdapter
- [ ] T065 Update `python/aof_gto_browser_ii/shared/exceptions/__init__.py` to export exception classes

### Test Coverage & Validation

- [ ] T066 Run full test suite from repository root:
  - Command: `python -m pytest tests/aof_gto_browser_ii/ -v`
  - Verify all tests pass
- [ ] T067 Generate coverage report:
  - Command: `python -m pytest tests/aof_gto_browser_ii/ --cov=aof_gto_browser_ii.shared.domain --cov=aof_gto_browser_ii.shared.adapters --cov-report=html`
  - Verify 80%+ line coverage (SC-007 target)
  - Review coverage report in htmlcov/ for uncovered lines
- [ ] T068 [P] Add missing unit tests to reach 80% line coverage:
  - Review coverage report for uncovered lines
  - Add specific tests for code paths not exercised (edge cases, error paths)
  - Rerun coverage until 80% is reached
- [ ] T069 Validate success criteria completion:
  - SC-001: ✅ All models frozen dataclass (immutable, HashError on mutation)
  - SC-002: ✅ HandRange parsing < 10ms (verify with performance test)
  - SC-003: ✅ EquityResult probability validation (sum to 1.0±0.01)
  - SC-004: ✅ Bet amount validation (> 0 and finite)
  - SC-005: ✅ CardAdapter O(1) < 1μs per conversion (verify with perf test)
  - SC-006: ✅ All models hashable (work in sets/dicts)
  - SC-007: ✅ 80% line coverage (coverage report confirms)
  - SC-008: ✅ All public APIs have docstrings (review each module)
  - SC-009: ✅ No type errors (run static type checker if available)
  - SC-010: Schedule team review meeting

### Documentation

- [ ] T070 Add comprehensive docstrings to all public methods:
  - Each method should have: purpose, parameters, return value, and usage example
  - Use Python docstring format (triple quotes)
  - Reference domain model documentation in docs/aof_gto_browser_ii/implementation/01_DOMAIN_MODELS/
- [ ] T071 Update README or add domain model documentation:
  - Document architecture: immutable value objects, enum-based type safety, frozen dataclass pattern
  - Document design choices: why immutability, why enums, why adapter pattern
  - Provide quick-start examples for using domain models
  - Link to quickstart.md for implementation details

### Final Validation

- [ ] T072 Run complete test suite one final time:
  - Command: `python -m pytest tests/aof_gto_browser_ii/ -v --tb=short`
  - All tests must pass
  - Coverage must be >= 80%
- [ ] T073 Verify no type errors (optional but recommended):
  - If mypy available: `mypy python/aof_gto_browser_ii/shared/`
  - Fix any type issues
- [ ] T074 Commit code changes and push to branch:
  - Commit message: "Phase 1.1: Implement domain models with 7 frozen dataclasses, adapter pattern, and 80% test coverage"
  - Push to `001-aof-phase1-foundation` branch

**Checkpoint**: Phase 1.1 complete with all success criteria validated

---

## Key Import Paths

For users of the domain models:
```python
from aof_gto_browser_ii.shared.domain import Card, Rank, Suit, Hand, HandRange, Board, EquityResult, Bet
from aof_gto_browser_ii.shared.adapters import CardAdapter
from aof_gto_browser_ii.shared.exceptions import ValidationError, RangeError
```

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion - BLOCKS all domain model implementation
- **Phase 3 (US1 Domain Models)**: Depends on Phase 2 completion:
  - Card → Hand → HandRange (sequential within phase due to dependencies)
  - Board, EquityResult, Bet can [P] in parallel with each other as separate models
  - All Phase 3 models can be [P] in parallel if split across team
- **Phase 4 (US1 Continued)**: Depends on Phase 2 + Phase 3 Card/Hand/HandRange
- **Phase 5 (US2 CardAdapter)**: Depends on Card/Hand implementation (CardAdapter depends on these)
- **Phase 6 (Polish)**: Depends on all user stories complete

### Within User Story 1 (Domain Models)

**Critical Path**:
```
Card (T009-T016)
  ↓
Hand (T017-T025) - depends on Card
  ↓
HandRange (T026-T034) - depends on Hand
```

**Parallel Opportunities**:
- T009-T010: Rank/Suit enums can [P]
- T016, T025, T034, T042, T048, T055: Tests for each model can [P]
- Board (T035-T042) can START in parallel with Hand/HandRange (no dependencies on them)
- EquityResult (T043-T048) can [P] with Board (independent models)
- Bet (T049-T055) can [P] with Board/EquityResult (independent models)

### Parallel Execution Example

**If team has 4+ developers** (max parallelism):

**Day 1**:
- Dev 1: T001-T007 (Setup) + T008 (Exceptions)
- After Setup completes (30 min), proceed in parallel:
  - Dev 1: Card (T009-T015)
  - Dev 2: Rank/Suit enums (T009-T010 in parallel), then prep Hand scaffolding
  - Dev 3: Prep Board/EquityResult/Bet scaffolding
  - After Card: Hand (T017-T024)
  - Tests can start immediately: T016 (Card tests) [P]

**Day 2**:
- Continue HandRange (T026-T033) - depends on Hand from Day 1
- Board (T035-T042) [P] with HandRange
- EquityResult (T043-T048) [P] with HandRange
- Bet (T049-T055) [P] with Board/EquityResult
- Tests: T034, T042, T048, T055 can all run [P]

**Day 3**:
- CardAdapter (T056-T060) depends on Card/Hand only (can start early Day 2 ideally)
- Tests: T061 for CardAdapter
- Coverage & documentation: T062-T074
- Final test run and validation

### Sequential Execution (Single Developer)

Follow Phase 3 → Phase 4 → Phase 5 → Phase 6 order with daily breakdown from quickstart.md:
- **Day 1**: T001-T007 (Setup) → T008 (Exceptions) → Card-Hand-HandRange (T009-T034)
- **Day 2**: Board-EquityResult-Bet (T035-T061 after Card/Hand complete)
- **Day 3**: CardAdapter tests, coverage validation, documentation (T062-T074)

---

## Success Criteria Checklist

Track completion of all success criteria:

- [ ] **SC-001**: All immutable domain models (Card, Hand, HandRange, Board, EquityResult, Bet) can be created, parsed from strings, serialized back to strings, and cannot be mutated after creation (attempt to modify raises AttributeError)
  - Verified by: T016, T025, T034, T042, T048, T055 (immutability tests)

- [ ] **SC-002**: HandRange parser correctly expands complex shorthand notation like "AKs+, QQ+, A5s-A2s" and contains() method correctly identifies membership for all 1326 possible hands in < 10ms
  - Verified by: T034 (HandRange tests with performance check)

- [ ] **SC-003**: EquityResult objects correctly validate that win_prob + draw_prob + loss_prob sums to 1.0 ± 0.01, raising ValueError with descriptive message for violations
  - Verified by: T048 (EquityResult validation tests)

- [ ] **SC-004**: Bet value type validates that amount_bb > 0 and is finite (not NaN/Infinity), raising ValueError for invalid inputs
  - Verified by: T055 (Bet validation tests)

- [ ] **SC-005**: CardAdapter converts domain Card objects to PokerKit string format ("As", "Kh", etc.) and back with 100% accuracy for all 52 cards in < 1μs per conversion (round-trip: Card → string → Card equals original)
  - Verified by: T061 (CardAdapter round-trip tests with performance check)

- [ ] **SC-006**: All domain model classes are hashable and work correctly in sets and as dictionary keys (e.g., {Card.from_string("As"): ...} or hand_set.add(hand))
  - Verified by: T016, T025, T034, T042, T048, T055 (hashability tests in each module's test suite)

- [ ] **SC-007**: Test coverage for domain models (Card, Hand, HandRange, Board, EquityResult, Bet, CardAdapter) reaches 80% line coverage (measured with `coverage.py` or equivalent) with unit tests for parsing, validation, edge cases, immutability, and round-trip serialization
  - Verified by: T067 (coverage report generation), T068 (fill gaps to reach 80%)

- [ ] **SC-008**: All public APIs have docstrings explaining purpose, parameters, return values, and example usage; README documents domain model architecture and design choices
  - Verified by: T070-T071 (docstring addition, documentation)

- [ ] **SC-009**: Domain models integrate with CardAdapter without type errors: CardAdapter methods accept Card objects and return strings; parsing methods handle all valid poker notation formats
  - Verified by: T061 (CardAdapter tests with Card objects), T069 (type error check)

- [ ] **SC-010**: Development team reviews and approves domain model API contracts; no breaking changes expected for Phase 1.2+ development
  - Action: Schedule review meeting after T074, gather team feedback

---

## Implementation Notes

### Code Examples from quickstart.md (Reference)

**Card Implementation**:
```python
from dataclasses import dataclass
from enum import IntEnum, Enum

class Rank(IntEnum):
    ACE = 14
    KING = 13
    QUEEN = 12
    JACK = 11
    TEN = 10
    # ... down to TWO = 2

@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit
    
    @staticmethod
    def from_string(s: str) -> 'Card':
        # Implement parsing logic
        pass
```

**Hand Implementation**:
```python
@dataclass(frozen=True)
class Hand:
    card1: Card
    card2: Card
    
    def __post_init__(self):
        if self.card1 == self.card2:
            raise ValueError("Hand cannot have duplicate cards")
    
    def to_shorthand(self) -> str:
        # Compute shorthand: "AKs", "22", "QJo", etc.
        pass
```

**HandRange Parser Algorithm**:
```
Parse Input: "AKs+,QQ+,A5s-A2s"
├─ Phase 1 (Parse): Split on comma → ["AKs+", "QQ+", "A5s-A2s"]
├─ Phase 2 (Expand): 
│  ├─ "AKs+" → suitable hands from AKs down to AKo+
│  ├─ "QQ+" → pairs QQ to AA
│  └─ "A5s-A2s" → suited A5s, A4s, A3s, A2s
└─ Phase 3 (Deduplicate): Remove duplicates, return HandRange
```

### Testing Patterns

**Immutability Test**:
```python
def test_card_immutable():
    card = Card(Rank.ACE, Suit.SPADES)
    with pytest.raises(AttributeError):
        card.rank = Rank.KING  # frozen dataclass prevents
```

**Round-Trip Test**:
```python
def test_card_round_trip():
    original = Card.from_string("As")
    string = original.to_string()
    reconstructed = Card.from_string(string)
    assert original == reconstructed
```

**Performance Test**:
```python
import timeit
def test_hand_range_parsing_performance():
    notation = "AKs+,QQ+,A5s-A2s"
    time = timeit.timeit(lambda: HandRange.from_shorthand(notation), number=1000)
    assert time / 1000 < 0.01  # < 10ms per iteration
```

---

## Post-Implementation

### Phase 1.2+ Planning (Not in Scope)

Phase 1.1 establishes foundation for:
- **Phase 1.2**: DTO/API contracts (frontend/backend serialization)
- **Phase 1.3**: Database models (persistence layer)
- **Phase 1.4**: Configuration system (game settings, aliases)
- **Phase 2**: Backend services (equity calculation, range analysis)
- **Phase 3**: GUI and real-time integration

These will reuse Phase 1.1 domain models as immutable, validated contracts.

---

**Status**: ✅ Tasks prepared for Phase 1.1 implementation (3-day sprint with 74 actionable tasks)
