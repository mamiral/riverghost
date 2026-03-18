# Panel Control Interface Contract

## Overview
The AoFBrowserPanel provides execution capabilities for precompute operations. The state machine controller delegates actual work to this interface while maintaining control flow.

## Interface Definition

### Class: AoFBrowserPanel (Extended)
**Location**: `hopilot.gui_components.aof_browser_panel`

#### Method: set_state_machine_controller
```python
def set_state_machine_controller(self, controller: StateMachineController) -> None
```
**Parameters**:
- `controller`: StateMachineController - The control layer instance

**Postconditions**:
- Controller reference stored
- Event routing configured
- State synchronization established

#### Method: start_precompute
```python
def start_precompute(self) -> bool
```
**Returns**: bool - True if precompute started successfully

**Preconditions**:
- No active precompute session
- Valid scenario configuration

**Postconditions**:
- New precompute session created
- Thread pool initialized
- Computation tasks submitted

**Error Conditions**:
- Invalid configuration: Returns False
- Resource allocation failure: Returns False, logs error

#### Method: pause_precompute
```python
def pause_precompute(self) -> bool
```
**Returns**: bool - True if paused successfully

**Preconditions**:
- Active precompute session in RUNNING state

**Postconditions**:
- Session state changed to PAUSED
- Active tasks cancelled
- Checkpoint saved

#### Method: resume_precompute
```python
def resume_precompute(self) -> bool
```
**Returns**: bool - True if resumed successfully

**Preconditions**:
- Active precompute session in PAUSED state
- Scenario configuration unchanged

**Postconditions**:
- Session state changed to RUNNING
- Computation tasks restarted
- Progress continues from checkpoint

**Error Conditions**:
- Scenario changed: Returns False, raises ValueError

#### Method: stop_precompute
```python
def stop_precompute(self) -> bool
```
**Returns**: bool - True if stopped successfully

**Preconditions**:
- Active precompute session

**Postconditions**:
- Session state changed to STOPPED
- All tasks cancelled
- Resources cleaned up
- Session reset for fresh start

#### Method: reset_precompute
```python
def reset_precompute(self) -> None
```
**Postconditions**:
- Precompute session cleared
- Thread pool shutdown
- UI state reset to idle

#### Method: update_precompute_config
```python
def update_precompute_config(self, config: PrecomputeConfig) -> None
```
**Parameters**:
- `config`: PrecomputeConfig - New configuration settings

**Postconditions**:
- Worker count updated
- Simulation settings applied
- UI controls reflect new values

#### Method: get_precompute_status
```python
def get_precompute_status(self) -> Dict[str, Any]
```
**Returns**: Dict containing:
- `state`: GuiRunState - Current session state
- `progress`: Optional[Dict] - Progress information if running
- `config`: PrecomputeConfig - Current configuration
- `can_start`: bool - Whether start operation is valid
- `can_pause`: bool - Whether pause operation is valid
- `can_resume`: bool - Whether resume operation is valid
- `can_stop`: bool - Whether stop operation is valid

## Event Routing

### Modified handle_event Method
```python
def handle_event(self, event) -> bool:
    # Route precompute button events to state machine
    if self._is_precompute_button_event(event):
        return self._handle_state_machine_event(event)

    # Handle other events normally
    return self._handle_normal_event(event)
```

**Preconditions**:
- State machine controller attached

**Postconditions**:
- Precompute events routed to controller
- Other events processed normally
- Return value indicates event consumption

## State Synchronization

### Progress Updates
Panel notifies state machine of progress changes:
- Completion events
- Error conditions
- Status message updates

### Configuration Changes
Panel accepts configuration updates:
- Worker count adjustments
- Simulation parameter changes
- UI control updates

## Resource Management

### Thread Pool Lifecycle
- Created on first start_precompute call
- Shutdown on reset_precompute
- Recreated if worker count changes

### Session Management
- Sessions persist across pause/resume
- Sessions cleared on stop/reset
- Checkpoints saved for resumability

## Error Handling
- Precompute failures logged and tracked
- Resource cleanup on errors
- State machine notified of failures
- Recovery through reset operations</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-state-machine-integration\contracts\panel_interface.md