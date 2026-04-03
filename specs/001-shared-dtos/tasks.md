# Tasks: Phase 1.2 - Shared Models & DTOs

**Branch**: `001-shared-dtos`  
**Status**: Ready for Implementation  
**Input Documents**: 
- [spec.md](spec.md) - Complete specification with all requirements
- [plan.md](plan.md) - Implementation approach and technical decisions
- [data-model.md](data-model.md) - Entity definitions and relationships
- [quickstart.md](quickstart.md) - Usage examples

**Output Path**: `aof_gto_browser_ii/shared/models/` (package) + `tests/aof_gto_browser_ii/test_shared_models.py` (tests)

---

## Format Guide

**Task Format**: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Task can run in parallel (different files, no dependencies)
- **[Story]**: User story this task belongs to (none for Setup/Foundational)
- **File paths**: Workspace-relative paths from project root

---

## Phase 1: Setup & Project Structure

**Purpose**: Initialize package structure and imports for all shared models

**Duration**: 15-30 minutes

- [ ] T001 Create Python package structure for shared models in `aof_gto_browser_ii/shared/models/` directory
- [ ] T002 [P] Create `aof_gto_browser_ii/shared/models/__init__.py` with all exports (enums, DTOs)
- [ ] T003 Create `aof_gto_browser_ii/shared/__init__.py` (parent package init if not exists)
- [ ] T004 Add type hints and imports at module level in `aof_gto_browser_ii/shared/models/__init__.py`

**Checkpoint**: Package structure initialized - ready for enum/DTO implementation

---

## Phase 2: Enumerations (Type Safety Foundation)

**Purpose**: Implement Position, Action, MetricType enums as string-inheriting enums (FR-001, FR-002, FR-003, FR-004, FR-005)

**Duration**: 1 hour

**Independent Test**: Each enum rejects invalid string values and supports creation by name/value

### Implementation for Enumerations

- [ ] T005 [P] Create Position enum in `aof_gto_browser_ii/shared/models/enums.py` with members UTG, BTN, SB, BB (string-inheriting, lowercase values)
- [ ] T006 [P] Create Action enum in `aof_gto_browser_ii/shared/models/enums.py` with members FOLD, ALL_IN (string-inheriting, lowercase values)
- [ ] T007 [P] Create MetricType enum in `aof_gto_browser_ii/shared/models/enums.py` with members EQUITY, EV, EQR, WIN_LOSE_PROBABILITY (string-inheriting)
- [ ] T008 Add docstrings to all enum members explaining their meaning in poker context in `aof_gto_browser_ii/shared/models/enums.py`

### Tests for Enumerations

- [ ] T009 [P] Create enum tests (≥3 independent test methods) in `tests/aof_gto_browser_ii/test_shared_models.py`: (1) Position creation by name `Position['BTN']`, (2) creation by value `Position('btn')`, (3) creation by attribute `Position.BTN`, plus invalid value rejection
- [ ] T010 [P] Test invalid enum values (ValueError raised for "cutoff" instead of Position member) in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T011 [P] Test Action and MetricType enum validation in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T012 [P] Test string conversion of enums (str(Position.BTN) == "btn") in `tests/aof_gto_browser_ii/test_shared_models.py`

**Checkpoint**: All 3 enums defined and tested. Foundation ready for DTOs.

---

## Phase 3: Input DTOs (Frontend → Backend Contract)

**Purpose**: Implement PositionContext, ActionContext, AnalysisRequest with validation (FR-006, FR-007, FR-008, FR-015, FR-016)

**Duration**: 1.5 hours for PositionContext + ActionContext, 2-3 hours for critical AnalysisRequest

### PositionContext Implementation

- [ ] T013 [P] Create PositionContext dataclass in `aof_gto_browser_ii/shared/models/input_context.py` with fields: position, num_opponents, heroes_hole_cards, pot_size_bb
- [ ] T014 Implement PositionContext `__post_init__()` validation for position (must be Position enum) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T015 Implement PositionContext `__post_init__()` validation for num_opponents (must be 1-3) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T016 Implement PositionContext `__post_init__()` validation for pot_size_bb (must be > 0) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T017 Implement PositionContext `__post_init__()` validation for heroes_hole_cards (must be Hand domain model if provided) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T018 Add comprehensive docstring to PositionContext class with FR-006 requirements and field descriptions in `aof_gto_browser_ii/shared/models/input_context.py`

### ActionContext Implementation

- [ ] T019 [P] Create ActionContext dataclass in `aof_gto_browser_ii/shared/models/input_context.py` with fields: position_context, action
- [ ] T020 Implement ActionContext `__post_init__()` validation for position_context (must be valid PositionContext) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T021 Implement ActionContext `__post_init__()` validation for action (must be Action enum FOLD or ALL_IN) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T022 Add `is_aggressive` property to ActionContext returning True for ALL_IN, False for FOLD in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T023 Add comprehensive docstring to ActionContext with FR-007 requirements in `aof_gto_browser_ii/shared/models/input_context.py`

### AnalysisRequest Implementation (⛔ CRITICAL/BLOCKER)

- [ ] T024 Create AnalysisRequest dataclass in `aof_gto_browser_ii/shared/models/input_context.py` with fields: position_context, opponent_range, metric_type, precompute, session_id (FR-008: CRITICAL)
- [ ] T025 Implement AnalysisRequest `__post_init__()` validation for position_context (must be valid PositionContext) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T026 Implement AnalysisRequest `__post_init__()` validation for opponent_range (must be HandRange domain model if provided) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T027 Implement AnalysisRequest `__post_init__()` validation for metric_type (must be valid MetricType enum) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T028 Implement AnalysisRequest `__post_init__()` validation for session_id (must be non-empty string if provided) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T029 Add property `is_heads_up` to AnalysisRequest (returns True if 1 opponent) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T030 Add property `is_partial_request` to AnalysisRequest (True if hero hand specified) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T031 Add property `is_precompute_requested` to AnalysisRequest (True if precompute flag set) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T032 Add property `effective_opponent_range` to AnalysisRequest (returns provided range or all hands if None) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T033 Add method `with_opponent_range(range_shorthand: str)` to AnalysisRequest (returns new request with different range, functional style) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T034 Add method `with_metric_type(metric: MetricType)` to AnalysisRequest (returns new request with different metric) in `aof_gto_browser_ii/shared/models/input_context.py`
- [ ] T035 Add comprehensive docstring to AnalysisRequest with FR-008 CRITICAL designation, all 5 fields documented, examples, and FR-021 session_id explanation in `aof_gto_browser_ii/shared/models/input_context.py`

### Tests for Input DTOs

- [ ] T036 [P] Create PositionContext tests (≥4 independent assertions) in `tests/aof_gto_browser_ii/test_shared_models.py`: (1) valid creation with all fields, (2) immutability enforcement (frozen=True), (3) equality/identity properties, (4) repr for debugging
- [ ] T037 [P] Test PositionContext validation (≥5 independent error cases) in `tests/aof_gto_browser_ii/test_shared_models.py`: (1) invalid position type (string instead of enum), (2) num_opponents < 1, (3) num_opponents > 3, (4) pot_size_bb <= 0, (5) heroes_hole_cards wrong type
- [ ] T038 [P] Test PositionContext validation with Hand domain model (valid) and invalid types in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T039 [P] Create ActionContext tests (≥3 independent assertions) in `tests/aof_gto_browser_ii/test_shared_models.py`: (1) valid creation with PositionContext and Action, (2) position_context validation (must be PositionContext instance), (3) action enum validation (only FOLD/ALL_IN)
- [ ] T040 [P] Test ActionContext `is_aggressive` property (True for ALL_IN, False for FOLD) in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T041 [P] Create AnalysisRequest tests (30+ test cases covering CRITICAL designation) in `tests/aof_gto_browser_ii/test_shared_models.py`:
  - Valid creation: minimal (position_context only) | full (all fields) | with HandRange
  - Field validation: position_context (must be PositionContext) | opponent_range (HandRange or None) | metric_type (MetricType enum) | precompute (boolean) | session_id (non-empty string or None)
  - Properties: is_heads_up (1 opponent = True) | is_partial_request (hero hand specified) | is_precompute_requested (precompute flag) | effective_opponent_range (provided or all hands)
  - Functional methods: with_opponent_range() creates new instance | with_metric_type() creates new instance | chaining works
  - Edge cases: None vs empty string handling | complex range formats | session_id for request correlation
- [ ] T042 [P] Test AnalysisRequest properties (`is_heads_up`, `is_partial_request`, `is_precompute_requested`, `effective_opponent_range`) in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T043 [P] Test AnalysisRequest functional methods (`with_opponent_range`, `with_metric_type`) return new instances with correct fields in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T044 Test AnalysisRequest immutability: verify frozen=True prevents mutation attempts in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T045 Test AnalysisRequest session_id tracking for request tracing/logging context in `tests/aof_gto_browser_ii/test_shared_models.py`

**Checkpoint**: AnalysisRequest (CRITICAL) fully implemented and tested. Phase 2 backend services can now proceed.

---

## Phase 4: Output DTOs (Backend → Frontend Contract)

**Purpose**: Implement HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress (FR-009, FR-010, FR-011, FR-012)

**Duration**: 2-3 hours

### HandEvaluation Implementation

- [ ] T046 [P] Create HandEvaluation dataclass in `aof_gto_browser_ii/shared/models/output_payload.py` with fields: hand_key, equity, equity_std, ev, win_probability, tie_probability, lose_probability, win_money, lose_money, num_simulations, is_computed
- [ ] T047 Implement HandEvaluation `__post_init__()` validation for hand_key (must match FR-021 canonical format: "AA", "AKs", "AKo", etc.) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T048 Implement HandEvaluation `__post_init__()` validation for equity (0.0-1.0) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T049 Implement HandEvaluation `__post_init__()` validation for all probabilities (0.0-1.0, sum to ~1.0 within ±0.01) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T050 Implement HandEvaluation `__post_init__()` validation for num_simulations (if is_computed=True, must be > 0) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T051 Add docstring to HandEvaluation with FR-009 requirements in `aof_gto_browser_ii/shared/models/output_payload.py`

### MatrixPayload Implementation

- [ ] T052 [P] Create MatrixPayload dataclass in `aof_gto_browser_ii/shared/models/output_payload.py` with fields: cells (Dict[str, HandEvaluation]), query_context, opponent_range, metric_type, average_equity, average_equity_pairs, average_equity_suited, average_equity_unsuited, median_equity, all_computed, total_simulations, computed_at
- [ ] T053 Create static method `MatrixPayload._generate_all_hand_keys()` returning set of all 169 poker hand keys (13 pairs + 78 suited + 78 unsuited per FR-021) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T054 Implement MatrixPayload `__post_init__()` validation for cells: must have exactly 169 keys, all must be in canonical hand key format (FR-021) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T055 Implement MatrixPayload `__post_init__()` validation for query_context (must be valid PositionContext), opponent_range (if provided, must be HandRange), metric_type (must be valid MetricType) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T056 Implement MatrixPayload `__post_init__()` validation for statistics: average_equity, median_equity (0.0-1.0) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T057 Add method `MatrixPayload.get_hand(hand_key: str)` to retrieve specific hand evaluation, raises KeyError if not found in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T058 Add method `MatrixPayload.get_hands_by_type(hand_type: str)` returning filtered dict by 'pairs', 'suited', or 'unsuited' in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T059 Add docstring to MatrixPayload with FR-010 requirements and hand key format explanation in `aof_gto_browser_ii/shared/models/output_payload.py`

### CellDisplay Implementation

- [ ] T060 [P] Create CellDisplay dataclass in `aof_gto_browser_ii/shared/models/output_payload.py` with fields: hand_key, metric_value, display_text, background_color, text_color, border_color, is_computed, confidence, show_border, highlight_level, is_hovering, is_selected, opacity, tooltip_text, secondary_text
- [ ] T061 Implement CellDisplay `__post_init__()` validation for hand_key (must be valid hand from FR-021) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T062 Implement CellDisplay `__post_init__()` validation for all color tuples (background_color, text_color, border_color): must be RGB with components 0-255 in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T063 Implement CellDisplay `__post_init__()` validation for confidence (0.0-1.0), opacity (0.0-1.0), highlight_level (0-3) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T064 Add docstring to CellDisplay with FR-011 requirements and rendering hints explanation in `aof_gto_browser_ii/shared/models/output_payload.py`

### PrecomputeProgress Implementation

- [ ] T065 [P] Create PrecomputeProgress dataclass in `aof_gto_browser_ii/shared/models/output_payload.py` with fields: session_id, total_hands, hands_completed, percent_complete, estimated_seconds_remaining, is_complete
- [ ] T066 Implement PrecomputeProgress `__post_ini(MINIMAL 6-field MVP) in `aof_gto_browser_ii/shared/models/output_payload.py` with fields: session_id, total_hands, hands_completed, percent_complete (FRACTIONAL: 0.0-1.0), estimated_seconds_remaining, is_complete
- [ ] T066 Implement PrecomputeProgress `__post_init__()` validation for session_id (non-empty string) and total_hands (should be 169) in `aof_gto_browser_ii/shared/models/output_payload.py` (NOTE: Rich helper methods like progress_bar_string deferred to Phase 2+)
- [ ] T067 Implement PrecomputeProgress `__post_init__()` validation for percent_complete (FRACTIONAL 0.0-1.0, NOT percentage 0-10f percent_complete=1.0) in `aof_gto_browser_ii/shared/models/output_payload.py`
- [ ] T069 Add docstring to PrecomputeProgress with FR-012 requirements in `aof_gto_browser_ii/shared/models/output_payload.py`

### Tests for Output DTOs

- [ ] T070 [P] Create HandEvaluation tests in `tests/aof_gto_browser_ii/test_shared_models.py`: valid creation, hand_key validation (all 169 keys), equity validation (0-1)
- [ ] T071 [P] Test HandEvaluation probability validation in `tests/aof_gto_browser_ii/test_shared_models.py`: all 0-1, sum to 1.0 (±0.01 tolerance)
- [ ] T072 [P] Test HandEvaluation num_simulations validation: must be > 0 if is_computed=True in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T073 [P] Create MatrixPayload tests in `tests/aof_gto_browser_ii/test_shared_models.py`: valid creation with 169 hands, exact hand key set validation
- [ ] T074 [P] Test MatrixPayload validation: rejects < 169 hands, rejects invalid hand keys, rejects duplicate keys in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T075 [P] Test MatrixPayload methods: `get_hand()` returns correct evaluation, raises KeyError for missing hand in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T076 [P] Test MatrixPayload filtering: `get_hands_by_type('pairs')` returns 13, `get_hands_by_type('suited')` returns 78, `get_hands_by_type('unsuited')` returns 78 in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T077 [P] Create CellDisplay tests in `tests/aof_gto_browser_ii/test_shared_models.py`: valid creation with all color/confidence/opacity values
- [ ] T078 [P] Test CellDisplay color validation in `tests/aof_gto_browser_ii/test_shared_models.py`: rejects RGB components > 255, < 0; rejects non-tuple colors
- [ ] T079 [P] Test CellDisplay numeric validation: confidence (0-1), opacity (0-1), highlight_level (0-3) in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T080 [P] Create PrecomputeProgress tests (≥4 independent test methods) in `tests/aof_gto_browser_ii/test_shared_models.py`: (1) valid creation with 6 required fields, (2) session_id required and non-empty, (3) immutability (frozen=True), (4) field validation
- [ ] T081 [P] Test PrecomputeProgress validation (≥5 independent error cases) in `tests/aof_gto_browser_ii/test_shared_models.py`: (1) percent_complete FRACTIONAL 0.0-1.0 (not 0-100), (2) hands_completed <= total_hands, (3) is_complete flag consistency (True iff percent_complete >= 1.0), (4) estimated_seconds_remaining >= 0, (5) session_id non-empty string

**Checkpoint**: All output DTOs fully implemented and tested.

---

## Phase 5: Integration Testing & Coverage

**Purpose**: Comprehensive integration tests, edge case coverage, cross-DTO validation, ≥95% code coverage (FR-014, FR-015, FR-016)

**Duration**: 2-3 hours

### Cross-DTO Integration Tests

- [ ] T082 [P] Test AnalysisRequest → PositionContext → ActionContext integration: verify nested validation works correctly in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T083 [P] Test AnalysisRequest → MatrixPayload workflow: verify request context matches payload context in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T084 [P] Test MatrixPayload → CellDisplay transformation: verify all 169 hands can be converted to display cells in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T085 [P] Test PrecomputeProgress session tracking: verify session_id from AnalysisRequest matches progress updates in `tests/aof_gto_browser_ii/test_shared_models.py`

### Edge Case & Boundary Testing

- [ ] T086 [P] Test hand key format validation (FR-021): all 169 keys correctly identified, invalid formats rejected in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T087 [P] Test immutability across all DTOs: verify frozen=True prevents any attribute modification in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T088 [P] Test type coercion and rejection: strings passed where enums required, wrong domain models, etc. in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T089 [P] Test boundary numeric values: 0.0, 1.0, -0.1, 1.01 for probabilities and confidence in `tests/aof_gto_browser_ii/test_shared_models.py`
- [ ] T090 [P] Test empty/None handling across optional fields in `tests/aof_gto_browser_ii/test_shared_models.py`

### Coverage Validation

- [ ] T091 Run pytest with coverage reports: `pytest tests/aof_gto_browser_ii/test_shared_models.py --cov=aof_gto_browser_ii.shared.models --cov-report=html --cov-report=term-missing`
- [ ] T092 Verify code coverage ≥95% for all classes/methods in `aof_gto_browser_ii/shared/models/`
- [ ] T093 Add any missing edge case tests to achieve ≥95% coverage in `tests/aof_gto_browser_ii/test_shared_models.py`. Ensure coverage includes:
  - All ValueError paths in `__post_init__()` for every DTO
  - Boundary values: 0, 1, -0.1, 1.01 for fractional fields (percent_complete, confidence, opacity, equity)
  - Type rejection: strings for enums, wrong domain models, tuples instead of lists
  - Optional fields: None vs provided (e.g., heroes_hole_cards=None vs =Hand(...))
  - Enum edge cases: invalid member creation, string conversion
  - Matrix validation: missing hand keys, duplicate keys, < 169 hands
  - Hand key format: all 169 canonical keys generated, invalid formats rejected

### Final Verification

- [ ] T105 Test JSON serialization round-trip of all DTOs in `tests/aof_gto_browser_ii/test_shared_models.py`: (1) all DTOs serialize via json.dumps() for primitive fields, (2) enums serialize as strings, (3) Hand/HandRange/Board domain models properly encoded, (4) deserialization produces matching API contract structure, (5) no data loss in round-trip
- [ ] T106 Verify import constraints (FR-017, FR-018, FR-019) before final submission: Run static analysis to confirm `aof_gto_browser_ii.shared.models` imports ONLY stdlib (dataclasses, typing, enum) or Phase 1.1 domain models. No imports from GUI, database, service, or external packages.

**Checkpoint**: Final validation complete. All 106 tasks total complete. Project ready for Phase 2 backend services.

---

## Phase 7: Final Validation & Metrics

**Purpose**: JSON serialization validation (REC-3) and import constraint verification (REC-4)

**Duration**: 2-3 hours combined

**REC-3 (T105)**: JSON contract validation ensures front-end/back-end can serialize/deserialize API contracts.

**REC-4 (T106)**: Import validation ensures strict layering—shared models isolated from UI/DB/services.

**Checkpoint**: All validations passed. DTOs meet all FRs and Constitution requirements. Ready for Phase 2.

---

## Dependencies & Metrics Summary

**Total Task Count**: 106 (original 104 + REC-3 T105 + REC-4 T106)

**Phase Breakdown**:
- Phase 1 (Setup): 4 tasks
- Phase 2 (Enums): 8 tasks  
- Phase 3 (Input DTOs): 45 tasks
- Phase 4 (Output DTOs): 23 tasks
- Phase 5 (Integration): 13 tasks
- Phase 6 (Polish): 11 tasks
- Phase 7 (Final Validation): 2 tasks (NEW: REC-3, REC-4)

**Timeline**: 2-3 days (Week 1, Days 2-3)

**Requirements Coverage**: 21/21 FRs (100%) + Architecture constraints validated

---

## Phase 6: Polish & Documentation

**Purpose**: Final validation, documentation, error messages, cross-module consistency

**Duration**: 1 hour

### Documentation & Docstrings

- [ ] T094 Add comprehensive module-level docstring to `aof_gto_browser_ii/shared/models/__init__.py` explaining purpose and exports
- [ ] T095 Ensure all docstrings include examples where appropriate (AnalysisRequest, MatrixPayload particularly) in all files
- [ ] T096 Add FR requirements callouts in docstrings where domain-critical (FR-008 for AnalysisRequest, FR-021 for hand keys, etc.) in all model files
- [ ] T097 Verify all validation error messages include actual vs expected values (FR-016) in all `__post_init__()` methods

### Validation & Consistency

- [ ] T098 Cross-check all dataclass decorators: verify all have `frozen=True` in `aof_gto_browser_ii/shared/models/enums.py`, `input_context.py`, `output_payload.py`
- [ ] T099 Verify all enum values are lowercase strings (except when inherited as str) in `enums.py`
- [ ] T100 Final import validation: ensure no circular imports, all Phase 1.1 domain models properly imported in all files
- [ ] T101 Test module imports: `from aof_gto_browser_ii.shared.models import *` should provide all 10 DTOs + 3 enums in Python REPL

### Final Verification

- [ ] T102 Run full test suite: `pytest tests/aof_gto_browser_ii/test_shared_models.py -v` all tests pass
- [ ] T103 Run type checking if available (mypy/pyright): no type errors in models or tests
- [ ] T104 Verify no warnings in test output (coverage, deprecation, etc.)

**Checkpoint**: Phase 1.2 complete. All artifacts ready for Phase 2 backend service implementation.

---

## Dependencies & Execution Order

### Phase Completion Order
```
Phase 1: Setup 
    ↓
Phase 2: Enumerations (Position, Action, MetricType)
    ↓
Phase 3: Input DTOs (PositionContext, ActionContext, AnalysisRequest)
    ↓
Phase 4: Output DTOs (HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress)
    ↓
Phase 5: Integration Testing & Coverage (≥95%)
    ↓
Phase 6: Polish & Documentation
```

### Parallel Execution Within Phases

**Phase 2 (Enumerations)**: All 3 enums can be implemented in parallel (T005, T006, T007)

**Phase 3 (Input DTOs)**: 
- PositionContext (T013-T018) and ActionContext (T019-T023) can run in parallel
- AnalysisRequest (T024-T035) must wait for PositionContext completion
- All tests (T036-T045) can run in parallel once implementations complete

**Phase 4 (Output DTOs)**:
- HandEvaluation (T046-T051) and CellDisplay (T060-T064) can run in parallel
- MatrixPayload (T052-T059) and PrecomputeProgress (T065-T069) can run in parallel
- All tests (T070-T081) can run in parallel once implementations complete

**Phase 5 (Testing)**: All integration tests (T082-T090) can run in parallel once Phase 4 complete

### Parallel Execution Example

**Day 1 - Setup & Enumerations (2 hours)**:
```
09:00 - T001-T004: Setup structure
10:00 - T005-T008, T009-T012: All enums + tests (parallel)
      ✓ Enumerations tested and merged
```

**Day 1-2 - Input DTOs (4 hours)**:
```
10:30 - T013-T018 (PositionContext impl) | T019-T023 (ActionContext impl) [parallel]
11:30 - T024-T035: AnalysisRequest impl (depends on PositionContext)
       - T036-T039 (PositionContext tests) | T040, T041-T045 (ActionContext + AnalysisRequest tests) [parallel once impl done]
       ✓ All input DTOs tested and merged
```

**Day 2-3 - Output DTOs (4 hours)**:
```
14:00 - T046-T051 (HandEvaluation) | T052-T059 (MatrixPayload) | T060-T064 (CellDisplay) | T065-T069 (PrecomputeProgress) [all parallel]
15:30 - T070-T081: All output DTO tests (parallel once implementations complete)
       ✓ All output DTOs tested and merged
```

**Day 3 - Integration & Polish (3 hours)**:
```
16:30 - T082-T090: Integration tests (parallel)
17:30 - T091-T093: Coverage validation
18:00 - T094-T104: Polish, documentation, final verification
       ✓ Phase 1.2 complete, ready for Phase 2
```

---

## Independent Test Criteria

Each phase can be verified independently:

### Phase 2 Success: Enumerations
- All 3 enums (Position, Action, MetricType) instantiate without error
- `Position("btn")` returns `Position.BTN`
- `Position.BTN` string value equals `"btn"`
- Invalid values raise `ValueError`

### Phase 3 Success: Input DTOs
- `PositionContext(Position.BTN, 1)` creates successfully
- Invalid num_opponents raises `ValueError`
- `AnalysisRequest(...)` with all validations passes
- `request.is_heads_up` returns correct value
- `request.with_metric_type(MetricType.EV)` returns new instance with EV

### Phase 4 Success: Output DTOs
- `HandEvaluation("AKs", 0.523, ...)` creates successfully
- `MatrixPayload(cells={...169 hands...}, ...)` creates successfully
- `payload.get_hand("AKs")` returns correct evaluation
- `CellDisplay("AKs", 0.523, ...)` with RGB tuples creates successfully
- `PrecomputeProgress("sess_123", 169, 85, 0.5, ...)` creates successfully

### Phase 5 Success: Coverage
- `pytest ... --cov-report=term-missing` shows ≥95% coverage
- No F in coverage report (all source lines covered)
- All branches tested (validation paths, edge cases)

### Phase 6 Success: Polish
- `from aof_gto_browser_ii.shared.models import *` imports all 13 classes
- No import errors, no circular dependencies
- All docstrings present and meaningful
- All tests pass: `pytest tests/aof_gto_browser_ii/test_shared_models.py -v`

---

## Success Criteria Summary

| Criterion | Target | Verification |
|-----------|--------|---------------|
| All DTOs implemented | 10 classes | Code review in `shared/models/` |
| All enums implemented | 3 classes | Code review in `enums.py` |
| Full validation | All validation rules from spec | All tests pass |
| Immutability | `frozen=True` on all dataclasses | Review decorators + test mutations fail |
| Test coverage | ≥95% | `--cov-report` shows ≥95% |
| No dependencies | Stdlib + Phase 1.1 only | Import audit, `grep -r "import"` review |
| All tests pass | 100/100 tests | `pytest -v` exit code 0 |
| Docstrings | All classes + critical methods | Doc review, examples provided |

---

## Notes

- **Critical Path**: AnalysisRequest (T024-T035, T041-T045) is BLOCKER for Phase 2. Prioritize completion.
- **Hand Key Format (FR-021)**: Implement `_generate_all_hand_keys()` once, reuse in MatrixPayload and CellDisplay validation.
- **Domain Model Dependencies**: Verify Phase 1.1 Hand, HandRange, Board imports work before Phase 3 begins.
- **Testing Framework**: Use `pytest` with markers for easy parallelization: `pytest -n auto` with `pytest-xdist`.
- **Documentation**: Reference the detailed docs at `/docs/aof_gto_browser_ii/implementation/02_SHARED_MODELS/` for comprehensive guidance on each DTO.

---

## Files Created/Modified

**Created**:
- `aof_gto_browser_ii/shared/__init__.py` (parent package)
- `aof_gto_browser_ii/shared/models/__init__.py` (package init + exports)
- `aof_gto_browser_ii/shared/models/enums.py` (~100 lines)
- `aof_gto_browser_ii/shared/models/input_context.py` (~600 lines)
- `aof_gto_browser_ii/shared/models/output_payload.py` (~900 lines)
- `tests/aof_gto_browser_ii/test_shared_models.py` (~3,000 lines)

**Total Implementation**: ~2,000 lines  
**Total Tests**: ~3,000 lines  
**Estimated Duration**: 2-3 days (Week 1, Days 2-3)

