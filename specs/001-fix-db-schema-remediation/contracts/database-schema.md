# Contract: Database Schema

**Date**: April 1, 2026
**Feature**: [specs/001-fix-db-schema-remediation/spec.md](specs/001-fix-db-schema-remediation/spec.md)

## Overview

This contract defines the confirmed database schema for the genuine GameStates-first architecture, ensuring all tables contain real simulation data with enforced foreign key constraints.

## Table Definitions

### GameStates Table
```sql
CREATE TABLE game_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cell_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    round TEXT NOT NULL CHECK (round IN ('preflop', 'flop', 'turn', 'river')),
    pot_size REAL NOT NULL CHECK (pot_size >= 0),
    board_cards INTEGER,
    FOREIGN KEY (cell_id) REFERENCES matrix_cells(id) ON DELETE CASCADE,
    FOREIGN KEY (board_cards) REFERENCES board_cards(id) ON DELETE SET NULL
);
```

**Constraints**:
- `cell_id` must reference existing MatrixCell
- `round` limited to valid poker rounds
- `pot_size` must be non-negative
- Board cards optional for preflop states

### Players Table
```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_state_id INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0 AND position <= 9),
    hole_cards TEXT NOT NULL,  -- JSON array: ["As", "Kh"]
    stack_size REAL NOT NULL CHECK (stack_size >= 0),
    is_hero BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (game_state_id) REFERENCES game_states(id) ON DELETE CASCADE
);
```

**Constraints**:
- `game_state_id` must reference existing GameState
- `position` valid for 10-max poker
- `hole_cards` must be valid JSON array of 2 cards
- `stack_size` must be non-negative

### Bets Table
```sql
CREATE TABLE bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_state_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    action_type TEXT NOT NULL CHECK (action_type IN ('fold', 'call', 'raise', 'all_in')),
    sequence INTEGER NOT NULL CHECK (sequence >= 0),
    FOREIGN KEY (game_state_id) REFERENCES game_states(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);
```

**Constraints**:
- `game_state_id` must reference existing GameState
- `player_id` must reference existing Player in same GameState
- `amount` must be positive
- `action_type` limited to valid actions
- `sequence` for ordering actions within game state

### BoardCards Table
```sql
CREATE TABLE board_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flop1 TEXT, flop2 TEXT, flop3 TEXT,
    turn TEXT, river TEXT,
    UNIQUE(flop1, flop2, flop3, turn, river)
);
```

**Constraints**:
- All card fields nullable for partial boards
- Unique constraint prevents duplicate board combinations
- Cards must be valid poker card representations

### Jackpots Table
```sql
CREATE TABLE jackpots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_state_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    jackpot_type TEXT NOT NULL,
    payout_amount REAL NOT NULL CHECK (payout_amount > 0),
    cards_used TEXT NOT NULL,  -- JSON array of qualifying cards
    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_state_id) REFERENCES game_states(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);
```

**Constraints**:
- `game_state_id` must reference existing GameState
- `player_id` must reference existing Player in same GameState
- `jackpot_type` must be recognized jackpot type
- `payout_amount` must be positive
- `cards_used` must be valid JSON array

## Indexes

### Required Indexes
```sql
CREATE INDEX idx_game_states_cell_id ON game_states(cell_id);
CREATE INDEX idx_game_states_timestamp ON game_states(timestamp);
CREATE INDEX idx_players_game_state_id ON players(game_state_id);
CREATE INDEX idx_bets_game_state_id ON bets(game_state_id);
CREATE INDEX idx_jackpots_game_state_id ON jackpots(game_state_id);
```

### Performance Indexes
```sql
CREATE INDEX idx_game_states_round ON game_states(round);
CREATE INDEX idx_players_position ON players(position);
CREATE INDEX idx_bets_player_id ON bets(player_id);
```

## Data Integrity Rules

### Foreign Key Enforcement
- All foreign key constraints enabled: `PRAGMA foreign_keys = ON;`
- Cascade deletes maintain referential integrity
- Constraint violations prevent invalid data insertion

### Business Rules
- Each GameState must have exactly 2 Players (hero + villain)
- Each Player must have exactly 1 Bet record (all-in-or-fold)
- BoardCards must be populated for flop/turn/river rounds
- Jackpot records only created when conditions met

### Validation Triggers
```sql
-- Example trigger for game state validation
CREATE TRIGGER validate_game_state_players
AFTER INSERT ON players
BEGIN
    SELECT CASE
        WHEN (SELECT COUNT(*) FROM players WHERE game_state_id = NEW.game_state_id) > 2
        THEN RAISE(ABORT, 'GameState cannot have more than 2 players')
    END;
END;
```

## Migration Contract

### From Current State
- Drop all existing fake data
- Recreate tables with proper constraints
- Reinitialize with genuine simulation data

### Backward Compatibility
- Existing queries may need updates for new schema
- Aggregated data recomputed from GameStates
- GUI components updated to work with real data

## Monitoring Contract

### Health Checks
- Foreign key constraint violations logged
- Table record counts monitored
- Data integrity validation queries

### Performance Metrics
- Insert throughput measured
- Query performance tracked
- Database file size monitored</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-fix-db-schema-remediation\contracts\database-schema.md