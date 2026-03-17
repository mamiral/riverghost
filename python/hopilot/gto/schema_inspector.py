"""
Developer tools for database schema inspection and analysis.

Provides comprehensive tools for developers to inspect, analyze, and understand
the database schema structure, relationships, and data patterns.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from collections import defaultdict

from sqlalchemy import text, inspect, MetaData, Table, Column
from sqlalchemy.orm import Session

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class SchemaInspector:
    """
    Comprehensive database schema inspection and analysis tool.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)

    async def get_schema_overview(self) -> Dict[str, Any]:
        """
        Get a comprehensive overview of the database schema.

        Returns:
            Dictionary containing schema metadata and statistics
        """
        def _get_overview() -> Dict[str, Any]:
            try:
                engine = self.db_connection.engine
                inspector = inspect(engine)

                tables = inspector.get_table_names()
                schema_info = {
                    'database_type': 'SQLite',
                    'table_count': len(tables),
                    'tables': {},
                    'relationships': {},
                    'indexes': {},
                    'constraints': {}
                }

                for table_name in tables:
                    # Get table details
                    columns = inspector.get_columns(table_name)
                    indexes = inspector.get_indexes(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    primary_keys = inspector.get_pk_constraint(table_name)

                    schema_info['tables'][table_name] = {
                        'column_count': len(columns),
                        'columns': [
                            {
                                'name': col['name'],
                                'type': str(col['type']),
                                'nullable': col.get('nullable', True),
                                'default': col.get('default'),
                                'primary_key': col['name'] in primary_keys.get('constrained_columns', [])
                            }
                            for col in columns
                        ],
                        'primary_key': primary_keys.get('constrained_columns', []),
                        'foreign_keys': foreign_keys,
                        'indexes': [
                            {
                                'name': idx.get('name'),
                                'columns': idx.get('column_names', []),
                                'unique': idx.get('unique', False)
                            }
                            for idx in indexes
                        ]
                    }

                    # Collect relationship information
                    for fk in foreign_keys:
                        referred_table = fk.get('referred_table')
                        if referred_table:
                            if referred_table not in schema_info['relationships']:
                                schema_info['relationships'][referred_table] = []
                            schema_info['relationships'][referred_table].append({
                                'from_table': table_name,
                                'from_columns': fk.get('constrained_columns', []),
                                'to_table': referred_table,
                                'to_columns': fk.get('referred_columns', [])
                            })

                return schema_info

            except Exception as e:
                logger.error(f"Schema overview generation failed: {e}")
                return {'error': str(e)}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_overview)

    async def analyze_table_relationships(self) -> Dict[str, Any]:
        """
        Analyze and visualize table relationships in the schema.

        Returns:
            Dictionary containing relationship analysis and dependency chains
        """
        def _analyze_relationships() -> Dict[str, Any]:
            try:
                schema_overview = asyncio.run(self.get_schema_overview())
                if 'error' in schema_overview:
                    return schema_overview

                relationships = schema_overview.get('relationships', {})
                tables = schema_overview.get('tables', {})

                # Build dependency graph
                dependency_graph = defaultdict(list)
                reverse_dependencies = defaultdict(list)

                for target_table, refs in relationships.items():
                    for ref in refs:
                        source_table = ref['from_table']
                        dependency_graph[source_table].append(target_table)
                        reverse_dependencies[target_table].append(source_table)

                # Find root tables (no dependencies)
                all_tables = set(tables.keys())
                dependent_tables = set(reverse_dependencies.keys())
                root_tables = all_tables - dependent_tables

                # Find leaf tables (no dependents)
                tables_with_dependents = set(dependency_graph.keys())
                leaf_tables = all_tables - tables_with_dependents

                return {
                    'dependency_graph': dict(dependency_graph),
                    'reverse_dependencies': dict(reverse_dependencies),
                    'root_tables': list(root_tables),
                    'leaf_tables': list(leaf_tables),
                    'relationship_summary': {
                        'total_relationships': sum(len(refs) for refs in relationships.values()),
                        'tables_with_relationships': len(relationships),
                        'isolated_tables': len(all_tables - set(relationships.keys()) - dependent_tables)
                    }
                }

            except Exception as e:
                logger.error(f"Relationship analysis failed: {e}")
                return {'error': str(e)}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _analyze_relationships)

    async def get_data_profile(self, table_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """
        Generate a data profile for a specific table.

        Args:
            table_name: Name of the table to profile
            sample_size: Number of rows to sample for analysis

        Returns:
            Dictionary containing data profiling information
        """
        def _profile_table() -> Dict[str, Any]:
            try:
                with self.db_connection.session() as session:
                    # Get total row count
                    total_count = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

                    # Get sample data for analysis
                    sample_query = text(f"SELECT * FROM {table_name} LIMIT {sample_size}")
                    sample_rows = session.execute(sample_query).fetchall()

                    if not sample_rows:
                        return {
                            'table_name': table_name,
                            'total_rows': total_count,
                            'sample_size': 0,
                            'columns': []
                        }

                    # Analyze each column
                    columns_info = []
                    column_names = sample_rows[0]._mapping.keys()

                    for col_name in column_names:
                        values = [getattr(row, col_name) for row in sample_rows]
                        non_null_values = [v for v in values if v is not None]

                        column_info = {
                            'name': col_name,
                            'total_count': len(values),
                            'null_count': len(values) - len(non_null_values),
                            'null_percentage': (len(values) - len(non_null_values)) / len(values) * 100 if values else 0,
                            'unique_count': len(set(non_null_values)),
                            'data_type': type(non_null_values[0]).__name__ if non_null_values else 'unknown'
                        }

                        # Add type-specific statistics
                        if non_null_values and isinstance(non_null_values[0], (int, float)):
                            column_info.update({
                                'min_value': min(non_null_values),
                                'max_value': max(non_null_values),
                                'avg_value': sum(non_null_values) / len(non_null_values)
                            })
                        elif non_null_values and isinstance(non_null_values[0], str):
                            lengths = [len(str(v)) for v in non_null_values]
                            column_info.update({
                                'min_length': min(lengths),
                                'max_length': max(lengths),
                                'avg_length': sum(lengths) / len(lengths)
                            })

                        columns_info.append(column_info)

                    return {
                        'table_name': table_name,
                        'total_rows': total_count,
                        'sample_size': len(sample_rows),
                        'columns': columns_info
                    }

            except Exception as e:
                logger.error(f"Data profiling failed for {table_name}: {e}")
                return {'error': str(e), 'table_name': table_name}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _profile_table)

    async def generate_schema_documentation(self) -> str:
        """
        Generate human-readable schema documentation.

        Returns:
            Markdown-formatted schema documentation
        """
        def _generate_docs() -> str:
            try:
                overview = asyncio.run(self.get_schema_overview())
                relationships = asyncio.run(self.analyze_table_relationships())

                if 'error' in overview or 'error' in relationships:
                    return "# Schema Documentation Error\n\nUnable to generate documentation due to errors in schema analysis."

                docs = ["# Database Schema Documentation\n"]
                docs.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

                # Overview section
                docs.append("## Schema Overview\n")
                docs.append(f"- **Database Type**: {overview.get('database_type', 'Unknown')}")
                docs.append(f"- **Total Tables**: {overview.get('table_count', 0)}")
                docs.append("")

                # Tables section
                docs.append("## Tables\n")
                for table_name, table_info in overview.get('tables', {}).items():
                    docs.append(f"### {table_name}\n")
                    docs.append(f"- **Columns**: {table_info.get('column_count', 0)}")
                    docs.append(f"- **Primary Key**: {', '.join(table_info.get('primary_key', []))}")
                    docs.append("")

                    # Columns
                    docs.append("#### Columns\n")
                    docs.append("| Column | Type | Nullable | Default | Primary Key |")
                    docs.append("|--------|------|----------|---------|-------------|")

                    for col in table_info.get('columns', []):
                        pk_marker = "✓" if col.get('primary_key') else ""
                        docs.append(f"| {col['name']} | {col['type']} | {col.get('nullable', True)} | {col.get('default', '')} | {pk_marker} |")

                    docs.append("")

                    # Foreign Keys
                    if table_info.get('foreign_keys'):
                        docs.append("#### Foreign Keys\n")
                        for fk in table_info['foreign_keys']:
                            constrained = ', '.join(fk.get('constrained_columns', []))
                            referred = ', '.join(fk.get('referred_columns', []))
                            docs.append(f"- {constrained} → {fk.get('referred_table', '')}.{referred}")
                        docs.append("")

                    # Indexes
                    if table_info.get('indexes'):
                        docs.append("#### Indexes\n")
                        for idx in table_info['indexes']:
                            unique_marker = " (unique)" if idx.get('unique') else ""
                            columns = ', '.join(idx.get('column_names', []))
                            docs.append(f"- {idx.get('name', 'unnamed')}: {columns}{unique_marker}")
                        docs.append("")

                # Relationships section
                docs.append("## Table Relationships\n")
                docs.append(f"- **Total Relationships**: {relationships.get('relationship_summary', {}).get('total_relationships', 0)}")
                docs.append(f"- **Tables with Relationships**: {relationships.get('relationship_summary', {}).get('tables_with_relationships', 0)}")
                docs.append(f"- **Isolated Tables**: {relationships.get('relationship_summary', {}).get('isolated_tables', 0)}")
                docs.append("")

                docs.append("### Dependency Graph\n")
                for source, targets in relationships.get('dependency_graph', {}).items():
                    docs.append(f"- **{source}** depends on: {', '.join(targets)}")
                docs.append("")

                docs.append("### Root Tables (no dependencies)\n")
                for table in relationships.get('root_tables', []):
                    docs.append(f"- {table}")
                docs.append("")

                docs.append("### Leaf Tables (no dependents)\n")
                for table in relationships.get('leaf_tables', []):
                    docs.append(f"- {table}")
                docs.append("")

                return "\n".join(docs)

            except Exception as e:
                logger.error(f"Documentation generation failed: {e}")
                return f"# Schema Documentation Error\n\n{str(e)}"

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _generate_docs)

    async def find_data_anomalies(self) -> Dict[str, Any]:
        """
        Find potential data anomalies and inconsistencies in the database.

        Returns:
            Dictionary containing identified anomalies
        """
        def _find_anomalies() -> Dict[str, Any]:
            try:
                anomalies = {
                    'orphaned_records': {},
                    'invalid_references': {},
                    'data_type_issues': {},
                    'constraint_violations': {}
                }

                with self.db_connection.session() as session:
                    # Check for orphaned AggregatedMetrics
                    orphaned_metrics = session.execute(text("""
                        SELECT COUNT(*) as count
                        FROM AggregatedMetrics am
                        LEFT JOIN MatrixCells mc ON am.cell_id = mc.id
                        WHERE mc.id IS NULL
                    """)).scalar()

                    if orphaned_metrics > 0:
                        anomalies['orphaned_records']['aggregated_metrics'] = orphaned_metrics

                    # Check for invalid convergence status values
                    invalid_status = session.execute(text("""
                        SELECT convergence_status, COUNT(*) as count
                        FROM AggregatedMetrics
                        WHERE convergence_status NOT IN ('CONVERGED', 'CONVERGING', 'FAILED')
                        GROUP BY convergence_status
                    """)).fetchall()

                    if invalid_status:
                        anomalies['data_type_issues']['invalid_convergence_status'] = [
                            {'status': row.convergence_status, 'count': row.count}
                            for row in invalid_status
                        ]

                    # Check for negative equity values (should be 0-1 range)
                    negative_equity = session.execute(text("""
                        SELECT COUNT(*) as count
                        FROM AggregatedMetrics
                        WHERE equity < 0 OR equity > 1
                    """)).scalar()

                    if negative_equity > 0:
                        anomalies['data_type_issues']['out_of_range_equity'] = negative_equity

                    # Check for duplicate hand keys in same matrix
                    duplicate_hands = session.execute(text("""
                        SELECT matrix_id, hand_key, COUNT(*) as count
                        FROM MatrixCells
                        GROUP BY matrix_id, hand_key
                        HAVING COUNT(*) > 1
                        LIMIT 10
                    """)).fetchall()

                    if duplicate_hands:
                        anomalies['constraint_violations']['duplicate_hand_keys'] = [
                            {'matrix_id': row.matrix_id, 'hand_key': row.hand_key, 'count': row.count}
                            for row in duplicate_hands
                        ]

                return anomalies

            except Exception as e:
                logger.error(f"Anomaly detection failed: {e}")
                return {'error': str(e)}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _find_anomalies)

    async def export_schema_as_sql(self) -> str:
        """
        Export the current schema as SQL DDL statements.

        Returns:
            SQL DDL statements for recreating the schema
        """
        def _export_sql() -> str:
            try:
                overview = asyncio.run(self.get_schema_overview())
                if 'error' in overview:
                    return f"-- Schema export failed: {overview['error']}"

                sql_statements = ["-- Database Schema Export"]
                sql_statements.append(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                sql_statements.append("")

                for table_name, table_info in overview.get('tables', {}).items():
                    # CREATE TABLE statement
                    sql_statements.append(f"-- Table: {table_name}")
                    columns_sql = []

                    for col in table_info.get('columns', []):
                        col_sql = f"    {col['name']} {col['type']}"
                        if not col.get('nullable', True):
                            col_sql += " NOT NULL"
                        if col.get('default'):
                            col_sql += f" DEFAULT {col['default']}"
                        columns_sql.append(col_sql)

                    # Add primary key
                    if table_info.get('primary_key'):
                        pk_cols = ', '.join(table_info['primary_key'])
                        columns_sql.append(f"    PRIMARY KEY ({pk_cols})")

                    # Add foreign keys
                    for fk in table_info.get('foreign_keys', []):
                        constrained = ', '.join(fk.get('constrained_columns', []))
                        referred_table = fk.get('referred_table', '')
                        referred = ', '.join(fk.get('referred_columns', []))
                        columns_sql.append(f"    FOREIGN KEY ({constrained}) REFERENCES {referred_table} ({referred})")

                    create_sql = f"CREATE TABLE {table_name} (\n" + ",\n".join(columns_sql) + "\n);"
                    sql_statements.append(create_sql)
                    sql_statements.append("")

                    # CREATE INDEX statements
                    for idx in table_info.get('indexes', []):
                        idx_name = idx.get('name', f"idx_{table_name}_{'_'.join(idx.get('column_names', []))}")
                        columns = ', '.join(idx.get('column_names', []))
                        unique = "UNIQUE " if idx.get('unique') else ""
                        index_sql = f"CREATE {unique}INDEX {idx_name} ON {table_name} ({columns});"
                        sql_statements.append(index_sql)

                    sql_statements.append("")

                return "\n".join(sql_statements)

            except Exception as e:
                logger.error(f"Schema SQL export failed: {e}")
                return f"-- Schema export failed: {str(e)}"

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _export_sql)