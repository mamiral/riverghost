# Simulator-GTO Integration Contract

**Version**: 1.0
**Date**: 2026-03-03

## Overview

This contract defines the integration interface between the poker simulator GUI and the GTO analysis engine. It ensures seamless operation while preserving existing simulator functionality.

## Integration Interfaces

### SimulationPanel Enhancement

#### Constructor Changes
```python
def __init__(self, screen: pygame.Surface, analyzer: PokerAnalyzer,
             x: int, y: int, simulator_gui: PokerSimulatorGUI):
    """
    Enhanced constructor with GTO integration.

    Args:
        screen: Pygame surface for drawing
        analyzer: PokerAnalyzer instance
        x, y: Panel position
        simulator_gui: Reference to parent GUI for GTO solver access
    """
```

#### New Methods

```python
def set_gto_enabled(self, enabled: bool) -> None:
    """
    Enable or disable GTO analysis.

    Args:
        enabled: Whether to show GTO options and run GTO analysis
    """
```

```python
def get_gto_parameters(self) -> Dict[str, Any]:
    """
    Get current GTO analysis parameters from UI inputs.

    Returns:
        Dict with:
        - 'enabled': bool
        - 'bonus_payouts': Dict[str, float]
        - 'pot_size': float (or None to use simulation pot)
        - 'bet_amount': float (or None to use simulation bet)
    """
```

```python
def run_gto_analysis(self) -> Optional[Dict[str, Any]]:
    """
    Run GTO analysis on current simulator scenario.

    Returns:
        GTO results dict or None if analysis fails/disabled

    Raises:
        ValueError: If GTO parameters are invalid
        RuntimeError: If GTO calculation fails
    """
```

```python
def display_gto_results(self, results: Dict[str, Any]) -> None:
    """
    Display GTO results in the simulation panel.

    Args:
        results: GTO analysis results from run_gto_analysis()
    """
```

### PokerSimulatorGUI Integration

#### Enhanced Methods

```python
def get_gto_scenario_data(self) -> Dict[str, Any]:
    """
    Extract current scenario data for GTO analysis.

    Returns:
        Dict with:
        - 'num_opponents': int
        - 'pot_size': float
        - 'bet_amount': float
        - 'hero_cards': List[str] (if specific cards)
        - 'hero_range': str (if range assigned)
        - 'board_cards': List[str]
    """
```

```python
def run_integrated_analysis(self) -> Dict[str, Any]:
    """
    Run both equity simulation and GTO analysis.

    Returns:
        Combined results dict with 'equity' and 'gto' keys
    """
```

## Data Contracts

### Parameter Mapping
- **num_opponents**: Derived from number of villains with cards/ranges in simulator
- **pot_size**: Either from GTO-specific input or current simulation pot size
- **bet_amount**: Either from GTO-specific input or current simulation bet amount
- **bonus_payouts**: From GTO configuration inputs in simulation panel

### Result Integration
- GTO results displayed alongside equity results
- GTO threshold shown as "GTO Threshold: X.XX equity"
- Optimal range displayed as list of recommended hands
- Individual hand recommendations shown for hero's specific cards

### Error Handling
- GTO failures don't prevent equity analysis display
- GTO errors shown in dedicated error section
- Invalid GTO parameters prevent analysis but allow equity simulation

## Performance Contracts

- GTO analysis runs asynchronously to avoid blocking UI
- Progress callbacks update UI during long calculations
- Results cached to prevent redundant calculations
- Memory usage remains under existing simulator limits

## UI Contracts

- GTO options appear only when enabled
- GTO button positioned next to existing simulation button
- GTO results displayed below equity results
- Configuration inputs follow existing simulator styling

## Version Compatibility

- Integration maintains backward compatibility
- Existing simulator functionality unchanged when GTO disabled
- GTO features only active when explicitly enabled</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\002-gto-simulator-integration\contracts\simulator-gto-integration.md