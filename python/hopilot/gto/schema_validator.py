"""
Database schema validation tools for the poker analysis system.

Provides comprehensive validation of database schema integrity, data consistency,
and referential constraints to ensure the database remains in a valid state
during development and production use.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

from sqlalchemy import text, inspect, MetaData
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Raised when schema validation fails."""
    pass


class SchemaValidationResult:
    """Result of a schema validation operation."""

    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.metadata: Dict[str, Any] = {}

    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)

    def add_info(self, message: str):
        """Add informational message."""
        self.info.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'metadata': self.metadata
        }


class DatabaseSchemaValidator:
    """
    Comprehensive database schema validation tool.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.expected_tables = {
            'Simulations': self._get_simulation_table_spec(),
            'HandMatrices': self._get_hand_matrix_table_spec(),
            'MatrixCells': self._get_matrix_cell_table_spec(),
            'AggregatedMetrics': self._get_aggregated_metrics_table_spec(),
            'GameStates': self._get_game_state_table_spec(),
            'Players': self._get_player_table_spec(),
            'Bets': self._get_bet_table_spec(),
            'BoardCards': self._get_board_card_table_spec(),
            'Jackpots': self._get_jackpot_table_spec()
        }

    def _get_simulation_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for Simulations table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'parameters': {'type': 'TEXT', 'nullable': False},
                'created_at': {'type': 'DATETIME', 'nullable': False},
                'updated_at': {'type': 'DATETIME', 'nullable': False}
            },
            'indexes': ['created_at']
        }

    def _get_hand_matrix_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for HandMatrices table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'simulation_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'Simulations.id'},
                'created_at': {'type': 'DATETIME', 'nullable': False}
            },
            'indexes': ['simulation_id']
        }

    def _get_matrix_cell_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for MatrixCells table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'matrix_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'HandMatrices.id'},
                'hand_key': {'type': 'VARCHAR', 'nullable': False},
                'row_index': {'type': 'INTEGER', 'nullable': False},
                'col_index': {'type': 'INTEGER', 'nullable': False}
            },
            'indexes': ['matrix_id', 'hand_key']
        }

    def _get_aggregated_metrics_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for AggregatedMetrics table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'cell_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'MatrixCells.id'},
                'equity': {'type': 'FLOAT', 'nullable': True},
                'jackpot_adjusted_ev': {'type': 'FLOAT', 'nullable': True},
                'convergence_status': {'type': 'VARCHAR', 'nullable': False},
                'last_updated': {'type': 'DATETIME', 'nullable': False}
            },
            'indexes': ['cell_id', 'convergence_status']
        }

    def _get_game_state_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for GameStates table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'cell_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'MatrixCells.id'},
                'pot_size': {'type': 'FLOAT', 'nullable': False},
                'created_at': {'type': 'DATETIME', 'nullable': False}
            },
            'indexes': ['cell_id']
        }

    def _get_player_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for Players table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'game_state_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'GameStates.id'},
                'position': {'type': 'VARCHAR', 'nullable': False},
                'hole_cards': {'type': 'TEXT', 'nullable': True}
            },
            'indexes': ['game_state_id']
        }

    def _get_bet_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for Bets table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'game_state_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'GameStates.id'},
                'player_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'Players.id'},
                'amount': {'type': 'FLOAT', 'nullable': False},
                'action_type': {'type': 'VARCHAR', 'nullable': False}
            },
            'indexes': ['game_state_id', 'player_id']
        }

    def _get_board_card_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for BoardCards table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'game_state_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'GameStates.id'},
                'card': {'type': 'VARCHAR', 'nullable': False},
                'position': {'type': 'INTEGER', 'nullable': False}
            },
            'indexes': ['game_state_id']
        }

    def _get_jackpot_table_spec(self) -> Dict[str, Any]:
        """Get expected schema for Jackpots table."""
        return {
            'columns': {
                'id': {'type': 'INTEGER', 'nullable': False, 'primary_key': True},
                'game_state_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'GameStates.id'},
                'jackpot_type': {'type': 'VARCHAR', 'nullable': False},
                'payout_amount': {'type': 'FLOAT', 'nullable': False},
                'cards_used': {'type': 'TEXT', 'nullable': True}
            },
            'indexes': ['game_state_id', 'jackpot_type']
        }

    async def validate_schema_structure(self) -> SchemaValidationResult:
        """
        Validate that the database schema matches expected structure.

        Returns:
            Validation result with any structural issues
        """
        def _validate_structure() -> SchemaValidationResult:
            result = SchemaValidationResult()

            try:
                engine = self.db_connection.engine
                inspector = inspect(engine)

                # Check that all expected tables exist
                existing_tables = inspector.get_table_names()
                for expected_table in self.expected_tables:
                    if expected_table not in existing_tables:
                        result.add_error(f"Missing table: {expected_table}")
                    else:
                        result.add_info(f"Table exists: {expected_table}")

                        # Validate table structure
                        table_result = self._validate_table_structure(
                            inspector, expected_table, self.expected_tables[expected_table]
                        )
                        result.errors.extend(table_result.errors)
                        result.warnings.extend(table_result.warnings)
                        result.info.extend(table_result.info)

                # Check for unexpected tables
                expected_table_names = set(self.expected_tables.keys())
                unexpected_tables = set(existing_tables) - expected_table_names
                for table in unexpected_tables:
                    result.add_warning(f"Unexpected table found: {table}")

            except Exception as e:
                result.add_error(f"Schema validation failed: {str(e)}")

            return result

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _validate_structure)

    def _validate_table_structure(self, inspector, table_name: str,
                                 spec: Dict[str, Any]) -> SchemaValidationResult:
        """Validate structure of a specific table."""
        result = SchemaValidationResult()

        try:
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)

            # Check columns
            expected_columns = spec['columns']
            actual_columns = {col['name']: col for col in columns}

            for col_name, col_spec in expected_columns.items():
                if col_name not in actual_columns:
                    result.add_error(f"Missing column {col_name} in table {table_name}")
                else:
                    actual_col = actual_columns[col_name]
                    # Basic type checking (SQLite types are simplified)
                    expected_type = col_spec['type'].upper()
                    actual_type = actual_col['type'].upper() if actual_col['type'] else ''

                    if expected_type not in actual_type and actual_type not in expected_type:
                        result.add_warning(f"Column {col_name} type mismatch: expected {expected_type}, got {actual_type}")

                    if col_spec.get('nullable', True) != actual_col.get('nullable', True):
                        result.add_warning(f"Column {col_name} nullable mismatch")

            # Check indexes
            expected_indexes = spec.get('indexes', [])
            actual_index_names = [idx['name'] for idx in indexes if idx['name']]

            for expected_idx in expected_indexes:
                if not any(expected_idx in idx_name for idx_name in actual_index_names):
                    result.add_warning(f"Missing index on {expected_idx} for table {table_name}")

        except Exception as e:
            result.add_error(f"Table validation failed for {table_name}: {str(e)}")

        return result

    async def validate_data_integrity(self) -> SchemaValidationResult:
        """
        Validate data integrity and referential constraints.

        Returns:
            Validation result with any data integrity issues
        """
        def _validate_integrity() -> SchemaValidationResult:
            result = SchemaValidationResult()

            try:
                with self.db_connection.session() as session:
                    # Check for orphaned records
                    integrity_checks = [
                        {
                            'name': 'AggregatedMetrics without MatrixCells',
                            'query': """
                                SELECT COUNT(*) as count
                                FROM AggregatedMetrics am
                                LEFT JOIN MatrixCells mc ON am.cell_id = mc.id
                                WHERE mc.id IS NULL
                            """
                        },
                        {
                            'name': 'MatrixCells without HandMatrices',
                            'query': """
                                SELECT COUNT(*) as count
                                FROM MatrixCells mc
                                LEFT JOIN HandMatrices hm ON mc.matrix_id = hm.id
                                WHERE hm.id IS NULL
                            """
                        },
                        {
                            'name': 'HandMatrices without Simulations',
                            'query': """
                                SELECT COUNT(*) as count
                                FROM HandMatrices hm
                                LEFT JOIN Simulations s ON hm.simulation_id = s.id
                                WHERE s.id IS NULL
                            """
                        },
                        {
                            'name': 'GameStates without MatrixCells',
                            'query': """
                                SELECT COUNT(*) as count
                                FROM GameStates gs
                                LEFT JOIN MatrixCells mc ON gs.cell_id = mc.id
                                WHERE mc.id IS NULL
                            """
                        }
                    ]

                    for check in integrity_checks:
                        count = session.execute(text(check['query'])).scalar()
                        if count > 0:
                            result.add_error(f"Data integrity violation: {check['name']} - {count} orphaned records")
                        else:
                            result.add_info(f"Data integrity OK: {check['name']}")

                    # Check for invalid enum values
                    enum_checks = [
                        {
                            'name': 'Invalid convergence_status values',
                            'query': """
                                SELECT COUNT(*) as count
                                FROM AggregatedMetrics
                                WHERE convergence_status NOT IN ('CONVERGED', 'CONVERGING', 'FAILED')
                            """
                        }
                    ]

                    for check in enum_checks:
                        count = session.execute(text(check['query'])).scalar()
                        if count > 0:
                            result.add_error(f"Data validation error: {check['name']} - {count} invalid values")
                        else:
                            result.add_info(f"Data validation OK: {check['name']}")

                    # Get some basic statistics
                    stats = {}
                    for table in self.expected_tables.keys():
                        try:
                            count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                            stats[table] = count
                        except:
                            stats[table] = 0

                    result.metadata['row_counts'] = stats

            except Exception as e:
                result.add_error(f"Data integrity validation failed: {str(e)}")

            return result

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _validate_integrity)

    async def validate_performance_indexes(self) -> SchemaValidationResult:
        """
        Validate that appropriate performance indexes exist.

        Returns:
            Validation result with index recommendations
        """
        def _validate_indexes() -> SchemaValidationResult:
            result = SchemaValidationResult()

            try:
                engine = self.db_connection.engine
                inspector = inspect(engine)

                # Check for critical indexes
                critical_indexes = [
                    ('MatrixCells', ['matrix_id']),
                    ('AggregatedMetrics', ['cell_id']),
                    ('HandMatrices', ['simulation_id']),
                    ('Simulations', ['created_at']),
                    ('GameStates', ['cell_id']),
                    ('Players', ['game_state_id']),
                    ('Bets', ['game_state_id']),
                    ('BoardCards', ['game_state_id']),
                    ('Jackpots', ['game_state_id'])
                ]

                for table, columns in critical_indexes:
                    indexes = inspector.get_indexes(table)
                    has_index = False

                    for index in indexes:
                        if set(index['column_names']) == set(columns):
                            has_index = True
                            break

                    if not has_index:
                        result.add_warning(f"Missing performance index on {table}({', '.join(columns)})")
                    else:
                        result.add_info(f"Performance index exists: {table}({', '.join(columns)})")

            except Exception as e:
                result.add_error(f"Index validation failed: {str(e)}")

            return result

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _validate_indexes)

    async def run_full_validation(self) -> SchemaValidationResult:
        """
        Run complete schema validation including structure, data integrity, and performance.

        Returns:
            Comprehensive validation result
        """
        result = SchemaValidationResult()

        # Run all validation types
        validations = [
            ('schema_structure', self.validate_schema_structure()),
            ('data_integrity', self.validate_data_integrity()),
            ('performance_indexes', self.validate_performance_indexes())
        ]

        for validation_name, validation_coro in validations:
            try:
                validation_result = await validation_coro

                # Merge results
                result.errors.extend(validation_result.errors)
                result.warnings.extend(validation_result.warnings)
                result.info.extend(validation_result.info)

                if validation_name in validation_result.metadata:
                    result.metadata[validation_name] = validation_result.metadata[validation_name]

            except Exception as e:
                result.add_error(f"{validation_name} validation failed: {str(e)}")

        # Update overall validity
        result.is_valid = len(result.errors) == 0

        return result