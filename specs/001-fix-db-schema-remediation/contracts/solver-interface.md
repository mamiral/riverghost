# Contract: AllInFoldGTOSolver Interface

**Date**: April 1, 2026
**Feature**: [specs/001-fix-db-schema-remediation/spec.md](specs/001-fix-db-schema-remediation/spec.md)

## Overview

This contract defines the modified interface for `AllInFoldGTOSolver` that writes directly to database tables during Monte Carlo simulations, eliminating the `AoFSolverAdapter` layer and ensuring genuine data storage.

## Method Signature

```python
class AllInFoldGTOSolver:
    def analyze_hand_strategy(
        self,
        hero_hand: List[str],  # ['As', 'Kh']
        villain_hand: List[str],  # ['Qd', 'Jd'] 
        board_cards: List[str],  # ['2c', '7h', 'Td', 'Qs', 'Ah']
        db_session: Session,  # SQLAlchemy session for database writes
        simulation_params: SimulationParams  # iterations, etc.
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation for all-in-or-fold scenario and store
        complete game states directly in database.
        
        Args:
            hero_hand: Hero's hole cards
            villain_hand: Villain's hole cards  
            board_cards: Community cards (flop, turn, river)
            db_session: Active SQLAlchemy session for data persistence
            simulation_params: Simulation configuration
            
        Returns:
            SimulationResult with aggregated metrics (for backward compatibility)
            
        Side Effects:
            - Creates GameState records for each simulation iteration
            - Creates Player records for hero and villain
            - Creates Bet records for all-in actions
            - Creates BoardCards record if not exists
            - Detects and creates Jackpot records for bonus events
            - All data is genuine simulation outcomes, no fabrication
        """
```

## Data Structures

### SimulationParams
```python
@dataclass
class SimulationParams:
    iterations: int = 10000
    enable_jackpot_detection: bool = True
    batch_size: int = 1000  # For bulk database operations
    matrix_cell_id: Optional[int] = None  # For linking to matrix
```

### SimulationResult  
```python
@dataclass
class SimulationResult:
    hero_equity: float  # Win probability for hero
    villain_equity: float  # Win probability for villain
    total_simulations: int  # Actual iterations completed
    jackpot_events: int  # Number of jackpot bonuses detected
    execution_time: float  # Time taken in seconds
```

## Database Operations Contract

### Required Inserts Per Simulation Iteration

1. **BoardCards**: Insert or find existing board card combination
2. **GameState**: Create game state record linking to board cards
3. **Players**: Create hero and villain player records
4. **Bets**: Create all-in bet records for both players
5. **Jackpots**: Create jackpot records if conditions met

### Transaction Scope

- Each simulation iteration wrapped in database transaction
- Rollback on any insertion failure
- Commit after successful completion of all inserts for iteration

### Foreign Key Constraints

- All foreign key relationships must be satisfied
- Referential integrity maintained at all times
- Constraint violations result in transaction rollback and logged errors

## Error Handling

### Validation Errors
- Invalid card combinations → ValueError with descriptive message
- Database connection issues → DatabaseError with retry logic
- Foreign key violations → IntegrityError with detailed diagnostics

### Recovery Mechanisms
- Failed iterations logged but don't stop simulation
- Partial transaction rollbacks prevent data corruption
- Graceful degradation with reduced functionality on persistent errors

## Performance Guarantees

- < 30 seconds for 1K iterations
- < 5 minutes for 10K iterations  
- Memory usage < 200MB per simulation run
- Database file size growth proportional to simulation count

## Testing Contract

Integration tests must verify:
- All database tables populated with real data
- Record counts match simulation iterations
- Foreign key constraints satisfied
- No fabricated or placeholder data
- Jackpot detection works correctly
- Performance requirements met</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-fix-db-schema-remediation\contracts\solver-interface.md