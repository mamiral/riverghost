# Quick-Start Guide: State Machine Completion

**Feature**: 003-state-machine-completion  
**Purpose**: Get up to speed on the state machine implementation  
**Target Audience**: Developers implementing this feature

---

## 30-Second Overview

The AoF Browser GUI state machine manages the lifecycle of poker simulations. Currently **3 callback handlers are TODO placeholders** and **a few transitions are unreachable**. This feature completes the implementation by:

1. Implementing the 3 TODO callbacks
2. Making unreachable transitions reachable
3. Adding comprehensive error recovery
4. Adding audit trail for debugging
5. Writing 7+ new tests

**Impact**: Takes state machine from ~80% → 100% production-ready. All 55+ tests pass. Error scenarios handled gracefully.

---

## Key Files You'll Edit

### `python/hopilot/gui_components/state_machine_controller.py` (PRIMARY)

This is the main file. Contains:
- 11 callback functions (3 are TODO)
- StateMachineController class (initialize, trigger_event())
- Mock AoFBrowserPanel for testing

**Lines to Update**:
- ~210-230: `cleanup_on_error()` callback (currently > placeholder)
- ~240-260: `clear_session_data()` callback (TODO)
- ~200: `initiate_shutdown()` callback (TODO)
- Add AuditTrail instance somewhere in __init__

### `python/hopilot/state_machine_config.py` (REVIEW)

Defines states, triggers, transitions. Likely doesn't need changes, but verify:
- 6 states defined: IDLE, RUNNING, PAUSED, STOPPING, COMPLETED, FAILED
- 7 transitions have correct callbacks
- COMPLETE_SIMULATION transition routes through STOPPING state

### `tests/test_state_machine_controller.py` (EXTEND)

Add 7+ new tests here. Currently has:
- 7 tests (48 passing with integration tests)
- New tests to add:
  - `test_success_path_complete_simulation()`
  - `test_error_path_fail_simulation()`
  - `test_reset_session_clears_data()`
  - `test_pause_resume_tracks_cells()`
  - `test_error_callback_logs_details()`

---

## The 3 TODO Callbacks

### 1. `clear_session_data()` - Reset Callback

**What it does**: Clears all simulation results and UI state before starting new run

**Location**: `state_machine_controller.py` (~line 250)

**Implementation**:
```python
def clear_session_data(self, event=None):
    """Clear session data when transitioning to IDLE after reset."""
    if self.panel and self.precompute_session:
        self.precompute_session.clear()  # Clear results but keep config
        self.logger.info("Session data cleared")
        # Update UI to show "Ready for new simulation"
```

**Test**: Verify session.results is None after reset

### 2. `cleanup_on_error()` - Error Handler

**What it does**: Handles exceptions when precompute fails, logs details, cleans up

**Location**: `state_machine_controller.py` (~line 215)

**Implementation**:
```python
def cleanup_on_error(self, event=None):
    """Cleanup when transition to FAILED state."""
    self.logger.error("Simulation failed", exc_info=True)
    if self.panel:
        # Cancel any pending work
        self.panel.cancel_pending_work()
    # Audit trail records exception in StateTransition
```

**Test**: Verify exception is logged and recorded in audit trail

### 3. `initiate_shutdown()` - Shutdown Handler

**What it does**: Gracefully shuts down precompute when user stops

**Location**: `state_machine_controller.py` (~line 200)

**Implementation**:
```python
def initiate_shutdown(self, event=None):
    """Begin graceful shutdown of running simulation."""
    if self.panel:
        self.panel.stop_workers()
    self.logger.info("Shutdown initiated")
```

**Test**: Verify workers are stopped

---

## State Transition Map

Visual representation of what you're implementing:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  IDLE ──START──→ RUNNING ──PAUSE──→ PAUSED                │
│   ↑              │                      │                  │
│   │              │                      └─RESUME──→ RUNNING│
│   │              ├─COMPLETE──→ STOPPING ──COMPLETE──→ COMPLETED
│   │              │                                      │  │
│   │              └─FAIL──→ FAILED ←────────────────────┘  │
│   │                          │                             │
│   └──────────RESET───────────┴─ COMPLETED                │
│                                                            │
└─────────────────────────────────────────────────────────────┘
```

**Key Paths**:
- **Success**: IDLE → RUNNING → STOPPING → COMPLETED → (reset) → IDLE
- **Error**: Any → RUNNING → FAIL_SIMULATION → FAILED → (reset) → IDLE
- **Pause**: RUNNING → PAUSED → RESUME → RUNNING

---

## Testing Pattern

### Test Template

```python
def test_my_scenario(controller, mock_panel):
    # Setup
    assert controller.get_current_state() == SimulationState.IDLE
    
    # Trigger event
    result = controller.trigger_event('start')
    
    # Assert state changed
    assert result is True
    assert controller.get_current_state() == SimulationState.RUNNING
    
    # Assert callback called
    mock_panel.method_name.assert_called_once()
    
    # Assert audit trail recorded
    history = controller.audit_trail.get_history()
    assert len(history) > 0
    assert history[-1]['dest'] == SimulationState.RUNNING
```

### New Tests to Add

1. **test_complete_simulation_path** - Verify RUNNING → STOPPING → COMPLETED
2. **test_fail_simulation_path** - Verify RUNNING → FAILED
3. **test_reset_clears_session** - Verify session reset works
4. **test_pause_resume_tracks_cells** - Verify pause doesn't skip cells
5. **test_error_callback_logs** - Verify error logging works
6. **test_context_validation_on_resume** - Verify validation works
7. **test_rapid_button_clicks** - Verify state machine doesn't crash on invalid transitions

---

## Audit Trail Usage

New feature: track all state transitions for debugging.

### Record Transition

```python
self.audit_trail.record(
    source=SimulationState.RUNNING,
    dest=SimulationState.STOPPING,
    trigger=SimulationTrigger.STOP_SIMULATION
)
```

### Retrieve History

```python
history = controller.audit_trail.get_history()
# Returns: List[Dict] with 'timestamp', 'source', 'dest', 'trigger', 'error'
```

### Usage in Tests

```python
def test_audit_trail_records():
    controller.trigger_event('start')
    history = controller.audit_trail.get_history()
    assert any(t['dest'] == SimulationState.RUNNING for t in history)
```

---

## Debugging Tips

### Verify State

```python
current_state = controller.get_current_state()
print(f"Current state: {current_state}")
```

### Get Status Info

```python
status = controller.get_state_info()
print(f"Can pause: {status['can_pause']}")
print(f"Can resume: {status['can_resume']}")
```

### Check Audit Trail

```python
for transition in controller.audit_trail.get_history():
    print(f"{transition['source']} → {transition['dest']} ({transition['trigger']})")
```

### Run Tests Verbosely

```bash
cd /Users/U446541/sandbox/riverghost
pytest tests/test_state_machine_controller.py -v -s
```

---

## Common Pitfalls

1. **Callbacks returning wrong type**: Return `bool` for conditions, `None` for after callbacks
2. **Not catching exceptions in callbacks**: Exceptions must be caught and logged, never propagated
3. **Modifying shared state in callbacks**: Reset callbacks must avoid race conditions
4. **Using print() instead of logger**: Always use `get_logger(__name__)`
5. **Forgetting audit trail recording**: Every transition should record event
6. **Tests in wrong directory**: Tests go in `/tests/`, not `python/tests/`

---

## Success Criteria Checklist

- [ ] All 3 TODO callbacks implemented
- [ ] All 48 existing tests pass
- [ ] 7+ new tests added (target: 55+ total)
- [ ] Code coverage ≥ 90% for state_machine_controller.py
- [ ] Audit trail records all transitions
- [ ] No unreachable code paths
- [ ] No unreachable state transitions
- [ ] Error scenarios don't crash UI
- [ ] Session reset works end-to-end

---

## Questions? Check These Docs

- **State Machine Design**: See [data-model.md](data-model.md)
- **Callback Contracts**: See [contracts/callbacks.md](contracts/callbacks.md)
- **Feature Requirements**: See [spec.md](spec.md)
- **Full Implementation Plan**: See [plan.md](plan.md)
