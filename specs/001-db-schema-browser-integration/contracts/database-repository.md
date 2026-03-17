# Interface Contract: DatabaseRepository

**Contract ID**: DB_REPO_001  
**Purpose**: Defines the interface between the browser data provider and the normalized database layer  
**Version**: 1.0  
**Status**: Active  

## Interface Definition

```python
class DatabaseRepository(Protocol):
    """Repository interface for accessing normalized poker database."""

    async def get_strategy_matrix(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: MetricType
    ) -> dict[HandKey, StrategyCellMetricValue]:
        """Retrieve complete 13x13 strategy matrix for given context.

        Args:
            position: Player position context
            action: Decision action context
            metric: Display metric type

        Returns:
            Dictionary mapping hand keys to metric values

        Raises:
            DatabaseConnectionError: If database is unavailable
            InvalidContextError: If position/action/metric combination invalid
        """
        ...

    async def get_hand_metric(
        self,
        position: PositionContext,
        action: ActionContext,
        metric: MetricType,
        hand_key: HandKey
    ) -> StrategyCellMetricValue:
        """Retrieve specific hand metric value.

        Args:
            position: Player position context
            action: Decision action context
            metric: Display metric type
            hand_key: Specific hand identifier

        Returns:
            Metric value for the hand

        Raises:
            DataNotFoundError: If hand/context combination not found
        """
        ...

    async def get_convergence_data(
        self,
        position: PositionContext,
        action: ActionContext
    ) -> list[ConvergencePoint]:
        """Retrieve convergence analysis data for position/action.

        Args:
            position: Player position context
            action: Decision action context

        Returns:
            List of convergence data points over time
        """
        ...
```

## Data Contracts

### PositionContext
```python
@dataclass(frozen=True)
class PositionContext:
    id: Literal["UTG", "BTN", "SB", "BB"]
    label: str
    sort_order: int
```

### ActionContext
```python
@dataclass(frozen=True)
class ActionContext:
    id: Literal["FOLD", "ALL_IN"]
    label: str
```

### MetricType
```python
@dataclass(frozen=True)
class MetricType:
    id: Literal["WIN_LOSE_PROBABILITY", "EV", "EQUITY", "EQR"]
    label: str
    display_format: Literal["percent", "decimal", "signed_decimal"]
    db_column: str
```

### HandKey
```python
@dataclass(frozen=True)
class HandKey:
    key: str  # e.g., "AKs", "72o"
    row_rank: PokerRank
    col_rank: PokerRank
    suitedness: Literal["PAIR", "SUITED", "OFFSUIT"]
```

### StrategyCellMetricValue
```python
@dataclass
class StrategyCellMetricValue:
    position: PositionContext
    action: ActionContext
    metric: MetricType
    hand_key: HandKey
    value: float | None
    status: Literal["AVAILABLE", "MISSING", "INVALID"]
    source_tag: str | None
    updated_at: datetime
```

## Error Contracts

### DatabaseConnectionError
```python
class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass
```

### InvalidContextError
```python
class InvalidContextError(ValueError):
    """Raised when position/action/metric combination is invalid."""
    pass
```

### DataNotFoundError
```python
class DataNotFoundError(LookupError):
    """Raised when requested data does not exist."""
    pass
```

## Performance Contracts

- **Response Time**: All methods must complete within 500ms under normal load
- **Concurrent Users**: Interface must support up to 10 concurrent users
- **Data Freshness**: Strategy data should reflect latest simulation results within 30 seconds
- **Error Rate**: <1% of requests should result in errors under normal operation