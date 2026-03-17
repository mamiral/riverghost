"""
Database model tests for normalized relational database schema.

This module contains unit tests for SQLAlchemy models and database operations.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from hopilot.database import DatabaseConnection
from hopilot.models.base import Base


@pytest.fixture(scope="session")
def engine():
    """Create in-memory SQLite engine for testing."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )


@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine, tables):
    """Provide a database session for testing."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def db_connection():
    """Provide a database connection instance for testing."""
    # Use in-memory database for tests
    conn = DatabaseConnection("sqlite:///:memory:")
    conn.create_tables()
    yield conn
    # Cleanup handled by SQLite in-memory database


class TestDatabaseConnection:
    """Test database connection functionality."""

    def test_connection_creation(self, db_connection):
        """Test that database connection can be created."""
        assert db_connection is not None

    def test_table_creation(self, db_connection):
        """Test that tables can be created."""
        # Tables should be created without error
        pass

    def test_session_creation(self, db_connection):
        """Test that sessions can be created."""
        session = db_connection.get_session()
        assert session is not None
        session.close()


# Placeholder for model-specific tests
# These will be expanded as models are implemented

class TestBaseModel:
    """Test base model functionality."""

    def test_base_model_exists(self):
        """Test that base model class exists."""
        from hopilot.models.base import Base
        assert Base is not None