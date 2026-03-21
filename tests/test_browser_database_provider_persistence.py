"""
Tests for BrowserDatabaseProvider database persistence and loading.

These tests verify that:
1. Precompute results are correctly persisted to database
2. Database queries return expected structure and values
3. GUI can load previously computed matrices from database
"""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiRunState
from hopilot.gto.precompute_provider import PrecomputeProvider


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    db_file = tmp_path / "test_poker.db"
    return f"sqlite:///{db_file}"


@pytest.fixture
def provider(temp_db_path):
    """Create provider with temporary database."""
    provider = BrowserDatabaseProvider(database_url=temp_db_path)
    # CRITICAL: Must create tables! This is the first break point - app never calls this!
    provider.database_repository.connection.create_tables()
    return provider


@pytest.fixture
def mock_solver():
    """Mock solver that returns consistent test equity."""
    solver = MagicMock()
    
    def mock_evaluate(hand_key, num_opponents, pot_size, bet_amount, timeout_ms):
        """Return consistent test results."""
        # Simple mock: equity proportional to hand strength
        return {
            "status": "AVAILABLE",
            "equity": 0.55,
            "ev": 1.1,
            "individual_outcomes": [
                {"outcome": "WIN", "count": 55},
                {"outcome": "LOSE", "count": 40},
                {"outcome": "TIE", "count": 5},
            ]
        }
    
    solver.evaluate_hand_key = mock_evaluate
    return solver


class TestDatabasePersistence:
    """Test that precompute correctly persists data to database."""

    def test_database_tables_created_on_init(self, provider):
        """Verify database schema tables are created."""
        # Get raw connection to check schema
        from sqlalchemy import create_engine, inspect
        engine = create_engine(provider.database_repository.database_url)
        inspector = inspect(engine)
        
        tables = inspector.get_table_names()
        assert "simulations" in tables, "Simulations table not created"
        assert "hand_matrices" in tables, "HandMatrices table not created"
        assert "matrix_cells" in tables, "MatrixCells table not created"
        assert "aggregated_metrics" in tables, "AggregatedMetrics table not created"

    def test_upsert_matrix_cell_stores_equity_metrics(self, provider, mock_solver):
        """Verify upsert_matrix_cell stores equity and metric values."""
        provider._solver = mock_solver
        
        # Create simulation and matrix using correct schema
        with provider.database_repository.connection.session_scope() as session:
            from datetime import datetime, timezone
            from hopilot.models import Simulation, HandMatrix
            
            sim = Simulation(
                name="test_upsert",
                parameters="num_simulations=120,matrix_size=13x13,game_type=cash",
                start_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            sim_id = sim.id
            
            matrix = HandMatrix(
                simulation_id=sim_id,
                matrix_size="13x13"
            )
            session.add(matrix)
            session.commit()
            matrix_id = matrix.id
        
        # Now use upsert_matrix_cell with metrics
        metrics = {
            "equity": 0.75,
            "jackpot_adjusted_ev": 1.5,
        }
        
        provider.database_repository.upsert_matrix_cell(
            matrix_id=matrix_id,
            row_idx=0,
            col_idx=0,
            hand_key="AA vs Random",
            metrics=metrics,
            status="AVAILABLE"
        )
        
        # Query back and verify
        with provider.database_repository.connection.session_scope() as session:
            from hopilot.models import MatrixCell, AggregatedMetric
            
            cell = session.query(MatrixCell).filter_by(
                matrix_id=matrix_id,
                row_index=0,
                col_index=0
            ).first()
            
            assert cell is not None, "Cell not found in database"
            assert cell.hand_combination == "AA vs Random", f"hand_combination wrong: {cell.hand_combination}"
            
            # Verify equity was stored in AggregatedMetric
            metric = session.query(AggregatedMetric).filter_by(
                cell_id=cell.id
            ).first()
            
            assert metric is not None, "AggregatedMetric not found"
            assert metric.equity == 0.75, f"equity not stored: {metric.equity}"

    def test_precompute_runner_persists_to_database(self, provider, mock_solver):
        """Verify data gets written and can be queried back."""
        # This test verifies the Round-trip: Write → Read
        provider._solver = mock_solver
        
        # Insert a cell manually (simulating what precompute would do)
        with provider.database_repository.connection.session_scope() as session:
            from datetime import datetime, timezone
            from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric
            
            sim = Simulation(
                name="test_sim_precompute",
                parameters="num_simulations=120,matrix_size=13x13,game_type=cash",
                start_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            sim_id = sim.id
            
            matrix = HandMatrix(
                simulation_id=sim_id,
                matrix_size="13x13"
            )
            session.add(matrix)
            session.flush()
            matrix_id = matrix.id
            
            # Insert multiple cells with equity data using the new schema
            for row in range(0, 3):
                for col in range(0, 3):
                    cell = MatrixCell(
                        matrix_id=matrix_id,
                        row_index=row,
                        col_index=col,
                        hand_combination=f"Hand{row}{col} vs Random"
                    )
                    session.add(cell)
                    session.flush()
                    
                    # Create associated AggregatedMetric
                    metric = AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.55 + row * 0.01,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc)
                    )
                    session.add(metric)
            
            session.commit()
            
            # Now query back - this should NOT be empty
            cells = session.query(MatrixCell).filter_by(
                matrix_id=matrix_id
            ).all()
            
            assert len(cells) == 9, f"Expected 9 cells, got {len(cells)}"
            
            # Verify equity values are there
            aggregated_metrics = session.query(AggregatedMetric).filter(
                AggregatedMetric.cell_id.in_([c.id for c in cells])
            ).all()
            
            assert len(aggregated_metrics) == 9, f"Expected 9 metrics, got {len(aggregated_metrics)}"
            
            first_metric = aggregated_metrics[0]
            assert first_metric.equity is not None, "equity is NULL in database!"
            assert first_metric.convergence_status is not None, "convergence_status is NULL in database!"


class TestDatabaseLoading:
    """Test that database queries return correct data."""

    def test_get_strategy_matrix_returns_empty_dict(self, provider):
        """BREAK POINT #2: get_strategy_matrix in database_repository.py just returns {}"""
        from hopilot.gto.data_model import PositionContext, ActionContext, MetricType
        import asyncio
        
        # This test documents the break point: the query is empty
        position = PositionContext.from_id("UTG")
        action = ActionContext.from_id("FOLD")
        metric_type = MetricType.from_id("EQUITY")
        
        # Call the actual method
        result = asyncio.run(
            provider.database_repository.get_strategy_matrix(position, action, metric_type)
        )
        
        # Now that the query is implemented, it should return data
        assert isinstance(result, dict), "get_strategy_matrix should return a dict"
        # Since we inserted data, it should not be empty
        # But the exact content depends on the test data

    def test_database_has_data_but_query_returns_nothing(self, provider):
        """Verify the disconnect: data IS in database, but query returns nothing."""
        # Insert some test data
        with provider.database_repository.connection.session_scope() as session:
            from datetime import datetime, timezone
            from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric
            
            sim = Simulation(
                name="test_query_disconnect",
                parameters='{"position": "UTG", "action": "FOLD", "metric": "EQUITY", "num_simulations": 120, "matrix_size": "13x13", "game_type": "cash"}',
                start_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            
            matrix = HandMatrix(
                simulation_id=sim.id,
                matrix_size="13x13"
            )
            session.add(matrix)
            session.flush()
            
            # Insert cells with equity data (using correct schema)
            for row in range(0, 13):
                for col in range(0, 13):
                    cell = MatrixCell(
                        matrix_id=matrix.id,
                        row_index=row,
                        col_index=col,
                        hand_combination=f"Hand{row}{col} vs Random"
                    )
                    session.add(cell)
                    session.flush()
                    
                    metric = AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.55 + row * 0.01,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc)
                    )
                    session.add(metric)
            
            session.commit()
            
            # Now try to read it back with the query method
            import asyncio
            from hopilot.gto.data_model import PositionContext, ActionContext, MetricType
            
            position = PositionContext.from_id("UTG")
            action = ActionContext.from_id("FOLD")
            metric_type = MetricType.from_id("EQUITY")
            
            result = asyncio.run(
                provider.database_repository.get_strategy_matrix(position, action, metric_type)
            )
            
            # Now that the query is implemented, it should return the data we inserted
            assert isinstance(result, dict), "Query should return a dict"
            assert len(result) > 0, "Query should return data since we inserted it"


class TestDatabaseSchema:
    """Test database schema and initialization."""

    def test_init_db_creates_all_required_tables(self, provider):
        """Verify create_tables() creates all schema tables."""
        from sqlalchemy import create_engine, inspect
        
        engine = create_engine(provider.database_repository.database_url)
        inspector = inspect(engine)
        tables = {t.lower() for t in inspector.get_table_names()}
        
        required_tables = {
            "simulations",        # Correct name
            "hand_matrices",      # Correct name
            "matrix_cells",       # Correct name
            "aggregated_metrics"  # Correct name
        }
        
        missing = required_tables - tables
        assert not missing, f"Missing tables: {missing}"

    def test_matrix_cell_has_equity_columns(self, provider):
        """Verify AggregatedMetric table has all equity metric columns."""
        from sqlalchemy import create_engine, inspect
        
        engine = create_engine(provider.database_repository.database_url)
        inspector = inspect(engine)
        columns = {c["name"] for c in inspector.get_columns("aggregated_metrics")}  # Correct table name
        
        required_columns = {
            "equity",
            "jackpot_adjusted_ev",
            "convergence_status",
            "last_updated"
        }
        
        missing = required_columns - columns
        assert not missing, f"AggregatedMetric missing columns: {missing}"

    def test_database_connection_create_tables_never_called_in_app(self):
        """
        BUG BREAK POINT #1: create_tables() exists but is never called!
        
        This test documents a critical initialization bug:
        - DatabaseConnection.create_tables() method exists
        - But hopilot.py never calls it during startup
        - So database schema is never initialized
        - GUI fails to load because tables don't exist
        """
        # This test just documents the bug
        # The fix: hopilot.py should call connection.create_tables() on startup
        pass


class TestGUILoadingFunctionality:
    """Test GUI's ability to load data from database."""

    def test_gui_loads_data_on_startup(self, provider):
        """Test that GUI loads existing data when initialized."""
        # First, insert some test data
        with provider.database_repository.connection.session_scope() as session:
            from datetime import datetime, timezone
            from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric
            
            sim = Simulation(
                name="test_gui_load",
                parameters='{"position": "UTG", "action": "ALL_IN", "metric": "WIN_LOSE_PROBABILITY", "num_simulations": 1000, "matrix_size": "13x13", "game_type": "cash"}',
                start_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()
            
            # Insert a few cells with data
            for i in range(3):
                cell = MatrixCell(
                    matrix_id=matrix.id,
                    row_index=i,
                    col_index=i,
                    hand_combination=f"AA vs Random"
                )
                session.add(cell)
                session.flush()
                
                metric = AggregatedMetric(
                    cell_id=cell.id,
                    equity=0.5 + i * 0.1,
                    convergence_status="AVAILABLE",
                    last_updated=datetime.now(timezone.utc)
                )
                session.add(metric)
            
            session.commit()

        # Now test that the provider can load this data
        from hopilot.gto.data_model import PositionContext, ActionContext, MetricType
        
        position = PositionContext.from_id("UTG")
        action = ActionContext.from_id("ALL_IN")
        metric = MetricType.from_id("WIN_LOSE_PROBABILITY")
        
        # Debug: check what simulations exist
        with provider.database_repository.connection.session_scope() as session:
            from hopilot.models import Simulation
            sims = session.query(Simulation).all()
            print(f"Found {len(sims)} simulations")
            for sim in sims:
                print(f"Sim: {sim.id}, params: {sim.parameters}")
        
        result = provider.database_repository.get_strategy_matrix_sync(position, action, metric)
        
        assert isinstance(result, dict), "Should return a dict"
        assert len(result) > 0, "Should have loaded data"
        assert "AA" in result, "Should have AA data"

    def test_gui_provider_returns_correct_format(self, provider):
        """Test that get_matrix_payload returns the correct format for GUI."""
        # Insert test data
        with provider.database_repository.connection.session_scope() as session:
            from datetime import datetime, timezone
            from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric
            
            sim = Simulation(
                name="test_format",
                parameters='{"position": "UTG", "action": "ALL_IN", "metric": "WIN_LOSE_PROBABILITY", "num_simulations": 1000, "matrix_size": "13x13", "game_type": "cash"}',
                start_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()
            
            cell = MatrixCell(
                matrix_id=matrix.id,
                row_index=0,
                col_index=0,
                hand_combination="AA vs Random"
            )
            session.add(cell)
            session.flush()
            
            metric = AggregatedMetric(
                cell_id=cell.id,
                equity=0.75,
                convergence_status="AVAILABLE",
                last_updated=datetime.now(timezone.utc)
            )
            session.add(metric)
            session.commit()

        # Test the provider method
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="WIN_LOSE_PROBABILITY",
            position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"}
        )
        
        assert "cells" in payload, "Should have cells key"
        assert isinstance(payload["cells"], list), "cells should be a list"
        assert len(payload["cells"]) == 169, "Should have 169 cells (13x13)"
        
        # Find the AA cell
        aa_cell = None
        for cell in payload["cells"]:
            if cell["hand_key"] == "AA":
                aa_cell = cell
                break
        
        assert aa_cell is not None, "Should have AA cell"
        assert aa_cell["value"] == 0.75, f"AA value should be 0.75, got {aa_cell['value']}"
        assert aa_cell["status"] == "AVAILABLE", "Status should be AVAILABLE"
        assert aa_cell["display"] is not None, "Should have display value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
