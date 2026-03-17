# Database Operations Contract

**Feature**: 001-normalized-db-schema  
**Date**: 2026-03-15  
**Purpose**: Defines the interface contract for database operations in the poker analysis system

## Dependencies

- SQLAlchemy >= 2.0 (ORM for database abstraction)
- Python >= 3.8 (for type hints and dataclasses)
- SQLite 3.x (built-in with Python, no external driver needed)

## Interface Overview

The database module provides a clean abstraction over SQLAlchemy operations, ensuring consistent data access patterns and transaction management.

## Core Interfaces

### DatabaseConnection
**Purpose**: Manages database connection lifecycle and session handling

```python
class DatabaseConnection:
    def __init__(self, database_url: str) -> None:
        """Initialize connection to SQLite database"""

    def get_session(self) -> Session:
        """Return a new SQLAlchemy session (caller responsible for closing)"""

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Context manager for session lifecycle (preferred pattern)"""

    def create_tables(self) -> None:
        """Create all database tables"""

    def drop_tables(self) -> None:
        """Drop all database tables (for testing)"""

    def close(self) -> None:
        """Close database connection"""
```

### SimulationRepository
**Purpose**: CRUD operations for simulation data

```python
class SimulationRepository:
    def create_simulation(self, name: str, parameters: dict) -> Simulation:
        """Create new simulation record"""

    def get_simulation(self, simulation_id: int) -> Optional[Simulation]:
        """Retrieve simulation by ID"""

    def update_simulation_end_time(self, simulation_id: int, end_time: datetime) -> None:
        """Update simulation completion timestamp"""

    def list_simulations(self, limit: int = 50) -> List[Simulation]:
        """List recent simulations"""
```

### GameStateRepository
**Purpose**: Operations for game state data with bulk operations

```python
class GameStateRepository:
    def bulk_insert_game_states(self, game_states: List[GameStateData]) -> None:
        """Bulk insert multiple game states efficiently"""

    def get_game_states_for_cell(self, cell_id: int, limit: int = 1000) -> List[GameState]:
        """Retrieve game states for specific matrix cell"""

    def get_convergence_data(self, cell_id: int) -> List[ConvergencePoint]:
        """Get timestamped equity data for convergence analysis"""
```

### QueryService
**Purpose**: Complex analytical queries

```python
class QueryService:
    def get_matrix_equity(self, matrix_id: int) -> Dict[str, float]:
        """Calculate equity for entire matrix"""

    def get_jackpot_analysis(self) -> List[JackpotStats]:
        """Aggregate jackpot frequency and payout data"""

    def replay_game(self, cell_id: int, hand_filter: str = None) -> List[GameReplay]:
        """Reconstruct game sequence for replay"""
```

## Data Contracts

### GameStateData
```python
@dataclass
class GameStateData:
    cell_id: int
    timestamp: datetime
    pot_size: Decimal
    board_cards: BoardCards
    players: List[PlayerData]
    bets: List[BetData]
    outcome: Optional[str] = None
```

### PlayerData
```python
@dataclass
class PlayerData:
    position: str  # 'hero' or 'villain'
    hole_cards: str  # e.g., "AsKh"
    stack_size: Decimal
    is_hero: bool
```

### BetData
```python
@dataclass
class BetData:
    player_position: str
    amount: Decimal
    action_type: str  # 'fold', 'call', 'raise'
```

## Error Handling

### DatabaseError
```python
class DatabaseError(Exception):
    """Base exception for database operations"""
    pass

class IntegrityError(DatabaseError):
    """Raised on constraint violations"""
    pass

class ConnectionError(DatabaseError):
    """Raised on connection issues"""
    pass

class DataValidationError(DatabaseError):
    """Raised when simulation data is corrupted or oversized"""
    pass
```

## Data Validation

### Data Size Limits
- Simulation parameters JSON: < 1MB
- Game state data per simulation: < 10,000 records
- Bulk insert batch size: < 1,000 records per transaction

### Corruption Handling
- Invalid card formats trigger DataValidationError
- Oversized JSON parameters trigger DataValidationError
- Duplicate board cards trigger IntegrityError

## Transaction Semantics

- All write operations use transactions
- Read operations may use read-only transactions for consistency
- Bulk operations use single transactions for atomicity
- Failed operations automatically rollback
- Transaction isolation level: SERIALIZABLE (SQLite default for ACID compliance)

## Performance Guarantees

- Bulk inserts: < 1 second per 1000 game states
- Complex queries: < 100ms response time
- Concurrent simulations: Support up to 16 simultaneous writers
- Memory usage: < 100MB for typical workloads