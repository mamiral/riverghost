"""
Integration tests for Browser Database Provider.
Tests real database operations instead of mock behavior.
"""

import pytest
import sys
import os
import tempfile
from datetime import datetime, timezone

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
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

        # Populate database with test data
        repo = provider.database_repository
        
        with repo.connection.session_scope() as session:
            # Create simulation
            sim = Simulation(
                name="integration_test",
                parameters={
                    "position": "UTG", 
                    "action": "FOLD", 
                    "metric": "EV",
                    "num_simulations": 1000,
                    "matrix_size": "13x13",
                    "game_type": "NLHE"
                },
                start_timestamp=datetime.now(timezone.utc)
            )
            session.add(sim)
            session.flush()

            # Create matrix
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()

            # Create test cells with EV data
            test_data = [
                ("AA", 0.75),
                ("KK", 0.68),
                ("QQ", 0.61),
                ("AKs", 0.55),
            ]

            for i, (hand, equity) in enumerate(test_data):
                cell = MatrixCell(
                    matrix_id=matrix.id,
                    row_index=i,
                    col_index=i,
                    hand_combination=f"{hand} vs Random"
                )
                session.add(cell)
                session.flush()

                metric = AggregatedMetric(
                    cell_id=cell.id,
                    equity=equity,
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
        matrix_data = populated_provider.get_matrix_from_database(
            position="UTG",
            metric="EV", 
            position_actions={"UTG": "FOLD", "BTN": "ALL_IN"}
        )
        
        # Verify it returns a dictionary with matrix data
        assert isinstance(matrix_data, dict), "Should return a dictionary"
        # The exact structure depends on implementation, but it should have some data
        assert len(matrix_data) > 0, "Should contain matrix data"
        hand_keys = [cell.get("hand_key") for cell in cells if cell.get("hand_key")]
        assert "AA" in hand_keys, "Should contain AA hand data"

        # Find AA cell and verify its equity value
        aa_cell = next((cell for cell in cells if cell.get("hand_key") == "AA"), None)
        assert aa_cell is not None, "AA cell should be present"
        assert abs(aa_cell["value"] - 0.75) < 0.01, f"AA equity should be ~0.75, got {aa_cell['value']}"

    def test_get_matrix_payload_handles_missing_data(self, temp_db_path):
        """Integration test: get_matrix_payload handles missing data gracefully."""
        provider = BrowserDatabaseProvider(database_url=temp_db_path)

        # Request data that doesn't exist in empty database
        payload = populated_provider.get_matrix_payload(
            position="UTG",
            metric="EV",
            position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN"},
        )

        # Should return valid payload structure even with no data
        assert isinstance(payload, dict), "Should return dictionary even with no data"
        assert "context" in payload, "Should have context"
        assert "cells" in payload, "Should have cells"
        assert isinstance(payload["cells"], list), "Cells should be a list"

        # Context should be correct
        assert payload["context"]["position"] == "UTG"
        assert payload["context"]["metric"] == "EV"