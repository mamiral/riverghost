# State Machine Integration Quickstart

## Overview
This guide provides the minimal steps to integrate the completed state machine with the AOF GTO Browser GUI, replacing manual precompute controls with state machine management.

## Prerequisites
- Python 3.8+
- Completed state machine implementation (`aof_gto_browser.py`)
- Existing AOF Browser Panel (`aof_browser_panel.py`)
- Configuration file (`config/gto_defaults.yaml`)

## Integration Steps

### 1. Create State Machine Controller
```python
from hopilot.gui_components.state_machine_controller import StateMachineController
from hopilot.gui_components.precompute_config import PrecomputeConfig

# Load configuration
config = PrecomputeConfig.from_yaml(Path("config/gto_defaults.yaml"))

# Create controller (will be implemented)
controller = StateMachineController(panel=None, config=config)
```

### 2. Modify AoFBrowserPanel
```python
class AoFBrowserPanel:
    def __init__(self, ...):
        # Existing initialization
        self.state_machine_controller = None

    def set_state_machine_controller(self, controller: StateMachineController):
        self.state_machine_controller = controller
        controller.panel = self  # Bidirectional reference

    def handle_event(self, event):
        # Route precompute events to state machine
        if self._is_precompute_event(event):
            return self.state_machine_controller.trigger_event(
                self._event_to_trigger(event)
            )

        # Handle other events normally
        return self._handle_normal_event(event)
```

### 3. Update Main GUI Entry Point
```python
class AoFGTOBrowserGUI:
    def __init__(self, ...):
        # Existing initialization
        self.panel = AoFBrowserPanel(...)

        # Add state machine integration
        config = PrecomputeConfig.from_yaml(Path("config/gto_defaults.yaml"))
        controller = StateMachineController(panel=self.panel, config=config)
        self.panel.set_state_machine_controller(controller)
```

### 4. Implement State Machine Callbacks
```python
class StateMachineController:
    def on_enter_running(self, event):
        self.panel.start_precompute()

    def on_enter_paused(self, event):
        self.panel.pause_precompute()

    def on_enter_stopped(self, event):
        self.panel.stop_precompute()

    def on_enter_idle(self, event):
        self.panel.reset_precompute()
```

## Testing the Integration

### Basic Functionality Test
```bash
cd python
python -m hopilot.aof_gto_browser_gui
```

**Expected Behavior**:
- GUI window opens with matrix display
- State machine buttons replace manual controls
- Start/Pause/Resume/Stop operations work through state machine
- Progress updates shown in state machine display
- State indicator in the right-side info panel matches the active controller state
- GUI loop remains capped at 60 FPS while precompute work runs in the background

### State Transition Test
1. Click "Start" → Should transition to running state
2. Click "Pause" → Should transition to paused state
3. Click "Resume" → Should return to running state
4. Click "Stop" → Should stop the session and return the controller to idle for a fresh start
5. Allow a run to finish naturally → Should transition to completed state
6. Force a runner failure → Should transition to failed state

### Configuration Test
1. Adjust worker count via state machine controls
2. Adjust simulation count via state machine controls
3. Verify changes applied to precompute operations
4. Restart the browser with a paused session checkpoint and verify the controller restores the paused state

### Performance Test
1. Verify controller transitions complete in under 100 ms with the attached panel callbacks
2. Verify the main GUI loop calls `clock.tick(60)` to preserve a 60 FPS frame budget

## Troubleshooting

### State Machine Not Responding
- Check that controller is properly attached to panel
- Verify state machine initialized in correct state
- Check logs for transition errors

### Precompute Not Starting
- Verify panel methods are being called
- Check configuration values are valid
- Ensure no existing precompute session conflicts

### UI Not Updating
- Confirm state machine display callbacks are connected
- Check that panel status updates reach state machine
- Verify pygame event handling is working

## Next Steps
1. Complete the StateMachineController implementation
2. Add comprehensive error handling
3. Implement configuration persistence
4. Add unit tests for integration points
5. Update documentation and examples</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-state-machine-integration\quickstart.md