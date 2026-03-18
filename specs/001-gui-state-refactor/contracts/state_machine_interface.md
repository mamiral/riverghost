# Interface Contract: State Machine API

**Contract ID**: SM-001
**Feature**: 001-gui-state-refactor
**Date**: March 18, 2026
**Version**: 1.0

## Overview

This contract defines the public interface for the refactored GuiRunState state machine. It specifies how external components (GUI handlers, tests, monitoring) interact with the simulation control system.

## Interface Definition

### Primary Interface: SimulationStateMachine

**Location**: `aof_gto_browser.py` (in GuiApplication class)

**Purpose**: Provides thread-safe simulation lifecycle management with event-driven state transitions.

#### Public Methods

##### State Query Methods
```python
# Get current simulation state
current_state: str = machine.state

# Check if specific state is active
is_idle: bool = machine.is_idle()
is_running: bool = machine.is_running()
is_paused: bool = machine.is_paused()
is_stopping: bool = machine.is_stopping()
is_completed: bool = machine.is_completed()
is_failed: bool = machine.is_failed()

# Check if transition is currently allowed
can_start: bool = machine.may_start_simulation()
can_pause: bool = machine.may_pause_simulation()
can_resume: bool = machine.may_resume_simulation()
can_stop: bool = machine.may_stop_simulation()
```

##### State Transition Methods
```python
# Start new simulation
success: bool = machine.start_simulation(scenario_config: dict) -> bool

# Pause running simulation
success: bool = machine.pause_simulation() -> bool

# Resume paused simulation
success: bool = machine.resume_simulation() -> bool

# Stop simulation (running or paused)
success: bool = machine.stop_simulation() -> bool

# Reset to idle state (from completed/failed)
success: bool = machine.reset_simulation() -> bool
```

##### Dynamic Trigger Method
```python
# Generic trigger for custom transitions
success: bool = machine.trigger(event_name: str, *args, **kwargs) -> bool
```

#### Events and Callbacks

##### State Change Events
- `on_enter_idle`: Fired when entering idle state
- `on_exit_idle`: Fired when exiting idle state
- `on_enter_running`: Fired when simulation starts
- `on_exit_running`: Fired when simulation stops/pauses
- `on_enter_paused`: Fired when simulation is paused
- `on_exit_paused`: Fired when simulation resumes/stops
- `on_enter_stopping`: Fired when graceful shutdown begins
- `on_enter_completed`: Fired when simulation completes successfully
- `on_enter_failed`: Fired when simulation ends with error

##### Transition Events
- `before_start_simulation`: Pre-validation before starting
- `after_start_simulation`: Post-startup setup
- `before_pause_simulation`: Pre-pause validation
- `after_pause_simulation`: Post-pause cleanup
- `before_resume_simulation`: Pre-resume validation
- `after_resume_simulation`: Post-resume setup
- `before_stop_simulation`: Pre-stop validation
- `after_stop_simulation`: Post-stop cleanup

##### Error Handling Events
- `on_simulation_error`: Fired when any transition encounters an error
- `finalize_simulation_event`: Always fired after any transition attempt

## Data Contracts

### Input Parameters

#### Scenario Configuration (start_simulation)
```python
{
    "scenario_name": str,           # Required: Name of simulation scenario
    "cell_range": tuple[int, int], # Required: (start_cell, end_cell)
    "worker_count": int,           # Optional: ThreadPoolExecutor max_workers (default: CPU count)
    "checkpoint_enabled": bool,    # Optional: Enable checkpoint saving (default: True)
    "timeout_seconds": int         # Optional: Maximum execution time (default: None)
}
```

#### Context Validation (resume_simulation)
```python
{
    "context_fingerprint": str,     # Required: Hash of scenario parameters
    "session_id": str,             # Required: Unique session identifier
    "last_checkpoint": datetime,   # Optional: Last saved checkpoint time
}
```

### Output Data

#### State Information
```python
{
    "current_state": str,          # Current state name
    "session_id": str|None,        # Active session identifier
    "start_time": datetime|None,   # When simulation started
    "pause_time": datetime|None,   # When simulation was paused
    "progress": float|None,        # Completion percentage (0.0-1.0)
    "error_message": str|None,     # Last error description
    "active_workers": int          # Number of running worker threads
}
```

#### Transition Result
```python
{
    "success": bool,               # Whether transition completed
    "new_state": str,              # Resulting state name
    "error": str|None,             # Error message if failed
    "transition_time": float       # Time taken for transition (seconds)
}
```

## Behavioral Contracts

### State Machine Guarantees

#### Thread Safety
- All public methods are thread-safe
- Concurrent calls are serialized via internal locking
- State consistency maintained across threads
- No race conditions in state transitions

#### Event Ordering
- Events fire in deterministic order
- State change occurs between `on_exit` and `on_enter`
- `finalize_event` always executes last
- Error events fire before finalization

#### Resource Management
- ThreadPoolExecutor created in `on_enter_running`
- ThreadPoolExecutor shutdown in `on_exit_running`
- Futures cancelled in `on_exit_paused` and `on_exit_stopping`
- No resource leaks on error conditions

### Error Handling Contracts

#### Invalid Transitions
- `may_*` methods return False for invalid transitions
- `trigger()` methods return False for invalid transitions
- No exceptions raised for invalid transitions (when `ignore_invalid_triggers=True`)

#### Exception Handling
- Exceptions in callbacks trigger `on_exception` events
- State machine remains in valid state after exceptions
- `finalize_event` executes even after exceptions
- Error information passed via EventData

#### Recovery Mechanisms
- Failed simulations transition to `failed` state
- `reset_simulation()` available from `completed`/`failed` states
- Context validation prevents invalid resumes
- Checkpoint restoration handles corrupted data

## Performance Contracts

### Latency Guarantees
- State queries (`is_*`, `may_*`): < 1ms
- Simple transitions (idle ↔ running): < 10ms
- Complex transitions (with validation): < 100ms
- ThreadPoolExecutor operations: < 500ms

### Throughput Requirements
- Support 100+ rapid button clicks per second
- Handle 10+ concurrent transition attempts
- Maintain UI responsiveness during long operations
- Process 1000+ simulation cells efficiently

### Resource Limits
- Memory usage: < 50MB for state machine overhead
- CPU usage: < 5% for state management operations
- Thread count: Dynamic based on worker_count parameter
- Disk I/O: Minimal, only for checkpoints

## Compatibility Contracts

### Backward Compatibility
- Existing checkpoint format preserved
- Public method signatures maintained
- Event firing patterns preserved
- Error message formats maintained

### Version Compatibility
- Compatible with transitions==0.9.3
- Supports Python 3.8+ (matching project requirements)
- Works with existing Pygame GUI framework
- Compatible with current ThreadPoolExecutor usage

## Testing Contracts

### Unit Test Interface
```python
# Mock state machine for testing
mock_machine = Mock()
mock_machine.state = "idle"
mock_machine.may_start_simulation.return_value = True
mock_machine.start_simulation.return_value = True

# Test callback execution
callback_mock = Mock()
machine.on_enter_running = callback_mock
machine.start_simulation()
callback_mock.assert_called_once()
```

### Integration Test Interface
```python
# Full state machine testing
gui = GuiApplication()
assert gui.machine.is_idle()

# Test complete workflow
gui.machine.start_simulation(config)
assert gui.machine.is_running()

gui.machine.pause_simulation()
assert gui.machine.is_paused()

gui.machine.stop_simulation()
assert gui.machine.is_idle()
```

## Monitoring Contracts

### Health Checks
```python
# State machine health
health = {
    "state_machine_operational": bool,
    "current_state_valid": bool,
    "active_threads": int,
    "pending_transitions": int,
    "last_transition_time": datetime
}
```

### Metrics Collection
- Transition count by type
- Error rate by transition
- Average transition latency
- Thread pool utilization
- State residency time

## Change Management

### Interface Evolution
- New methods added with default implementations
- Existing method signatures preserved
- Deprecation warnings for changed behavior
- Version compatibility matrix maintained

### Breaking Changes
- Require major version bump
- Provide migration guide
- Maintain backward compatibility period
- Document upgrade path

This contract ensures reliable integration between the state machine and external components while maintaining thread safety and performance requirements.