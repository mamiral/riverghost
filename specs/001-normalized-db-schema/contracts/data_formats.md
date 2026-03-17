# Data Format Contracts

**Feature**: 001-normalized-db-schema  
**Date**: 2026-03-15  
**Purpose**: Defines data format standards and validation rules for poker analysis data

## Assumptions

- Operating System: Windows/Linux (SQLite file-based database compatible with both)
- File System: Supports file paths and permissions for database file access

## Card Representation

### Format Specification
Cards are represented as 2-character strings:
- First character: Rank (2-9, T, J, Q, K, A)
- Second character: Suit (s=spades, h=hearts, d=diamonds, c=clubs)

**Examples**:
- "As" = Ace of spades
- "Kh" = King of hearts
- "Td" = Ten of diamonds
- "2c" = Two of clubs

### Validation Rules
```python
def validate_simulation_parameters(params: str) -> bool:
    """Validate simulation parameters JSON string"""
    try:
        data = json.loads(params)
        # Check required fields
        required = ["num_simulations", "matrix_size", "game_type"]
        return all(key in data for key in required)
    except (json.JSONDecodeError, TypeError):
        return False
```

## Hand Representation

### Format Specification
Hole cards are represented as space-separated card pairs:
- "As Kh" = Ace of spades, King of hearts
- "Td 2c" = Ten of diamonds, Two of clubs

### Validation Rules
```python
def validate_hole_cards(cards: str) -> bool:
    card_list = cards.split()
    return (len(card_list) == 2 and
            all(validate_card(card) for card in card_list))
```

## Board Cards

### Format Specification
Complete board represented as 5 individual cards in BoardCards table:
- flop1, flop2, flop3: First three community cards
- turn: Fourth community card
- river: Fifth community card

### Validation Rules
```python
def validate_board_cards(board: BoardCards) -> bool:
    cards = [board.flop1, board.flop2, board.flop3, board.turn, board.river]
    return (len(cards) == 5 and
            all(validate_card(card) for card in cards) and
            len(set(cards)) == 5)  # No duplicates
```

## Simulation Parameters

### JSON Schema
```json
{
  "type": "object",
  "properties": {
    "num_simulations": {"type": "integer", "minimum": 1, "maximum": 100000},
    "matrix_size": {"type": "string", "enum": ["13x13"]},
    "game_type": {"type": "string", "enum": ["all_in_or_fold"]},
    "blinds": {
      "type": "object",
      "properties": {
        "small": {"type": "number", "minimum": 0},
        "big": {"type": "number", "minimum": 0}
      },
      "required": ["small", "big"]
    },
    "jackpot_enabled": {"type": "boolean"},
    "convergence_threshold": {"type": "number", "minimum": 0, "maximum": 1}
  },
  "required": ["num_simulations", "matrix_size", "game_type"]
}
```

## Jackpot Metadata

### JSON Schema
```json
{
  "type": "object",
  "properties": {
    "cards_used": {
      "type": "array",
      "items": {"type": "string", "pattern": "^[2-9TJQKA][shdc]$"},
      "minItems": 1,
      "maxItems": 7
    },
    "hand_type": {
      "type": "string",
      "enum": ["straight_flush", "four_of_a_kind", "full_house", "flush", "straight"]
    },
    "hole_cards_used": {
      "type": "boolean",
      "description": "Whether both hole cards contributed to the jackpot hand"
    }
  },
  "required": ["cards_used", "hand_type"]
}
```

## Equity Values

### Format Specification
Equity values stored as DECIMAL(5,4) representing percentages:
- Range: 0.0000 to 1.0000
- Example: 0.7532 = 75.32% equity

### Validation Rules
```python
def validate_equity(equity: Decimal) -> bool:
    return 0 <= equity <= 1
```

## Monetary Values

### Format Specification
All monetary values use DECIMAL(10,2) for precise calculations:
- Range: -99999999.99 to 99999999.99
- Always stored in cents (1.00 = $1.00)

### Validation Rules
```python
def validate_amount(amount: Decimal) -> bool:
    return amount.scale <= 2  # Max 2 decimal places
```

## Timestamp Format

### Format Specification
All timestamps stored as UTC datetime objects:
- Format: ISO 8601 with timezone
- Example: "2026-03-15T14:30:00Z"

### Validation Rules
```python
def validate_timestamp(ts: datetime) -> bool:
    return ts.tzinfo is not None and ts.tzinfo.utcoffset(ts) is not None
```

## Data Quality Rules

### Uniqueness Constraints
- Simulation names must be unique
- Matrix cells must be unique per matrix (row_index, col_index)
- No duplicate timestamps for same cell (prevent replay issues)

### Referential Integrity
- All foreign keys must reference existing records
- Cascade deletes enabled for simulation cleanup
- Orphaned records automatically prevented

### Business Logic Validation
- Hero player must exist in each game state
- Pot size must equal sum of all bets
- Board cards must be valid poker cards
- Jackpot payouts must be positive amounts