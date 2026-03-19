# Callback Interface Contracts

**Contract Type**: State Machine Callbacks  
**Feature**: 003-state-machine-completion  
**Created**: March 18, 2026

---

## Callback Contract Overview

All state machine callbacks follow a standard contract for consistency, testing, and error handling.

---

## Standard Callback Signature

```python
def callback_name(self, event=None) -> Optional[bool]:
    """
    State machine callback - execute on state change event.
    
    Universal Pattern:
    1. Log entry (optional, except for errors)
    2. Perform action or validation
    3. Log result or error
    4. Return bool (conditions only) or None (after callbacks)
    
    Args:
        self: StateMachineController instance (self.model in transitions)
        event: transitions.core.Event object (optional)
               - event.model = state machine model (self)
               - event.transition = Transition object
               - event.event = Event instance
               - event.source = source state
               - event.dest = destination state
    
    Returns:
        bool: For condition callbacks (default: True)
        None: For before/after callbacks
        
    Raises:
        Never. All exceptions caught, logged, not propagated.
        Exception is stored in StateTransition record if in error path.
    """
```

---

## Callback Categories

### 1. Condition Callbacks (Pre-Transition Validation)

**Purpose**: Check if transition is allowed to proceed

**Pattern**:
```python
def condition_callback(self, event=None) -> bool:
    try:
        # Validation logic
        result = check_something()
        if result:
            self.logger.debug(f"Condition passed: {condition_name}")
            return True
        else:
            self.logger.warning(f"Condition failed: {condition_name}; reason=...")
            return False
    except Exception as e:
        self.logger.error(f"Error in {condition_name}", exc_info=True)
        return False  # Prevent transition on error
```

**Examples**:
- `has_valid_config()` - Returns True if config complete
- `validate_scenario()` - Returns True if board/players valid
- `context_matches()` - Returns True if resume context unchanged
- `all_work_done()` - Returns True if no pending work

**Contract**:
- Must always return `bool` (True or False)
- Must catch all exceptions and return False
- Use logger for debugging


### 2. Before Callbacks (Pre-Transition Setup)

**Purpose**: Set up state before transition commits

**Pattern**:
```python
def before_callback(self, event=None) -> None:
    try:
        self.logger.info(f"Preparing for {event.dest} state")
        # Setup logic
        setup_action()
        self.logger.info("Setup complete")
    except Exception as e:
        self.logger.error("Setup failed", exc_info=True)
        raise  # Let state machine handle error
```

**Examples**:
- `clear_session_data()` - Clear old data on reset
- `prepare_resources()` - Allocate resources before starting

**Contract**:
- Return type: Any (usually None)
- Can raise exception to prevent/handle failure
- Idempotent (safe to call multiple times)


### 3. After Callbacks (Post-Transition Actions)

**Purpose**: Execute side effects after transition completes

**Pattern**:
```python
def after_callback(self, event=None) -> None:
    try:
        self.logger.info(f"Entered {event.dest} state")
        # Action logic
        post_transition_action()
        self.logger.info("Post-transition complete")
    except Exception as e:
        self.logger.error("Post-transition failed", exc_info=True)
        # Don't raise - transition already committed
```

**Examples**:
- `notify_simulation_started()` - Update UI after start
- `cancel_pending_work()` - Cancel work on pause
- `cleanup_on_error()` - Clean up after failure
- `restart_workers()` - Resume work after pause

**Contract**:
- Executes after transition is committed
- Exceptions logged but transition not reversed
- Best effort - avoid critical operations


---

## Specific Callback Contracts

### Required Callbacks (Implement First)

#### `clear_session_data()` - BEFORE → IDLE

**Event**: Transition to IDLE from COMPLETED/FAILED (i.e., session reset)

**Responsibility**: 
- Clear simulation results
- Clear UI state
- Reset panel to "ready" display

**Implementation Contract**:
```python
def clear_session_data(self, event=None) -> None:
    """Clear all session data when entering IDLE state (typically after reset)."""
    try:
        if self.precompute_session:
            self.precompute_session.results = None
            self.precompute_session.progress = 0
        if self.panel:
            self.panel.clear_simulation_display()
        self.logger.info("Session cleared")
    except Exception as e:
        self.logger.error("Failed to clear session", exc_info=True)
```

**Testable**: 
- Call reset → IDLE
- Assert session.results is None
- Assert UI shows "Ready"


#### `cleanup_on_error()` - AFTER → FAILED

**Event**: Transition to FAILED after exception

**Responsibility**:
- Log error with full traceback
- Cancel pending work
- Record exception in audit trail
- Clean up partial results

**Implementation Contract**:
```python
def cleanup_on_error(self, event=None) -> None:
    """Cleanup and error handling when entering FAILED state."""
    try:
        # Capture exception context
        import sys
        exc_info = sys.exc_info()
        
        self.logger.error(
            f"Simulation failed during {event.source}",
            exc_info=exc_info
        )
        
        # Cancel work
        if self.panel:
            self.panel.cancel_pending_work()
        
        # Clear partial results
        if self.precompute_session:
            self.precompute_session.results = None
        
        # Record error in audit trail
        self.audit_trail.record(
            source=event.source,
            dest=event.dest,
            trigger=event.transition.trigger,
            exception=exc_info[1]
        )
    except Exception as e:
        self.logger.error("Error cleanup also failed", exc_info=True)
```

**Testable**:
- Trigger error → FAILED
- Assert exception logged with traceback
- Assert work cancelled
- Assert error in audit trail


#### `notify_simulation_started()` - AFTER → RUNNING

**Event**: Transition to RUNNING after successful validation and resource prep

**Responsibility**:
- Notify user that simulation started
- Update UI indicators (progress bar, status text)
- Start any monitoring/heartbeat

**Implementation Contract**:
```python
def notify_simulation_started(self, event=None) -> None:
    """Notify UI that simulation has started."""
    try:
        self.logger.info("Simulation started")
        if self.panel:
            self.panel.status_message = "Simulation running..."
            self.panel.show_progress_bar()
    except Exception as e:
        self.logger.error("Failed to notify simulation start", exc_info=True)
```

**Testable**:
- Start → RUNNING
- Assert UI shows running status


### Error Handling Requirements

**All callbacks MUST**:

1. Wrap code in try/except
2. Log errors with `self.logger.error(msg, exc_info=True)`
3. Return `False` if condition callback, `None` if before/after
4. Never propagate exceptions to state machine
5. Record exception in audit trail if relevant

**Error Audit Trail Example**:
```python
self.audit_trail.record(
    source=SimulationState.RUNNING,
    dest=SimulationState.FAILED,
    trigger=SimulationTrigger.FAIL_SIMULATION,
    exception=Exception("precompute timeout")
)
```

---

## Testing Callbacks

### Test Template

```python
@patch('hopilot.gui_components.aof_browser_panel.AoFBrowserPanel.method_name')
def test_callback_name(controller, mock_method):
    # Setup
    controller.state = SimulationState.SOURCE
    
    # Call callback
    controller.callback_name()
    
    # Assert expected action
    mock_method.assert_called_once()
    
    # Assert logging
    assert controller.logger.info.called or controller.logger.error.called
```

### Callback Test Categories

1. **Happy Path**: Normal execution, all checks pass
2. **Error Path**: Exception during callback execution
3. **Validation Path**: Condition checks fail gracefully
4. **UI Update Path**: UI components updated correctly

---

## Callback Composition Rules

**Independence**: Each callback MUST be independently callable without side effects from other callbacks

**Idempotency**: Callbacks safe to call multiple times (important for retries)

**Logging**: Every callback must log entry point (at debug level), key decisions (info), and errors (error level)

**No Shared Mutable State**: Avoid static/global variables; use instance variables

---

## Reference Implementation: cleanup_on_error

```python
def cleanup_on_error(self, event=None) -> None:
    """
    Cleanup when entering FAILED state after exception.
    
    Handles:
    - Exception logging
    - Work cancellation
    - Results cleanup
    - Audit trail recording
    """
    try:
        # Extract exception context
        import sys
        exc_info = sys.exc_info()
        exception = exc_info[1] if exc_info[1] else None
        
        # Log error
        self.logger.error(
            f"Simulation failed during state {event.source}",
            exc_info=True
        )
        
        # Cancel pending work
        if self.panel and self.precompute_session:
            self.panel.cancel_pending_work()
        
        # Clear partial results
        if self.precompute_session:
            self.precompute_session.results = None
        
        # Record in audit trail
        if self.audit_trail:
            self.audit_trail.record(
                source=event.source,
                dest=event.dest,
                trigger=event.transition.trigger,
                exception=exception
            )
        
    except Exception as nested_error:
        # Catch errors in error handling itself
        self.logger.error(
            f"Error handler failed: {nested_error}",
            exc_info=True
        )
```

---

## Verification Checklist

For each callback implementation:

- [ ] Returns correct type (bool or None)
- [ ] Wrapped in try/except
- [ ] Uses `get_logger(__name__)`
- [ ] Logs important decisions and errors
- [ ] Doesn't raise exceptions to state machine
- [ ] Idempotent (safe to call multiple times)
- [ ] No shared mutable state
- [ ] Has at least 1 test case
- [ ] Error path tested
- [ ] UI effects verified if UI interaction
