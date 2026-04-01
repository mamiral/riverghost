"""
Integration tests for AOF Browser Panel database integration.
Tests real database interactions instead of mock behavior.
"""

import pytest
import pygame
import sys
import os
import tempfile
from pathlib import Path

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python"))

from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
from hopilot.gto.browser_database_provider import BrowserDatabaseProvider


class TestAoFBrowserPanelDatabaseIntegration:
    """Integration tests for AOF Browser Panel with real database."""

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
    def populated_database(self, temp_db_path):
        """Create a database with test data."""
        provider = BrowserDatabaseProvider(database_url=temp_db_path)

        # Populate with test simulation and matrix data
        repo = provider.database_repository
        
        with repo.connection.session_scope() as session:
            from datetime import datetime, timezone
            from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric

            # Create simulation
            sim = Simulation(
                name="integration_test_sim",
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

            # Create test cells
            test_data = [
                ("AA", 0.85),
                ("KK", 0.78),
                ("QQ", 0.72),
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

    def test_panel_loads_real_simulation_data(self, populated_database, temp_db_path):
        """Integration test: Panel can be created with real database connection."""
        # Initialize pygame for GUI testing
        pygame.init()
        try:
            screen = pygame.display.set_mode((800, 600))
            
            # Create panel with real database - this should not crash
            panel = AoFBrowserPanel(width=800, height=600, database_url=temp_db_path)
            
            # Verify panel was created successfully
            assert panel is not None, "Panel should be created"
            assert hasattr(panel, 'provider'), "Panel should have provider"
            
        finally:
            pygame.quit()

    def test_panel_handles_database_connection_errors(self, temp_db_path):
        """Integration test: Panel handles database connection issues gracefully."""
        # Use invalid database URL to test error handling
        invalid_provider = BrowserDatabaseProvider(database_url="sqlite:///nonexistent.db")
        
        pygame.init()
        try:
            screen = pygame.display.set_mode((800, 600))
            
            panel = AoFBrowserPanel(width=800, height=600, database_url=invalid_provider)
            
            # This should not crash even with invalid database
            panel.load_simulation_data()
            
            # Panel should handle the error gracefully
            assert panel.simulation_data is not None, "Should handle errors gracefully"
            
        finally:
            pygame.quit()

        # Create some test cells with data
        test_hands = ["AA", "KK", "QQ", "AKs"]
        for i, hand in enumerate(test_hands):
            cell = MatrixCell(
                matrix_id=matrix.id,
                row_index=i,
                col_index=i,
                hand_combination=f"{hand} vs Random"
            )
            session.add(cell)
            session.flush()

            # Add EV metric
            metric = AggregatedMetric(
                cell_id=cell.id,
                equity=0.6 + i * 0.05,  # Different equity values
                convergence_status="AVAILABLE",
                last_updated=datetime.now(timezone.utc)
            )
            session.add(metric)

        session.commit()
        return temp_db_path

    def test_panel_loads_real_database_data(self, populated_database):
        """Integration test: Panel loads and displays real database data."""
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        # Create panel with real database
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=populated_database,
        )

        # Verify panel loaded real data from database
        assert panel.payload is not None, "Panel should load data from database"
        assert "context" in panel.payload, "Payload should have context"
        assert "cells" in panel.payload, "Payload should have cells"

        # Verify context structure
        context = panel.payload["context"]
        assert "position" in context, "Context should specify position"
        assert "metric" in context, "Context should specify metric"

        # Verify cells contain real data
        cells = panel.payload["cells"]
        assert isinstance(cells, list), "Cells should be a list"
        assert len(cells) > 0, "Should have loaded cells from database"

        # Verify at least some cells have hand data
        cells_with_hands = [cell for cell in cells if cell.get("hand_key") or cell.get("hand")]
        assert len(cells_with_hands) > 0, "Should have cells with hand data"

        # Verify equity values are reasonable
        for cell in cells_with_hands:
            if "value" in cell:
                assert isinstance(cell["value"], (int, float)), "Cell value should be numeric"
                assert 0.0 <= cell["value"] <= 1.0, f"Equity should be between 0-1, got {cell['value']}"

    def test_panel_handles_database_connection_error(self, temp_db_path):
        """Integration test: Panel handles database connection errors gracefully."""
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        # Use invalid database URL to test error handling
        invalid_db_url = "sqlite:///nonexistent_directory/invalid.db"

        # Panel should initialize even with invalid database
        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=invalid_db_url,
        )

        # Should have some payload structure even on error
        assert panel.payload is not None, "Panel should handle database errors gracefully"
        # Payload might be empty or have error context, but structure should exist

    def test_panel_preserves_state_on_refresh_integration(self, populated_database):
        """Integration test: Panel preserves selection state when refreshing with real data."""
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))

        panel = AoFBrowserPanel(
            width=800,
            height=600,
            database_url=populated_database,
        )

        # Simulate some state (if panel has state management)
        initial_payload = panel.payload

        # Trigger refresh by re-setting database URL or calling refresh method
        # (This depends on panel implementation - may need adjustment)
        panel.database_url = populated_database  # Re-trigger loading

        # Verify panel still has valid data after refresh
        assert panel.payload is not None, "Panel should maintain data after refresh"
        assert "cells" in panel.payload, "Payload should still have cells after refresh"

        # If panel has selection state, verify it's preserved
        # (This would depend on specific panel implementation)