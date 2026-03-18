# State Machine Control Interface Contract

## Overview
The StateMachineController provides a thread-safe interface for managing precompute operations through a defined state machine. External clients interact with precompute operations through this contract.

## Interface Definition

### Class: StateMachineController
**Location**: `hopilot.gui_components.state_machine_controller`

#### Constructor
```python
def __init__(self, panel: AoFBrowserPanel, config: PrecomputeConfig)
```
**Parameters**:
- `panel`: AoFBrowserPanel - The GUI panel to control
- `config`: PrecomputeConfig - Initial configuration settings

**Postconditions**:
- State machine initialized in 'idle' state
- Panel reference stored for delegation
- Configuration applied to panel

#### Method: trigger_event
```python
def trigger_event(self, event: str, **kwargs) -> bool
```
**Parameters**:
- `event`: str - Event name ('start', 'pause', 'resume', 'stop', 'reset')
- `**kwargs` - Event-specific parameters

**Returns**: bool - True if event accepted and processed

**Preconditions**:
- State machine properly initialized
- Event name is valid for current state

**Postconditions**:
- State transition occurs if valid
- Callbacks executed on transition
- Panel methods called as appropriate

**Error Conditions**:
- Invalid event for current state: Returns False, logs warning
- Callback failure: Transitions to error state, returns False

#### Method: get_current_state
```python
def get_current_state(self) -> str
```
**Returns**: str - Current state machine state

#### Method: get_status_info
```python
def get_status_info(self) -> Dict[str, Any]
```
**Returns**: Dict containing:
- `state`: str - Current state
- `can_start`: bool - Whether start event is valid
- `can_pause`: bool - Whether pause event is valid
- `can_resume`: bool - Whether resume event is valid
- `can_stop`: bool - Whether stop event is valid
- `progress`: Optional[Dict] - Current progress if running

#### Method: update_config
```python
def update_config(self, config: PrecomputeConfig) -> None
```
**Parameters**:
- `config`: PrecomputeConfig - New configuration settings

**Postconditions**:
- Configuration applied to panel
- State machine reflects new settings

## Event Specifications

### start Event
**Valid States**: idle, stopped, completed, failed
**Parameters**: None
**Actions**:
- Calls panel._start_precompute()
- Transitions to 'running'

### pause Event
**Valid States**: running
**Parameters**: None
**Actions**:
- Calls panel.pause_precompute()
- Transitions to 'paused'

### resume Event
**Valid States**: paused
**Parameters**: None
**Actions**:
- Calls panel.resume_precompute()
- Transitions to 'running'

### stop Event
**Valid States**: running, paused
**Parameters**: None
**Actions**:
- Calls panel.stop_precompute()
- Transitions to 'stopped'

### reset Event
**Valid States**: Any
**Parameters**: None
**Actions**:
- Calls panel.reset_precompute()
- Transitions to 'idle'

## Callback Contract

### State Callbacks
State machine callbacks follow the pattern:
```python
def on_enter_<state>(self, event, **kwargs):
    # Execute state-specific logic
    pass
```

**Required Callbacks**:
- `on_enter_running` - Start precompute execution
- `on_enter_paused` - Pause active execution
- `on_enter_stopped` - Stop execution and cleanup
- `on_enter_idle` - Reset to initial state

## Thread Safety
- All methods are thread-safe through LockedMachine
- External calls can be made from any thread
- Internal panel calls marshalled to main thread as needed

## Error Handling
- Invalid state transitions logged and rejected
- Callback exceptions caught and logged
- State machine enters error state on critical failures
- Recovery through reset event</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-state-machine-integration\contracts\state_machine_interface.md