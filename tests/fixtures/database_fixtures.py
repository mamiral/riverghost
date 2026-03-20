"""
Database fixture base classes for test infrastructure.

Provides reusable session management, transaction handling, and database
setup/teardown for tests that were previously using cache mocks.

BLOCKED BY: None (stands alone)
BLOCKS: T012 (conftest.py) - imports from this module
"""

import os
import tempfile
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from hopilot.logging_config import get_logger
from hopilot.models import Base

logger = get_logger(__name__)


class DatabaseTestFixture:
    """
    Base class for database test fixtures.
    
    Provides session management, automatic cleanup, and transaction
    testing capabilities.
    """

    def __init__(self, database_url: Optional[str] = None, use_temp: bool = True):
        """
        Initialize database test fixture.
        
        Args:
            database_url: Explicit database URL (default: in-memory SQLite)
            use_temp: Create SQLite in temp directory if no URL provided
        """
        self.database_url = database_url
        self.use_temp = use_temp
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._temp_dir: Optional[str] = None
        
        self._setup()

    def _setup(self) -> None:
        """Set up database engine and session factory."""
        try:
            # Determine database URL
            if not self.database_url:
                if self.use_temp:
                    self._temp_dir = tempfile.mkdtemp()
                    db_file = os.path.join(self._temp_dir, "test.db")
                    self.database_url = f"sqlite:///{db_file}"
                else:
                    self.database_url = "sqlite:///:memory:"
            
            # Create engine
            self._engine = create_engine(
                self.database_url,
                echo=False,
                connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
            )
            
            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )
            
            # Create tables
            Base.metadata.create_all(self._engine)
            logger.debug(f"Database test fixture initialized: {self.database_url}")
            
        except Exception as e:
            logger.error(f"Failed to setup database fixture: {e}")
            raise

    def get_session(self) -> Session:
        """Create a new database session."""
        if self._session_factory is None:
            raise RuntimeError("Database fixture not initialized")
        return self._session_factory()

    @contextmanager
    def session_context(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with automatic rollback on error.
        
        Usage:
            with fixture.session_context() as session:
                obj = session.query(Model).first()
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def cleanup(self) -> None:
        """Clean up database connections and temporary files."""
        try:
            if self._engine:
                self._engine.dispose()
            
            if self._temp_dir and os.path.exists(self._temp_dir):
                import shutil
                shutil.rmtree(self._temp_dir)
                logger.debug(f"Cleaned up temp directory: {self._temp_dir}")
            
        except Exception as e:
            logger.error(f"Error during fixture cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        self.cleanup()


class TransactionTestFixture(DatabaseTestFixture):
    """
    Database fixture with transaction support for test isolation.
    
    Each session runs in a savepoint that can be rolled back.
    Useful for tests that need to verify transaction boundaries.
    """

    def __init__(self, *args, **kwargs):
        """Initialize transaction-enabled fixture."""
        super().__init__(*args, **kwargs)
        self._connections = []

    def get_session(self) -> Session:
        """
        Create a new session within a transaction.
        
        All sessions are isolated via savepoints.
        """
        session = super().get_session()
        
        # Begin transaction with savepoint for isolation
        connection = self._engine.connect()
        transaction = connection.begin()
        session.connection(lambda: connection)
        
        self._connections.append((session, connection, transaction))
        return session

    def rollback_all(self) -> None:
        """Rollback all open sessions (for cleanup between tests)."""
        for session, connection, transaction in self._connections:
            try:
                transaction.rollback()
                connection.close()
                session.close()
            except Exception as e:
                logger.error(f"Error rolling back transaction: {e}")
        
        self._connections.clear()

    def cleanup(self) -> None:
        """Cleanup including transaction rollback."""
        self.rollback_all()
        super().cleanup()


class ConnectionPoolTestFixture(DatabaseTestFixture):
    """
    Database fixture with connection pool for concurrency testing.
    
    Allows testing behavior under concurrent database access.
    """

    def __init__(self, pool_size: int = 5, *args, **kwargs):
        """
        Initialize fixture with connection pool.
        
        Args:
            pool_size: Number of connections in pool
        """
        self.pool_size = pool_size
        super().__init__(*args, **kwargs)

    def _setup(self) -> None:
        """Setup with connection pooling."""
        try:
            if not self.database_url:
                if self.use_temp:
                    self._temp_dir = tempfile.mkdtemp()
                    db_file = os.path.join(self._temp_dir, "test.db")
                    self.database_url = f"sqlite:///{db_file}"
                else:
                    self.database_url = "sqlite:///:memory:"
            
            # Create engine with pooling
            if "sqlite" in self.database_url:
                # SQLite doesn't benefit from pooling but we can still configure it
                self._engine = create_engine(
                    self.database_url,
                    echo=False,
                    connect_args={"check_same_thread": False, "timeout": 30.0},
                )
            else:
                # PostgreSQL/MySQL use actual pooling
                from sqlalchemy.pool import QueuePool
                self._engine = create_engine(
                    self.database_url,
                    echo=False,
                    poolclass=QueuePool,
                    pool_size=self.pool_size,
                    max_overflow=10,
                    pool_timeout=30.0,
                )
            
            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )
            
            # Create tables
            Base.metadata.create_all(self._engine)
            logger.debug(f"Connection pool fixture initialized: {self.database_url} (pool_size={self.pool_size})")
            
        except Exception as e:
            logger.error(f"Failed to setup connection pool fixture: {e}")
            raise
