"""
Database schema creation and migration utilities.

Provides utilities for creating, dropping, and migrating database schemas.
"""

import os
from typing import Any, Dict, Optional

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger
from hopilot.models.base import Base

logger = get_logger(__name__)

try:
    from alembic import command
    from alembic.config import Config
    from alembic.environment import EnvironmentContext
    from alembic.script import ScriptDirectory
    ALEMBIC_AVAILABLE = True
except ImportError:
    ALEMBIC_AVAILABLE = False
    logger.warning("Alembic not available - migration features disabled")

from sqlalchemy import create_engine, text

logger = get_logger(__name__)


class SchemaManager:
    """
    Manages database schema creation, migration, and utilities.
    """

    def __init__(self, database_url: str):
        """
        Initialize schema manager.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        self.connection = DatabaseConnection(database_url)

    def create_schema(self) -> None:
        """
        Create all database tables from SQLAlchemy models.
        """
        logger.info("Creating database schema...")
        self.connection.create_tables()

        # Enable foreign key constraints for SQLite
        if self.database_url.startswith("sqlite"):
            self._enable_sqlite_foreign_keys()

        # Create indexes for performance
        self._create_indexes()

        # Create views for efficient querying
        self._create_views()

        logger.info("Database schema created successfully")

    def drop_schema(self) -> None:
        """
        Drop all database tables.
        """
        logger.warning("Dropping database schema...")
        self.connection.drop_tables()
        logger.info("Database schema dropped")

    def reset_schema(self) -> None:
        """
        Reset database schema (drop and recreate).
        """
        logger.info("Resetting database schema...")
        self.drop_schema()
        self.create_schema()
        logger.info("Database schema reset complete")

    def _enable_sqlite_foreign_keys(self) -> None:
        """
        Enable foreign key constraints and WAL mode in SQLite.
        """
        with self.connection.session_scope() as session:
            session.execute(text("PRAGMA foreign_keys = ON;"))
            session.execute(text("PRAGMA journal_mode = WAL;"))
            session.execute(text("PRAGMA synchronous = NORMAL;"))
            logger.debug("SQLite foreign keys and WAL mode enabled")

    def _create_indexes(self) -> None:
        """
        Create database indexes for query performance.
        """
        with self.connection.session_scope() as session:
            # Index on GameStates.cell_id for convergence queries
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_game_states_cell_id
                ON game_states (cell_id);
            """))

            # Index on GameStates.timestamp for temporal queries
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_game_states_timestamp
                ON game_states (timestamp);
            """))

            # Index on MatrixCells for matrix navigation
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_matrix_cells_matrix_id_row_col
                ON matrix_cells (matrix_id, row_index, col_index);
            """))

            # Index on Jackpots for aggregation queries
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_jackpots_type
                ON jackpots (jackpot_type);
            """))

            # Indexes to support view performance (index underlying tables)
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_simulations_parameters_position
                ON simulations (json_extract(parameters, '$.position'));
            """))

            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_simulations_parameters_action
                ON simulations (json_extract(parameters, '$.action'));
            """))

            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_aggregated_metrics_convergence
                ON aggregated_metrics (convergence_status);
            """))

            logger.debug("Database indexes created")

    def _create_views(self) -> None:
        """
        Create database views for efficient querying.
        """
        with self.connection.session_scope() as session:
            # View for position-based filtering
            session.execute(text("""
                CREATE VIEW IF NOT EXISTS simulation_positions AS
                SELECT
                    id,
                    name,
                    json_extract(parameters, '$.position') as position,
                    json_extract(parameters, '$.action') as action,
                    start_timestamp,
                    end_timestamp
                FROM simulations
                WHERE json_extract(parameters, '$.position') IS NOT NULL;
            """))

            # View for matrix data with position context
            session.execute(text("""
                CREATE VIEW IF NOT EXISTS matrix_data_with_context AS
                SELECT
                    am.cell_id,
                    mc.matrix_id,
                    mc.row_index,
                    mc.col_index,
                    mc.hand_combination,
                    am.equity,
                    am.jackpot_adjusted_ev,
                    am.convergence_status,
                    sp.position,
                    sp.action
                FROM aggregated_metrics am
                JOIN matrix_cells mc ON am.cell_id = mc.id
                JOIN hand_matrices hm ON mc.matrix_id = hm.id
                JOIN simulation_positions sp ON hm.simulation_id = sp.id
                WHERE am.convergence_status = 'CONVERGED';
            """))

            logger.debug("Database views created")

    def validate_schema(self) -> bool:
        """
        Validate that the database schema matches the models.

        Returns:
            True if schema is valid, False otherwise
        """
        try:
            # Try to create a test session
            with self.connection.session_scope() as session:
                # Check if all tables exist
                for table in Base.metadata.tables.values():
                    session.execute(text(f"SELECT 1 FROM {table.name} LIMIT 1"))
                logger.info("Database schema validation passed")
                return True
        except Exception as e:
            logger.error(f"Database schema validation failed: {e}")
            return False

    def get_schema_info(self) -> dict:
        """
        Get information about the current database schema.

        Returns:
            Dictionary with schema information
        """
        info = {
            "tables": [],
            "indexes": [],
            "constraints": []
        }

        with self.connection.session_scope() as session:
            # Get table information
            if self.database_url.startswith("sqlite"):
                result = session.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name;
                """))
                info["tables"] = [row[0] for row in result]

                # Get index information
                result = session.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name;
                """))
                info["indexes"] = [row[0] for row in result]

        return info

    def add_table(self, table_name: str, columns: Dict[str, Any], 
                  foreign_keys: Optional[Dict[str, str]] = None) -> None:
        """
        Add a new table to the database schema dynamically.

        Args:
            table_name: Name of the new table
            columns: Dictionary mapping column names to SQLAlchemy column definitions
            foreign_keys: Optional dictionary mapping column names to foreign key references
        """
        with self.connection.session_scope() as session:
            # Build CREATE TABLE statement
            column_defs = []
            
            for col_name, col_def in columns.items():
                col_sql = f"{col_name} {col_def}"
                column_defs.append(col_sql)
            
            # Add foreign key constraints
            if foreign_keys:
                for col_name, ref_table in foreign_keys.items():
                    fk_sql = f"FOREIGN KEY ({col_name}) REFERENCES {ref_table}(id)"
                    column_defs.append(fk_sql)
            
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    {', '.join(column_defs)}
                );
            """
            
            session.execute(text(create_sql))
            logger.info(f"Added table '{table_name}' to schema")

    def add_column(self, table_name: str, column_name: str, 
                   column_def: str, foreign_key: Optional[str] = None) -> None:
        """
        Add a new column to an existing table.

        Args:
            table_name: Name of the table to modify
            column_name: Name of the new column
            column_def: SQL column definition (e.g., "VARCHAR(255) NOT NULL")
            foreign_key: Optional foreign key reference (e.g., "other_table(id)")
        """
        with self.connection.session_scope() as session:
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
            session.execute(text(alter_sql))
            
            if foreign_key:
                # For SQLite, we need to recreate the table to add foreign keys
                # This is a simplified version - production code would need more robust migration
                logger.warning(f"Foreign key constraints require table recreation for column {column_name}")
            
            logger.info(f"Added column '{column_name}' to table '{table_name}'")

    def create_index(self, table_name: str, column_name: str, 
                     index_name: Optional[str] = None, unique: bool = False) -> None:
        """
        Create an index on a table column for performance.

        Args:
            table_name: Name of the table
            column_name: Name of the column to index
            index_name: Optional custom index name
            unique: Whether the index should enforce uniqueness
        """
        if not index_name:
            index_name = f"ix_{table_name}_{column_name}"
        
        unique_str = "UNIQUE" if unique else ""
        
        with self.connection.session_scope() as session:
            index_sql = f"""
                CREATE {unique_str} INDEX IF NOT EXISTS {index_name}
                ON {table_name} ({column_name});
            """
            session.execute(text(index_sql))
            logger.info(f"Created index '{index_name}' on {table_name}.{column_name}")


def init_schema(database_url: str) -> SchemaManager:
    """
    Initialize schema manager for the given database.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        SchemaManager instance
    """
    return SchemaManager(database_url)


# Alembic migration support (for future use)
def create_alembic_config(database_url: str, script_location: str = "migrations"):
    """
    Create Alembic configuration for migrations.

    Args:
        database_url: SQLAlchemy database URL
        script_location: Path to migration scripts

    Returns:
        Alembic Config object
    """
    if not ALEMBIC_AVAILABLE:
        raise RuntimeError("Alembic not available. Install with: pip install alembic")
    
    config = Config()
    config.set_main_option("script_location", script_location)
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def run_migration(database_url: str, revision: str = "head") -> None:
    """
    Run database migration to specified revision.

    Args:
        database_url: SQLAlchemy database URL
        revision: Migration revision to apply
    """
    if not ALEMBIC_AVAILABLE:
        raise RuntimeError("Alembic not available. Install with: pip install alembic")
    
    config = create_alembic_config(database_url)
    command.upgrade(config, revision)
    logger.info(f"Database migrated to revision: {revision}")