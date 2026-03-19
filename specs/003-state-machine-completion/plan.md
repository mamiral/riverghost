# Implementation Plan: Complete State Machine with Error Recovery

**Branch**: `003-state-machine-completion` | **Date**: March 18, 2026 | **Spec**: [specs/003-state-machine-completion/spec.md](spec.md)
**Input**: Feature specification from `/specs/003-state-machine-completion/spec.md`

**Status**: Phase 0 - Initial Planning

## Summary

**Primary Requirement**: Complete the state machine implementation in AoF Browser GUI by making 3 unreachable transitions reachable (COMPLETE_SIMULATION, FAIL_SIMULATION, RESET_SIMULATION), implementing 3 TODO callback placeholders with real validation logic, and adding comprehensive error recovery and session reset capabilities.

**Current State**: State machine partially implemented (Pause/Resume ~80% done); 3 transitions unreachable; 3 callbacks are TODO placeholders. 48 existing tests passing.

**Target State**: Production-ready state machine with all transitions reachable, all callbacks implemented, error recovery paths tested, and 55+ tests passing (48 existing + 7+ new).

**Technical Approach**: 
1. Fix/extend Pause/Resume implementation (complete testing, resolve cell-skipping bug)
2. Implement unreachable transitions: RUNNING → COMPLETE_SIMULATION (via STOPPING state after success)
3. Implement successful path callbacks: validate_scenario, prepare_resources, notify_simulation_started, check completion
4. Implement error path callbacks: cleanup on failure, log errors
5. Implement reset callbacks: clear_session_data
6. Add state transition audit trail (in-memory list with dataclass records)
7. Write 7+ new tests covering all paths and error scenarios
8. Verify backward compatibility (all 48 existing tests pass)

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

## Technical Context

**Language/Version**: Python 3.x (confirmed: virtual environment with .venv, requirements.txt dependencies)

**Primary Dependencies**: 
- `transitions` library (LockedMachine for thread-safe state machine)
- `pygame` (pygame GUI framework for desktop application)
- `pytest` (testing framework; existing: 48 passing tests)

**Storage**: 
- SQLite database cache for AOF simulation scenarios (`python/hopilot/cache/aof_scenario_cache.sqlite3`)
- Session-level data (simulation results, UI state) - cleared on RESET_SIMULATION
- Database connections and cache persist across resets

**Testing**: 
- pytest framework (standard)
- Test files in root `tests/` directory per constitution
- Current coverage: 48 tests across 3 modules (test_state_machine_controller.py, test_state_machine_integration.py, test_aof_browser_gui.py)
- Target: 55+ tests (add 7+ new tests for new paths)
- Mocking: Mock AoFBrowserPanel for isolated state machine testing

**Target Platform**: Windows desktop

**Project Type**: Desktop GUI application (poker analysis tool)

**Performance Goals**: UI responsiveness during error scenarios: ≤100ms for error callbacks

**Constraints**: 
- Backward compatibility: all 48 existing tests must pass
- Code coverage: ≥90% for state_machine_controller.py
- No unreachable code paths in state machine

**Scale/Scope**: 
- Single feature affecting: state_machine_config.py, state_machine_controller.py, aof_browser_panel.py, related tests
- Codebase size: ~44,500 LOC (136 Python files)
- Complexity: State machine with 6 states, 11 callbacks, complex callback logic

## Constitution Check

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle Compliance Assessment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Real-Time Poker Analysis | ✅ N/A | State machine is infrastructure; doesn't violate |
| II. Computer Vision Accuracy | ✅ N/A | Not applicable to state machine |
| III. Modular Design | ✅ **COMPLIANCE** | State machine callbacks are modular, independently testable components |
| IV. Configuration Management | ✅ **COMPLIANT** | State transitions defined in code (state_machine_config.py); not config files per user, appropriate for framework integration |
| V. Real-Time Screen Capture | ✅ N/A | Not applicable to state machine |
| VI. Comprehensive Testing | ✅ **REQUIRED** | Feature MUST add 7+ tests to reach 55+ total; maintain ≥90% code coverage |
| VII. Consistent Logging | ✅ **REQUIRED** | All callbacks MUST use `get_logger(__name__)` for consistent logging; error handling must log details |
| VIII. Virtual Environment | ✅ **COMPLIANT** | Code runs from python/ directory within .venv |
| IX. DRY Principle | ✅ **REQUIRED** | Callback implementations must not duplicate logic; error handling abstracted |
| X. Single Responsibility | ✅ **REQUIRED** | Each callback has single responsibility; no callback should handle multiple concerns |
| XI. Established Design Patterns | ✅ **COMPLIANT** | Using `transitions` library (established state machine pattern); callbacks follow standard event handler pattern |

### Additional Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| Python in python/ directory | ✅ **COMPLIANT** | State machine code in python/hopilot/; tests in root tests/ per constitution |
| pytest in root tests/ | ✅ **REQUIRED** | All new tests MUST be in /tests/, not under python/ |
| Centralized logging | ✅ **REQUIRED** | Use hopilot.logging_config.get_logger |
| venv environment | ✅ **COMPLIANT** | Already established |

### Gate Evaluation

**Result**: ✅ **PASS - No Principles Violated**

- Feature aligns with modular design requirements (III)
- Comprehensive testing requirement (VI) addressed with 7+ new tests
- Logging consistency (VII) enforced for all callbacks
- DRY and SRP principles (IX, X) will be verified in code review
- Configuration management (IV) appropriately code-based for this feature

**Proceeding to Phase 0 Research**

## Project Structure

## Project Structure

### Documentation (this feature)

```text
specs/003-state-machine-completion/
├── spec.md                  # Feature specification (COMPLETE)
├── plan.md                  # This file (IN PROGRESS)
├── research.md              # Phase 0 research findings (GENERATED BY /speckit.plan)
├── data-model.md            # Phase 1 data model & contracts (GENERATED BY /speckit.plan)
├── quickstart.md            # Phase 1 quick reference (GENERATED BY /speckit.plan)
├── contracts/               # Phase 1 interface contracts (GENERATED BY /speckit.plan)
│   ├── callbacks.md         # Callback interface contracts
│   └── audit-trail.md       # Audit trail data structure
└── tasks.md                 # Phase 2 task breakdown (GENERATED BY /speckit.tasks)
```

### Source Code (repository root)

```text
python/hopilot/
├── state_machine_config.py              # State & transition definitions (MODIFY)
├── state_machine_utils.py               # Utility functions (REVIEW/EXTEND)
└── gui_components/
    ├── state_machine_controller.py      # Callbacks & controller logic (MODIFY - KEY FILE)
    └── aof_browser_panel.py             # GUI integration & buttons (REVIEW)

tests/
├── test_state_machine_controller.py     # State machine tests (EXTEND +7 tests)
├── test_state_machine_integration.py    # Integration tests (MAINTAIN)
└── test_aof_browser_gui.py              # GUI tests (MAINTAIN)
```

### Structure Decision

**Single-Module Feature**: State machine is a single cohesive module within the hopilot package. No microservices or multi-tier architecture needed. 

**Key Files**:
1. **state_machine_controller.py** (11 callbacks, 3 TODO → implement)
   - Callbacks: validate_scenario, has_valid_config, prepare_resources, notify_simulation_started, cancel_pending_work, context_matches, restart_workers, initiate_shutdown, all_work_done, cleanup_on_error, clear_session_data
   - Currently: 3 are TODO placeholders

2. **state_machine_config.py** (transition definitions)
   - 6 states: IDLE, RUNNING, PAUSED, STOPPING, COMPLETED, FAILED
   - 7 triggers / transitions
   - Currently: COMPLETE_SIMULATION from STOPPING is unreachable in practice

3. **aof_browser_panel.py** (GUI integration)
   - Buttons: start, pause, resume, stop, reset
   - Event handlers for button clicks

**Test Structure**: Tests in root `/tests/` directory per constitution. No tests under `python/`.

## Complexity Tracking

**No Constitution violations**. Feature is well-scoped and aligned with project principles. No special justifications needed.

---

# PHASE 0: Research & Validation

## Research Questions Resolved

All major clarifications from /speckit.clarify have been resolved:

1. ✅ **Q1: Pause/Resume Scope** → Answer C (Fix/Extend) - 80% implemented, complete testing + bug fix
2. ✅ **Q2: Error Message Handling** → Answer A (Separation of concerns) - callbacks log, UI formats
3. ✅ **Q3: Database State on Reset** → Answer A (Clear session only) - preserve connections/cache
4. ✅ **Q4: Audit Trail** → Answer B (In-memory list) - dataclass records, cleared on reset

### Technology Validation

| Component | Decision | Rationale/Evidence |
|-----------|----------|-------------------|
| State Machine Pattern | `transitions` library (LockedMachine) | Already in use; thread-safe, well-tested |
| Async Handling | Existing panel.pause_precompute/resume | Don't block UI during long operations |
| Testing Framework | pytest with mocks | Standard in project; 48 tests pass |
| Logging | hopilot.logging_config.get_logger | Consistent project pattern |
| Error Strategy | Try/catch + transition to FAILED | Explicit error states > silent failures |
| Session Data Clearing | Direct object assignment to new instance | Simple, avoids reference issues |

### Known Limitations & Workarounds

| Issue | Impact | Handling |
|-------|--------|----------|
| Cell-skipping bug in Pause/Resume | Low: intermittent data issues | Fix in Phase 1: track pending cells via index tracking |
| Context validation race condition | Low: edge case with config changes mid-pause | Document limitation: "Resume fails if scenario changed" |
| No timeout on long precompute | Medium: UI could appear frozen | Phase 2 enhancement (out of scope) |
| Audit trail not persisted | Low for current scope | In-memory only per decision; sufficient for debugging |

---

# PHASE 1: Design & Contracts

## 1. Data Model & Entities

### StateTransition (Core Entity)

```python
@dataclass
class StateTransition:
    """Record of a state machine transition event."""
    timestamp: float  # time.time()
    source_state: str  # SimulationState value
    dest_state: str    # SimulationState value
    trigger: str       # SimulationTrigger value
    exception: Optional[Exception] = None
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'source': self.source_state,
            'dest': self.dest_state,
            'trigger': self.trigger,
            'error': str(self.exception) if self.exception else None
        }
```

### SimulationSession (Aggregate Root)

```python
@dataclass
class SimulationSession:
    """Container for all data related to a single simulation run."""
    session_id: str
    board_definition: Dict[str, Any]
    player_positions: List[str]
    results: Optional[SimulationResults] = None
    
    def clear(self):
        """Clear results and intermediate data; keep configuration."""
        self.results = None
        # UI state cleared via panel reset
        
    def reset(self):
        """Full reset: new session instance created."""
        pass  # Handled by state callback
```

### AuditTrail (Audit/History)

```python
class AuditTrail:
    """In-memory list of state transitions."""
    def __init__(self):
        self.transitions: List[StateTransition] = []
    
    def record(self, source, dest, trigger, exception=None):
        transition = StateTransition(
            timestamp=time.time(),
            source_state=source,
            dest_state=dest,
            trigger=trigger,
            exception=exception
        )
        self.transitions.append(transition)
        return transition
    
    def get_history(self) -> List[Dict]:
        return [t.to_dict() for t in self.transitions]
    
    def clear(self):
        self.transitions.clear()
```

### Callback Hierarchy

All callbacks must follow pattern:
```python
def callback_name(self, event=None):
    """Callback description.
    
    Args:
        event: transitions library event (provides .model for accessing state machine)
    
    Returns:
        bool: True if condition passes, False to prevent transition
    
    Raises:
        Custom exceptions logged but not propagated to state machine
    """
```

## 2. Interface Contracts

### Callback Contract

See `/specs/003-state-machine-completion/contracts/callbacks.md`

**Interface**: State callbacks in `StateMachineController`
- **Before callbacks**: Execute before transition; can prevent transition by returning False
- **After callbacks**: Execute after transition; cannot prevent transition
- **Condition callbacks**: Check preconditions; return bool

**Error Handling Contract**:
- Log all errors with `logger.error(msg, exc_info=True)`
- Never raise exceptions to state machine (catch and log)
- Return False from conditions if validation fails
- Transition to FAILED state on critical errors

### Audit Trail Contract

See `/specs/003-state-machine-completion/contracts/audit-trail.md`

**Interface**: AuditTrail dataclass
- **record(source, dest, trigger, exception)**: Add transition record
- **get_history()**: Retrieve transition list as dicts
- **clear()**: Clear all records (called on session reset)

---

# PHASE 1: Implementation Architecture

## 1. Module Changes Required

### `state_machine_config.py` (Minor - Verify)
- ✅ States defined: IDLE, RUNNING, PAUSED, STOPPING, COMPLETED, FAILED
- ✅ Triggers defined: START, PAUSE, RESUME, STOP, COMPLETE, FAIL, RESET
- ⚠️ **Verify**: COMPLETE_SIMULATION transition exists from STOPPING state
- ⚠️ **Verify**: Callback names match controller implementation

### `state_machine_controller.py` (Major - Implement)

**11 Callbacks to Implement**:

| # | Callback | Type | Current | Status | Priority |
|---|----------|------|---------|--------|----------|
| 1 | validate_scenario | condition | ✅ exists | REVIEW | P0 |
| 2 | has_valid_config | condition | ✅ exists | REVIEW | P0 |
| 3 | prepare_resources | before | ✅ exists | REVIEW | P0 |
| 4 | notify_simulation_started | after | ✅ exists | REVIEW | P0 |
| 5 | cancel_pending_work | after | ✅ exists (pause) | FIX | P1 |
| 6 | context_matches | condition | ✅ exists | REVIEW | P1 |
| 7 | restart_workers | after | ✅ exists | REVIEW | P1 |
| 8 | initiate_shutdown | after | ❌ TODO | IMPLEMENT | P2 |
| 9 | all_work_done | condition | ❌ TODO | IMPLEMENT | P2 |
| 10 | cleanup_on_error | after | ❌ TODO | IMPLEMENT | P0 |
| 11 | clear_session_data | before | ❌ TODO | IMPLEMENT | P0 |

**Key Changes**:
- Lines 210-230: Implement error recovery callback (currently logging only)
- Add AuditTrail instance to __init__
- Add _record_transition() helper for audit logging
- Implement callback for each TODO (focus on cleanup_on_error, clear_session_data)

### `aof_browser_panel.py` (Minor - Verify)
- ✅ Buttons exist: start, pause, resume, stop, reset
- ✅ Event handlers call controller.trigger_event()
- ⚠️ **Verify**: Reset button properly triggers RESET_SIMULATION

---

## 2. Testing Strategy

### New Tests Required (7+)

| Test Category | Description | Count |
|---------------|-------------|-------|
| P1 Core Flow | Start → Running → Complete → Idle | 1 |
| Error Recovery | Start → Running → Fail → Idle | 1 |
| Session Reset | Multiple consecutive successful runs | 1 |
| Pause/Resume | Pause → Resume → Complete, with cell tracking | 2 |
| Error Callbacks | Callback validation & logging | 1 |
| Edge Cases | Invalid transitions, rapid clicks | 1 |
| **Total New Tests** | | **7+** |

### Test Fixtures

```python
@pytest.fixture
def audit_trail():
    return AuditTrail()

@pytest.fixture
def mock_panel(monkeypatch):
    panel = MagicMock()
    panel.pause_precompute.return_value = True
    panel.resume_precompute.return_value = True
    return panel

@pytest.fixture
def controller(mock_panel):
    return StateMachineController(panel=mock_panel)
```

### Verification Points

- ✅ All 48 existing tests pass
- ✅ 7+ new tests pass
- ✅ Code coverage ≥ 90% for state_machine_controller.py
- ✅ Audit trail records all transitions
- ✅ No unreachable code paths

---

# PHASE 2: Quick-Start Implementation Guide

## Getting Started

### Step 1: Understand Current State (30 min)
1. Read `python/hopilot/state_machine_config.py` - understand transition graph
2. Read `python/hopilot/gui_components/state_machine_controller.py` - understand callback pattern
3. Run existing tests: `pytest tests/test_state_machine_controller.py -v`

### Step 2: Implement Core Callbacks (2-3 hours)

**Priority Order**:
1. `clear_session_data` - simple reset callback
2. `cleanup_on_error` - error recovery logic
3. `all_work_done` - completion check
4. `initiate_shutdown` - graceful shutdown
5. Fix `cancel_pending_work` - cell tracking logic (bug fix)

### Step 3: Add Audit Trail (1 hour)

1. Create StateTransition dataclass
2. Add AuditTrail class
3. Hook into state_machine_controller to record transitions
4. Add API method to retrieve history

### Step 4: Write New Tests (2-3 hours)

1. Test fixtures and mock setup (30 min)
2. P1 tests: success path (30 min)
3. P1 tests: error path (30 min)
4. P2 tests: pause/resume (1 hour)
5. Coverage verification (30 min)

### Step 5: Verification (1 hour)

1. Run full test suite: `pytest tests/ -v`
2. Check coverage: `pytest tests/ --cov=hopilot --cov-report=html`
3. Verify no regressions in existing tests
4. Manual GUI testing: run simulator and test all transitions

---

# artifacts

## Artifact: Implementation Checklist

- [ ] Implement clear_session_data callback
- [ ] Implement cleanup_on_error callback with exception handling
- [ ] Implement all_work_done condition callback
- [ ] Implement initiate_shutdown callback
- [ ] Fix cancel_pending_work to track pending cells
- [ ] Add StateTransition dataclass
- [ ] Add AuditTrail class
- [ ] Hook audit trail into state machine
- [ ] Write test_success_path
- [ ] Write test_error_path
- [ ] Write test_reset_session
- [ ] Write test_pause_resume
- [ ] Write test_error_callbacks
- [ ] Write test_rapid_clicks
- [ ] Write test_audit_trail
- [ ] Verify 55+ tests passing
- [ ] Verify ≥90% coverage
- [ ] Manual GUI testing

---

# Next Steps

**Phase 2**: Execute /speckit.tasks to generate detailed task list with dependencies

**Outputs**: tasks.md with 10-20 actionable tasks ready for implementation

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
