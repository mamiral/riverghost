# Audit Trail Interface Contract

**Contract Type**: Data Structure for Debugging  
**Feature**: 003-state-machine-completion  
**Created**: March 18, 2026

---

## Overview

The audit trail is an **in-memory history** of all state transitions during a session. It enables debugging and replay of state machine events without database overhead.

**Lifecycle**: Created with controller → records transitions → cleared on session reset

---

## Core Data Structures

### StateTransition (Record)

Immutable record of a single state transition.

```python
@dataclass
class StateTransition:
    """Record of a state machine transition event."""
    timestamp: float                           # Unix timestamp
    source_state: str                          # Origin state name
    dest_state: str                            # Destination state name
    trigger: str                               # Event trigger name
    exception: Optional[Exception] = None      # Exception if failed, None if success
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for logging/testing."""
        return {
            'timestamp': self.timestamp,
            'source': self.source_state,
            'dest': self.dest_state,
            'trigger': self.trigger,
            'error': str(self.exception) if self.exception else None,
            'timestamp_iso': datetime.fromisoformat(
                datetime.utcfromtimestamp(self.timestamp).isoformat()
            )
        }
```

**Properties**:
- Immutable (dataclass frozen=True optional)
- Serializable (provides to_dict())
- Traceable (includes timestamp)
- Error-aware (records exceptions)

---

### AuditTrail (Collection)

In-memory collection managing state transition records.

```python
class AuditTrail:
    """In-memory audit trail of state transitions."""
    
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
        """
        Record a state transition.
        
        Args:
            source: Source state (SimulationState value)
            dest: Destination state (SimulationState value)
            trigger: Event trigger (SimulationTrigger value)
            exception: Optional exception that caused transition
        
        Returns:
            StateTransition: The recorded transition
        """
        import time
        transition = StateTransition(
            timestamp=time.time(),
            source_state=source,
            dest_state=dest,
            trigger=trigger,
            exception=exception
        )
        self.transitions.append(transition)
        self.logger.debug(
            f"Transition recorded: {source} → {dest} ({trigger})"
        )
        return transition
    
    def get_history(self) -> List[Dict]:
        """
        Get all transitions as dictionaries.
        
        Returns:
            List of transition dicts with format:
            {
                'timestamp': float,
                'source': str,
                'dest': str,
                'trigger': str,
                'error': Optional[str]
            }
        """
        return [t.to_dict() for t in self.transitions]
    
    def get_last_transition(self) -> Optional[StateTransition]:
        """Get the most recent transition."""
        return self.transitions[-1] if self.transitions else None
    
    def get_transitions_for_state(self, state: str) -> List[StateTransition]:
        """Get all transitions to/from a specific state."""
        return [
            t for t in self.transitions
            if t.source_state == state or t.dest_state == state
        ]
    
    def get_transitions_with_errors(self) -> List[StateTransition]:
        """Get all transitions that recorded errors."""
        return [t for t in self.transitions if t.exception is not None]
    
    def clear(self) -> None:
        """Clear all transition records. Called on session reset."""
        count = len(self.transitions)
        self.transitions.clear()
        self.logger.info(f"Audit trail cleared ({count} transitions)")
```

---

## Integration Points

### 1. Recording in State Machine Controller

**Hook Point**: After each transition, before next state entered

```python
# In StateMachineController._init_state_machine()
self.audit_trail = AuditTrail()

# In StateMachineController (wrap state machine callback)
def _record_transition(self, event):
    """Record transition in audit trail."""
    self.audit_trail.record(
        source=event.source,
        dest=event.dest,
        trigger=event.transition.trigger,
        exception=None  # Or capture from event if error
    )

# Register callback
self.machine.add_callback('after_state_change', self._record_transition)
```

### 2. Error Recording

**When**: In cleanup_on_error() callback

```python
def cleanup_on_error(self, event=None) -> None:
    try:
        # ... cleanup logic ...
    except Exception as e:
        # Record error in audit trail
        self.audit_trail.record(
            source=event.source,
            dest=event.dest,
            trigger=event.transition.trigger,
            exception=e
        )
```

### 3. Session Reset

**When**: User clicks "Reset"

```python
def clear_session_data(self, event=None) -> None:
    # Clear audit trail along with session data
    self.audit_trail.clear()
    self.precompute_session.clear()
```

---

## Usage Patterns

### Pattern 1: Debugging (What Happened?)

```python
# Get full history
history = controller.audit_trail.get_history()

for transition in history:
    print(f"{transition['timestamp']}: "
          f"{transition['source']} → {transition['dest']} "
          f"({transition['trigger']})")
    if transition['error']:
        print(f"  ERROR: {transition['error']}")
```

### Pattern 2: Error Tracking (What Went Wrong?)

```python
# Find all error transitions
errors = controller.audit_trail.get_transitions_with_errors()

for transition in errors:
    print(f"Error at {transition.timestamp}")
    print(f"During: {transition.source_state} → {transition.dest_state}")
    print(f"Exception: {transition.exception}")
```

### Pattern 3: State Investigation (Where Are We?)

```python
# Find all transitions for RUNNING state
running_transitions = controller.audit_trail.get_transitions_for_state('running')

print(f"Entered RUNNING {len([t for t in running_transitions if t.dest_state == 'running'])} times")
print(f"Exited RUNNING {len([t for t in running_transitions if t.source_state == 'running'])} times")
```

### Pattern 4: Testing (Did This Happen?)

```python
def test_state_transition():
    controller.trigger_event('start')
    
    # Verify transition recorded
    history = controller.audit_trail.get_history()
    last_transition = history[-1]
    
    assert last_transition['source'] == SimulationState.IDLE
    assert last_transition['dest'] == SimulationState.RUNNING
    assert last_transition['trigger'] == SimulationTrigger.START_SIMULATION
    assert last_transition['error'] is None
```

---

## Data Retention Policy

| Scenario | Retention | Action |
|----------|-----------|--------|
| Normal usage | Session lifetime | Audit trail persists until user reset |
| Session reset | Cleared | `clear()` called when → IDLE |
| App restart | Lost | In-memory only; not persisted to database |
| Error scenario | Preserved | Error transitions recorded before cleanup |

**Rationale**: 
- In-memory keeps it simple and fast
- Session-scoped fits with feature scope
- Debugging-focused, not persistence-focused
- Can be extended to database in future if needed

---

## Storage Format

### In-Memory Representation

```python
audit_trail.transitions = [
    StateTransition(
        timestamp=1710769200.123,
        source_state='idle',
        dest_state='running',
        trigger='start_simulation',
        exception=None
    ),
    StateTransition(
        timestamp=1710769205.456,
        source_state='running',
        dest_state='failed',
        trigger='fail_simulation',
        exception=Exception("precompute failed")
    ),
    # ... more transitions ...
]
```

### Serialized Format (to_dict)

```json
{
    "timestamp": 1710769200.123,
    "timestamp_iso": "2026-03-18T16:00:00",
    "source": "idle",
    "dest": "running",
    "trigger": "start_simulation",
    "error": null
}
```

---

## Query Interface

### Available Queries

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_history()` | List[Dict] | All transitions as dicts |
| `get_last_transition()` | Optional[StateTransition] | Most recent transition |
| `get_transitions_for_state(state)` | List[StateTransition] | All entries/exits for state |
| `get_transitions_with_errors()` | List[StateTransition] | All error transitions |
| Custom iteration | N/A | `for t in audit_trail.transitions: ...` |

### Example: Complex Query

```python
# Find the path taken to reach FAILED state
def get_path_to_state(audit_trail, target_state):
    """Get sequence of states leading to target state."""
    path = []
    for transition in audit_trail.transitions:
        if transition.dest_state == target_state:
            path.append(transition)
            break
        path.append(transition)
    return path

# Usage
path = get_path_to_state(controller.audit_trail, SimulationState.FAILED)
print(" → ".join(t.dest_state for t in path))
# Output: idle → running → failed
```

---

## Testing Audit Trail

### Test Template

```python
def test_audit_trail_recording():
    audit_trail = AuditTrail()
    
    # Record some transitions
    audit_trail.record('idle', 'running', 'start_simulation')
    audit_trail.record('running', 'paused', 'pause_simulation')
    
    # Verify history
    history = audit_trail.get_history()
    assert len(history) == 2
    assert history[0]['dest'] == 'running'
    assert history[1]['dest'] == 'paused'

def test_audit_trail_error_recording():
    audit_trail = AuditTrail()
    
    # Record transition with error
    exc = Exception("test error")
    audit_trail.record('running', 'failed', 'fail_simulation', exception=exc)
    
    # Verify error captured
    errors = audit_trail.get_transitions_with_errors()
    assert len(errors) == 1
    assert str(errors[0].exception) == "test error"

def test_audit_trail_clear():
    audit_trail = AuditTrail()
    audit_trail.record('idle', 'running', 'start_simulation')
    assert len(audit_trail.transitions) == 1
    
    # Clear
    audit_trail.clear()
    assert len(audit_trail.transitions) == 0
```

---

## Performance Considerations

**Memory Usage**: 
- Per transition: ~200 bytes (timestamp, 3 strings, optional exception)
- 100 transitions: ~20 KB
- Session-scoped → bounded by session length

**CPU Cost**:
- Record: O(1) append
- Query: O(n) linear scan (acceptable for debugging)

**Optimization Points** (if needed):
- Add index on state for faster queries
- Add timestamp-based range queries
- Implement circular buffer for bounded memory

---

## Reference: Full Audit Trail Example

```python
# Simulated session with multiple transitions and error

audit_trail = AuditTrail()

# User starts simulation
audit_trail.record('idle', 'running', 'start_simulation')

# Simulation pauses
audit_trail.record('running', 'paused', 'pause_simulation')

# User resumes
audit_trail.record('paused', 'running', 'resume_simulation')

# Precompute fails with exception
exc = Exception("Invalid board configuration")
audit_trail.record('running', 'failed', 'fail_simulation', exception=exc)

# User clicks reset
audit_trail.record('failed', 'idle', 'reset_simulation')

# Query history
print("All transitions:")
for t in audit_trail.get_history():
    print(f"  {t['source']} → {t['dest']} ({t['trigger']})")

print("Errors:")
for t in audit_trail.get_transitions_with_errors():
    print(f"  {t.exception}")

# Output:
# All transitions:
#   idle → running (start_simulation)
#   running → paused (pause_simulation)
#   paused → running (resume_simulation)
#   running → failed (fail_simulation)
#   failed → idle (reset_simulation)
# Errors:
#   Invalid board configuration
```
