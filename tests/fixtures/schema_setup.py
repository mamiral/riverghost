"""
Database schema setup utilities for testing.

Provides helpers for initializing test database schemas, applying
migrations, and verifying schema consistency.

BLOCKED BY: None (stands alone)
BLOCKS: None (optional utility)
"""

import os
from typing import Optional

from sqlalchemy import inspect, create_engine, MetaData, Table
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from hopilot.logging_config import get_logger
from hopilot.models import Base

logger = get_logger(__name__)


class SchemaSetup:
    """Utilities for database schema initialization and verification."""

    @staticmethod
    def create_tables(engine: Engine, models: Optional[Base] = None) -> None:
        """
        Create all tables in the database.
        
        Args:
            engine: SQLAlchemy engine
            models: Model base class (default: hopilot.models.Base)
        """
        if models is None:
            models = Base
        
        try:
            models.metadata.create_all(engine)
            logger.info(f"Schema created: {len(models.metadata.tables)} tables")
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            raise

    @staticmethod
    def drop_tables(engine: Engine, models: Optional[Base] = None) -> None:
        """
        Drop all tables from the database.
        
        Args:
            engine: SQLAlchemy engine
            models: Model base class (default: hopilot.models.Base)
        """
        if models is None:
            models = Base
        
        try:
            models.metadata.drop_all(engine)
            logger.info(f"Schema dropped: {len(models.metadata.tables)} tables removed")
        except Exception as e:
            logger.error(f"Failed to drop schema: {e}")
            raise

    @staticmethod
    def verify_schema(engine: Engine, models: Optional[Base] = None) -> dict:
        """
        Verify schema against models.
        
        Args:
            engine: SQLAlchemy engine
            models: Model base class (default: hopilot.models.Base)
        
        Returns:
            Dict with verification results
        """
        if models is None:
            models = Base
        
        inspector = inspect(engine)
        db_tables = set(inspector.get_table_names())
        model_tables = set(models.metadata.tables.keys())
        
        missing_tables = model_tables - db_tables
        orphaned_tables = db_tables - model_tables
        
        result = {
            "valid": len(missing_tables) == 0 and len(orphaned_tables) == 0,
            "model_tables": sorted(model_tables),
            "db_tables": sorted(db_tables),
            "missing_tables": sorted(missing_tables),
            "orphaned_tables": sorted(orphaned_tables),
        }
        
        if result["valid"]:
            logger.info(f"Schema verification: ✅ VALID ({len(db_tables)} tables)")
        else:
            logger.warning(f"Schema verification: ⚠️ MISMATCH")
            if missing_tables:
                logger.warning(f"  Missing tables: {missing_tables}")
            if orphaned_tables:
                logger.warning(f"  Orphaned tables: {orphaned_tables}")
        
        return result

    @staticmethod
    def get_columns(engine: Engine, table_name: str) -> dict:
        """
        Get column information for a table.
        
        Args:
            engine: SQLAlchemy engine
            table_name: Table name
        
        Returns:
            Dict of {column_name: column_type}
        """
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        return {col['name']: str(col['type']) for col in columns}

    @staticmethod
    def get_indexes(engine: Engine, table_name: str) -> list:
        """
        Get index information for a table.
        
        Args:
            engine: SQLAlchemy engine
            table_name: Table name
        
        Returns:
            List of index definitions
        """
        inspector = inspect(engine)
        return inspector.get_indexes(table_name)

    @staticmethod
    def get_foreign_keys(engine: Engine, table_name: str) -> list:
        """
        Get foreign key information for a table.
        
        Args:
            engine: SQLAlchemy engine
            table_name: Table name
        
        Returns:
            List of foreign key definitions
        """
        inspector = inspect(engine)
        return inspector.get_foreign_keys(table_name)

    @staticmethod
    def print_schema(engine: Engine) -> None:
        """
        Print complete schema information.
        
        Args:
            engine: SQLAlchemy engine
        """
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info("=" * 80)
        logger.info("DATABASE SCHEMA")
        logger.info("=" * 80)
        
        for table in sorted(tables):
            logger.info(f"\nTable: {table}")
            
            # Columns
            columns = inspector.get_columns(table)
            logger.info("  Columns:")
            for col in columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                logger.info(f"    - {col['name']}: {col['type']} ({nullable})")
            
            # Foreign Keys
            fks = inspector.get_foreign_keys(table)
            if fks:
                logger.info("  Foreign Keys:")
                for fk in fks:
                    logger.info(f"    - {fk['constrained_columns']} -> {fk['referred_table']}")
            
            # Indexes
            indexes = inspector.get_indexes(table)
            if indexes:
                logger.info("  Indexes:")
                for idx in indexes:
                    logger.info(f"    - {idx['name']}: {idx['column_names']}")
        
        logger.info("\n" + "=" * 80)


class SampleDataLoader:
    """Load sample data for testing."""

    @staticmethod
    def load_minimal_scenario(session: Session) -> dict:
        """
        Load minimal test scenario (one simulation with one matrix).
        
        Args:
            session: SQLAlchemy session
        
        Returns:
            Dict with 'simulation' and 'matrix' keys
        """
        from tests.fixtures.model_fixtures import ModelFactory
        
        factory = ModelFactory()
        
        # Create simulation
        sim = factory.create_simulation(
            session,
            name="minimal_test",
            num_hands=100,
        )
        
        # Create matrix with cells
        matrix = factory.create_hand_matrix(session, sim.id)
        
        # Create a few cells
        for i in range(5):
            factory.create_matrix_cell(
                session,
                hand_matrix_id=matrix.id,
                row=i % 13,
                col=i % 13,
                hand_name="AA",
                ev_value=1.5,
                action="raise",
            )
        
        session.commit()
        
        return {"simulation": sim, "matrix": matrix}

    @staticmethod
    def load_full_scenario(session: Session) -> dict:
        """
        Load full test scenario (complete 13x13 matrix).
        
        Args:
            session: SQLAlchemy session
        
        Returns:
            Dict with 'simulation', 'matrix', 'cells' keys
        """
        from tests.fixtures.model_fixtures import ScenarioBuilder
        
        builder = ScenarioBuilder(session)
        return builder.create_full_scenario()


class TestDatabaseManager:
    """High-level manager for test database lifecycle."""

    def __init__(self, database_url: str = "sqlite:///:memory:"):
        """
        Initialize test database manager.
        
        Args:
            database_url: Database URL (default: in-memory SQLite)
        """
        self.database_url = database_url
        self.engine: Optional[Engine] = None
        self.session: Optional[Session] = None

    def setup(self) -> None:
        """Initialize database and session."""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=False,
                connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
            )
            SchemaSetup.create_tables(self.engine)
            logger.debug(f"Test database initialized: {self.database_url}")
        except Exception as e:
            logger.error(f"Failed to setup test database: {e}")
            raise

    def teardown(self) -> None:
        """Clean up database."""
        try:
            if self.engine:
                SchemaSetup.drop_tables(self.engine)
                self.engine.dispose()
            logger.debug("Test database cleanup complete")
        except Exception as e:
            logger.error(f"Error during teardown: {e}")

    def verify(self) -> bool:
        """Verify schema integrity."""
        if not self.engine:
            return False
        
        result = SchemaSetup.verify_schema(self.engine)
        return result["valid"]

    def __enter__(self):
        """Context manager entry."""
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.teardown()
