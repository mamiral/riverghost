# State Machine Integration Research

## Current GUI Architecture

### Entry Point
- `AoFGTOBrowserGUI` (aof_gto_browser_gui.py): Main pygame application that creates window and delegates to panel
- Simple event loop: handle events → draw → tick
- Command-line interface preserved for backward compatibility

### Panel Implementation
- `AoFBrowserPanel` (gui_components/aof_browser_panel.py): Complex panel with all business logic
- Contains precompute controls, matrix display, cell details, convergence plotting
- Manual state management for precompute operations

## Precompute Control System

### UI Controls
- **Buttons**: start, pause, resume, stop (pygame.Rect collision detection)
- **Knobs**: workers (1-16), simulations/cell (100-50000) with up/down buttons
- **State**: GuiRunState enum (IDLE, RUNNING, PAUSED, STOPPING, COMPLETED, FAILED)

### State Management
- `precompute_session`: GuiPrecomputeRunSession with run state, progress tracking
- `precompute_executor`: ThreadPoolExecutor for concurrent cell computation
- `precompute_futures`: Dict tracking active computation tasks
- Checkpoint persistence for resumability

### Key Methods
- `_start_precompute()`: Initializes session, creates executor, starts computation
- `runner.pause_gui_session()`: Transitions to PAUSED state
- `runner.resume_gui_session()`: Validates scenario fingerprint, transitions to RUNNING
- `runner.stop_gui_session()`: Transitions to STOPPING then PAUSED, cancels futures

## State Machine Integration Points

### Control Replacement
- State machine buttons replace manual pygame event handling in `handle_event()`
- State machine callbacks trigger panel's precompute methods
- Worker/simulation adjustments routed through state machine actions

### State Mapping
- State machine states → GuiRunState transitions
- State machine guards prevent invalid operations (e.g., pause when not running)
- Progress updates flow from runner back to state machine display

### Callback Integration
- State machine `on_enter_*` callbacks call panel methods
- State machine conditions check panel state (session.run_state)
- State machine actions update panel configuration (workers, simulations)

## Technical Constraints

### Threading
- Precompute uses ThreadPoolExecutor - state machine must be thread-safe
- transitions.LockedMachine already used in state machine implementation
- GUI updates happen on main thread, computation on worker threads

### Event Handling
- Panel's `handle_event()` method processes pygame events
- State machine needs to intercept precompute button events
- Other events (matrix selection, dropdowns) must pass through unchanged

### Configuration
- Worker count loaded from config/gto_defaults.yaml
- Simulation count has step sizing logic (coarse/fine adjustments)
- State machine needs to expose these as configurable parameters

## Integration Strategy

### Phase 1: Control Layer
- Replace button event handling with state machine triggers
- Route state machine callbacks to existing panel methods
- Preserve all existing functionality and UI layout

### Phase 2: State Synchronization
- Connect state machine states to GuiRunState
- Update state machine display with progress information
- Handle error states and recovery scenarios

### Phase 3: Enhanced Features
- Add state machine validation guards
- Implement state machine-based configuration
- Add state machine logging and telemetry

## Decision: Direct Panel Integration

**Rationale**: The existing AoFBrowserPanel contains all necessary precompute logic. Rather than duplicating this complex functionality, integrate the state machine as a control layer that delegates to the panel's existing methods.

**Approach**:
1. Modify AoFBrowserPanel to accept state machine callbacks
2. Replace manual button handling with state machine triggers
3. Connect state machine display to panel status updates
4. Preserve all existing panel functionality and UI

**Benefits**:
- Minimal code duplication
- Preserves tested precompute logic
- Maintains existing UI layout and user experience
- Clear separation: state machine controls, panel executes

**Risks**:
- Tight coupling between state machine and panel
- Need careful event routing to avoid conflicts

## Alternatives Considered

### Option 1: State Machine Wrapper
Create a new state machine GUI that wraps the existing panel, intercepting events before they reach the panel.

**Pros**: Clean separation, panel unchanged
**Cons**: Complex event interception, duplicate UI layout logic

### Option 2: Panel Refactor
Extract precompute logic from panel into separate controller class, then integrate state machine.

**Pros**: Clean architecture, testable controller
**Cons**: Major refactoring, risk of breaking existing functionality

**Decision**: Direct integration chosen for minimal risk and fastest path to working solution.</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-state-machine-integration\research.md