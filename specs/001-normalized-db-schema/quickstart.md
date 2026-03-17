# Quick Start: Normalized Database Schema

**Feature**: 001-normalized-db-schema  
**Date**: 2026-03-15  
**Audience**: Developers integrating the poker analysis database

## Prerequisites

- Python 3.8+
- SQLAlchemy installed: `pip install sqlalchemy`
- Access to project repository

## Basic Setup

### 1. Import Database Components

```python
from hopilot.database import DatabaseConnection
from hopilot.models import Simulation, HandMatrix, MatrixCell
from hopilot.queries import QueryService
```

### 2. Initialize Database

```python
# Create database connection
db = DatabaseConnection("sqlite:///poker_analysis.db")

# Create all tables
db.create_tables()
```

### 3. Create a Simulation

```python
from hopilot.models import Simulation
from datetime import datetime
import json

# Create simulation record
simulation = Simulation(
    name="Tournament Analysis",
    start_timestamp=datetime.utcnow(),
    parameters=json.dumps({
        "num_simulations": 10000,
        "matrix_size": "13x13",
        "game_type": "all_in_or_fold",
        "blinds": {"small": 25, "big": 50}
    })
)

# Add to database
session = db.get_session()
session.add(simulation)
session.commit()
```

## Running Simulations

### 1. Set Up Matrix Structure

```python
from hopilot.models import HandMatrix, MatrixCell

# Create hand matrix for simulation
hand_matrix = HandMatrix(
    simulation_id=simulation.id,
    matrix_size="13x13"
)
session.add(hand_matrix)
session.commit()

# Create matrix cells (13x13 = 169 cells)
for row in range(13):
    for col in range(13):
        cell = MatrixCell(
            matrix_id=hand_matrix.id,
            row_index=row,
            col_index=col,
            hand_combination=f"Hand_{row}_vs_Hand_{col}"
        )
        session.add(cell)
session.commit()
```

### 2. Store Game States

```python
from hopilot.models import GameState, Player, Bet, BoardCard
from decimal import Decimal

# Example game state data
game_state = GameState(
    cell_id=cell.id,
    timestamp=datetime.utcnow(),
    round="preflop",
    pot_size=Decimal("150.00")
)

# Add board cards
board = BoardCard(
    flop1="As", flop2="Kh", flop3="Qd",
    turn="Js", river="Td"
)
session.add(board)
game_state.board_cards = board

# Add players
hero = Player(
    game_state_id=game_state.id,
    position="hero",
    hole_cards="Ac Kd",
    stack_size=Decimal("1000.00"),
    is_hero=True
)

villain = Player(
    game_state_id=game_state.id,
    position="villain",
    hole_cards="Qs Jd",
    stack_size=Decimal("1200.00"),
    is_hero=False
)

session.add_all([hero, villain])

# Add bets (all-in actions)
hero_bet = Bet(
    game_state_id=game_state.id,
    player_id=hero.id,
    amount=Decimal("1000.00"),
    action_type="raise"
)

villain_bet = Bet(
    game_state_id=game_state.id,
    player_id=villain.id,
    amount=Decimal("1200.00"),
    action_type="raise"
)

session.add_all([hero_bet, villain_bet])
session.commit()
```

## Querying Data

### 1. Basic Queries

```python
from hopilot.queries import QueryService

query_service = QueryService(db)

# Get all simulations
simulations = session.query(Simulation).all()

# Get game states for specific cell
cell_states = query_service.get_game_states_for_cell(cell_id=1, limit=100)
```

### 2. Analytical Queries

```python
# Get matrix equity overview
equity_data = query_service.get_matrix_equity(matrix_id=hand_matrix.id)

# Get jackpot statistics
jackpot_stats = query_service.get_jackpot_analysis()

# Replay specific hand
replay_data = query_service.replay_game(cell_id=1, hand_filter="Ac Kd")
```

## Testing

### 1. Unit Tests

```python
import pytest
from hopilot.models import Simulation

def test_simulation_creation(db_session):
    sim = Simulation(name="Test Sim", parameters='{"test": true}')
    db_session.add(sim)
    db_session.commit()

    assert sim.id is not None
    assert sim.name == "Test Sim"
```

### 2. Integration Tests

```python
def test_full_simulation_workflow(db_connection):
    # Create simulation
    sim = create_test_simulation(db_connection)

    # Run mock simulation
    run_mock_simulation(db_connection, sim.id)

    # Verify data integrity
    verify_simulation_data(db_connection, sim.id)
```

## Common Patterns

### Bulk Operations

```python
# For performance, use bulk operations
game_states_data = [create_game_state_data(i) for i in range(1000)]
db.bulk_insert_game_states(game_states_data)
```

### Transaction Management

```python
# Use transactions for data consistency
with db.get_session() as session:
    try:
        # Multiple operations
        session.add(simulation)
        session.add(hand_matrix)
        session.commit()
    except Exception:
        session.rollback()
        raise
```

### Error Handling

```python
from hopilot.database import IntegrityError

try:
    db.create_simulation("Duplicate Name", {})
except IntegrityError:
    print("Simulation name already exists")
```

## Troubleshooting

### Common Issues

1. **Foreign Key Errors**: Ensure parent records exist before creating children
2. **Connection Timeouts**: Check database file permissions and disk space
3. **Performance Issues**: Use bulk operations for large data sets
4. **Memory Usage**: Process data in chunks for large simulations

### Debug Mode

```python
# Enable SQL logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Next Steps

- Review the [data model documentation](data-model.md) for detailed schema information
- Check the [database operations contract](contracts/database_operations.md) for API specifications
- Review [data format contracts](contracts/data_formats.md) for validation rules
- Run the test suite to verify implementation