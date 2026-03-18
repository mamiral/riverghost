# Configuration Interface Contract

## Overview
The PrecomputeConfig class manages user-configurable settings for precompute operations. Configuration is loaded from YAML files and applied to both the state machine and panel components.

## Interface Definition

### Class: PrecomputeConfig
**Location**: `hopilot.gui_components.precompute_config`

#### Constructor
```python
def __init__(self, max_workers: int = None, simulations_per_cell: int = None)
```
**Parameters**:
- `max_workers`: Optional[int] - Thread pool size (defaults to system detection)
- `simulations_per_cell`: Optional[int] - Base computation samples (defaults to 1000)

**Postconditions**:
- Values clamped to valid ranges
- Default values applied if None provided

#### Class Method: from_yaml
```python
@classmethod
def from_yaml(cls, config_path: Path) -> PrecomputeConfig
```
**Parameters**:
- `config_path`: Path - Path to YAML configuration file

**Returns**: PrecomputeConfig - Loaded configuration instance

**Error Conditions**:
- File not found: Uses default values, logs warning
- Invalid YAML: Uses default values, logs error
- Invalid values: Clamps to valid ranges, logs warning

#### Method: to_dict
```python
def to_dict(self) -> Dict[str, Any]
```
**Returns**: Dict with configuration values for serialization

#### Method: update
```python
def update(self, **kwargs) -> None
```
**Parameters**:
- `**kwargs` - Configuration values to update

**Postconditions**:
- Values validated and clamped
- Instance updated with new values

#### Properties
```python
@property
def max_workers(self) -> int
@property
def simulations_per_cell(self) -> int
@property
def step_sizes(self) -> Dict[str, int]
```

## Configuration Schema

### YAML Structure
```yaml
aof_browser_runtime:
  precompute_max_workers: 4
  precompute_simulations_per_cell: 1000
```

### Validation Rules
- `precompute_max_workers`: Integer ∈ [1, 16]
- `precompute_simulations_per_cell`: Integer ∈ [100, 50000]

### Default Values
- `max_workers`: min(4, cpu_count()) or 2
- `simulations_per_cell`: 1000
- `step_sizes`: {'coarse': 1000, 'fine': 100}

## Loading Priority

1. Explicit constructor parameters
2. YAML configuration file values
3. System-detected defaults
4. Hardcoded fallbacks

## Update Mechanisms

### Runtime Updates
- Worker count: Via state machine 'adjust_workers' event
- Simulations: Via state machine 'adjust_simulations' event
- Persistence: Changes saved back to YAML file

### Validation
- All updates validated before application
- Invalid values rejected with descriptive errors
- Out-of-range values clamped with warnings

## Integration Points

### State Machine
- Configuration passed to StateMachineController constructor
- Updates applied through controller.update_config()

### Panel
- Configuration applied through panel.update_precompute_config()
- UI controls reflect current configuration values

### Persistence
- Configuration saved on application exit
- Loaded on application startup
- User preferences preserved across sessions</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-state-machine-integration\contracts\configuration_interface.md