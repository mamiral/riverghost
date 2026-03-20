"""
Pytest configuration and fixtures for cache-removal refactoring.

Provides database session fixtures and test utilities for all tests
that were previously using cache mocks.

BLOCKED BY: T008 (database_fixtures.py must exist for import)
BLOCKS: T024-T027 (config removal tests), T028-T035 (test refactoring)
"""

import os
import sys
import tempfile
from typing import Generator

# Add python/ directory to path so hopilot can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from hopilot import db
from hopilot.logging_config import get_logger
from hopilot.models import Base
from .fixtures.database_fixtures import (
    ConnectionPoolTestFixture,
    DatabaseTestFixture,
    TransactionTestFixture,
)
from .fixtures.model_fixtures import ModelFactory, ScenarioBuilder

logger = get_logger(__name__)


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def db_fixture() -> Generator[DatabaseTestFixture, None, None]:
    """
    Function-scoped database fixture.
    
    Creates a fresh in-memory SQLite database for each test.
    Perfect for isolated unit tests.
    
    Usage:
        def test_something(db_fixture):
            with db_fixture.session_context() as session:
                # test code here
    """
    fixture = DatabaseTestFixture(use_temp=False)  # Use in-memory
    try:
        yield fixture
    finally:
        fixture.cleanup()


@pytest.fixture(scope="function")
def db_session(db_fixture: DatabaseTestFixture) -> Generator[Session, None, None]:
    """
    Database session fixture for direct session access.
    
    Yields a fresh session for each test. Session auto-commits on success,
    auto-rollsback on exception.
    
    Usage:
        def test_something(db_session):
            result = db_session.query(Model).first()
            assert result is not None
    """
    session = db_fixture.get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Test session error: {e}")
        raise
    finally:
        session.close()


@pytest.fixture(scope="function")
def transaction_db_fixture() -> Generator[TransactionTestFixture, None, None]:
    """
    Transaction-scoped database fixture for testing transaction boundaries.
    
    Each session runs in a savepoint that can be rolled back independently.
    Useful for testing transaction isolation and rollback behavior.
    
    Usage:
        def test_transaction_rollback(transaction_db_fixture):
            session1 = transaction_db_fixture.get_session()
            # Make changes
            transaction_db_fixture.rollback_all()
            # Verify rollback
    """
    fixture = TransactionTestFixture(use_temp=False)
    try:
        yield fixture
    finally:
        fixture.cleanup()


@pytest.fixture(scope="function")
def connection_pool_fixture() -> Generator[ConnectionPoolTestFixture, None, None]:
    """
    Connection pool fixture for concurrency testing.
    
    Provides a connection pool to test concurrent database access patterns.
    
    Usage:
        def test_concurrent_access(connection_pool_fixture):
            with connection_pool_fixture.session_context() as session:
                # Multiple threads can get sessions from the pool
    """
    fixture = ConnectionPoolTestFixture(pool_size=5, use_temp=False)
    try:
        yield fixture
    finally:
        fixture.cleanup()


# ============================================================================
# MODEL FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def factory(db_session: Session) -> ModelFactory:
    """
    Model factory for creating test data.
    
    Provides convenient methods to create Simulation, HandMatrix,
    MatrixCell, and other model instances.
    
    Usage:
        def test_matrix_cell(factory):
            sim = factory.create_simulation(db_session)
            matrix = factory.create_hand_matrix(db_session, sim.id)
            cell = factory.create_matrix_cell(db_session, matrix.id, 0, 0)
    """
    return ModelFactory()


@pytest.fixture(scope="function")
def scenario_builder(db_session: Session) -> ScenarioBuilder:
    """
    Scenario builder for creating complete test scenarios.
    
    Provides convenience methods for creating full scenarios with
    simulations, matrices, cells, and other related data.
    
    Usage:
        def test_full_scenario(scenario_builder):
            scenario = scenario_builder.create_full_scenario()
            # scenario has 'simulation', 'matrix', 'cells'
    """
    return ScenarioBuilder(db_session)


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def sample_simulation(factory: ModelFactory, db_session: Session):
    """Create a sample simulation for tests."""
    return factory.create_simulation(db_session, name="test_sim")


@pytest.fixture(scope="function")
def sample_matrix(factory: ModelFactory, db_session: Session, sample_simulation):
    """Create a sample hand matrix with full cell population."""
    from tests.fixtures.model_fixtures import POKER_HANDS
    
    matrix = factory.create_hand_matrix(
        db_session,
        simulation_id=sample_simulation.id
    )
    
    # Populate with all 169 hands
    for row in range(13):
        for col in range(13):
            hand = POKER_HANDS[row * 13 + col]
            factory.create_matrix_cell(
                db_session,
                hand_matrix_id=matrix.id,
                row=row,
                col=col,
                hand_name=hand,
                ev_value=0.5 + (row + col) * 0.01,  # Reasonable EV range
                action="raise" if row > col else "call" if row == col else "fold",
            )
    
    db_session.commit()
    return matrix


@pytest.fixture(scope="function")
def sample_game_state(factory: ModelFactory, db_session: Session, sample_simulation):
    """Create a sample game state with board cards."""
    state = factory.create_game_state(
        db_session,
        simulation_id=sample_simulation.id,
        phase="flop",
    )
    
    # Add flop cards
    factory.create_board_card(db_session, state.id, "A", "s", 0)
    factory.create_board_card(db_session, state.id, "K", "h", 1)
    factory.create_board_card(db_session, state.id, "Q", "d", 2)
    
    db_session.commit()
    return state


@pytest.fixture(scope="function")
def sample_players(factory: ModelFactory, db_session: Session):
    """Create a table of players."""
    from tests.fixtures.model_fixtures import POSITIONS
    
    players = []
    for pos in POSITIONS:
        player = factory.create_player(
            db_session,
            name=pos,
            position=pos,
            stack_size=100.0
        )
        players.append(player)
    
    db_session.commit()
    return players


# ============================================================================
# CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Configure pytest."""
    logger.info("Pytest configuration: Cache-removal test suite")
    logger.info("Using database fixtures instead of cache mocks")


def pytest_collection_modifyitems(config, items):
    """Modify test collection (add markers, etc.)."""
    for item in items:
        # Add database marker to tests using db fixtures
        if any(fixture in item.fixturenames for fixture in [
            'db_fixture', 'db_session', 'transaction_db_fixture',
            'connection_pool_fixture', 'factory', 'scenario_builder'
        ]):
            item.add_marker(pytest.mark.database)


# ============================================================================
# HELPERS
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Setup logging for test runs."""
    logger.info("=" * 80)
    logger.info("TEST SESSION START: Cache-Removal Refactoring")
    logger.info("=" * 80)
    yield
    logger.info("=" * 80)
    logger.info("TEST SESSION END")
    logger.info("=" * 80)


# ============================================================================
# MARKERS
# ============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "database: mark test as using database fixtures"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
