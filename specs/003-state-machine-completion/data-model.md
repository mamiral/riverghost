# Data Model: State Machine Completion Feature

**Feature**: 003-state-machine-completion  
**Component**: State Machine with Error Recovery  
**Created**: March 18, 2026

---

## Entity Relationships

```
SimulationSession (root)
├── board_definition: Dict
├── player_positions: List
└── results: SimulationResults (optional)

StateTransition (audit history)
├── timestamp: float
├── source_state: str
├── dest_state: str
├── trigger: str
└── exception: Optional[Exception]

AuditTrail (aggregate)
└── transitions: List[StateTransition]
```

---

## Core Entities

### 1. State Machine States

**Enumeration**: `SimulationState`

```python
class SimulationState:
    IDLE = 'idle'
    RUNNING = 'running'
    PAUSED = 'paused'
    STOPPING = 'stopping'
    COMPLETED = 'completed'
    FAILED = 'failed'
```

**Lifecycle**:
```
IDLE → RUNNING → [PAUSED → RUNNING] → STOPPING → COMPLETED
                                     ↓
                               FAILED ← (any failure)
                                ↓
                              (reset to) IDLE
```

### 2. StateTransition (Record)

**Purpose**: Audit trail entry for each state transition

**Fields**:
- `timestamp: float` - Unix timestamp of transition
- `source_state: str` - Origin state (SimulationState value)
- `dest_state: str` - Destination state
- `trigger: str` - Event that triggered transition (SimulationTrigger value)
- `exception: Optional[Exception]` - Exception if transition failed, None if success

**Behavior**:
- Immutable once created
- Serializable via `to_dict()` method
- Used for debugging and replay

### 3. AuditTrail (Collection)

**Purpose**: In-memory log of all state transitions in current session

**Methods**:
- `record(source, dest, trigger, exception=None)` → StateTransition
- `get_history() → List[Dict]` - Get all transitions as dicts
- `clear()` - Clear all records (called on session reset)

**Lifecycle**:
- Created when StateMachineController initializes
- Records accumulate during session
- Cleared when user clicks "Reset" or session ends
- Not persisted to database (in-memory only)

### 4. SimulationSession (Aggregate Root)

**Purpose**: Container for all data related to one simulation run

**Fields**:
- `session_id: str` - Unique session identifier
- `board_definition: Dict[str, Any]` - Board state (cards, positions)
- `player_positions: List[str]` - Player seating
- `results: Optional[SimulationResults]` - Output of successful simulation

**Methods**:
- `clear()` - Clear results; keep configuration
- `reset()` - Create new session instance

**Lifecycle**:
- New session created when user clicks "Start"
- Configuration set from current GUI state
- Results populated after successful COMPLETING
- Cleared on RESET_SIMULATION
- Database connections outside this object persist

### 5. Callback Interface

**Purpose**: Extensible hooks executed during state transitions

**Contract**:
```python
def callback_name(event=None) -> bool:
    """
    Callback executed on state machine event.
    
    Args:
        event: transitions.core.Event object
               event.model = StateMachineController instance
               event.transition = Transition object
    
    Returns:
        bool: True to allow transition, False to prevent (conditions only)
        
    Raises:
        Never raises; catches and logs exceptions
    """
```

**Types**:
1. **Conditions** (return bool)
   - `validate_scenario()` - Check board/players are valid
   - `has_valid_config()` - Config exists and complete
   - `context_matches()` - Resume state matches current scenario
   - `all_work_done()` - All work completed successfully

2. **Before Callbacks** (execute before transition)
   - `clear_session_data()` - Clear old session data

3. **After Callbacks** (execute after transition)
   - `prepare_resources()` - Allocate precompute resources
   - `notify_simulation_started()` - Notify UI simulation started
   - `cancel_pending_work()` - Cancel pending precompute work
   - `restart_workers()` - Restart paused workers
   - `initiate_shutdown()` - Begin graceful shutdown
   - `cleanup_on_error()` - Handle cleanup after failure

---

## Data Validation Rules

### SimulationSession Validation

- `board_definition` must have all required cards
- `player_positions` must have 2+ players
- `results` may be None (not yet computed)

### State Transition Validation

- Source state must be valid (in SIMULATION_STATES)
- Destination state must be valid
- Transition must be allowed (defined in SIMULATION_TRANSITIONS)
- Trigger must correspond to transition

### Callback Validation

- All callbacks must return bool or None (conditions)
- All exceptions caught and logged (never propagated)
- All logging goes through `get_logger(__name__)`

---

## State Transition Matrix

**Allowed Transitions**:

| From | Event | To | Condition |
|------|-------|----|----|
| IDLE, COMPLETED, FAILED | START_SIMULATION | RUNNING | has_valid_config |
| RUNNING | PAUSE_SIMULATION | PAUSED | (none) |
| PAUSED | RESUME_SIMULATION | RUNNING | context_matches |
| RUNNING, PAUSED | STOP_SIMULATION | STOPPING | (none) |
| STOPPING | COMPLETE_SIMULATION | COMPLETED | all_work_done |
| RUNNING | FAIL_SIMULATION | FAILED | (none) |
| COMPLETED, FAILED | RESET_SIMULATION | IDLE | (none) |

**Unreachable Transitions** (To Be Fixed):
- RUNNING → COMPLETED (must go through STOPPING)
- Direct completion feedback needed (currently user waits for STOPPING)

---

## Session Data Lifecycle

### On Initialize
```
new SimulationSession(
    session_id=uuid.uuid4(),
    board_definition={},
    player_positions=[],
    results=None
)
```

### On Start Simulation
```
session.board_definition = copy(current_board)
session.player_positions = copy(current_players)
session.results = None
```

### On Success
```
session.results = SimulationResults(...)
# Stay in COMPLETED state with results
```

### On Failure
```
session.results = None  # Results discarded
# Move to FAILED state
```

### On Reset
```
session.clear()  # Results cleared
# New session created
# User can start new simulation immediately
```

---

## Error Handling Model

**Error Propagation**:
```
Exception in precompute
    ↓
catch in callback wrapper
    ↓
log to file with traceback
    ↓
transition to FAILED state
    ↓
UI displays "Error occurred. Click Reset to try again."
```

**No Silent Failures**: Every error results in explicit FAILED state transition

**Error Record**: Audit trail records exception in StateTransition object
