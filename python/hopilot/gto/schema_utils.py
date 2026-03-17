"""
Schema extension utilities for the normalized poker database.

Provides utilities for extending the database schema with new analytical
features while maintaining data integrity and referential constraints.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy import text, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import Session

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class SchemaExtensionError(Exception):
    """Raised when schema extension operations fail."""
    pass


class SchemaValidator:
    """
    Validates database schema integrity and referential constraints.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)

    def close(self) -> None:
        """Close database connection and cleanup resources."""
        self.db_connection.close()

    async def validate_schema_integrity(self) -> Dict[str, Any]:
        """
        Perform comprehensive schema integrity validation.

        Returns:
            Dictionary with validation results and any issues found
        """
        def _validate_schema() -> Dict[str, Any]:
            try:
                results = {
                    'foreign_keys_valid': True,
                    'referential_integrity': True,
                    'data_consistency': True,
                    'issues': []
                }

                with self.db_connection.session_scope() as session:
                    # Check for orphaned records in AggregatedMetrics
                    orphaned_metrics = session.execute(text("""
                        SELECT COUNT(*) as orphaned_count
                        FROM AggregatedMetrics am
                        LEFT JOIN MatrixCells mc ON am.cell_id = mc.id
                        WHERE mc.id IS NULL
                    """)).scalar()

                    if orphaned_metrics > 0:
                        results['referential_integrity'] = False
                        results['issues'].append(f"Found {orphaned_metrics} orphaned AggregatedMetrics records")

                    # Check for MatrixCells without metrics
                    missing_metrics = session.execute(text("""
                        SELECT COUNT(*) as missing_count
                        FROM MatrixCells mc
                        LEFT JOIN AggregatedMetrics am ON mc.id = am.cell_id
                        WHERE am.id IS NULL
                    """)).scalar()

                    if missing_metrics > 0:
                        results['data_consistency'] = False
                        results['issues'].append(f"Found {missing_metrics} MatrixCells without metrics")

                    # Check for invalid convergence_status values
                    invalid_status = session.execute(text("""
                        SELECT COUNT(*) as invalid_count
                        FROM AggregatedMetrics
                        WHERE convergence_status NOT IN ('CONVERGED', 'CONVERGING', 'FAILED')
                    """)).scalar()

                    if invalid_status > 0:
                        results['data_consistency'] = False
                        results['issues'].append(f"Found {invalid_status} records with invalid convergence_status")

                return results

            except Exception as e:
                logger.error(f"Schema validation failed: {e}")
                return {
                    'foreign_keys_valid': False,
                    'referential_integrity': False,
                    'data_consistency': False,
                    'issues': [f"Validation failed: {str(e)}"]
                }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _validate_schema)

    async def get_table_statistics(self) -> Dict[str, Any]:
        """
        Retrieve statistics about all tables in the schema.

        Returns:
            Dictionary with table row counts and basic statistics
        """
        def _get_stats() -> Dict[str, Any]:
            try:
                stats = {}

                with self.db_connection.session_scope() as session:
                    tables = ['Simulations', 'HandMatrices', 'MatrixCells', 'AggregatedMetrics',
                             'GameStates', 'Players', 'Bets', 'BoardCards', 'Jackpots']

                    for table in tables:
                        try:
                            count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                            stats[table] = {'row_count': count}
                        except Exception as e:
                            stats[table] = {'error': str(e)}

                return stats

            except Exception as e:
                logger.error(f"Table statistics retrieval failed: {e}")
                return {'error': str(e)}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_stats)


class SchemaExtender:
    """
    Utilities for extending the database schema with new features.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)

    def close(self) -> None:
        """Close database connection and cleanup resources."""
        self.db_connection.close()

    async def add_analytical_column(self, table_name: str, column_name: str,
                                   column_type: str, default_value: Any = None) -> bool:
        """
        Add a new analytical column to an existing table.

        Args:
            table_name: Name of the table to extend
            column_name: Name of the new column
            column_type: SQL column type (INTEGER, FLOAT, VARCHAR, etc.)
            default_value: Default value for existing rows

        Returns:
            True if successful, False otherwise
        """
        def _add_column() -> bool:
            try:
                with self.db_connection.session_scope() as session:
                    # Check if column already exists
                    result = session.execute(text(f"""
                        PRAGMA table_info({table_name})
                    """)).fetchall()

                    existing_columns = [row[1] for row in result]  # Column names are in index 1

                    if column_name in existing_columns:
                        logger.info(f"Column {column_name} already exists in {table_name}")
                        return True

                    # Add the column
                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"

                    if default_value is not None:
                        if isinstance(default_value, str):
                            alter_sql += f" DEFAULT '{default_value}'"
                        else:
                            alter_sql += f" DEFAULT {default_value}"

                    session.execute(text(alter_sql))
                    session.commit()

                    logger.info(f"Successfully added column {column_name} to {table_name}")
                    return True

            except Exception as e:
                logger.error(f"Failed to add column {column_name} to {table_name}: {e}")
                return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _add_column)

    async def create_extension_table(self, table_name: str, columns: Dict[str, str],
                                    foreign_keys: Optional[Dict[str, str]] = None) -> bool:
        """
        Create a new extension table with proper foreign key relationships.

        Args:
            table_name: Name of the new table
            columns: Dictionary mapping column names to SQL types
            foreign_keys: Optional dictionary mapping column names to referenced tables

        Returns:
            True if successful, False otherwise
        """
        def _create_table() -> bool:
            try:
                with self.db_connection.session_scope() as session:
                    # Check if table already exists
                    result = session.execute(text("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name=?
                    """), (table_name,)).fetchone()

                    if result:
                        logger.info(f"Table {table_name} already exists")
                        return True

                    # Build CREATE TABLE statement
                    column_defs = []

                    # Add id column as primary key
                    column_defs.append("id INTEGER PRIMARY KEY AUTOINCREMENT")

                    # Add other columns
                    for col_name, col_type in columns.items():
                        column_defs.append(f"{col_name} {col_type}")

                    # Add foreign keys
                    if foreign_keys:
                        for col_name, ref_table in foreign_keys.items():
                            column_defs.append(f"FOREIGN KEY ({col_name}) REFERENCES {ref_table}(id)")

                    # Add timestamps
                    column_defs.extend([
                        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
                        "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                    ])

                    create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"

                    session.execute(text(create_sql))
                    session.commit()

                    logger.info(f"Successfully created extension table {table_name}")
                    return True

            except Exception as e:
                logger.error(f"Failed to create extension table {table_name}: {e}")
                return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _create_table)

    async def add_performance_index(self, table_name: str, columns: List[str]) -> bool:
        """
        Add a performance index on specified columns.

        Args:
            table_name: Name of the table to index
            columns: List of column names to include in the index

        Returns:
            True if successful, False otherwise
        """
        def _add_index() -> bool:
            try:
                with self.db_connection.session_scope() as session:
                    index_name = f"idx_{table_name}_{'_'.join(columns)}"

                    # Check if index already exists
                    result = session.execute(text("""
                        SELECT name FROM sqlite_master
                        WHERE type='index' AND name=?
                    """), (index_name,)).fetchone()

                    if result:
                        logger.info(f"Index {index_name} already exists")
                        return True

                    # Create the index
                    index_sql = f"CREATE INDEX {index_name} ON {table_name} ({', '.join(columns)})"

                    session.execute(text(index_sql))
                    session.commit()

                    logger.info(f"Successfully created index {index_name}")
                    return True

            except Exception as e:
                logger.error(f"Failed to create index on {table_name}: {e}")
                return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _add_index)