"""
AOF GTO Browser - SQLite Database Creation with Actual Domain Models

This script creates a SQLite database with the normalized relational schema
and populates it with relationally correct mock data using actual domain models
from aof_gto_browser_ii.shared.

Key features:
- Uses Card, Hand, Board, Position, Action enums from shared models
- Supports 2-4 player all-in games (ONLY fold and all-in actions)
- All foreign keys point to valid parent records
- Relationships are transactionally consistent
"""

import sys
import os
from pathlib import Path

# Add python directory to path for imports
python_dir = Path(__file__).parent.parent / "python"
sys.path.insert(0, str(python_dir))

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Tuple
import random

from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit
from aof_gto_browser_ii.shared.domain.hand import Hand
from aof_gto_browser_ii.shared.domain.board import Board
from aof_gto_browser_ii.shared.models.enums import Action, Position
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# All possible cards (52 total)
ALL_CARDS = [
    Card(rank, suit) 
    for rank in Rank 
    for suit in Suit
]

# Hand notations for 13x13 matrix
HAND_NOTATIONS = [
    'AA', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
    'AKo', 'KK', 'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s',
    'AQo', 'KQo', 'QQ', 'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'Q6s', 'Q5s', 'Q4s', 'Q3s', 'Q2s',
    'AJo', 'KJo', 'QJo', 'JJ', 'JTs', 'J9s', 'J8s', 'J7s', 'J6s', 'J5s', 'J4s', 'J3s', 'J2s',
    'ATo', 'KTo', 'QTo', 'JTo', 'TT', 'T9s', 'T8s', 'T7s', 'T6s', 'T5s', 'T4s', 'T3s', 'T2s',
    'A9o', 'K9o', 'Q9o', 'J9o', 'T9o', '99', '98s', '97s', '96s', '95s', '94s', '93s', '92s',
    'A8o', 'K8o', 'Q8o', 'J8o', 'T8o', '98o', '88', '87s', '86s', '85s', '84s', '83s', '82s',
    'A7o', 'K7o', 'Q7o', 'J7o', 'T7o', '97o', '87o', '77', '76s', '75s', '74s', '73s', '72s',
    'A6o', 'K6o', 'Q6o', 'J6o', 'T6o', '96o', '86o', '76o', '66', '65s', '64s', '63s', '62s',
    'A5o', 'K5o', 'Q5o', 'J5o', 'T5o', '95o', '85o', '75o', '65o', '55', '54s', '53s', '52s',
    'A4o', 'K4o', 'Q4o', 'J4o', 'T4o', '94o', '84o', '74o', '64o', '54o', '44', '43s', '42s',
    'A3o', 'K3o', 'Q3o', 'J3o', 'T3o', '93o', '83o', '73o', '63o', '53o', '43o', '33', '32s',
    'A2o', 'K2o', 'Q2o', 'J2o', 'T2o', '92o', '82o', '72o', '62o', '52o', '42o', '32o', '22',
]

JACKPOT_TYPES = [
    'straight_flush_both_hole_cards',
    'straight_flush_one_hole_card',
    'quads',
    'full_house',
    'flush',
]

# Position rotation for multi-way pots
ALL_POSITIONS = [Position.UTG, Position.BTN, Position.SB, Position.BB]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_unique_cards(num_cards: int) -> List[Card]:
    """Generate N unique cards using domain model."""
    return random.sample(ALL_CARDS, num_cards)


def generate_hand() -> Hand:
    """Generate a random 2-card hand using the Hand domain model."""
    cards = generate_unique_cards(2)
    return Hand(card1=cards[0], card2=cards[1])


def generate_board() -> Board:
    """Generate a random board with 0-5 cards using the Board domain model."""
    # Randomly choose 0-5 cards for all-in-or-fold context
    num_cards = random.randint(0, 5)
    cards = generate_unique_cards(num_cards)
    return Board(cards=cards)


def get_available_positions(num_players: int) -> List[Position]:
    """Get position assignments for N players (2-4) in order."""
    if num_players < 2 or num_players > 4:
        raise ValueError(f"All-in games support 2-4 players, got {num_players}")
    return ALL_POSITIONS[:num_players]


# ============================================================================
# DATABASE SCHEMA CREATION
# ============================================================================

def create_schema(db_path: str) -> sqlite3.Connection:
    """Create the database schema according to spec."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Simulations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            start_timestamp DATETIME NOT NULL,
            end_timestamp DATETIME,
            parameters TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # HandMatrices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hand_matrices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simulation_id INTEGER UNIQUE NOT NULL,
            matrix_size TEXT DEFAULT '13x13' NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (simulation_id) REFERENCES simulations(id)
                ON DELETE CASCADE
        );
    """)

    # MatrixCells table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matrix_cells (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matrix_id INTEGER NOT NULL,
            row_index INTEGER NOT NULL,
            col_index INTEGER NOT NULL,
            hand_notation TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (matrix_id) REFERENCES hand_matrices(id)
                ON DELETE CASCADE,
            UNIQUE (matrix_id, row_index, col_index)
        );
    """)

    # BoardCards table (created first for FK references)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS board_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cards TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # GameStates table - supports 2-4 players
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            num_players INTEGER NOT NULL,
            board_cards_id INTEGER NOT NULL,
            pot_size DECIMAL(10,2) NOT NULL,
            outcome TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cell_id) REFERENCES matrix_cells(id)
                ON DELETE CASCADE,
            FOREIGN KEY (board_cards_id) REFERENCES board_cards(id)
                ON DELETE CASCADE
        );
    """)

    # Create index on GameStates for query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_game_states_cell_timestamp
        ON game_states(cell_id, timestamp);
    """)

    # Players table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_state_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            hole_cards TEXT NOT NULL,
            stack_size DECIMAL(10,2) NOT NULL,
            is_hero BOOLEAN DEFAULT 0 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_state_id) REFERENCES game_states(id)
                ON DELETE CASCADE
        );
    """)

    # Bets table - ONLY FOLD and ALL_IN actions for all-in-or-fold games
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_state_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            amount DECIMAL(10,2) DEFAULT 0 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_state_id) REFERENCES game_states(id)
                ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id)
                ON DELETE CASCADE
        );
    """)

    # Jackpots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jackpots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_state_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            jackpot_type TEXT NOT NULL,
            payout_amount DECIMAL(10,2) NOT NULL,
            cards_used TEXT NOT NULL,
            triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_state_id) REFERENCES game_states(id)
                ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id)
                ON DELETE CASCADE
        );
    """)

    # Create index on Jackpots for analysis
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jackpots_type_timestamp
        ON jackpots(jackpot_type, triggered_at);
    """)

    # AggregatedMetrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aggregated_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER UNIQUE NOT NULL,
            last_updated DATETIME NOT NULL,
            equity DECIMAL(5,4),
            ev DECIMAL(10,4),
            win_prob DECIMAL(5,4),
            draw_prob DECIMAL(5,4),
            loss_prob DECIMAL(5,4),
            jackpot_adjusted_ev DECIMAL(10,4),
            jackpot_frequency DECIMAL(5,4),
            avg_jackpot_payout DECIMAL(10,2),
            convergence_status TEXT,
            iterations INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cell_id) REFERENCES matrix_cells(id)
                ON DELETE CASCADE
        );
    """)

    conn.commit()
    return conn


# ============================================================================
# MOCK DATA INSERTION
# ============================================================================

def insert_simulation(cursor: sqlite3.Cursor, sim_id: int) -> int:
    """Insert a simulation record and return its ID."""
    name = f"4MAX_AOF_{sim_id}_100k_iter_2026-04-03"
    start = datetime.now() - timedelta(hours=2)
    end = datetime.now() - timedelta(hours=1)
    
    params = {
        "max_iterations": 100000,
        "convergence_threshold": 0.001,
        "random_seed": sim_id * 42,
        "solver": "aof_poker",
        "positions": [p.value for p in ALL_POSITIONS],
        "max_players": 4,
        "game_type": "CASH"
    }

    cursor.execute("""
        INSERT INTO simulations (name, start_timestamp, end_timestamp, parameters)
        VALUES (?, ?, ?, ?)
    """, (name, start, end, json.dumps(params)))

    return cursor.lastrowid


def insert_hand_matrix(cursor: sqlite3.Cursor, simulation_id: int) -> int:
    """Insert a hand matrix and return its ID."""
    cursor.execute("""
        INSERT INTO hand_matrices (simulation_id, matrix_size)
        VALUES (?, '13x13')
    """, (simulation_id,))

    return cursor.lastrowid


def insert_matrix_cells(cursor: sqlite3.Cursor, matrix_id: int) -> List[int]:
    """Insert all 169 matrix cells (13x13) and return list of cell IDs."""
    cells = []
    hand_idx = 0

    for row in range(13):
        for col in range(13):
            hand_notation = HAND_NOTATIONS[hand_idx]
            cursor.execute("""
                INSERT INTO matrix_cells (matrix_id, row_index, col_index, hand_notation)
                VALUES (?, ?, ?, ?)
            """, (matrix_id, row, col, hand_notation))
            cells.append(cursor.lastrowid)
            hand_idx += 1

    return cells


def insert_board_cards(cursor: sqlite3.Cursor, board: Board) -> int:
    """Insert board cards (using Board domain model) and return its ID."""
    cards_json = json.dumps([card.to_string() for card in board.cards])
    cursor.execute("""
        INSERT INTO board_cards (cards)
        VALUES (?)
    """, (cards_json,))

    return cursor.lastrowid


def insert_game_states_and_players(
    cursor: sqlite3.Cursor, cell_id: int, num_games: int = 100
) -> List[Tuple[int, List[int]]]:
    """
    Insert game states for a cell with 2-4 players and all-in/fold actions only.
    Returns list of (game_state_id, [player_ids]) tuples.
    """
    results = []
    base_time = datetime.now() - timedelta(hours=1)

    for i in range(num_games):
        # Randomly choose 2-4 players for all-in-or-fold context
        num_players = random.randint(2, 4)
        
        # Generate board using Board domain model
        board = generate_board()
        board_id = insert_board_cards(cursor, board)

        # Create game state
        timestamp = base_time + timedelta(seconds=i * 36)
        pot_size = round(random.uniform(1.5, 10), 2)
        outcome = random.choice(['hero_win', 'hero_loss', 'draw'])

        cursor.execute("""
            INSERT INTO game_states (cell_id, timestamp, num_players, board_cards_id, pot_size, outcome)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cell_id, timestamp, num_players, board_id, pot_size, outcome))

        game_state_id = cursor.lastrowid

        # Get positions for this number of players
        positions = get_available_positions(num_players)
        
        # Create players using Hand domain model (one is hero, rest are villains)
        player_ids = []
        used_cards = set()
        
        for idx, position in enumerate(positions):
            # Generate unique hand using Hand domain model
            hand = generate_hand()
            while any(card in used_cards for card in hand.to_cards()):
                hand = generate_hand()
            used_cards.update(hand.to_cards())
            
            is_hero = (idx == 0)  # First position is hero
            stack_size = round(random.uniform(50, 500), 2)
            hole_cards_str = f"{hand.card1.to_string()}{hand.card2.to_string()}"

            cursor.execute("""
                INSERT INTO players (game_state_id, position, hole_cards, stack_size, is_hero)
                VALUES (?, ?, ?, ?, ?)
            """, (game_state_id, position.value, hole_cards_str, stack_size, is_hero))

            player_ids.append(cursor.lastrowid)

        # Create ONLY FOLD and ALL_IN actions using Action enum
        for player_id in player_ids:
            action = random.choice([Action.FOLD, Action.ALL_IN])
            amount = round(random.uniform(0.5, 50), 2) if action == Action.ALL_IN else 0

            cursor.execute("""
                INSERT INTO bets (game_state_id, player_id, action_type, amount)
                VALUES (?, ?, ?, ?)
            """, (game_state_id, player_id, action.value, amount))

        # Randomly insert jackpot events (20% chance)
        if random.random() < 0.2:
            for player_id in player_ids:
                jackpot_type = random.choice(JACKPOT_TYPES)
                payout = round(random.uniform(10, 1000), 2)
                
                # Use Hand and Board domain models for jackpot details
                jackpot_hand = generate_hand()
                jackpot_board = generate_board()
                
                cards_used = {
                    "hole_cards": [jackpot_hand.card1.to_string(), jackpot_hand.card2.to_string()],
                    "board": [card.to_string() for card in jackpot_board.cards]
                }

                cursor.execute("""
                    INSERT INTO jackpots (game_state_id, player_id, jackpot_type, payout_amount, cards_used)
                    VALUES (?, ?, ?, ?, ?)
                """, (game_state_id, player_id, jackpot_type, payout, json.dumps(cards_used)))

        results.append((game_state_id, player_ids))

    return results


def insert_aggregated_metrics(cursor: sqlite3.Cursor, cell_id: int) -> None:
    """Insert aggregated metrics for a cell."""
    equity = round(random.random(), 4)
    ev = round(random.uniform(-50, 100), 4)
    win_prob = round(random.random(), 4)
    draw_prob = round(random.random() * (1 - win_prob), 4)
    loss_prob = round(1 - win_prob - draw_prob, 4)

    jackpot_adjusted_ev = ev + round(random.uniform(0, 20), 4)
    jackpot_freq = round(random.random() * 0.3, 4)
    avg_payout = round(random.uniform(50, 500), 2) if jackpot_freq > 0 else 0

    cursor.execute("""
        INSERT INTO aggregated_metrics (
            cell_id, last_updated, equity, ev, win_prob, draw_prob, loss_prob,
            jackpot_adjusted_ev, jackpot_frequency, avg_jackpot_payout,
            convergence_status, iterations
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cell_id,
        datetime.now(),
        equity,
        ev,
        win_prob,
        draw_prob,
        loss_prob,
        jackpot_adjusted_ev,
        jackpot_freq,
        avg_payout,
        'converged',
        100000
    ))


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def create_aof_database(
    db_path: str = "aof_analysis.db",
    num_simulations: int = 1,
    games_per_cell: int = 100,
    sample_cells: int = 10  # Sample only N cells from 169 to speed up mock data
) -> None:
    """
    Create SQLite database with relational schema and mock data.

    Args:
        db_path: Path to SQLite database file
        num_simulations: Number of simulations to create
        games_per_cell: Number of game states per cell
        sample_cells: Number of cells to populate (to speed up mock creation)
    """
    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()
        print(f"Removed existing database: {db_path}")

    print(f"✨ Creating AOF database with domain models: {db_path}")
    conn = create_schema(str(db_file))
    cursor = conn.cursor()

    try:
        for sim_num in range(num_simulations):
            print(f"\n  📊 Simulation {sim_num + 1}/{num_simulations}")

            # Create simulation
            sim_id = insert_simulation(cursor, sim_num + 1)
            print(f"    ✓ Created simulation (id={sim_id})")

            # Create hand matrix
            matrix_id = insert_hand_matrix(cursor, sim_id)
            print(f"    ✓ Created hand matrix (id={matrix_id})")

            # Create all 169 cells
            cell_ids = insert_matrix_cells(cursor, matrix_id)
            print(f"    ✓ Created {len(cell_ids)} matrix cells")

            # Sample cells for mock game data
            sampled_cells = random.sample(cell_ids, min(sample_cells, len(cell_ids)))

            for idx, cell_id in enumerate(sampled_cells):
                # Insert games and players (2-4 player all-in games)
                games = insert_game_states_and_players(cursor, cell_id, num_games=games_per_cell)
                
                # Insert aggregated metrics
                insert_aggregated_metrics(cursor, cell_id)

                if (idx + 1) % 5 == 0:
                    print(f"      ✓ Populated {idx + 1}/{len(sampled_cells)} cells with games")

            print(f"    ✓ Populated {len(sampled_cells)} cells with 2-4 player all-in games")

        conn.commit()
        print(f"\n✅ Database created successfully!")
        print(f"   Location: {db_file.absolute()}")
        print(f"   Simulations: {num_simulations}")
        print(f"   Total cells: {num_simulations * 169}")
        print(f"   Populated cells: {num_simulations * sample_cells}")
        print(f"   Games per cell: {games_per_cell}")
        print(f"   Game type: All-in-or-fold (2-4 players)")
        print(f"   Valid actions: FOLD, ALL_IN only")
        print(f"   Domain models: Using Card, Hand, Board, Action, Position enums")

        # Print database stats
        cursor.execute("SELECT COUNT(*) FROM simulations;")
        print(f"   Total simulations: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM game_states;")
        game_states = cursor.fetchone()[0]
        print(f"   Total game states: {game_states}")

        cursor.execute("SELECT COUNT(*) FROM players;")
        print(f"   Total players: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM bets;")
        print(f"   Total bet actions (FOLD/ALL_IN): {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM jackpots;")
        print(f"   Total jackpot events: {cursor.fetchone()[0]}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating database: {e}")
        logger.error(f"Database creation failed: {e}", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Create database in prototyping folder
    db_path = Path(__file__).parent / "aof_analysis.db"

    create_aof_database(
        db_path=str(db_path),
        num_simulations=2,          # 2 simulations
        games_per_cell=100,         # 100 games per cell
        sample_cells=20             # Populate 20 out of 169 cells per simulation
    )
