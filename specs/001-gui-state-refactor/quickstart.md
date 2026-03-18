# Quickstart: Refactored GuiRunState State Machine

**Feature**: 001-gui-state-refactor
**Date**: March 18, 2026

## Overview

The refactored GuiRunState system provides a robust, thread-safe state machine for simulation control using the transitions library. This guide shows how to use the new state machine in your code.

## Basic Usage

### Initialization

```python
from transitions.extensions import LockedMachine as Machine

class GuiApplication:
    def __init__(self):
        # Define states
        self.states = ['idle', 'running', 'paused', 'stopping', 'completed', 'failed']

        # Define transitions
        self.transitions = [
            {'trigger': 'start_simulation', 'source': 'idle', 'dest': 'running',
             'before': 'prepare_simulation', 'after': 'notify_simulation_started'},
            {'trigger': 'pause_simulation', 'source': 'running', 'dest': 'paused',
             'after': 'cancel_pending_work'},
            {'trigger': 'resume_simulation', 'source': 'paused', 'dest': 'running',
             'conditions': 'context_matches', 'after': 'restart_workers'},
            {'trigger': 'stop_simulation', 'source': ['running', 'paused'], 'dest': 'stopping',
             'after': 'initiate_shutdown'},
            {'trigger': 'complete_simulation', 'source': 'stopping', 'dest': 'completed',
             'conditions': 'all_work_done'},
            {'trigger': 'fail_simulation', 'source': 'running', 'dest': 'failed',
             'after': 'cleanup_on_error'},
            {'trigger': 'reset_simulation', 'source': ['completed', 'failed'], 'dest': 'idle',
             'before': 'clear_session_data'}
        ]

        # Create state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='idle',
            send_event=True,      # Pass data to callbacks
            queued=True,          # Sequential event processing
            on_exception='handle_error'  # Error recovery
        )
```

### Basic Operations

```python
# Check current state
if gui.machine.is_idle():
    print("Ready to start simulation")

# Check if action is allowed
if gui.machine.may_start_simulation():
    gui.machine.start_simulation(scenario_config)

# Use generic trigger
gui.machine.trigger('pause_simulation')
```

## Callback Implementation

### State Callbacks

```python
def on_enter_running(self, event):
    """Called when entering running state"""
    self.executor = ThreadPoolExecutor(max_workers=self.worker_count)
    self.start_time = datetime.now()
    self.submit_simulation_tasks()

def on_exit_running(self, event):
    """Called when exiting running state"""
    if self.executor:
        self.executor.shutdown(wait=False)
        self.executor = None

def on_enter_paused(self, event):
    """Called when entering paused state"""
    self.pause_time = datetime.now()
    self.cancel_pending_futures()

def on_exit_paused(self, event):
    """Called when exiting paused state"""
    self.pause_time = None
```

### Transition Callbacks

```python
def prepare_simulation(self, event):
    """Validate and prepare before starting"""
    config = event.kwargs.get('scenario_config', {})
    if not self.validate_config(config):
        raise ValueError("Invalid simulation configuration")

def context_matches(self, event):
    """Check if resume context is valid"""
    current_fingerprint = self.calculate_context_fingerprint()
    resume_fingerprint = event.kwargs.get('context_fingerprint')
    return current_fingerprint == resume_fingerprint

def handle_error(self, event):
    """Global error handler"""
    print(f"State machine error: {event.error}")
    # Log error but don't re-raise to keep state machine stable
```

## GUI Integration

### Button Enablement

```python
def update_button_states(self):
    """Update GUI button enabled states based on current state"""
    self.start_button.enabled = self.machine.may_start_simulation()
    self.pause_button.enabled = self.machine.may_pause_simulation()
    self.resume_button.enabled = self.machine.may_resume_simulation()
    self.stop_button.enabled = self.machine.may_stop_simulation()
```

### Event Handling

```python
def handle_button_click(self, button_name, **kwargs):
    """Handle GUI button clicks"""
    try:
        if self.machine.may_trigger(button_name):
            success = self.machine.trigger(button_name, **kwargs)
            if success:
                self.update_button_states()
                self.update_status_display()
            else:
                self.show_error("Action failed")
        else:
            self.show_error("Action not allowed in current state")
    except Exception as e:
        self.show_error(f"Unexpected error: {e}")
```

## Advanced Usage

### Custom Transitions

```python
# Add dynamic transitions at runtime
self.machine.add_transition(
    'emergency_stop',
    source='*',  # From any state
    dest='idle',
    after='emergency_cleanup'
)
```

### Event Data Usage

```python
def notify_simulation_started(self, event):
    """Access event data in callbacks"""
    config = event.kwargs.get('scenario_config', {})
    scenario_name = config.get('scenario_name', 'Unknown')

    self.status_text = f"Running simulation: {scenario_name}"
    self.log_event(f"Simulation started with config: {config}")
```

### Error Recovery

```python
def handle_error(self, event):
    """Comprehensive error handling"""
    error_info = {
        'error': str(event.error),
        'source_state': event.state.name if event.state else 'unknown',
        'target_transition': event.transition.name if event.transition else 'unknown',
        'timestamp': datetime.now()
    }

    # Log error
    self.logger.error("State machine error", extra=error_info)

    # Attempt recovery based on error type
    if isinstance(event.error, ValueError):
        # Configuration error - stay in current state
        self.show_user_error("Configuration error - please check settings")
    else:
        # System error - transition to failed state
        self.machine.trigger('fail_simulation')
```

## Testing

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch

def test_start_simulation():
    gui = GuiApplication()
    config = {'scenario_name': 'test_scenario'}

    # Mock the preparation method
    gui.prepare_simulation = Mock()

    # Start simulation
    result = gui.machine.start_simulation(scenario_config=config)

    assert result is True
    assert gui.machine.is_running()
    gui.prepare_simulation.assert_called_once()

def test_invalid_transition():
    gui = GuiApplication()

    # Try to pause when not running
    result = gui.machine.pause_simulation()

    assert result is False
    assert gui.machine.is_idle()
```

### Integration Testing

```python
def test_full_simulation_workflow():
    gui = GuiApplication()
    config = {'scenario_name': 'integration_test'}

    # Start simulation
    assert gui.machine.start_simulation(scenario_config=config)
    assert gui.machine.is_running()

    # Pause simulation
    assert gui.machine.pause_simulation()
    assert gui.machine.is_paused()

    # Resume simulation
    assert gui.machine.resume_simulation()
    assert gui.machine.is_running()

    # Stop simulation
    assert gui.machine.stop_simulation()
    assert gui.machine.is_idle()
```

## Troubleshooting

### Common Issues

**"Can't trigger event from state"**
- Check current state with `machine.state`
- Verify transition conditions with `machine.may_trigger(trigger_name)`
- Ensure source state matches transition definition

**"Callback method not found"**
- Verify callback method exists on model class
- Check method name matches transition definition
- Use string names for callbacks, not function objects

**Threading deadlocks**
- Use `LockedMachine` for thread safety
- Avoid calling state machine methods from within callbacks
- Use `queued=True` for sequential event processing

**Memory leaks**
- Ensure `on_exit` callbacks clean up resources
- Check for circular references in callback methods
- Monitor ThreadPoolExecutor lifecycle

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger('transitions').setLevel(logging.DEBUG)

# Inspect current state
print(f"Current state: {gui.machine.state}")
print(f"Available triggers: {gui.machine.get_triggers()}")

# Check transition validity
for trigger in gui.machine.events:
    can_trigger = gui.machine.may_trigger(trigger)
    print(f"{trigger}: {'allowed' if can_trigger else 'blocked'}")
```

## Migration from Old System

### Key Changes
1. **State queries**: `gui.run_state` → `gui.machine.state`
2. **Button checks**: Manual logic → `gui.machine.may_trigger()`
3. **Actions**: Direct method calls → `gui.machine.trigger()`
4. **Callbacks**: Scattered → Centralized in state/transition callbacks

### Migration Steps
1. Replace state checks with `machine.is_*()` methods
2. Move button enablement logic to `update_button_states()`
3. Convert direct method calls to `machine.trigger()` calls
4. Implement state callbacks for resource management
5. Add error handling with `on_exception` callbacks

This quickstart provides the foundation for using the refactored state machine. Refer to the full specification and data model for detailed implementation guidance.