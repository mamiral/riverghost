# GTO Solver API Contract

**Version**: 1.0
**Date**: 2026-02-27

## Overview

This contract defines the programmatic interface for the All-In-or-Fold GTO Solver component. All implementations must adhere to these contracts to ensure compatibility with the HoPilot system.

## Core Interfaces

### AllInFoldGTOSolver

#### Constructor
```python
def __init__(self, analyzer: PokerAnalyzer) -> None:
    """
    Initialize GTO solver with poker analysis backend.

    Args:
        analyzer: PokerAnalyzer instance for equity calculations

    Raises:
        TypeError: If analyzer is not a PokerAnalyzer instance
    """
```

#### Public Methods

```python
def set_bonus_payouts(self, payouts: Dict[str, float]) -> None:
    """
    Configure bonus payout multipliers.

    Args:
        payouts: Dict mapping hand categories to multipliers
                 Keys: 'royal_flush', 'straight_flush', 'four_of_a_kind',
                       'full_house', 'flush', 'straight', 'three_of_a_kind',
                       'two_pair', 'one_pair'

    Raises:
        ValueError: If payout values are negative
        TypeError: If payouts is not a dict
    """
```

```python
def find_gto_threshold(self, num_opponents: int, pot_size: float,
                      bet_amount: float, num_simulations: int = 5000) -> Dict[str, Any]:
    """
    Calculate the GTO equity threshold for all-in-or-fold decisions.

    Args:
        num_opponents: Number of opponents (1-9)
        pot_size: Current pot size (> 0)
        bet_amount: All-in bet amount (> 0)
        num_simulations: Monte Carlo simulations per hand (100-10000)

    Returns:
        Dict containing:
        - 'threshold_equity': float (0.0-1.0)
        - 'optimal_hands': int
        - 'total_hands': int
        - 'optimal_range': List[str]
        - 'top_10_hands': List[Dict]
        - 'bottom_10_hands': List[Dict]
        - 'bonus_payouts': Dict[str, float]

    Raises:
        ValueError: If parameters are out of valid ranges
        RuntimeError: If calculation fails
    """
```

```python
def analyze_hand_strategy(self, hole_cards: List[str], num_opponents: int,
                         pot_size: float, bet_amount: float,
                         num_simulations: int = 5000) -> Dict[str, Any]:
    """
    Analyze the optimal strategy for a specific hand.

    Args:
        hole_cards: Two card names (e.g., ['As', 'Kh'])
        num_opponents: Number of opponents (1-9)
        pot_size: Current pot size (> 0)
        bet_amount: All-in bet amount (> 0)
        num_simulations: Monte Carlo simulations (100-10000)

    Returns:
        Dict containing:
        - 'hand': List[str]
        - 'shorthand': str
        - 'equity': float
        - 'ev': float
        - 'hand_category': str
        - 'bonus_multiplier': float
        - 'recommendation': str ('ALL-IN' or 'FOLD')
        - 'pot_size': float
        - 'bet_amount': float
        - 'num_opponents': int

    Raises:
        ValueError: If hole_cards is invalid
        RuntimeError: If analysis fails
    """
```

## RangeManager

### Constructor
```python
def __init__(self, storage_dir: Optional[str] = None) -> None:
    """
    Initialize range manager with storage location.

    Args:
        storage_dir: Directory for YAML files (default: config/ranges/)
    """
```

### Public Methods

```python
def save_range(self, range_obj: PokerRange, filename: Optional[str] = None) -> str:
    """
    Save a poker range to YAML file.

    Args:
        range_obj: PokerRange instance to save
        filename: Optional filename (default: generated from range name)

    Returns:
        Path to saved file

    Raises:
        IOError: If file cannot be written
        ValueError: If range_obj is invalid
    """
```

```python
def load_range(self, filename: str) -> PokerRange:
    """
    Load a poker range from YAML file.

    Args:
        filename: Name of YAML file (without .yaml extension)

    Returns:
        PokerRange instance

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML is invalid or range data is malformed
    """
```

```python
def list_ranges(self) -> List[str]:
    """
    List all available range files.

    Returns:
        List of range filenames (without .yaml extension)
    """
```

```python
def delete_range(self, filename: str) -> bool:
    """
    Delete a range file.

    Args:
        filename: Name of range file to delete

    Returns:
        True if deleted, False if not found

    Raises:
        IOError: If deletion fails
    """
```

## Data Contracts

### Input Validation
- All monetary values must be positive floats
- Card names must follow standard poker notation (As, Kh, etc.)
- Hand ranges must contain valid shorthand notations
- Simulation counts must be reasonable (100-10000)

### Output Guarantees
- Equity values are always in range [0.0, 1.0]
- EV calculations include bonus payouts correctly
- Recommendations are always 'ALL-IN' or 'FOLD'
- All timestamps use UTC

### Error Handling
- Invalid inputs raise ValueError with descriptive messages
- System errors raise RuntimeError
- File operations raise IOError
- All exceptions include context about what operation failed

## Performance Contracts

- `find_gto_threshold()` must complete in < 30 seconds for 5000 simulations
- `analyze_hand_strategy()` must complete in < 5 seconds
- Memory usage must not exceed 500MB during calculations
- File operations must complete in < 1 second

## Thread Safety

- All methods are not thread-safe (single-threaded usage assumed)
- GUI components must serialize calls to solver methods
- Long-running calculations should provide progress callbacks

## Version Compatibility

- API is versioned at 1.0
- Breaking changes will increment major version
- Backward compatibility maintained within major versions