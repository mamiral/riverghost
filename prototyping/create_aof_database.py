#!/usr/bin/env python3
"""
AOF GTO Browser - Database Population with SQLAlchemy ORM Models

This script creates a SQLite database and populates it with relationally correct
mock data using SQLAlchemy ORM models and actual domain models from 
aof_gto_browser_ii.shared.

Key features:
- Uses ORM models (Simulation, GameState, Player, etc.)
- Uses Card, Hand, Board, Position, Action enums from shared models
- Supports 2-4 player all-in games (FOLD and ALL_IN actions only)
- Transactional consistency with cascade deletes
- Type-safe database operations
"""

import sys
import os
from pathlib import Path

# Add python directory to path for imports
python_dir = Path(__file__).parent.parent / "python"
sys.path.insert(0, str(python_dir))

import json
import random
from datetime import datetime, timedelta
from typing import List

from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit
from aof_gto_browser_ii.shared.domain.hand import Hand
from aof_gto_browser_ii.shared.domain.board import Board
from aof_gto_browser_ii.shared.models.enums import Action, Position
from hopilot.logging_config import get_logger

# Import ORM models
from aof_orm_models import (
    Base, Simulation, HandMatrix, MatrixCell, GameState,
    Player, Bet, BoardCard, Jackpot, AggregatedMetric,
    ActionType, JackpotType, ConvergenceStatus
)

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

logger = get_logger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# All possible cards (52 total)
ALL_CARDS = [Card(rank, suit) for rank in Rank for suit in Suit]

# Position rotation for multi-way pots
ALL_POSITIONS = [Position.UTG, Position.BTN, Position.SB, Position.BB]

JACKPOT_TYPES = [
    JackpotType.STRAIGHT_FLUSH_BOTH_HOLE_CARDS,
    JackpotType.STRAIGHT_FLUSH_ONE_HOLE_CARD,
    JackpotType.QUADS,
    JackpotType.FULL_HOUSE,
    JackpotType.FLUSH,
]


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
    num_cards = random.randint(0, 5)
    cards = generate_unique_cards(num_cards)
    return Board(cards=cards)


def get_available_positions(num_players: int) -> List[Position]:
    """Get position assignments for N players (2-4) in order."""
    if num_players < 2 or num_players > 4:
        raise ValueError(f"All-in games support 2-4 players, got {num_players}")
    return ALL_POSITIONS[:num_players]


def hand_to_shorthand(hand: Hand) -> str:
    """Convert Hand object to string notation (e.g., 'AsKh')."""
    return f"{hand.card1.rank.value}{hand.card1.suit.value}{hand.card2.rank.value}{hand.card2.suit.value}"


def board_to_json(board: Board) -> str:
    """Convert Board object to JSON array notation."""
    cards_str = [f"{card.rank.value}{card.suit.value}" for card in board.cards]
    return json.dumps(cards_str) if cards_str else None


def get_hand_notation(row_index: int, col_index: int) -> str:
    """Generate hand notation from matrix indices (e.g., 'AsKs')."""
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    
    rank1 = ranks[row_index]
    rank2 = ranks[col_index]
    
    if row_index == col_index:
        return f"{rank1}{rank2}x"  # Pair
    elif row_index < col_index:
        return f"{rank1}{rank2}s"  # Suited
    else:
        return f"{rank1}{rank2}o"  # Offsuit


# ============================================================================
# DATABASE POPULATION USING ORM
# ============================================================================

def create_aof_database(db_path: str = "aof_analysis.db", num_simulations: int = 2) -> None:
    """Create and populate AOF database using SQLAlchemy ORM."""
    
    print("=" * 70)
    print("CREATING AOF DATABASE WITH ORM MODELS")
    print("=" * 70)
    
    # Remove existing database
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"\n✨ Removed existing database: {db_path}")
    
    # Initialize database and get session factory
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        print(f"📊 Creating database: {db_path}")
        
        # ====================================================================
        # CREATE SIMULATIONS
        # ====================================================================
        print("\n[1/2] Creating simulations and matrices...")
        
        total_game_states = 0
        total_players = 0
        total_bets = 0
        total_jackpots = 0
        
        for sim_num in range(1, num_simulations + 1):
            # Create simulation using ORM
            sim = Simulation(
                name=f"AOF_Simulation_{sim_num}",
                parameters={
                    "game_type": "all_in_or_fold",
                    "players": "2-4",
                    "actions": ["fold", "all_in"],
                    "num_games_per_cell": 100,
                    "total_cells": 169,
                },
            )
            session.add(sim)
            session.flush()  # Assign ID
            
            print(f"  Simulation {sim_num}: {sim.name} (ID: {sim.id})")
            
            # Create hand matrix using ORM
            matrix = HandMatrix(
                simulation_id=sim.id,
                matrix_size=13,
                total_cells=169,
                analyzed_cells=0,
            )
            session.add(matrix)
            session.flush()  # Assign ID
            
            # ================================================================
            # CREATE MATRIX CELLS AND GAMES
            # ================================================================
            print(f"  [2/2] Creating games for simulation {sim_num}...")
            
            # Create all 169 cells (13x13 matrix)
            cells = []
            for row in range(13):
                for col in range(13):
                    cell = MatrixCell(
                        matrix_id=matrix.id,
                        row_index=row,
                        col_index=col,
                        hand_notation=get_hand_notation(row, col),
                    )
                    session.add(cell)
                    cells.append(cell)
            
            session.flush()  # Assign all cell IDs
            
            # Populate 20 random cells with 100 games each
            sample_cells = random.sample(cells, min(20, len(cells)))
            
            for cell_idx, cell in enumerate(sample_cells, 1):
                # Generate 100 games for this cell
                for game_num in range(100):
                    # Determine players
                    num_players = random.randint(2, 4)
                    positions = get_available_positions(num_players)
                    
                    # Generate board using Board domain model
                    board = generate_board()
                    board_json = board_to_json(board)
                    
                    # Create board card record
                    board_card = BoardCard(cards=board_json)
                    session.add(board_card)
                    session.flush()  # Get ID
                    
                    # Create game state
                    game_time = datetime.utcnow() - timedelta(
                        hours=random.randint(1, 24),
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    )
                    game = GameState(
                        cell_id=cell.id,
                        timestamp=game_time,
                        num_players=num_players,
                        board_cards_id=board_card.id,
                        pot_size=round(random.uniform(10, 100), 2),
                        outcome=random.choice(['hero_win', 'hero_loss', 'draw']),
                    )
                    session.add(game)
                    session.flush()  # Get ID
                    
                    # Create players (one is hero) using Hand domain model
                    hero_position = random.randint(0, num_players - 1)
                    
                    for pos_idx, position in enumerate(positions):
                        hand = generate_hand()
                        hand_str = hand_to_shorthand(hand)
                        
                        player = Player(
                            game_state_id=game.id,
                            position=position.value,
                            hole_cards=hand_str,
                            stack_size=round(random.uniform(20, 100), 2),
                            is_hero=(pos_idx == hero_position),
                        )
                        session.add(player)
                        total_players += 1
                    
                    session.flush()  # Assign player IDs
                    
                    # Create bets (FOLD or ALL_IN only using Action enum)
                    game_players = session.query(Player).filter(
                        Player.game_state_id == game.id
                    ).all()
                    
                    for player in game_players:
                        action = random.choice([ActionType.FOLD, ActionType.ALL_IN])
                        amount = 0 if action == ActionType.FOLD else round(random.uniform(5, 50), 2)
                        
                        bet = Bet(
                            game_state_id=game.id,
                            player_id=player.id,
                            action_type=action,
                            amount=amount,
                        )
                        session.add(bet)
                        total_bets += 1
                    
                    # Occasionally add jackpot
                    if random.random() < 0.61:
                        hero_player = next(
                            (p for p in game_players if p.is_hero), 
                            game_players[0]
                        )
                        jackpot = Jackpot(
                            game_state_id=game.id,
                            player_id=hero_player.id,
                            jackpot_type=random.choice(JACKPOT_TYPES),
                            payout_amount=round(random.uniform(400, 600), 2),
                        )
                        session.add(jackpot)
                        total_jackpots += 1
                    
                    total_game_states += 1
                    
                    # Commit every 100 games to manage memory
                    if game_num % 100 == 0:
                        session.commit()
                
                # Create aggregated metrics for this cell
                metric = AggregatedMetric(
                    cell_id=cell.id,
                    equity=round(random.uniform(0.2, 0.98), 4),
                    ev=round(random.uniform(-10, 50), 2),
                    convergence_status=ConvergenceStatus.CONVERGENCE,
                )
                session.add(metric)
                
                if cell_idx % 5 == 0:
                    print(f"    Processed {cell_idx} cells")
            
            # Update matrix analyzed cells
            matrix.analyzed_cells = len(sample_cells)
            
            # Final commit for this simulation
            session.commit()
        
        print("\n" + "=" * 70)
        print("DATABASE CREATION COMPLETE")
        print("=" * 70)
        print(f"\n✅ Database created successfully!")
        print(f"   Location: {Path(db_path).absolute()}")
        print(f"   Simulations: {num_simulations}")
        print(f"   Total game states: {total_game_states:,}")
        print(f"   Total players: {total_players:,}")
        print(f"   Total bet actions (FOLD/ALL_IN): {total_bets:,}")
        print(f"   Total jackpot events: {total_jackpots:,}")
        print(f"   Domain models: Card, Hand, Board, Action, Position enums")
        print("=" * 70 + "\n")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error creating database: {e}")
        logger.error(f"Database creation failed: {e}", exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_aof_database()
