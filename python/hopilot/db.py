"""
SQLAlchemy session management and database initialization.

Provides unified session access for CLI, GUI, and test modules.
Handles database lifecycle including initialization, session creation,
and connection pooling configuration.
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, sessionmaker as session_factory_class

from hopilot.logging_config import get_logger

logger = get_logger(__name__)

# Global session factory (initialized in initialize_database)
_session_factory: Optional[session_factory_class] = None
_engine: Optional[Engine] = None


def initialize_database(database_url: str, pool_size: int = 5, pool_timeout: float = 30.0) -> None:
    """
    Initialize the database connection and session factory.
    
    Must be called once at application startup before any database operations.
    
    Args:
        database_url: SQLAlchemy database URL (e.g., "sqlite:///poker.db")
        pool_size: Connection pool size for concurrent access
        pool_timeout: Timeout for acquiring a connection from pool
    
    Raises:
        ValueError: If database_url is invalid or empty
    """
    global _session_factory, _engine
    
    if not database_url:
        raise ValueError("database_url cannot be empty")
    
    try:
        # Configure engine with connection pooling
        engine_kwargs = {
            "echo": False,  # Set to True for SQL logging during debug
        }
        
        # SQLite-specific settings
        if database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {
                "check_same_thread": False,
                "timeout": pool_timeout,
            }
            engine_kwargs["poolclass"] = None  # SQLite doesn't benefit from pooling
        else:
            # PostgreSQL/MySQL use connection pools
            from sqlalchemy.pool import QueuePool
            engine_kwargs["poolclass"] = QueuePool
            engine_kwargs["pool_size"] = pool_size
            engine_kwargs["max_overflow"] = 10
            engine_kwargs["pool_timeout"] = pool_timeout
            engine_kwargs["pool_recycle"] = 3600
        
        _engine = create_engine(database_url, **engine_kwargs)
        
        # Create session factory
        _session_factory = sessionmaker(
            bind=_engine,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
        
        logger.info(f"Database initialized: {database_url}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        SQLAlchemy Session instance
        
    Raises:
        RuntimeError: If database not initialized (call initialize_database first)
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call initialize_database(database_url) first."
        )
    return _session_factory()


@contextmanager
def session_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup.
    
    Usage:
        with session_context() as session:
            result = session.query(SomeModel).first()
    
    Yields:
        SQLAlchemy Session instance that auto-commits and closes
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session error, rolled back: {e}")
        raise
    finally:
        session.close()


def get_engine() -> Engine:
    """
    Get the SQLAlchemy engine instance.
    
    Returns:
        SQLAlchemy Engine
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _engine is None:
        raise RuntimeError(
            "Database not initialized. Call initialize_database(database_url) first."
        )
    return _engine


def close_database() -> None:
    """
    Close all database connections.
    
    Should be called during application shutdown.
    """
    global _session_factory, _engine
    
    if _engine is not None:
        _engine.dispose()
        logger.info("Database connections closed")
    
    _session_factory = None
    _engine = None
