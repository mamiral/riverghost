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
                parameters={
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                },
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
                parameters={
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                },
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

    def test_get_strategy_matrix_returns_matrix_data(self, provider):
        """Verify get_strategy_matrix returns persisted matrix data from the database."""
        from hopilot.gto.data_model import PositionContext, ActionContext, MetricType
        import asyncio
        
        # Seed test data so get_strategy_matrix has a matching scenario to query.
        from datetime import datetime, timezone
        from hopilot.gto.aof_hand_matrix import build_matrix_keys
        from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric

        with provider.database_repository.connection.session_scope() as session:
            sim = Simulation(
                name="test_strategy_matrix",
                parameters={
                    "position": "UTG",
                    "action": "FOLD",
                    "metric": "EQUITY",
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                },
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()
            keys = build_matrix_keys()
            for row in range(13):
                for col in range(13):
                    cell = MatrixCell(
                        matrix_id=matrix.id,
                        row_index=row,
                        col_index=col,
                        hand_combination=keys[row][col]
                    )
                    session.add(cell)
                    session.flush()
                    session.add(AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.55,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc)
                    ))
            session.commit()

        position = PositionContext.from_id("UTG")
        action = ActionContext.from_id("FOLD")
        metric_type = MetricType.from_id("EQUITY")
        
        # Call the actual method
        result = asyncio.run(
            provider.database_repository.get_strategy_matrix(position, action, metric_type)
        )
        
        # Now that the query is implemented, it should return data
        assert isinstance(result, dict), "get_strategy_matrix should return a dict"
        assert len(result) > 0, "Query should return data since database contains test data"
        
        # Validate that result contains expected hand keys and equity values
        sample_hand_key = next(iter(result.keys()))
        sample_equity = result[sample_hand_key]
        assert isinstance(sample_hand_key, str), "Hand key should be a string"
        assert isinstance(sample_equity, dict), "Equity result should be a metric dictionary"
        assert metric_type.id in sample_equity, f"Result should contain metric key {metric_type.id}"
        assert isinstance(sample_equity[metric_type.id], (int, float)), "Equity value should be numeric"
        assert 0.0 <= sample_equity[metric_type.id] <= 1.0, "Equity should be between 0 and 1"

    def test_get_matrix_payload_warm_read_is_sub_250ms(self, provider):
        """Validate warm browser read latency stays below 250ms."""
        import time

        # Seed a valid matrix scenario for the provider
        from datetime import datetime, timezone
        from hopilot.gto.aof_hand_matrix import build_matrix_keys
        from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric

        keys = build_matrix_keys()
        with provider.database_repository.connection.session_scope() as session:
            sim = Simulation(
                name="warm_read_latency",
                parameters={
                    "selected_position": "UTG",
                    "hero_action": "FOLD",
                    "position_actions": {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
                    "active_players": 1,
                    "num_opponents": 1,
                    "pot_size": 20.0,
                    "bet_amount": 10.0,
                    "sims_per_combo": 120,
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                    "run_kind": "matrix_sweep"
                },
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()

            for row in range(13):
                for col in range(13):
                    cell = MatrixCell(matrix_id=matrix.id, row_index=row, col_index=col, hand_combination=keys[row][col])
                    session.add(cell)
                    session.flush()
                    session.add(AggregatedMetric(cell_id=cell.id, equity=0.55, ev=0.75, convergence_status="AVAILABLE", last_updated=datetime.now(timezone.utc)))

            session.commit()

        # Warm the cache with one read
        provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        start = time.perf_counter()
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )
        duration = time.perf_counter() - start

        assert payload["status"] == "AVAILABLE"
        assert duration < 0.25, f"Warm read should complete under 250ms, got {duration:.3f}s"

    def test_find_matrix_sweep_run_by_contract_prefers_latest_completed_run(self, provider):
        """Verify current historical run selection prefers latest completion timestamp."""
        from datetime import datetime, timedelta, timezone

        with provider.database_repository.connection.session_scope() as session:
            from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric

            base_params = {
                "selected_position": "UTG",
                "hero_action": "FOLD",
                "position_actions": {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
                "active_players": 1,
                "num_opponents": 1,
                "pot_size": 20.0,
                "bet_amount": 10.0,
                "sims_per_combo": 120,
                "num_simulations": 120,
                "matrix_size": "13x13",
                "game_type": "cash",
                "run_kind": "matrix_sweep"
            }

            older = Simulation(
                name="older_test_run",
                parameters=base_params,
                start_timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
                end_timestamp=datetime.now(timezone.utc) - timedelta(minutes=5)
            )
            session.add(older)
            session.flush()
            older_matrix = HandMatrix(simulation_id=older.id, matrix_size="13x13")
            session.add(older_matrix)
            session.flush()
            older_cell = MatrixCell(matrix_id=older_matrix.id, row_index=0, col_index=0, hand_combination="AA")
            session.add(older_cell)
            session.flush()
            session.add(AggregatedMetric(cell_id=older_cell.id, ev=0.5, convergence_status="AVAILABLE", last_updated=datetime.now(timezone.utc)))

            newer = Simulation(
                name="newer_test_run",
                parameters=base_params,
                start_timestamp=datetime.now(timezone.utc) - timedelta(minutes=2),
                end_timestamp=datetime.now(timezone.utc) - timedelta(minutes=1)
            )
            session.add(newer)
            session.flush()
            newer_matrix = HandMatrix(simulation_id=newer.id, matrix_size="13x13")
            session.add(newer_matrix)
            session.flush()
            newer_cell = MatrixCell(matrix_id=newer_matrix.id, row_index=0, col_index=0, hand_combination="AA")
            session.add(newer_cell)
            session.flush()
            session.add(AggregatedMetric(cell_id=newer_cell.id, ev=0.75, convergence_status="AVAILABLE", last_updated=datetime.now(timezone.utc)))

            session.commit()

        contract = base_params.copy()
        chosen = provider.database_repository.find_matrix_sweep_run_by_contract(contract)
        assert chosen is not None, "Expected a matching run"
        assert chosen.id == newer.id, "Should choose the run with later end_timestamp"

    def test_get_matrix_payload_returns_missing_for_simulation_without_hand_matrix(self, provider):
        """Verify a matching run without a HandMatrix is treated as an explicit missing scenario."""
        from datetime import datetime, timezone
        from hopilot.models import Simulation

        with provider.database_repository.connection.session_scope() as session:
            sim = Simulation(
                name="missing_hand_matrix",
                parameters={
                    "selected_position": "UTG",
                    "hero_action": "FOLD",
                    "position_actions": {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
                    "active_players": 1,
                    "num_opponents": 1,
                    "pot_size": 20.0,
                    "bet_amount": 10.0,
                    "sims_per_combo": 120,
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                    "run_kind": "matrix_sweep"
                },
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.commit()

        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        assert payload["status"] == "MISSING"
        assert len(payload["cells"]) == 169
        assert all(cell["status"] == "MISSING" for cell in payload["cells"])

    def test_get_matrix_payload_substitutes_zero_for_missing_metric_rows(self, provider):
        """Verify a missing AggregatedMetric row substitutes 0 and still returns available status."""
        from datetime import datetime, timezone
        from hopilot.gto.aof_hand_matrix import build_matrix_keys
        from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric

        keys = build_matrix_keys()
        with provider.database_repository.connection.session_scope() as session:
            sim = Simulation(
                name="missing_metric_row",
                parameters={
                    "selected_position": "UTG",
                    "hero_action": "FOLD",
                    "position_actions": {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
                    "active_players": 1,
                    "num_opponents": 1,
                    "pot_size": 20.0,
                    "bet_amount": 10.0,
                    "sims_per_combo": 120,
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                    "run_kind": "matrix_sweep"
                },
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()

            for row in range(13):
                for col in range(13):
                    hand_key = keys[row][col]
                    cell = MatrixCell(matrix_id=matrix.id, row_index=row, col_index=col, hand_combination=hand_key)
                    session.add(cell)
                    session.flush()
                    if row != 0 or col != 0:
                        metric = AggregatedMetric(
                            cell_id=cell.id,
                            equity=0.55,
                            ev=0.75,
                            convergence_status="AVAILABLE",
                            last_updated=datetime.now(timezone.utc)
                        )
                        session.add(metric)

            session.commit()

        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        missing_cell = next(cell for cell in payload["cells"] if cell["hand_key"] == "AA")
        assert missing_cell["value"] == 0.0
        assert payload["status"] == "AVAILABLE"

    def test_database_has_data_but_query_returns_nothing(self, provider):
        """Verify the disconnect: data IS in database, but query returns nothing."""
        # Insert some test data
        from hopilot.gto.aof_hand_matrix import build_matrix_keys

        with provider.database_repository.connection.session_scope() as session:
            from datetime import datetime, timezone
            from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric
            
            sim = Simulation(
                name="test_query_disconnect",
                parameters={
                    "position": "UTG",
                    "action": "FOLD",
                    "metric": "EQUITY",
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                },
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
            keys = build_matrix_keys()
            
            # Insert cells with equity data (using correct schema)
            for row in range(0, 13):
                for col in range(0, 13):
                    cell = MatrixCell(
                        matrix_id=matrix.id,
                        row_index=row,
                        col_index=col,
                        hand_combination=keys[row][col]
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
            assert len(result) == 169, "Should return 13x13 matrix (169 cells)"
            
            # Validate that all cells have proper equity values
            for hand_key, value_dict in result.items():
                assert isinstance(hand_key, str), f"Hand key should be string, got {type(hand_key)}"
                assert isinstance(value_dict, dict), f"Equity result should be a dict, got {type(value_dict)}"
                assert "EQUITY" in value_dict, "Result dict should contain EQUITY metric"
                equity_value = value_dict["EQUITY"]
                assert isinstance(equity_value, (int, float)), f"Equity should be numeric, got {type(equity_value)}"
                assert 0.0 <= equity_value <= 1.0, f"Equity should be between 0 and 1, got {equity_value}"


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
        """Test that GUI loads existing aggregated matrix data when initialized."""
        from datetime import datetime, timezone
        from hopilot.gto.aof_hand_matrix import build_matrix_keys
        from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric

        keys = build_matrix_keys()
        with provider.database_repository.connection.session_scope() as session:
            sim = Simulation(
                name="test_gui_load",
                parameters={
                    "selected_position": "UTG",
                    "hero_action": "ALL_IN",
                    "position_actions": {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"},
                    "active_players": 4,
                    "num_opponents": 3,
                    "pot_size": 20.0,
                    "bet_amount": 10.0,
                    "sims_per_combo": 120,
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                    "run_kind": "matrix_sweep"
                },
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()

            for row in range(13):
                for col in range(13):
                    cell = MatrixCell(
                        matrix_id=matrix.id,
                        row_index=row,
                        col_index=col,
                        hand_combination=keys[row][col]
                    )
                    session.add(cell)
                    session.flush()
                    metric = AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.5,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc)
                    )
                    session.add(metric)
            session.commit()

        payload = provider.get_matrix_payload(
            position="UTG",
            metric="WIN_LOSE_PROBABILITY",
            position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"}
        )

        assert isinstance(payload, dict), "Payload should be a dictionary"
        assert payload["status"] == "AVAILABLE"
        assert len(payload["cells"]) == 169
        assert any(cell["hand_key"] == "AA" for cell in payload["cells"])

    def test_gui_provider_returns_correct_format(self, provider):
        """Test that get_matrix_payload returns the correct format for GUI."""
        from datetime import datetime, timezone
        from hopilot.gto.aof_hand_matrix import build_matrix_keys
        from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric

        keys = build_matrix_keys()
        with provider.database_repository.connection.session_scope() as session:
            sim = Simulation(
                name="test_format",
                parameters={
                    "selected_position": "UTG",
                    "hero_action": "ALL_IN",
                    "position_actions": {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"},
                    "active_players": 4,
                    "num_opponents": 3,
                    "pot_size": 20.0,
                    "bet_amount": 10.0,
                    "sims_per_combo": 120,
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                    "run_kind": "matrix_sweep"
                },
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()

            for row in range(13):
                for col in range(13):
                    cell = MatrixCell(
                        matrix_id=matrix.id,
                        row_index=row,
                        col_index=col,
                        hand_combination=keys[row][col]
                    )
                    session.add(cell)
                    session.flush()
                    session.add(AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.75,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc)
                    ))
            session.commit()

        payload = provider.get_matrix_payload(
            position="UTG",
            metric="WIN_LOSE_PROBABILITY",
            position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"}
        )

        assert "cells" in payload, "Should have cells key"
        assert isinstance(payload["cells"], list), "cells should be a list"
        assert len(payload["cells"]) == 169, "Should have 169 cells (13x13)"

        aa_cell = next((cell for cell in payload["cells"] if cell["hand_key"] == "AA"), None)
        assert aa_cell is not None, "Should have AA cell"
        assert aa_cell["value"] == 0.75, f"AA value should be 0.75, got {aa_cell['value']}"
        assert aa_cell["status"] == "AVAILABLE", "Status should be AVAILABLE"
        assert aa_cell["display"] is not None, "Should have display value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
