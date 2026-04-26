"""
Integration tests for Browser Database Provider.
Tests real database operations instead of mock behavior.
"""

import pytest
import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider, STATUS_AVAILABLE, STATUS_MISSING
from hopilot.gto.aof_hand_matrix import build_matrix_keys
from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric


class TestBrowserDatabaseProviderIntegration:
    """Integration tests for Browser Database Provider with real database."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield f"sqlite:///{db_path}"
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass

    @pytest.fixture
    def populated_provider(self, temp_db_path):
        """Create a provider with populated test database."""
        provider = BrowserDatabaseProvider(database_url=temp_db_path)

        # Populate database with a valid matrix-sweep run and a full 13x13 matrix
        repo = provider.database_repository
        
        with repo.connection.session_scope() as session:
            # Create simulation with canonical scenario contract
            sim = Simulation(
                name="integration_test",
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

            keys = build_matrix_keys()
            for row in range(13):
                for col in range(13):
                    hand_key = keys[row][col]
                    cell = MatrixCell(
                        matrix_id=matrix.id,
                        row_index=row,
                        col_index=col,
                        hand_combination=hand_key
                    )
                    session.add(cell)
                    session.flush()

                    metric = AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.5,
                        ev=0.75 + (row * 13 + col) * 0.001,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc)
                    )
                    session.add(metric)

            session.commit()
        
        return provider

    def test_get_matrix_payload_returns_real_data(self, populated_provider):
        """Integration test: get_matrix_payload returns real database data."""
        payload = populated_provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        # Verify payload structure
        assert isinstance(payload, dict), "Payload should be a dictionary"
        assert "context" in payload, "Payload should have context"
        assert "cells" in payload, "Payload should have cells"

        # Verify context
        context = payload["context"]
        assert context["position"] == "UTG", "Context should have correct position"
        assert context["metric"] == "EV", "Context should have correct metric"

        # Verify cells structure (may be empty if no matching data, but should be a list)
        cells = payload["cells"]
        assert isinstance(cells, list), "Cells should be a list"
        
        # If there are cells, verify their structure
        if len(cells) > 0:
            cell = cells[0]
            assert "row" in cell, "Cell should have row"
            assert "col" in cell, "Cell should have col"
            assert "hand_key" in cell, "Cell should have hand_key"
            assert "value" in cell, "Cell should have value"
            assert "status" in cell, "Cell should have status"

    def test_get_matrix_from_database_returns_real_data(self, populated_provider):
        """Integration test: get_matrix_from_database returns real database data."""
        payload = populated_provider.get_matrix_from_database(
            position="UTG",
            metric="EV", 
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"}
        )
        
        assert isinstance(payload, dict), "Should return a dictionary"
        assert "context" in payload
        assert "cells" in payload
        assert payload["context"]["position"] == "UTG"
        assert payload["context"]["metric"] == "EV"
        assert isinstance(payload["cells"], list)
        assert len(payload["cells"]) == 169

        aa_cell = next((cell for cell in payload["cells"] if cell.get("hand_key") == "AA"), None)
        assert aa_cell is not None, "AA cell should be present"
        assert aa_cell["status"] == "AVAILABLE"
        assert abs(aa_cell["value"] - 0.75) < 0.01, f"AA equity should be ~0.75, got {aa_cell['value']}"

    def test_get_matrix_payload_prefers_newest_aggregated_run(self, temp_db_path):
        """Integration test: provider should select the newest aggregated run for the same scenario."""
        provider = BrowserDatabaseProvider(database_url=temp_db_path)
        repo = provider.database_repository

        with repo.connection.session_scope() as session:
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
                name="older_run",
                parameters=base_params,
                start_timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
                end_timestamp=datetime.now(timezone.utc) - timedelta(minutes=5)
            )
            session.add(older)
            session.flush()
            older_matrix = HandMatrix(simulation_id=older.id, matrix_size="13x13")
            session.add(older_matrix)
            session.flush()
            for row in range(13):
                for col in range(13):
                    hand_key = build_matrix_keys()[row][col]
                    cell = MatrixCell(matrix_id=older_matrix.id, row_index=row, col_index=col, hand_combination=hand_key)
                    session.add(cell)
                    session.flush()
                    session.add(AggregatedMetric(cell_id=cell.id, equity=0.45, ev=0.45, convergence_status="AVAILABLE", last_updated=datetime.now(timezone.utc)))

            newer = Simulation(
                name="newer_run",
                parameters=base_params,
                start_timestamp=datetime.now(timezone.utc) - timedelta(minutes=2),
                end_timestamp=datetime.now(timezone.utc) - timedelta(minutes=1)
            )
            session.add(newer)
            session.flush()
            newer_matrix = HandMatrix(simulation_id=newer.id, matrix_size="13x13")
            session.add(newer_matrix)
            session.flush()
            for row in range(13):
                for col in range(13):
                    hand_key = build_matrix_keys()[row][col]
                    cell = MatrixCell(matrix_id=newer_matrix.id, row_index=row, col_index=col, hand_combination=hand_key)
                    session.add(cell)
                    session.flush()
                    session.add(AggregatedMetric(cell_id=cell.id, equity=0.85, ev=0.85, convergence_status="AVAILABLE", last_updated=datetime.now(timezone.utc)))

            session.commit()

        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        aa_cell = next((cell for cell in payload["cells"] if cell["hand_key"] == "AA"), None)
        assert aa_cell is not None
        assert aa_cell["value"] == 0.85
        assert payload["status"] == STATUS_AVAILABLE

    def test_get_matrix_payload_prefers_highest_id_on_tie(self, temp_db_path):
        """Integration test: provider should prefer the later run by ID when end timestamps tie."""
        provider = BrowserDatabaseProvider(database_url=temp_db_path)
        repo = provider.database_repository

        with repo.connection.session_scope() as session:
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
            shared_timestamp = datetime.now(timezone.utc)

            first = Simulation(
                name="tie_first_run",
                parameters=base_params,
                start_timestamp=shared_timestamp,
                end_timestamp=shared_timestamp
            )
            session.add(first)
            session.flush()
            first_matrix = HandMatrix(simulation_id=first.id, matrix_size="13x13")
            session.add(first_matrix)
            session.flush()
            for row in range(13):
                for col in range(13):
                    hand_key = build_matrix_keys()[row][col]
                    cell = MatrixCell(matrix_id=first_matrix.id, row_index=row, col_index=col, hand_combination=hand_key)
                    session.add(cell)
                    session.flush()
                    session.add(AggregatedMetric(cell_id=cell.id, equity=0.5, ev=0.5, convergence_status="AVAILABLE", last_updated=shared_timestamp))

            second = Simulation(
                name="tie_second_run",
                parameters=base_params,
                start_timestamp=shared_timestamp,
                end_timestamp=shared_timestamp
            )
            session.add(second)
            session.flush()
            second_matrix = HandMatrix(simulation_id=second.id, matrix_size="13x13")
            session.add(second_matrix)
            session.flush()
            for row in range(13):
                for col in range(13):
                    hand_key = build_matrix_keys()[row][col]
                    cell = MatrixCell(matrix_id=second_matrix.id, row_index=row, col_index=col, hand_combination=hand_key)
                    session.add(cell)
                    session.flush()
                    session.add(AggregatedMetric(cell_id=cell.id, equity=0.9, ev=0.9, convergence_status="AVAILABLE", last_updated=shared_timestamp))

            session.commit()

        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
        )

        aa_cell = next((cell for cell in payload["cells"] if cell["hand_key"] == "AA"), None)
        assert aa_cell is not None
        assert aa_cell["value"] == 0.9
        assert payload["status"] == STATUS_AVAILABLE

    def test_get_matrix_payload_handles_missing_data(self, temp_db_path):
        """Integration test: get_matrix_payload handles missing data gracefully."""
        provider = BrowserDatabaseProvider(database_url=temp_db_path)

        # Request data that doesn't exist in empty database
        payload = provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN"},
        )

        # Should return valid payload structure even with no data
        assert isinstance(payload, dict), "Should return dictionary even with no data"
        assert "context" in payload, "Should have context"
        assert "cells" in payload, "Should have cells"
        assert isinstance(payload["cells"], list), "Cells should be a list"
        assert len(payload["cells"]) == 169
        assert payload["status"] == "MISSING"
        assert all(cell["status"] == "MISSING" for cell in payload["cells"])

        # Context should be correct
        assert payload["context"]["position"] == "UTG"
        assert payload["context"]["metric"] == "EV"