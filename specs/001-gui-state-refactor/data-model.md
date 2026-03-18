# Data Model: GuiRunState State Machine Refactor

**Feature**: 001-gui-state-refactor
**Date**: March 18, 2026

## Overview

The refactored GuiRunState system uses the transitions library to implement a robust state machine for simulation control. The data model centers around the state machine's core entities and their relationships.

## Core Entities

### StateMachine (transitions.Machine)
**Purpose**: Core state machine instance managing simulation lifecycle
**Attributes**:
- `states`: OrderedDict of State objects
- `events`: Dict of Event objects by trigger name
- `models`: List of managed model objects (GUI instances)
- `initial`: String name of initial state
- `send_event`: Boolean for data encapsulation
- `queued`: Boolean for sequential event processing

**Relationships**:
- Manages multiple State entities
- Contains multiple Event entities
- Controls multiple Model entities
- References current State for each Model

**Lifecycle**:
- Created during GUI initialization
- Persisted across application sessions
- Manages state transitions via triggers

### State (transitions.State)
**Purpose**: Represents a specific condition in the simulation lifecycle
**Attributes**:
- `name`: String identifier (idle, running, paused, stopping, completed, failed)
- `on_enter`: List of callback functions executed when entering state
- `on_exit`: List of callback functions executed when exiting state
- `final`: Boolean indicating terminal state

**Relationships**:
- Referenced by StateMachine.states
- Source/destination for Transition entities
- Contains callback references to Model methods

**Validation Rules**:
- Name must be unique within StateMachine
- Callbacks must be callable or resolvable method names
- Final states cannot have outgoing transitions

### Transition (transitions.Transition)
**Purpose**: Defines valid state changes with associated logic
**Attributes**:
- `trigger`: String method name added to models
- `source`: String or list of source state names
- `dest`: String destination state name or None (internal transition)
- `conditions`: List of condition check functions
- `before`: List of pre-transition callback functions
- `after`: List of post-transition callback functions
- `prepare`: List of preparation callback functions

**Relationships**:
- Owned by Event entity
- References State entities for source/destination
- Contains callback references to Model methods

**Validation Rules**:
- Source states must exist in StateMachine
- Destination state must exist (unless None for internal)
- All callbacks must be callable or resolvable

### Event (transitions.Event)
**Purpose**: Groups transitions by trigger and manages execution
**Attributes**:
- `name`: String trigger name
- `transitions`: Dict of transitions by source state
- `machine`: Reference to owning StateMachine

**Relationships**:
- Owned by StateMachine.events
- Contains multiple Transition entities
- Executes on Model instances

### Model (GuiApplication)
**Purpose**: The GUI application instance being managed by the state machine
**Attributes**:
- `state`: Current state name (managed by StateMachine)
- `precompute_session`: Optional simulation session object
- `precompute_context`: Optional simulation context data
- `executor`: Optional ThreadPoolExecutor instance

**Relationships**:
- Managed by StateMachine.models
- Contains simulation-specific data
- Implements callback methods for state transitions

**Lifecycle States**:
- `idle`: No active simulation
- `running`: Simulation executing
- `paused`: Simulation suspended
- `stopping`: Simulation shutting down
- `completed`: Simulation finished successfully
- `failed`: Simulation ended with error

## Data Flow

### State Transition Flow
1. User action triggers Event via model.trigger()
2. Event validates source state and executes matching Transition
3. Transition executes callbacks in order: prepare → conditions → before → on_exit → on_enter → after
4. StateMachine updates model.state to destination
5. finalize_event callbacks execute regardless of outcome

### Resource Management Flow
- **on_exit** callbacks: Clean up resources (shutdown ThreadPoolExecutor)
- **on_enter** callbacks: Initialize resources (create ThreadPoolExecutor)
- **Exception handling**: on_exception callbacks for error recovery
- **Finalization**: finalize_event callbacks for guaranteed cleanup

## Validation Rules

### State Machine Integrity
- All states referenced by transitions must exist
- All callbacks must be resolvable on model instances
- Initial state must be defined and exist
- No circular dependencies in state definitions

### Transition Validity
- Source states must be valid state names or wildcards
- Destination must be valid state name, None, or reflexive (=)
- Conditions must return boolean values
- Callbacks must not modify state machine during execution

### Thread Safety
- All model attributes accessed by callbacks must be thread-safe
- Shared resources must use appropriate locking
- Callbacks should avoid long-running operations

## Entity Relationships Diagram

```
StateMachine
├── states: Dict<string, State>
├── events: Dict<string, Event>
├── models: List<Model>
└── current_state: State

State
├── name: string
├── on_enter: List<callback>
├── on_exit: List<callback>
└── final: boolean

Event
├── name: string
├── transitions: Dict<string, Transition>
└── machine: StateMachine

Transition
├── trigger: string
├── source: string|List<string>
├── dest: string|None
├── conditions: List<callback>
├── before: List<callback>
├── after: List<callback>
└── prepare: List<callback>

Model (GuiApplication)
├── state: string (managed)
├── precompute_session: Session|None
├── precompute_context: Context|None
├── executor: ThreadPoolExecutor|None
└── callback_methods: Dict<string, function>
```

## Data Persistence

### Checkpoint Data
- `precompute_session`: Serialized simulation state
- `precompute_context`: Scenario parameters and configuration
- `state`: Current state machine state name

### Serialization Strategy
- Use Python pickle for complex objects
- Store state separately for restoration
- Validate state consistency on load
- Handle version compatibility for saved data

## Performance Considerations

### Memory Usage
- StateMachine: Minimal overhead (~100KB for typical configurations)
- State objects: Lightweight with callback references
- Transition objects: Small with condition/before/after lists

### Execution Performance
- Callback resolution: O(1) for method names, O(log n) for imports
- State validation: O(1) lookup in ordered dict
- Transition execution: O(number of callbacks) per transition

### Threading Impact
- LockedMachine adds lock acquisition overhead
- Queued transitions prevent concurrent execution
- Context manager approach minimizes lock contention

## Extensibility

### Adding New States
1. Define state with name, on_enter/on_exit callbacks
2. Add to StateMachine.states
3. Create transitions to/from new state
4. Update model callback methods if needed

### Adding New Transitions
1. Define transition with trigger, source, dest, callbacks
2. Add to appropriate Event.transitions
3. Ensure model has trigger method (auto-generated)
4. Test condition and callback logic

### Custom Extensions
- HierarchicalMachine for nested states
- AsyncMachine for async callbacks
- Custom state classes for specialized behavior
- Plugin system for additional features