# State Machine Integration Data Model

## Overview
The state machine integration introduces a control layer that manages precompute operations through defined states and transitions, while delegating execution to the existing AoFBrowserPanel infrastructure.

## Core Entities

### StateMachineController
**Purpose**: Manages precompute operation lifecycle through state machine
**Fields**:
- `machine`: LockedMachine instance with defined states and transitions
- `current_state`: Current state machine state (str)
- `panel`: AoFBrowserPanel reference for execution delegation
- `config`: PrecomputeConfig with worker/simulation settings

**Relationships**:
- Controls → PrecomputeSession (1:1)
- Delegates to → AoFBrowserPanel (1:1)
- Configured by → PrecomputeConfig (1:1)

**State Transitions**:
- idle → running (on start)
- running → paused (on pause)
- paused → running (on resume)
- running|paused → stopped (on stop)
- Any state → idle (on reset)

### PrecomputeSession
**Purpose**: Tracks execution state and progress of precompute operations
**Fields**:
- `run_id`: Optional[int] - Database run identifier
- `scenario_fingerprint`: str - Scenario configuration hash
- `run_state`: GuiRunState - Current execution state
- `simulations_per_cell`: int - Computation intensity setting
- `total_cells`: int - Total work units (169 for 13x13 matrix)
- `completed_cells`: int - Successfully computed cells
- `failed_cells`: int - Failed computation attempts
- `next_cell_index`: int - Next cell to process
- `current_cell_index`: Optional[int] - Currently processing cell

**Relationships**:
- Managed by → StateMachineController (1:1)
- Persisted via → AoFScenarioCacheStore (many:1)

**Invariants**:
- `completed_cells + failed_cells + (1 if current_cell_index else 0) ≤ total_cells`
- `next_cell_index ≤ total_cells`
- State transitions follow GuiRunState validation rules

### PrecomputeConfig
**Purpose**: User-configurable precompute parameters
**Fields**:
- `max_workers`: int - Thread pool size (1-16)
- `simulations_per_cell`: int - Base computation samples (100-50000)
- `step_sizes`: Dict[str, int] - Adjustment increments for UI controls

**Relationships**:
- Configures → StateMachineController (1:1)
- Loaded from → gto_defaults.yaml (1:1)

**Validation Rules**:
- `max_workers ∈ [1, 16]`
- `simulations_per_cell ∈ [100, 50000]`

### AoFBrowserPanel (Extended)
**Purpose**: GUI panel with integrated state machine control
**New Fields**:
- `state_machine`: Optional[StateMachineController] - Control layer
- `precompute_config`: PrecomputeConfig - Current configuration

**Existing Fields** (preserved):
- `precompute_session`: Optional[GuiPrecomputeRunSession]
- `precompute_executor`: Optional[ThreadPoolExecutor]
- `precompute_buttons`: Dict[str, pygame.Rect] - UI button positions
- `precompute_worker_buttons`: Dict[str, pygame.Rect] - Worker control positions
- `precompute_sim_buttons`: Dict[str, pygame.Rect] - Simulation control positions

**Methods** (extended):
- `set_state_machine(controller: StateMachineController)` - Attach control layer
- `handle_state_machine_event(event: str, **kwargs)` - Route state machine triggers
- `update_precompute_config(config: PrecomputeConfig)` - Apply configuration changes

## Data Flow

### Configuration Flow
1. Load defaults from `gto_defaults.yaml`
2. Create `PrecomputeConfig` instance
3. Initialize `StateMachineController` with config
4. Attach controller to `AoFBrowserPanel`

### Execution Flow
1. User triggers state machine event (start/pause/resume/stop)
2. State machine validates transition and executes callbacks
3. Callbacks delegate to panel's precompute methods
4. Panel updates `PrecomputeSession` state
5. Progress updates flow back to state machine display

### Persistence Flow
1. Session state changes trigger checkpoint saves
2. `AoFScenarioCacheStore` persists session data
3. Configuration changes saved to user preferences
4. Recovery loads latest valid session on startup

## State Synchronization

### State Machine → Panel
- State transitions trigger panel method calls
- Configuration updates applied to panel settings
- Display updates reflect current state machine state

### Panel → State Machine
- Progress updates notify state machine of completion
- Error conditions trigger state machine error handling
- Status messages update state machine display

## Error Handling

### State Machine Errors
- Invalid transitions logged and rejected
- Callback failures transition to error state
- Recovery mechanisms attempt state machine reset

### Precompute Errors
- Cell computation failures increment `failed_cells`
- Session failures transition to `FAILED` state
- Error recovery allows restart from last checkpoint

## Performance Considerations

### Memory Management
- Session objects kept lightweight (< 1KB each)
- Progress updates batched to avoid UI thrashing
- Configuration cached to minimize file I/O

### Threading Safety
- State machine uses `LockedMachine` for thread safety
- Panel methods called on main thread only
- Progress updates marshalled through pygame event queue

### Scalability Limits
- Maximum 16 worker threads (configurable)
- Maximum 50,000 simulations per cell
- Total cells fixed at 169 (13x13 matrix)</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-state-machine-integration\data-model.md