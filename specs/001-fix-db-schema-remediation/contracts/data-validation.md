# Contract: Data Validation Rules

**Date**: April 1, 2026
**Feature**: [specs/001-fix-db-schema-remediation/spec.md](specs/001-fix-db-schema-remediation/spec.md)

## Overview

This contract defines validation rules and integrity checks to prevent silent failures and ensure genuine simulation data quality in the GameStates-first architecture.

## Pre-Insertion Validation

### GameState Validation
```python
def validate_game_state(game_state: dict) -> List[str]:
    """
    Validate GameState data before database insertion.
    
    Args:
        game_state: Dictionary with game state fields
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    required = ['cell_id', 'round', 'pot_size']
    for field in required:
        if field not in game_state or game_state[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # Round validation
    if game_state.get('round') not in ['preflop', 'flop', 'turn', 'river']:
        errors.append(f"Invalid round: {game_state.get('round')}")
    
    # Pot size validation
    if game_state.get('pot_size', 0) < 0:
        errors.append(f"Invalid pot size: {game_state.get('pot_size')}")
    
    # Board cards required for post-flop
    if game_state.get('round') != 'preflop' and not game_state.get('board_cards'):
        errors.append("Board cards required for post-flop rounds")
    
    return errors
```

### Player Validation
```python
def validate_player(player: dict) -> List[str]:
    """
    Validate Player data before database insertion.
    """
    errors = []
    
    # Required fields
    required = ['game_state_id', 'position', 'hole_cards', 'stack_size']
    for field in required:
        if field not in player or player[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # Position validation
    if not (0 <= player.get('position', -1) <= 9):
        errors.append(f"Invalid position: {player.get('position')}")
    
    # Hole cards validation
    try:
        cards = json.loads(player.get('hole_cards', '[]'))
        if len(cards) != 2:
            errors.append("Player must have exactly 2 hole cards")
        for card in cards:
            if not is_valid_card(card):
                errors.append(f"Invalid card: {card}")
    except json.JSONDecodeError:
        errors.append("Invalid hole cards JSON format")
    
    # Stack size validation
    if player.get('stack_size', -1) < 0:
        errors.append(f"Invalid stack size: {player.get('stack_size')}")
    
    return errors
```

### Bet Validation
```python
def validate_bet(bet: dict) -> List[str]:
    """
    Validate Bet data before database insertion.
    """
    errors = []
    
    # Required fields
    required = ['game_state_id', 'player_id', 'amount', 'action_type']
    for field in required:
        if field not in bet or bet[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # Amount validation
    if bet.get('amount', 0) <= 0:
        errors.append(f"Invalid bet amount: {bet.get('amount')}")
    
    # Action type validation
    valid_actions = ['fold', 'call', 'raise', 'all_in']
    if bet.get('action_type') not in valid_actions:
        errors.append(f"Invalid action type: {bet.get('action_type')}")
    
    return errors
```

## Referential Integrity Checks

### Foreign Key Validation
```python
def validate_foreign_keys(db_session: Session, data: dict) -> List[str]:
    """
    Validate all foreign key relationships before insertion.
    """
    errors = []
    
    # Check MatrixCell exists
    cell_id = data.get('game_state', {}).get('cell_id')
    if cell_id and not db_session.query(MatrixCell).filter_by(id=cell_id).first():
        errors.append(f"MatrixCell not found: {cell_id}")
    
    # Check BoardCards exists (if provided)
    board_id = data.get('game_state', {}).get('board_cards')
    if board_id and not db_session.query(BoardCards).filter_by(id=board_id).first():
        errors.append(f"BoardCards not found: {board_id}")
    
    # Check GameState exists for related records
    game_state_id = data.get('player', {}).get('game_state_id') or data.get('bet', {}).get('game_state_id')
    if game_state_id and not db_session.query(GameState).filter_by(id=game_state_id).first():
        errors.append(f"GameState not found: {game_state_id}")
    
    return errors
```

## Business Rule Validation

### Game State Consistency
```python
def validate_game_state_consistency(db_session: Session, game_state_id: int) -> List[str]:
    """
    Validate business rules for complete game state.
    """
    errors = []
    
    # Must have exactly 2 players
    player_count = db_session.query(Player).filter_by(game_state_id=game_state_id).count()
    if player_count != 2:
        errors.append(f"GameState must have exactly 2 players, found {player_count}")
    
    # Each player must have exactly 1 bet (all-in-or-fold)
    players = db_session.query(Player).filter_by(game_state_id=game_state_id).all()
    for player in players:
        bet_count = db_session.query(Bet).filter_by(game_state_id=game_state_id, player_id=player.id).count()
        if bet_count != 1:
            errors.append(f"Player {player.id} must have exactly 1 bet, found {bet_count}")
    
    # Hero flag must be set for exactly 1 player
    hero_count = db_session.query(Player).filter_by(game_state_id=game_state_id, is_hero=True).count()
    if hero_count != 1:
        errors.append(f"GameState must have exactly 1 hero player, found {hero_count}")
    
    return errors
```

## Error Handling Contract

### Validation Failure Response
```python
class ValidationError(Exception):
    """Raised when data validation fails."""
    
    def __init__(self, errors: List[str], data: dict):
        self.errors = errors
        self.data = data
        super().__init__(f"Validation failed: {', '.join(errors)}")
```

### Logging Requirements
- All validation failures logged with ERROR level
- Include data context and specific validation rules violated
- Track validation performance metrics

### Recovery Mechanisms
- Validation failures prevent database insertion
- Failed records logged for analysis
- Simulation continues with next iteration
- Aggregate validation statistics reported

## Performance Requirements

### Validation Performance
- Pre-insertion validation < 1ms per record
- Foreign key checks < 5ms per operation
- Business rule validation < 10ms per game state

### Error Rate Limits
- Validation failure rate < 1% of total operations
- Foreign key violations < 0.1% of insertions
- Business rule violations logged and tracked

## Testing Contract

Validation tests must cover:
- All validation rules with valid/invalid inputs
- Error message accuracy and completeness
- Performance requirements met
- Integration with database constraint enforcement</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-fix-db-schema-remediation\contracts\data-validation.md