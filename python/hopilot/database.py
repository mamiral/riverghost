"""
Database connection and session management for poker analysis system.

This module provides SQLAlchemy-based database connectivity with proper
session management and transaction handling.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from hopilot.logging_config import get_logger

logger = get_logger(__name__)


# Register proper SQLite datetime adapters to avoid deprecation warnings
def adapt_datetime(dt):
    """Convert datetime to ISO format string for SQLite."""
    return dt.isoformat()


def convert_datetime(s):
    """Convert ISO format string back to datetime for SQLite."""
    return datetime.fromisoformat(s)


# Register the adapters
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)


class DatabaseConnection:
    """
    Manages database connection lifecycle and session handling.

    Provides both direct session access and context manager patterns
    for proper resource management.
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize connection to SQLite database.

        Args:
            database_url: SQLAlchemy database URL (e.g., "sqlite:///poker.db")
        """
        self.database_url = database_url
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

        # Configure SQLite-specific settings
        connect_args = {}
        if database_url.startswith("sqlite"):
            connect_args = {
                "check_same_thread": False,  # Allow multi-threaded access
                "timeout": 30.0,  # Connection timeout
                "detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,  # Enable type detection
            }

        self._engine = create_engine(
            database_url,
            connect_args=connect_args,
            poolclass=QueuePool,
            pool_pre_ping=True,  # Verify connections before use
            pool_size=5,  # Limit connection pool size
            max_overflow=10,  # Allow overflow connections
            echo=bool(os.getenv("SQLALCHEMY_ECHO", False)),  # Debug logging
            isolation_level="SERIALIZABLE",  # ACID compliance
        )

        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,  # Keep objects after commit
        )

        # Enable WAL mode for better concurrency
        if database_url.startswith("sqlite"):
            self._enable_wal_mode()

        logger.info(f"Database connection initialized: {database_url}")

    def _enable_wal_mode(self) -> None:
        """
        Enable Write-Ahead Logging mode for SQLite.

        WAL mode provides better concurrency and performance for
        multi-threaded applications.
        """
        try:
            with self._engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode = WAL;"))
                conn.execute(text("PRAGMA synchronous = NORMAL;"))
                conn.execute(text("PRAGMA wal_autocheckpoint = 1000;"))
                conn.commit()
            logger.debug("SQLite WAL mode enabled")
        except Exception as e:
            logger.warning(f"Failed to enable WAL mode: {e}")

    def get_session(self) -> Session:
        """
        Return a new SQLAlchemy session.

        Note: Caller is responsible for closing the session.
        Consider using session_scope() context manager instead.

        Returns:
            New SQLAlchemy session
        """
        if not self._session_factory:
            raise RuntimeError("Database connection not initialized")
        return self._session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Context manager for session lifecycle.

        Automatically handles commit/rollback and session cleanup.
        Preferred pattern for database operations.

        Yields:
            SQLAlchemy session

        Raises:
            Exception: Any exception from database operations
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            session.close()

    def create_tables(self) -> None:
        """Create all database tables from SQLAlchemy models."""
        from hopilot.models.base import Base
        Base.metadata.create_all(self._engine)
        logger.info("Database tables created")

    def drop_tables(self) -> None:
        """Drop all database tables (for testing/cleanup)."""
        from hopilot.models.base import Base
        Base.metadata.drop_all(self._engine)
        logger.info("Database tables dropped")

    def close(self) -> None:
        """Close database connection and cleanup resources."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connection closed")


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class IntegrityError(DatabaseError):
    """Raised on constraint violations."""
    pass


class ConnectionError(DatabaseError):
    """Raised on connection issues."""
    pass


class DataValidationError(DatabaseError):
    """Raised when simulation data is corrupted or oversized."""
    pass


# Global database connection instance
_db_connection: Optional[DatabaseConnection] = None


def get_database_connection() -> DatabaseConnection:
    """
    Get the global database connection instance.

    Returns:
        DatabaseConnection instance

    Raises:
        RuntimeError: If database not initialized
    """
    global _db_connection
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_connection


def init_database(database_url: str) -> None:
    """
    Initialize the global database connection.

    Args:
        database_url: SQLAlchemy database URL
    """
    global _db_connection
    _db_connection = DatabaseConnection(database_url)
    logger.info("Global database connection initialized")


def close_database() -> None:
    """Close the global database connection."""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        _db_connection = None
        logger.info("Global database connection closed")


def bulk_insert_game_states(game_states_data: List[Dict[str, Any]], batch_size: int = 1000) -> None:
    """
    Bulk insert multiple game states efficiently with batching.

    Args:
        game_states_data: List of game state data dictionaries
        batch_size: Number of records to process in each batch

    Raises:
        DataValidationError: If data is invalid
        IntegrityError: If foreign key constraints are violated
    """
    if not game_states_data:
        raise DataValidationError("No game state data provided")
    
    if batch_size <= 0:
        raise DataValidationError("Batch size must be positive")
    
    if len(game_states_data) > 10000:  # Reasonable limit to prevent memory issues
        raise DataValidationError("Too many game states in single operation (max 10000)")
    
    # Validate input data structure
    _validate_game_states_data(game_states_data)
    
    conn = get_database_connection()

    # Process in batches to avoid memory issues
    for i in range(0, len(game_states_data), batch_size):
        batch = game_states_data[i:i + batch_size]
        _bulk_insert_batch(conn, batch)

    logger.info(f"Bulk inserted {len(game_states_data)} game states in batches")


def _validate_game_states_data(game_states_data: List[Dict[str, Any]]) -> None:
    """
    Validate game states data structure and content.
    
    Args:
        game_states_data: List of game state dictionaries to validate
        
    Raises:
        DataValidationError: If validation fails
    """
    required_fields = ['cell_id', 'timestamp', 'pot_size', 'board_cards']
    
    for i, gs_data in enumerate(game_states_data):
        if not isinstance(gs_data, dict):
            raise DataValidationError(f"Game state {i} must be a dictionary")
        
        # Check required fields
        for field in required_fields:
            if field not in gs_data:
                raise DataValidationError(f"Game state {i} missing required field: {field}")
        
        # Validate cell_id
        if not isinstance(gs_data['cell_id'], int) or gs_data['cell_id'] <= 0:
            raise DataValidationError(f"Game state {i} has invalid cell_id: {gs_data['cell_id']}")
        
        # Validate timestamp
        if not isinstance(gs_data['timestamp'], datetime):
            raise DataValidationError(f"Game state {i} has invalid timestamp: {gs_data['timestamp']}")
        
        # Validate pot_size
        try:
            pot_size = Decimal(str(gs_data['pot_size']))
            if pot_size < 0:
                raise DataValidationError(f"Game state {i} has negative pot_size: {pot_size}")
        except (ValueError, TypeError):
            raise DataValidationError(f"Game state {i} has invalid pot_size: {gs_data['pot_size']}")
        
        # Validate board_cards structure
        if not isinstance(gs_data['board_cards'], dict):
            raise DataValidationError(f"Game state {i} has invalid board_cards structure")
        
        required_board_cards = ['flop1', 'flop2', 'flop3', 'turn', 'river']
        for card_field in required_board_cards:
            if card_field not in gs_data['board_cards']:
                raise DataValidationError(f"Game state {i} missing board card: {card_field}")
        
        # Validate optional nested data
        if 'players' in gs_data:
            if not isinstance(gs_data['players'], list):
                raise DataValidationError(f"Game state {i} players must be a list")
            for j, player in enumerate(gs_data['players']):
                if not isinstance(player, dict):
                    raise DataValidationError(f"Game state {i} player {j} must be a dictionary")
        
        if 'bets' in gs_data:
            if not isinstance(gs_data['bets'], list):
                raise DataValidationError(f"Game state {i} bets must be a list")
            for j, bet in enumerate(gs_data['bets']):
                if not isinstance(bet, dict):
                    raise DataValidationError(f"Game state {i} bet {j} must be a dictionary")


def _bulk_insert_batch(conn: DatabaseConnection, game_states_data: List[Dict[str, Any]]) -> None:
    """
    Internal function to handle a single batch of bulk inserts.
    """
    with conn.session_scope() as session:
        try:
            # Create board cards first (avoid duplicates)
            board_cards_map = {}
            for gs_data in game_states_data:
                board_key = (gs_data["board_cards"]["flop1"],
                           gs_data["board_cards"]["flop2"],
                           gs_data["board_cards"]["flop3"],
                           gs_data["board_cards"]["turn"],
                           gs_data["board_cards"]["river"])

                if board_key not in board_cards_map:
                    board_card = BoardCard(**gs_data["board_cards"])
                    session.add(board_card)
                    session.flush()  # Get ID
                    board_cards_map[board_key] = board_card.id
                gs_data["board_cards_id"] = board_cards_map[board_key]

            # Remove board_cards dict, keep only ID
            for gs_data in game_states_data:
                del gs_data["board_cards"]

            # Bulk create game states
            game_states = []
            for gs_data in game_states_data:
                gs = GameState(**gs_data)
                game_states.append(gs)
                session.add(gs)

            session.flush()  # Get IDs for relationships

            # Handle nested data (players, bets) in batches
            for gs, gs_data in zip(game_states, game_states_data):
                # Create players
                if "players" in gs_data:
                    for player_data in gs_data["players"]:
                        player_data["game_state_id"] = gs.id
                        player = Player(**player_data)
                        session.add(player)

                # Create bets
                if "bets" in gs_data:
                    for bet_data in gs_data["bets"]:
                        bet_data["game_state_id"] = gs.id
                        bet = Bet(**bet_data)
                        session.add(bet)

        except Exception as e:
            logger.error(f"Bulk insert batch failed: {e}")
            if "FOREIGN KEY" in str(e):
                raise IntegrityError(f"Foreign key constraint violation: {e}")
            elif "UNIQUE" in str(e):
                raise IntegrityError(f"Unique constraint violation: {e}")
            else:
                raise DataValidationError(f"Data validation error: {e}")


def get_game_states_for_cell(cell_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Retrieve game states for specific matrix cell.

    Args:
        cell_id: Matrix cell ID
        limit: Maximum number of states to return

    Returns:
        List of game state dictionaries
    """
    from hopilot.models import GameState

    conn = get_database_connection()

    with conn.session_scope() as session:
        game_states = (
            session.query(GameState)
            .filter(GameState.cell_id == cell_id)
            .order_by(GameState.timestamp.desc())
            .limit(limit)
            .all()
        )

        return [gs.to_dict() for gs in game_states]


def get_convergence_data(cell_id: int) -> List[Dict[str, Any]]:
    """
    Get timestamped equity data for convergence analysis.

    Args:
        cell_id: Matrix cell ID

    Returns:
        List of convergence data points
    """
    from hopilot.models import GameState

    conn = get_database_connection()

    with conn.session_scope() as session:
        # Note: This assumes GameState has equity field or needs to be calculated
        # For now, return basic timestamp data
        game_states = (
            session.query(GameState.timestamp)
            .filter(GameState.cell_id == cell_id)
            .order_by(GameState.timestamp)
            .all()
        )

        return [
            {"timestamp": gs.timestamp.isoformat(), "sequence": i}
            for i, gs in enumerate(game_states)
        ]