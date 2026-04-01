# Quick Start: Database Schema Remediation

**Date**: April 1, 2026
**Feature**: [specs/001-fix-db-schema-remediation/spec.md](specs/001-fix-db-schema-remediation/spec.md)

## Overview

This guide provides step-by-step instructions for implementing the genuine GameStates-first database architecture that eliminates fake data generation and ensures all simulation results are stored as real game states.

## Prerequisites

- Python 3.x environment
- SQLAlchemy installed
- Existing HoPilot codebase
- Database file with current schema

## Step 1: Database Migration

### Backup Existing Data
```bash
# From project root
cp database/hopilot.db database/hopilot_backup.db
```

### Drop Fake Data Tables
```python
# Run in Python REPL from python/ directory
from hopilot.database.session import get_db_session
from hopilot.database.models import GameState, Player, Bet, Jackpot

session = get_db_session()
# Drop all existing fake data
session.query(Jackpot).delete()
session.query(Bet).delete() 
session.query(Player).delete()
session.query(GameState).delete()
session.commit()
```

### Enable Foreign Key Constraints
```sql
-- Execute in database
PRAGMA foreign_keys = ON;
```

## Step 2: Modify AllInFoldGTOSolver

### Update Method Signature
```python
# In python/hopilot/poker_analyzer.py
class AllInFoldGTOSolver:
    def analyze_hand_strategy(
        self,
        hero_hand: List[str],
        villain_hand: List[str], 
        board_cards: List[str],
        db_session: Session,  # NEW: Database session parameter
        simulation_params: SimulationParams
    ) -> SimulationResult:
        # Implementation changes below
```

### Add Database Writing Logic
```python
# Inside analyze_hand_strategy method
for iteration in range(simulation_params.iterations):
    # Run simulation
    outcome = self._simulate_single_hand(hero_hand, villain_hand, board_cards)
    
    # Create database records
    board_record = self._get_or_create_board_cards(db_session, board_cards)
    game_state = GameState(
        cell_id=simulation_params.matrix_cell_id,
        round='preflop',  # All-in-or-fold
        pot_size=outcome.pot_size,
        board_cards=board_record.id if board_record else None
    )
    db_session.add(game_state)
    db_session.flush()  # Get game_state.id
    
    # Create player records
    hero_player = Player(
        game_state_id=game_state.id,
        position=0,  # Hero position
        hole_cards=json.dumps(hero_hand),
        stack_size=outcome.hero_stack,
        is_hero=True
    )
    villain_player = Player(
        game_state_id=game_state.id,
        position=1,  # Villain position  
        hole_cards=json.dumps(villain_hand),
        stack_size=outcome.villain_stack,
        is_hero=False
    )
    db_session.add_all([hero_player, villain_player])
    db_session.flush()
    
    # Create bet records
    hero_bet = Bet(
        game_state_id=game_state.id,
        player_id=hero_player.id,
        amount=outcome.hero_bet,
        action_type='all_in',
        sequence=0
    )
    villain_bet = Bet(
        game_state_id=game_state.id,
        player_id=villain_player.id,
        amount=outcome.villain_bet,
        action_type='all_in', 
        sequence=1
    )
    db_session.add_all([hero_bet, villain_bet])
    
    # Check for jackpots
    jackpot = self._detect_jackpot(outcome, hero_hand, villain_hand, board_cards)
    if jackpot:
        jackpot_record = Jackpot(
            game_state_id=game_state.id,
            player_id=hero_player.id if jackpot.player == 'hero' else villain_player.id,
            jackpot_type=jackpot.type,
            payout_amount=jackpot.amount,
            cards_used=json.dumps(jackpot.cards_used)
        )
        db_session.add(jackpot_record)
    
    # Commit transaction for this iteration
    db_session.commit()
```

## Step 3: Remove AoFSolverAdapter

### Delete Adapter File
```bash
# From python/ directory
rm hopilot/aof_solver_adapter.py
```

### Update Import Statements
```python
# In files that imported AoFSolverAdapter
# REMOVE: from hopilot.aof_solver_adapter import AoFSolverAdapter
# REPLACE with direct solver usage
from hopilot.poker_analyzer import AllInFoldGTOSolver
```

## Step 4: Add Data Validation

### Create Validation Module
```python
# python/hopilot/validation/data_validator.py
from typing import List, Dict
import json

class DataValidator:
    @staticmethod
    def validate_game_state(data: Dict) -> List[str]:
        # Implementation from contracts/data-validation.md
        pass
    
    @staticmethod
    def validate_foreign_keys(session, data: Dict) -> List[str]:
        # Implementation from contracts/data-validation.md
        pass
```

### Integrate Validation
```python
# In AllInFoldGTOSolver.analyze_hand_strategy
from hopilot.validation.data_validator import DataValidator

# Before database insertion
errors = DataValidator.validate_game_state(game_state_data)
if errors:
    logger.error(f"Validation failed: {errors}")
    continue  # Skip this iteration

fk_errors = DataValidator.validate_foreign_keys(db_session, game_state_data)
if fk_errors:
    logger.error(f"Foreign key validation failed: {fk_errors}")
    db_session.rollback()
    continue
```

## Step 5: Update Aggregation Engine

### Modify MatrixCell Computation
```python
# In aggregation engine
def compute_matrix_cells(db_session: Session) -> None:
    """Compute MatrixCells from stored GameStates."""
    
    # Get all unique cell_ids from GameStates
    cell_ids = db_session.query(GameState.cell_id).distinct().all()
    
    for (cell_id,) in cell_ids:
        # Aggregate outcomes for this cell
        game_states = db_session.query(GameState).filter_by(cell_id=cell_id).all()
        
        hero_wins = sum(1 for gs in game_states if gs.outcome == 'hero_win')
        total_games = len(game_states)
        equity = hero_wins / total_games if total_games > 0 else 0
        
        # Update or create MatrixCell
        matrix_cell = db_session.query(MatrixCell).filter_by(id=cell_id).first()
        if matrix_cell:
            # Update aggregated metrics
            matrix_cell.equity = equity
            # ... other aggregations
```

## Step 6: Run Integration Tests

### Create Test Database
```bash
# From project root
python -c "
from hopilot.database.session import create_test_db
create_test_db()
"
```

### Run Tests
```bash
# From project root
pytest tests/test_database_remediation.py -v
pytest tests/test_solver_integration.py -v
```

### Verify Real Data
```python
# In Python REPL
from hopilot.database.session import get_db_session
from hopilot.database.models import GameState, Player, Bet

session = get_db_session()
print(f'GameStates: {session.query(GameState).count()}')
print(f'Players: {session.query(Player).count()}') 
print(f'Bets: {session.query(Bet).count()}')

# Check for real data
sample_gs = session.query(GameState).first()
if sample_gs:
    print(f'Sample GameState has timestamp: {sample_gs.timestamp is not None}')
    print(f'Sample GameState has pot_size: {sample_gs.pot_size > 0}')
```

## Step 7: Performance Validation

### Run Benchmark
```python
# Test performance requirements
import time
from hopilot.poker_analyzer import AllInFoldGTOSolver

solver = AllInFoldGTOSolver()
start_time = time.time()

# Test 1K iterations
result = solver.analyze_hand_strategy(
    hero_hand=['As', 'Kh'],
    villain_hand=['Qd', 'Jd'],
    board_cards=['2c', '7h', 'Td'],
    db_session=get_db_session(),
    simulation_params=SimulationParams(iterations=1000)
)

elapsed = time.time() - start_time
print(f'1K iterations took {elapsed:.2f}s (target: <30s)')
assert elapsed < 30, f'Performance requirement failed: {elapsed}s'
```

## Troubleshooting

### Foreign Key Violations
```sql
-- Check for constraint violations
PRAGMA foreign_key_check;
```

### Performance Issues
- Check database indexes are created
- Monitor memory usage during large simulations
- Consider batch commits for very large iteration counts

### Data Integrity Issues
- Run validation checks on existing data
- Check for orphaned records
- Verify all required relationships exist

## Next Steps

1. Update GUI components to work with real data
2. Implement convergence analysis queries
3. Add game replay functionality
4. Optimize query performance for large datasets</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-fix-db-schema-remediation\quickstart.md