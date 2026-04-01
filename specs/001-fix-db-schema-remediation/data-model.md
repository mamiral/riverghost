# Data Model: Fix Database Schema Remediation

**Date**: April 1, 2026
**Feature**: [specs/001-fix-db-schema-remediation/spec.md](specs/001-fix-db-schema-remediation/spec.md)

## Overview

This document describes the confirmed data model for the genuine GameStates-first architecture, based on the schema defined in `specs/001-normalized-db-schema`. The model ensures all simulation data is stored as primary GameState records with derived MatrixCells and AggregatedMetrics computed from real simulation outcomes.

## Core Entities

### GameState (Primary Data Source)
Represents a complete snapshot of game state at any point in a Monte Carlo simulation.

**Attributes**:
- `id` (PK): Unique identifier
- `cell_id` (FK to MatrixCells): Links to the hand combination being simulated
- `timestamp`: When this game state occurred
- `round`: Game round ('preflop' for all-in-or-fold)
- `pot_size`: Total chips in pot
- `board_cards` (FK to BoardCards): Community cards dealt

**Relationships**:
- 1:N with Players (all players in this game state)
- 1:N with Bets (all betting actions in this game state)
- N:1 with MatrixCells (the hand combination)
- N:1 with BoardCards (community cards)

### Player
Represents a player participating in a specific game state.

**Attributes**:
- `id` (PK): Unique identifier
- `game_state_id` (FK to GameStates): The game state this player belongs to
- `position`: Seat position (0-8)
- `hole_cards`: Player's private cards (JSON array)
- `stack_size`: Chip count at this state
- `is_hero`: Whether this is the hero player

**Relationships**:
- N:1 with GameStates

### Bet
Represents a betting action in a specific game state.

**Attributes**:
- `id` (PK): Unique identifier
- `game_state_id` (FK to GameStates): The game state this bet belongs to
- `player_id` (FK to Players): Which player made this bet
- `amount`: Chip amount bet
- `action_type`: Bet type ('fold', 'call', 'raise' - though all-in-or-fold is primarily 'raise')

**Relationships**:
- N:1 with GameStates
- N:1 with Players

### BoardCards
Represents the community cards dealt in a hand.

**Attributes**:
- `id` (PK): Unique identifier
- `flop1`, `flop2`, `flop3`: First three community cards
- `turn`: Fourth community card
- `river`: Fifth community card

**Relationships**:
- 1:N with GameStates (multiple game states may reference same board)

### Jackpot
Represents detected jackpot events during simulations.

**Attributes**:
- `id` (PK): Unique identifier
- `game_state_id` (FK to GameStates): When the jackpot occurred
- `player_id` (FK to Players): Which player won the jackpot
- `jackpot_type`: Type of jackpot ('straight_flush_both_hole_cards', etc.)
- `payout_amount`: Bonus amount awarded
- `cards_used`: JSON array of cards that formed the jackpot
- `triggered_at`: Timestamp of jackpot detection

**Relationships**:
- N:1 with GameStates
- N:1 with Players

## Derived Entities

### MatrixCell (Computed from GameStates)
Aggregated statistics for specific hand vs hand matchups.

**Attributes**:
- `id` (PK): Unique identifier
- `matrix_id` (FK to HandMatrices): Which matrix this cell belongs to
- `row_index`, `col_index`: Position in 13x13 matrix (0-12)
- `hand_combination`: Text description (e.g., "AsKh vs QdJd")

**Computation**: Created by aggregating all GameStates for each unique hand combination.

### AggregatedMetric (Computed from GameStates)
Statistical measures computed from simulation outcomes.

**Attributes**:
- `id` (PK): Unique identifier
- `cell_id` (FK to MatrixCells): Which cell these metrics describe
- `equity`: Win probability computed from GameState outcomes
- `jackpot_adjusted_ev`: Expected value including jackpot payouts
- `jackpot_frequency`: How often jackpots occur for this hand
- `convergence_status`: Statistical convergence measure

**Computation**: Calculated from all GameStates associated with each MatrixCell.

## Data Flow

1. **Simulation Execution**: AllInFoldGTOSolver runs Monte Carlo simulations
2. **Real-time Storage**: Each simulation iteration creates GameState, Player, Bet, and BoardCards records
3. **Jackpot Detection**: During simulation, jackpot conditions are checked and Jackpot records created
4. **Aggregation**: MatrixCells and AggregatedMetrics computed from stored GameStates
5. **Analysis**: Queries operate on genuine simulation data for convergence, replay, and EV analysis

## Integrity Constraints

- All foreign key relationships enforced at database level
- GameState records must have associated Player and Bet records
- BoardCards must be properly populated for post-flop game states
- Jackpot records must reference valid GameStates and Players
- MatrixCells and AggregatedMetrics computed only from existing GameStates

## Performance Considerations

- GameState insertions batched per simulation iteration
- Indexes on frequently queried columns (cell_id, timestamp)
- Foreign key constraints validated during insertion
- Aggregation queries optimized for large datasets</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-fix-db-schema-remediation\data-model.md