# State Machine Error Handling Utilities
# Feature: 001-gui-state-refactor

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Any, List, Dict, Optional
from functools import wraps
import time

from hopilot.logging_config import get_logger

logger = get_logger(__name__)

# ==============================================================================
# AUDIT TRAIL DATA STRUCTURES (T007, T008)
# ==============================================================================

@dataclass
class StateTransition:
    """Record of a single state machine transition event.
    
    Immutable record capturing all information about a state change for
    debugging, testing, and audit trail purposes.
    
    **Usage - Access Transition Details**:
    ```python
    transition = audit_trail.get_last_transition()
    
    print(f"From: {transition.source_state}")
    print(f"To: {transition.dest_state}")
    print(f"Via: {transition.trigger}")
    print(f"At: {transition.timestamp}")
    
    if transition.exception:
        print(f"ERROR: {transition.exception}")
    ```
    
    **Usage - Check Transition Type**:
    ```python
    for t in audit_trail.transitions:
        if t.exception:
            print(f"Error transition: {t.source_state} → {t.dest_state}")
        elif t.dest_state == 'running':
            print(f"Start transition: {t.trigger}")
    ```
    
    **Usage - Serialize for Logging**:
    ```python
    transition = audit_trail.get_last_transition()
    transition_dict = transition.to_dict()
    logger.info(f"Latest: {transition_dict['timestamp_iso']} - "
                f"{transition_dict['source']} → {transition_dict['dest']}")
    ```
    
    See contracts/audit-trail.md for complete specification.
    """
    timestamp: float                           # Unix timestamp
    source_state: str                          # Origin state name
    dest_state: str                            # Destination state name
    trigger: str                               # Event trigger name
    exception: Optional[Exception] = None      # Exception if failed, None if success
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for logging and testing.
        
        Converts the transition record to a JSON-serializable dict with
        both Unix timestamp (float) and ISO format (string) for convenience.
        Error messages are stringified if present.
        
        **Returns**:
            Dictionary with keys:
            - timestamp (float): Unix timestamp
            - timestamp_iso (str): ISO 8601 format with timezone
            - source (str): Source state name
            - dest (str): Destination state name
            - trigger (str): Event trigger name
            - error (Optional[str]): Exception string if error occurred, None otherwise
        
        **Usage - Print Readable Timeline**:
        ```python
        for transition in audit_trail.transitions:
            t = transition.to_dict()
            error_mark = " ✗" if t['error'] else ""
            print(f"{t['timestamp_iso']}: {t['source']} → {t['dest']}{error_mark}")
        ```
        
        **Usage - JSON Logging**:
        ```python
        import json
        history_dicts = [t.to_dict() for t in audit_trail.transitions]
        json_log = json.dumps(history_dicts, default=str)
        logger.info(f"Session history: {json_log}")
        ```
        
        **Usage - Test Assertions on Timestamps**:
        ```python
        last_dict = audit_trail.get_last_transition().to_dict()
        assert last_dict['source'] == 'running'
        assert last_dict['timestamp'] > start_time
        assert last_dict['error'] is None
        ```
        """
        timestamp_iso = datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()
        return {
            'timestamp': self.timestamp,
            'timestamp_iso': timestamp_iso,
            'source': self.source_state,
            'dest': self.dest_state,
            'trigger': self.trigger,
            'error': str(self.exception) if self.exception else None,
        }


class AuditTrail:
    """In-memory audit trail of state transitions.
    
    Manages session-scoped history of all state machine transitions for
    debugging and testing purposes. Cleared on session reset.
    
    **Data Retention**: Session-lifetime (reset on clear_session_data callback)
    **Debugging Use**: Trace state machine path, identify error points, verify transitions
    
    **Usage Patterns**:
    
    1. **Debugging Complete History**:
       ```python
       history = audit_trail.get_history()
       for t in history:
           print(f"{t['timestamp_iso']}: {t['source']} → {t['dest']} ({t['trigger']})")
       ```
    
    2. **Finding Errors**:
       ```python
       errors = audit_trail.get_transitions_with_errors()
       if errors:
           for transition in errors:
               print(f"Error: {transition.exception}")
       ```
    
    3. **Tracking Specific State Usage**:
       ```python
       running_transitions = audit_trail.get_transitions_for_state('running')
       entries = [t for t in running_transitions if t.dest_state == 'running']
       exits = [t for t in running_transitions if t.source_state == 'running']
       print(f"RUNNING state entered {len(entries)}, exited {len(exits)} times")
       ```
    
    4. **Testing State Paths**:
       ```python
       last = audit_trail.get_last_transition()
       assert last.dest_state == 'completed'
       ```
    
    See contracts/audit-trail.md for complete specification.
    """
    
    def __init__(self):
        """Initialize empty audit trail."""
        self.transitions: List[StateTransition] = []
        self.logger = get_logger(__name__)
    
    def record(
        self,
        source: str,
        dest: str,
        trigger: str,
        exception: Optional[Exception] = None
    ) -> StateTransition:
        """Record a state transition.
        
        Called by state machine callbacks to record all transitions (including errors).
        Timestamps automatically captured. Errors logged at WARNING level.
        
        **Args**:
            source: Source state (SimulationState value like 'idle', 'running')
            dest: Destination state (SimulationState value)
            trigger: Event trigger (SimulationTrigger value like 'start_simulation')
            exception: Optional exception that caused transition (if error path)
        
        **Returns**:
            StateTransition: The recorded transition (can be used for testing)
        
        **Usage**:
        ```python
        # Normal transition
        audit_trail.record('idle', 'running', 'start_simulation')
        
        # Error transition
        exc = Exception("precompute failed")
        audit_trail.record('running', 'failed', 'fail_simulation', exception=exc)
        
        # Verify in test
        last = audit_trail.record('running', 'completed', 'done')
        assert last.dest_state == 'completed'
        ```
        
        **Debugging**: Every transition logged at DEBUG level; errors logged at WARNING level.
        Check logs to verify transitions are being recorded (set log level to DEBUG).
        """
        transition = StateTransition(
            timestamp=time.time(),
            source_state=source,
            dest_state=dest,
            trigger=trigger,
            exception=exception
        )
        self.transitions.append(transition)
        
        if exception:
            self.logger.warning(
                f"Transition recorded with error: {source} → {dest} ({trigger}): {exception}"
            )
        else:
            self.logger.debug(
                f"Transition recorded: {source} → {dest} ({trigger})"
            )
        
        return transition
    
    def get_history(self) -> List[Dict]:
        """Get all transitions as dictionaries.
        
        Returns all recorded transitions in serialized format for debugging,
        testing, and logging. Timestamps are both Unix float and ISO string.
        
        **Returns**:
            List of transition dicts with format:
            ```python
            {
                'timestamp': 1710769200.123,      # Unix timestamp (float)
                'timestamp_iso': '2026-03-18T16:00:00+00:00',  # ISO format
                'source': 'idle',                   # Source state
                'dest': 'running',                  # Destination state
                'trigger': 'start_simulation',      # Event trigger
                'error': None                       # Exception string if error, None otherwise
            }
            ```
        
        **Usage - Print Full Timeline**:
        ```python
        history = audit_trail.get_history()
        for t in history:
            status = "✓" if not t['error'] else "✗"
            print(f"{status} {t['timestamp_iso']}: {t['source']} → {t['dest']}")
        ```
        
        **Usage - Find Transition Path**:
        ```python
        history = audit_trail.get_history()
        path = " → ".join([h['source'] for h in history[:-1]] + [history[-1]['dest']])
        print(f"Path: {path}")  # e.g., "idle → running → stopping → completed"
        ```
        
        **Debugging**: Use in tests to verify full transition sequence.
        """
        return [t.to_dict() for t in self.transitions]
    
    def get_last_transition(self) -> Optional[StateTransition]:
        """Get the most recent transition.
        
        Returns the last recorded transition object for quick access to current
        machine state and how we got here. Returns None if no transitions yet.
        
        **Returns**:
            StateTransition or None if audit trail is empty
        
        **Usage - Check Current Path**:
        ```python
        last = audit_trail.get_last_transition()
        if last:
            print(f"Currently in: {last.dest_state}")
            print(f"Got here via: {last.trigger} from {last.source_state}")
        ```
        
        **Usage - Verify Transition in Test**:
        ```python
        controller.trigger_event('pause')
        last = audit_trail.get_last_transition()
        assert last.dest_state == 'paused'
        assert last.trigger == 'pause_simulation'
        ```
        
        **Usage - Check If Error Occurred**:
        ```python
        last = audit_trail.get_last_transition()
        if last and last.exception:
            print(f"Last transition had error: {last.exception}")
        ```
        
        **Debugging**: Use to quickly inspect current state and error state after operations.
        """
        return self.transitions[-1] if self.transitions else None
    
    def get_transitions_for_state(self, state: str) -> List[StateTransition]:
        """Get all transitions to/from a specific state.
        
        Returns transitions where the given state was either source or destination.
        Useful for understanding how many times a state was visited or exited.
        
        **Args**:
            state: State name to filter by (e.g., 'running', 'paused', 'failed')
        
        **Returns**:
            List of transitions where state was source or destination (may be empty)
        
        **Usage - Count State Entries**:
        ```python
        running_transitions = audit_trail.get_transitions_for_state('running')
        entries = [t for t in running_transitions if t.dest_state == 'running']
        print(f"RUNNING entered {len(entries)} times")
        ```
        
        **Usage - Detect State Thrashing**:
        ```python
        paused_transitions = audit_trail.get_transitions_for_state('paused')
        if len(paused_transitions) > 10:
            print(f"WARNING: Paused {len(paused_transitions)} times - possible UI bug?")
        ```
        
        **Usage - Trace Errors from Specific State**:
        ```python
        running_transitions = audit_trail.get_transitions_for_state('running')
        errors_from_running = [t for t in running_transitions 
                               if t.source_state == 'running' and t.exception]
        for t in errors_from_running:
            print(f"Error while in RUNNING: {t.exception}")
        ```
        
        **Debugging**: Use to understand state visit patterns and detect logic bugs.
        """
        return [
            t for t in self.transitions
            if t.source_state == state or t.dest_state == state
        ]
    
    def get_transitions_with_errors(self) -> List[StateTransition]:
        """Get all transitions that recorded errors.
        
        Returns only transitions where an exception was captured. Useful for
        post-simulation error analysis and debugging failure paths.
        
        **Returns**:
            List of transitions where exception was recorded (may be empty if no errors)
        
        **Usage - Get Error Count**:
        ```python
        errors = audit_trail.get_transitions_with_errors()
        if errors:
            print(f"Simulation encountered {len(errors)} transition errors")
        else:
            print("Simulation completed without errors ✓")
        ```
        
        **Usage - Debug Error Paths**:
        ```python
        errors = audit_trail.get_transitions_with_errors()
        for transition in errors:
            print(f"Failed: {transition.source_state} → {transition.dest_state}")
            print(f"Trigger: {transition.trigger}")
            print(f"Error: {transition.exception}")
            print(f"Time: {transition.timestamp}")
        ```
        
        **Usage - Test Error Handling**:
        ```python
        # Trigger an error path
        controller.inject_invalid_config()
        controller.trigger_event('start')
        
        # Verify error was recorded
        errors = audit_trail.get_transitions_with_errors()
        assert len(errors) == 1
        assert errors[0].dest_state == 'failed'
        ```
        
        **Debugging**: Primary method for analyzing simulation failures and verifying error recovery.
        """
        return [t for t in self.transitions if t.exception is not None]
    
    def clear(self) -> None:
        """Clear all transition records.
        
        Called on session reset (before transitioning to IDLE) to prepare for
        the next simulation session. All transitions are discarded. This is
        intentional - audit trail is session-scoped, not persisted.
        
        **Called By**: clear_session_data() callback before IDLE transition
        
        **Logging**: Logs INFO message with count of transitions cleared for debugging
        
        **Usage - Verify Reset Occurred**:
        ```python
        # Run simulation
        controller.trigger_event('start')
        // ... simulation runs ...
        controller.trigger_event('reset')
        
        # Verify audit trail was cleared
        history = audit_trail.get_history()
        assert len(history) == 0  # All previous transitions cleared
        ```
        
        **Usage - Preserve History Before Reset**:
        ```python
        # If you need to keep audit history for analysis, save it before reset
        history_backup = audit_trail.get_history()
        
        # Then reset is safe
        controller.trigger_event('reset')  # Calls audit_trail.clear() internally
        
        # History is gone from audit_trail but preserved in history_backup
        ```
        
        **Debugging**: Check logs for "Audit trail cleared (X transitions)" to verify sessions complete.
        
        See contracts/audit-trail.md - Data Retention Policy for session lifecycle details.
        """
        count = len(self.transitions)
        self.transitions.clear()
        self.logger.info(f"Audit trail cleared ({count} transitions)")


# ==============================================================================
# ERROR HANDLING UTILITIES
# ==============================================================================

def state_machine_error_handler(func: Callable) -> Callable:
    """
    Decorator for state machine callbacks that provides error handling and logging.

    Args:
        func: The callback function to wrap

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in state machine callback {func.__name__}: {e}", exc_info=True)
            # Re-raise to let state machine handle it
            raise
    return wrapper

def handle_simulation_error(event) -> None:
    """
    Global error handler for simulation state machine transitions.

    Called when any callback raises an exception during state transitions.

    Args:
        event: The transition event that caused the error
    """
    logger.error(f"Simulation state machine error during {event.event.name}: {event.error}")
    # Additional error handling logic can be added here
    # For example, attempt recovery or notify UI

def validate_transition_conditions(func: Callable[[Any], bool]) -> Callable[[Any], bool]:
    """
    Decorator for transition condition functions that provides validation and logging.

    Args:
        func: The condition function to wrap

    Returns:
        Wrapped condition function
    """
    @wraps(func)
    def wrapper(model, *args, **kwargs):
        try:
            result = func(model, *args, **kwargs)
            logger.debug(f"Transition condition {func.__name__} evaluated to: {result}")
            return result
        except Exception as e:
            logger.error(f"Error evaluating transition condition {func.__name__}: {e}")
            return False  # Fail closed for safety
    return wrapper