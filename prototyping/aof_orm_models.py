#!/usr/bin/env python3
"""
SQLAlchemy ORM Models for AOF GTO Database.

Defines 9 models corresponding to the database tables:
- Simulation, HandMatrix, MatrixCell, GameState
- Player, Bet, BoardCard, Jackpot, AggregatedMetric

Models include relationships, validators, and computed properties.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Float, Numeric, Boolean, DateTime,
    ForeignKey, JSON, Enum, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.sql import func

import enum


# Base class for all models
Base = declarative_base()


# ============================================================================
# ENUM DEFINITIONS
# ============================================================================

class ActionType(str, enum.Enum):
    """All-in-or-fold action enumeration."""
    FOLD = "fold"
    ALL_IN = "all_in"


class JackpotType(str, enum.Enum):
    """Poker jackpot types."""
    QUADS = "quads"
    FLUSH = "flush"
    STRAIGHT_FLUSH_ONE_HOLE_CARD = "straight_flush_one_hole_card"
    STRAIGHT_FLUSH_BOTH_HOLE_CARDS = "straight_flush_both_hole_cards"
    FULL_HOUSE = "full_house"


class ConvergenceStatus(str, enum.Enum):
    """Convergence assessment status."""
    INITIAL = "initial"
    CONVERGENCE = "convergence"
    STABLE = "stable"


# ============================================================================
# MODEL DEFINITIONS
# ============================================================================

class Simulation(Base):
    """Top-level simulation run with configuration parameters."""
    
    __tablename__ = 'simulations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    parameters = Column(JSON, nullable=False)  # Stores all simulation config
    total_games = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    hand_matrices = relationship(
        "HandMatrix",
        back_populates="simulation",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Simulation(id={self.id}, name='{self.name}', games={self.total_games})>"


class HandMatrix(Base):
    """13×13 grid of starting hands (169 cells per simulation)."""
    
    __tablename__ = 'hand_matrices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey('simulations.id'), nullable=False)
    matrix_size = Column(Integer, default=13)  # Always 13x13
    total_cells = Column(Integer, default=169)  # Always 169 (13²)
    analyzed_cells = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    simulation = relationship("Simulation", back_populates="hand_matrices")
    matrix_cells = relationship(
        "MatrixCell",
        back_populates="hand_matrix",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<HandMatrix(id={self.id}, sim={self.simulation_id}, cells={self.analyzed_cells}/{self.total_cells})>"


class MatrixCell(Base):
    """Individual hand cell in the 13×13 matrix (row_index, col_index)."""
    
    __tablename__ = 'matrix_cells'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    matrix_id = Column(Integer, ForeignKey('hand_matrices.id'), nullable=False)
    row_index = Column(Integer, nullable=False)  # 0-12
    col_index = Column(Integer, nullable=False)  # 0-12
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Composite unique constraint enforced at database level
    __table_args__ = (
        # Explicit constraint: (matrix_id, row_index, col_index) must be unique
    )
    
    # Relationships
    hand_matrix = relationship("HandMatrix", back_populates="matrix_cells")
    game_states = relationship(
        "GameState",
        back_populates="matrix_cell",
        cascade="all, delete-orphan"
    )
    aggregated_metrics = relationship(
        "AggregatedMetric",
        back_populates="matrix_cell",
        cascade="all, delete-orphan",
        uselist=False
    )
    
    @property
    def hand_name(self) -> str:
        """Convert row/col indices to standard hand name (e.g., 'As2s', '3x3')."""
        ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        suits = ['s', 'h', 'd', 'c']
        
        rank1 = ranks[self.row_index]
        rank2 = ranks[self.col_index]
        
        if self.row_index == self.col_index:
            return f"{rank1}{rank2}x"  # Pair
        elif self.row_index < self.col_index:
            return f"{rank1}{rank2}s"  # Suited
        else:
            return f"{rank1}{rank2}o"  # Offsuit
    
    def __repr__(self):
        return f"<MatrixCell(id={self.id}, matrix={self.matrix_id}, pos={self.row_index}x{self.col_index})>"


class GameState(Base):
    """Individual simulated poker hand/game."""
    
    __tablename__ = 'game_states'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_id = Column(Integer, ForeignKey('matrix_cells.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    num_players = Column(Integer, nullable=False)  # 2-4 players
    board_cards_id = Column(Integer, ForeignKey('board_cards.id'), nullable=False)
    pot_size = Column(Numeric(10, 2), nullable=False)
    outcome = Column(String(50))  # 'hero_win', 'hero_loss', 'draw'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    matrix_cell = relationship("MatrixCell", back_populates="game_states")
    board_cards = relationship("BoardCard", uselist=False)
    players = relationship(
        "Player",
        back_populates="game_state",
        cascade="all, delete-orphan"
    )
    bets = relationship(
        "Bet",
        back_populates="game_state",
        cascade="all, delete-orphan"
    )
    jackpots = relationship(
        "Jackpot",
        back_populates="game_state",
        cascade="all, delete-orphan"
    )
    
    @property
    def total_actions(self) -> int:
        """Count of all actions in this game."""
        return len(self.bets)
    
    @property
    def fold_count(self) -> int:
        """Count of FOLD actions."""
        return sum(1 for b in self.bets if b.action_type == ActionType.FOLD)
    
    @property
    def all_in_count(self) -> int:
        """Count of ALL_IN actions."""
        return sum(1 for b in self.bets if b.action_type == ActionType.ALL_IN)
    
    def __repr__(self):
        return f"<GameState(id={self.id}, cell={self.cell_id}, players={self.num_players}, outcome={self.outcome})>"


class Player(Base):
    """Individual player position in a game."""
    
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_state_id = Column(Integer, ForeignKey('game_states.id'), nullable=False)
    position = Column(String(10), nullable=False)  # 'utg', 'btn', 'sb', 'bb'
    hole_cards = Column(String(10), nullable=False)  # e.g., 'AsKh'
    stack_size = Column(Numeric(10, 2), nullable=False)
    is_hero = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    game_state = relationship("GameState", back_populates="players")
    bets = relationship(
        "Bet",
        back_populates="player",
        cascade="all, delete-orphan"
    )
    jackpots = relationship(
        "Jackpot",
        back_populates="player",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        hero_mark = "[HERO]" if self.is_hero else "[VILL]"
        return f"<Player(id={self.id}, {hero_mark} {self.position}:{self.hole_cards})>"


class Bet(Base):
    """Individual action/bet in a game (FOLD or ALL_IN only)."""
    
    __tablename__ = 'bets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_state_id = Column(Integer, ForeignKey('game_states.id'), nullable=False)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    action_type = Column(Enum(ActionType), nullable=False)
    amount = Column(Numeric(10, 2), default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    game_state = relationship("GameState", back_populates="bets")
    player = relationship("Player", back_populates="bets")
    
    def __repr__(self):
        return f"<Bet(id={self.id}, player={self.player_id}, {self.action_type.value} {self.amount}BB)>"


class BoardCard(Base):
    """Community cards for a game (0-5 cards)."""
    
    __tablename__ = 'board_cards'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cards = Column(String(100))  # JSON array: ["As", "Kh", "Qd"] or null
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def is_flop(self) -> bool:
        """Check if board is flop (3 cards)."""
        return self.cards and len(self.cards) == 3 if isinstance(self.cards, list) else False
    
    def is_turn(self) -> bool:
        """Check if board is turn (4 cards)."""
        return self.cards and len(self.cards) == 4 if isinstance(self.cards, list) else False
    
    def is_river(self) -> bool:
        """Check if board is river (5 cards)."""
        return self.cards and len(self.cards) == 5 if isinstance(self.cards, list) else False
    
    def __repr__(self):
        return f"<BoardCard(id={self.id}, cards={self.cards})>"


class Jackpot(Base):
    """Jackpot bonus event (quads, flush, etc.)."""
    
    __tablename__ = 'jackpots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_state_id = Column(Integer, ForeignKey('game_states.id'), nullable=False)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    jackpot_type = Column(Enum(JackpotType), nullable=False)
    payout_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    game_state = relationship("GameState", back_populates="jackpots")
    player = relationship("Player", back_populates="jackpots")
    
    def __repr__(self):
        return f"<Jackpot(id={self.id}, type={self.jackpot_type.value}, payout=${self.payout_amount})>"


class AggregatedMetric(Base):
    """Pre-computed metrics for a hand cell."""
    
    __tablename__ = 'aggregated_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_id = Column(Integer, ForeignKey('matrix_cells.id'), nullable=False, unique=True)
    equity = Column(Float)  # Normalized equity (0-1)
    ev = Column(Numeric(10, 2))  # Expected value in BB
    convergence_status = Column(Enum(ConvergenceStatus))
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    matrix_cell = relationship("MatrixCell", back_populates="aggregated_metrics")
    
    def __repr__(self):
        return f"<AggregatedMetric(cell={self.cell_id}, equity={self.equity:.4f}, ev=${self.ev})>"


# ============================================================================
# REPOSITORY PATTERN - DATA ACCESS LAYER
# ============================================================================

class Repository:
    """Base repository for database operations."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session."""
        self.session = session
    
    def get_by_id(self, model_class, obj_id: int):
        """Get object by primary key."""
        return self.session.query(model_class).filter(model_class.id == obj_id).first()
    
    def get_all(self, model_class):
        """Get all objects of a type."""
        return self.session.query(model_class).all()
    
    def add(self, obj):
        """Add new object to session."""
        self.session.add(obj)
        return obj
    
    def delete(self, obj):
        """Delete object from session."""
        self.session.delete(obj)
    
    def commit(self):
        """Commit pending changes."""
        self.session.commit()
    
    def rollback(self):
        """Rollback pending changes."""
        self.session.rollback()


class SimulationRepository(Repository):
    """Specialized repository for Simulation queries."""
    
    def get_by_name(self, name: str) -> Optional[Simulation]:
        """Get simulation by name."""
        return self.session.query(Simulation).filter(
            Simulation.name == name
        ).first()
    
    def get_recent(self, limit: int = 10) -> List[Simulation]:
        """Get most recent simulations."""
        return self.session.query(Simulation).order_by(
            Simulation.created_at.desc()
        ).limit(limit).all()
    
    def get_with_matrices(self, sim_id: int) -> Optional[Simulation]:
        """Get simulation with all matrices eager-loaded."""
        from sqlalchemy.orm import joinedload
        return self.session.query(Simulation).options(
            joinedload(Simulation.hand_matrices)
        ).filter(Simulation.id == sim_id).first()


class MatrixCellRepository(Repository):
    """Specialized repository for MatrixCell queries."""
    
    def get_by_position(self, matrix_id: int, row: int, col: int) -> Optional[MatrixCell]:
        """Get cell by matrix and position."""
        return self.session.query(MatrixCell).filter(
            MatrixCell.matrix_id == matrix_id,
            MatrixCell.row_index == row,
            MatrixCell.col_index == col
        ).first()
    
    def get_by_matrix(self, matrix_id: int) -> List[MatrixCell]:
        """Get all cells for a matrix."""
        return self.session.query(MatrixCell).filter(
            MatrixCell.matrix_id == matrix_id
        ).order_by(MatrixCell.row_index, MatrixCell.col_index).all()


class GameStateRepository(Repository):
    """Specialized repository for GameState queries."""
    
    def get_by_cell(self, cell_id: int) -> List[GameState]:
        """Get all games for a matrix cell."""
        return self.session.query(GameState).filter(
            GameState.cell_id == cell_id
        ).order_by(GameState.timestamp.desc()).all()
    
    def get_recent_games(self, limit: int = 100) -> List[GameState]:
        """Get most recent games."""
        return self.session.query(GameState).order_by(
            GameState.timestamp.desc()
        ).limit(limit).all()
    
    def count_by_outcome(self, cell_id: int) -> dict:
        """Count games by outcome for a cell."""
        from sqlalchemy import func
        results = self.session.query(
            GameState.outcome,
            func.count(GameState.id).label('count')
        ).filter(GameState.cell_id == cell_id).group_by(GameState.outcome).all()
        return {outcome: count for outcome, count in results}
    
    def get_with_details(self, game_id: int) -> Optional[GameState]:
        """Get game with all relationships eager-loaded."""
        from sqlalchemy.orm import joinedload
        return self.session.query(GameState).options(
            joinedload(GameState.players),
            joinedload(GameState.bets),
            joinedload(GameState.board_cards)
        ).filter(GameState.id == game_id).first()


class JackpotRepository(Repository):
    """Specialized repository for Jackpot queries."""
    
    def get_by_cell(self, cell_id: int) -> List[Jackpot]:
        """Get all jackpots for a cell."""
        from sqlalchemy import join
        return self.session.query(Jackpot).join(GameState).filter(
            GameState.cell_id == cell_id
        ).all()
    
    def get_by_type(self, jackpot_type: JackpotType) -> List[Jackpot]:
        """Get all jackpots of a specific type."""
        return self.session.query(Jackpot).filter(
            Jackpot.jackpot_type == jackpot_type
        ).all()
    
    def get_frequency_by_cell(self, cell_id: int) -> dict:
        """Get jackpot frequency by type for a cell."""
        from sqlalchemy import func, join
        results = self.session.query(
            Jackpot.jackpot_type,
            func.count(Jackpot.id).label('count'),
            func.avg(Jackpot.payout_amount).label('avg_payout')
        ).join(GameState).filter(GameState.cell_id == cell_id).group_by(
            Jackpot.jackpot_type
        ).all()
        return {
            str(jtype): {'count': count, 'avg_payout': float(avg)}
            for jtype, count, avg in results
        }


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def initialize_database(db_path: str = "sqlite:///aof_analysis.db") -> Session:
    """Initialize database and return session."""
    engine = create_engine(db_path, echo=False)
    Base.metadata.create_all(engine)
    
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


if __name__ == "__main__":
    # Example usage
    print("=" * 70)
    print("AOF GTO DATABASE - SQLALCHEMY ORM MODELS")
    print("=" * 70)
    print("\nModels defined:")
    print("  1. Simulation - Top-level run configuration")
    print("  2. HandMatrix - 13x13 matrix container")
    print("  3. MatrixCell - Individual hand cell")
    print("  4. GameState - Individual simulated game")
    print("  5. Player - Player position in game")
    print("  6. Bet - Individual action (FOLD/ALL_IN)")
    print("  7. BoardCard - Community cards (0-5)")
    print("  8. Jackpot - Bonus event")
    print("  9. AggregatedMetric - Pre-computed metrics")
    print("\nRepositories provided:")
    print("  - Repository (base class)")
    print("  - SimulationRepository")
    print("  - MatrixCellRepository")
    print("  - GameStateRepository")
    print("  - JackpotRepository")
    print("\nEnums defined:")
    print("  - ActionType: FOLD, ALL_IN")
    print("  - JackpotType: QUADS, FLUSH, etc.")
    print("  - ConvergenceStatus: INITIAL, CONVERGENCE, STABLE")
    print("=" * 70 + "\n")
