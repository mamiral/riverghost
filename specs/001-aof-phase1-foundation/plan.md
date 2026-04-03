# Implementation Plan: AOF Phase 1, Stage 1.1 - Foundation Domain Models

**Branch**: `001-aof-phase1-foundation` | **Date**: April 3, 2026 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-aof-phase1-foundation/spec.md`

## Summary

Phase 1, Stage 1.1 establishes core immutable domain models (Card, Hand, HandRange, Board, EquityResult, Bet) with full validation and parsing support. CardAdapter enables PokerKit solver integration using adapter pattern. No external solver dependencies for Phase 1.1; all types use Python standard library only. Deliverable: 7 frozen dataclasses with enum types, comprehensive parsing engines, O(1) conversion methods for solver integration.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: None (standard library only; PokerKit optional for Phase 2)  
**Storage**: N/A (in-memory only)  
**Testing**: pytest with coverage.py for 80% line coverage  
**Target Platform**: Python (Linux/Windows development)  
**Project Type**: Library (domain models for backend analysis engine)  
**Performance Goals**: HandRange parsing < 10ms; CardAdapter conversions < 1μs per call  
**Constraints**: All domain models frozen dataclass (immutable); all types hashable (set/dict compatible)  
**Scale/Scope**: 7 domain classes, 2 enum types, 1 adapter with 4 methods, ~1300-1500 LOC total

**PokerKit Integration Note**: Phase 1.1 uses Python standard library ONLY and does NOT import PokerKit. CardAdapter provides string-based format conversion for PokerKit integration in Phase 2; Phase 1.1 implementation focuses on immutable domain models with zero external solver dependencies.

## Constitution Check

**Principles Alignment:**
- ✅ **III. Modular Design**: Each domain model independently testable; single responsibility per class
- ✅ **VI. Comprehensive Testing**: 80% line coverage; tests validate real behavior (parsing, validation, immutability) not mocks or placeholders
- ✅ **IX. DRY Principle**: Parsing logic centralized in factory methods; no string parsing scattered throughout codebase
- ✅ **X. Single Responsibility**: Card (rank+suit), Hand (2 cards), HandRange (collection), Board (streets), EquityResult (probabilities), Bet (amount)
- ✅ **XI. Design Patterns**: Immutable value objects, Factory pattern (from_string), Adapter pattern (CardAdapter)
- ✅ **XII. Quality Assurance**: Strict validation prevents invalid states; tests validate real functionality not mocks

**Local Constitution Reference**: See [constitution.md](constitution.md) (version 2.4.0, last amended 2026-04-01) for governing principles.

**Gate Status**: ✅ **PASS** - All principles satisfied. Phase 1.1 scope is well-bounded and focused. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-aof-phase1-foundation/
├── spec.md              # Feature specification (COMPLETE)
├── plan.md              # This file
├── research.md          # Phase 0: Research unknowns (PENDING)
├── data-model.md        # Phase 1: Entity design (PENDING)
├── quickstart.md        # Phase 1: Developer onboarding (PENDING)
└── checklists/
    └── requirements.md  # Quality validation (COMPLETE)
```

### Source Code

```text
python/aof_gto_browser_ii/
├── __init__.py              # Package exports
└── shared/
    ├── __init__.py
    ├── domain/
    │   ├── __init__.py
    │   ├── card.py              # Card, Rank, Suit enums
    │   ├── hand.py              # Hand with shorthand parsing
    │   ├── hand_range.py        # HandRange with complex notation parser
    │   ├── board.py             # Board with street detection
    │   ├── equity_result.py     # EquityResult with probability validation
    │   └── bet.py               # Bet value type
    ├── adapters/
    │   ├── __init__.py
    │   └── card_adapter.py      # CardAdapter for PokerKit
    └── exceptions/
        ├── __init__.py
        └── validation_errors.py # Custom exception types

tests/aof_gto_browser_ii/
├── test_card.py                    # Card tests
├── test_hand.py                    # Hand tests
├── test_hand_range.py              # HandRange tests
├── test_board.py                   # Board tests
├── test_equity_result.py           # EquityResult tests
├── test_bet.py                     # Bet tests
├── test_card_adapter.py            # CardAdapter tests
└── conftest.py                     # Shared fixtures
```

**Structure Decision**: Single package (`python/aof_gto_browser_ii/shared`) with `domain/`, `adapters/`, and `exceptions/` submodules. Tests in `tests/aof_gto_browser_ii/` following project convention. This structure enables Phase 1.2 (DTOs) and Phase 1.3 (database) to coexist cleanly.

## Phase 0: Research & Clarifications

**Status**: Not Needed  
**Rationale**: Specification includes all technical details from reference documentation (01_DOMAIN_MODELS/*.md). Test coverage metric clarified to "80% line coverage (coverage.py)". No external research required.

## Phase 1: Design & Contracts

### Data Model Design

See [data-model.md](data-model.md) for detailed entity specifications.

### Public API Contracts

Domain models define the primary contract. No external API for Phase 1.1.

## Implementation Tasks

Detailed breakdown in [tasks.md](tasks.md) (generated via `/speckit.tasks` command).

## Success Metrics (from Spec)

- SC-001: All domain models frozen and immutable
- SC-002: HandRange parsing < 10ms for complex notation
- SC-003: EquityResult validates probabilities sum to 1.0 ± 0.01
- SC-004: Bet validates amount > 0 and finite
- SC-005: CardAdapter < 1μs per conversion
- SC-006: All classes hashable and work in sets/dicts
- SC-007: 80% line coverage with pytest/coverage.py
- SC-008: Complete docstrings with examples
- SC-009: Domain models integrate with CardAdapter without type errors
- SC-010: Team reviews and approves domain API

## Next Stages

- **Phase 1.2**: Shared DTOs + Enums (Position, Action, MetricType, GameType)
- **Phase 1.3**: Database Models + Connection Factory
- **Phase 1.4**: Configuration System
- **Phase 2**: Backend Services (AnalysisService, PrecomputeService, PokerKit solver)
