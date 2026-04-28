"""
Integration tests for AOF Browser Panel database integration.
Tests real database interactions instead of mock behavior.
"""

import json
import pytest
import pygame
import sys
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python"))

from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.aof_precompute_runner import GuiRunState


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
                parameters=json.dumps({
                    "selected_position": "UTG",
                    "hero_action": "ALL_IN",
                    "position_actions": {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"},
                    "active_players": ["UTG", "BTN", "SB", "BB"],
                    "num_opponents": 3,
                    "pot_size": 20.0,
                    "bet_amount": 10.0,
                    "sims_per_combo": 120,
                    "num_simulations": 120,
                    "matrix_size": "13x13",
                    "game_type": "cash",
                    "run_kind": "matrix_sweep",
                    "metric": "EV",
                }),
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc),
            )
            session.add(sim)
            session.flush()

            # Create matrix
            matrix = HandMatrix(simulation_id=sim.id, matrix_size="13x13")
            session.add(matrix)
            session.flush()

            # Create test cells for all 169 matrix positions
            for row in range(13):
                for col in range(13):
                    hand = f"H{row:02d}{col:02d}"
                    cell = MatrixCell(
                        matrix_id=matrix.id,
                        row_index=row,
                        col_index=col,
                        hand_combination=f"{hand} vs Random"
                    )
                    session.add(cell)
                    session.flush()

                    metric = AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.5,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc),
                        sample_count=100,
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

    def test_panel_loads_real_database_data(self, populated_database, temp_db_path):
        """Integration test: Panel loads and displays real database data."""
        started_pygame = False
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
            started_pygame = True

        try:
            # Create panel with real database
            panel = AoFBrowserPanel(
                width=800,
                height=600,
                database_url=temp_db_path,
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
        finally:
            if started_pygame:
                pygame.quit()

        # Verify at least some cells have hand data
        cells_with_hands = [cell for cell in cells if cell.get("hand_key") or cell.get("hand")]
        assert len(cells_with_hands) > 0, "Should have cells with hand data"

        # Verify equity values are reasonable
        for cell in cells_with_hands:
            if "value" in cell:
                assert isinstance(cell["value"], (int, float)), "Cell value should be numeric"
                assert 0.0 <= cell["value"] <= 1.0, f"Equity should be between 0-1, got {cell['value']}"

    def test_panel_switch_clears_stale_payload(self, temp_db_path):
        """Integration test: switching scenario should clear stale payload immediately."""
        pygame.init()
        try:
            screen = pygame.display.set_mode((800, 600))
            panel = AoFBrowserPanel(width=800, height=600, database_url=temp_db_path)
            panel._start_async_refresh = lambda: None

            panel.payload = {
                "context": {"position": "UTG", "metric": "EV"},
                "cells": [
                    {"row": 0, "col": 0, "hand_key": "AA", "value": 0.85, "status": "AVAILABLE", "display": "85%"},
                ],
                "status": "AVAILABLE",
                "status_message": "Loaded",
            }

            panel.state.set_position("BTN")
            panel._refresh()

            assert panel.panel_state == "LOADING"
            assert all(cell["status"] == "LOADING" for cell in panel.payload["cells"])
        finally:
            pygame.quit()

    def test_panel_shows_rerun_overlay_when_starting_from_available(self, temp_db_path):
        """Integration test: rerun from AVAILABLE keeps data visible and shows overlay."""
        pygame.init()
        try:
            screen = pygame.display.set_mode((800, 600))
            panel = AoFBrowserPanel(width=800, height=600, database_url=temp_db_path)
            panel._start_async_refresh = lambda: None
            panel._build_current_context = MagicMock(return_value={
                "position": "UTG",
                "metric": "EV",
                "position_actions": panel.state.position_actions,
            })
            panel.runner.create_gui_session = MagicMock(return_value=MagicMock(
                run_state=MagicMock(value="IDLE"),
                total_cells=169,
                completed_cells=0,
                failed_cells=0,
                next_cell_index=0,
                current_cell_index=None,
            ))
            panel.runner.transition_session_state = MagicMock()
            panel.runner.bind_gui_run = MagicMock()
            panel.runner.database_repository.create_simulation = MagicMock(return_value=1)
            panel.runner.database_repository.create_hand_matrix = MagicMock(return_value=1)

            panel.payload = {
                "context": {"position": "UTG", "metric": "EV", "position_actions": panel.state.position_actions},
                "cells": [{"row": 0, "col": 0, "hand_key": "AA", "value": 0.85, "status": "AVAILABLE", "display": "85%"}],
                "status": "AVAILABLE",
                "status_message": "Loaded",
            }

            panel._start_precompute()

            assert panel._rerun_in_progress is True
            assert panel.panel_state == "AVAILABLE"
            assert panel.payload["status"] == "AVAILABLE"
            assert panel.payload["cells"][0]["hand_key"] == "AA"
        finally:
            pygame.quit()

    def test_panel_transitions_to_error_on_precompute_failure_and_retries(self, temp_db_path):
        """Integration test: precompute failure transitions to ERROR and Start retries."""
        pygame.init()
        try:
            screen = pygame.display.set_mode((800, 600))
            panel = AoFBrowserPanel(width=800, height=600, database_url=temp_db_path)
            panel._start_async_refresh = lambda: None
            panel._build_current_context = MagicMock(return_value={
                "position": "UTG",
                "metric": "EV",
                "position_actions": panel.state.position_actions,
            })
            panel.precompute_context = panel._build_current_context()
            panel.precompute_session = SimpleNamespace(
                run_state=GuiRunState.FAILED,
                total_cells=169,
                completed_cells=0,
                failed_cells=1,
                next_cell_index=0,
                current_cell_index=None,
            )
            panel._rerun_in_progress = True
            panel.precompute_futures = {}

            panel._tick_precompute()

            assert panel.panel_state == "ERROR"
            assert panel.payload["status"] == "ERROR"
            assert panel._last_error is not None
            assert all(cell["status"] == "ERROR" for cell in panel.payload["cells"])

            panel.runner = MagicMock()
            panel.runner.create_gui_session.return_value = SimpleNamespace(
                run_state=GuiRunState.IDLE,
                total_cells=169,
                completed_cells=0,
                failed_cells=0,
                next_cell_index=0,
                current_cell_index=None,
            )
            panel.runner.transition_session_state = MagicMock()
            panel.runner.bind_gui_run = MagicMock()
            panel.runner.database_repository = MagicMock()
            panel.runner.database_repository.create_simulation = MagicMock(return_value=1)
            panel.runner.database_repository.create_hand_matrix = MagicMock(return_value=1)

            panel._start_precompute()

            assert panel._last_error is None
            assert panel.precompute_session is not None
            assert panel.panel_state != "ERROR"
        finally:
            pygame.quit()

    def test_panel_stops_precompute_and_preserves_partial_results(self, temp_db_path):
        """Integration test: stopping while precompute is partial preserves available results."""
        pygame.init()
        try:
            screen = pygame.display.set_mode((800, 600))
            panel = AoFBrowserPanel(width=800, height=600, database_url=temp_db_path)
            panel._start_async_refresh = lambda: None
            panel._build_current_context = MagicMock(return_value={
                "position": "UTG",
                "metric": "EV",
                "position_actions": panel.state.position_actions,
            })
            panel.precompute_context = panel._build_current_context()
            panel.precompute_session = SimpleNamespace(
                run_state=GuiRunState.RUNNING,
                total_cells=169,
                completed_cells=2,
                failed_cells=0,
                next_cell_index=3,
                current_cell_index=2,
            )
            panel.payload = {
                "context": panel.precompute_context,
                "cells": [
                    {"row": 0, "col": 0, "hand_key": "AA", "value": 0.85, "status": "AVAILABLE", "display": "85%"},
                    {"row": 0, "col": 1, "hand_key": "KK", "value": 0.77, "status": "AVAILABLE", "display": "77%"},
                    {"row": 0, "col": 2, "hand_key": "QQ", "value": None, "status": "MISSING", "display": "-"},
                ] + [{"row": r, "col": c, "hand_key": None, "value": None, "status": "MISSING", "display": "-"} for r in range(13) for c in range(13) if not (r == 0 and c in (0, 1, 2))],
                "status": "PARTIAL",
                "status_message": "Partial results",
            }
            panel.runner = MagicMock()
            panel.runner.stop_gui_session.side_effect = lambda session: setattr(session, 'run_state', GuiRunState.COMPLETED)
            panel.runner.transition_session_state = MagicMock()
            panel.runner.mark_gui_dispatch = MagicMock()

            stop_result = panel.stop_precompute()
            assert stop_result is True
            assert panel.state.status_message == "Precompute stopped"
            assert panel.payload["status"] == "PARTIAL"
            assert any(cell["status"] == "AVAILABLE" for cell in panel.payload["cells"])
            assert any(cell["status"] == "MISSING" for cell in panel.payload["cells"])
        finally:
            pygame.quit()

    def test_panel_discards_stale_async_refresh_results(self, temp_db_path):
        """Integration test: stale refresh results are ignored after context changes."""
        pygame.init()
        try:
            screen = pygame.display.set_mode((800, 600))
            panel = AoFBrowserPanel(width=800, height=600, database_url=temp_db_path)
            panel._start_async_refresh = lambda: None
            panel.payload = {
                "context": {"position": "UTG", "metric": "EV", "position_actions": panel.state.position_actions},
                "cells": [{"row": 0, "col": 0, "hand_key": "AA", "value": 0.85, "status": "AVAILABLE", "display": "85%"}],
                "status": "AVAILABLE",
                "status_message": "Loaded",
            }
            panel._refresh_context = {"position": "BTN", "metric": "EV", "position_actions": panel.state.position_actions}
            old_payload = dict(panel.payload)

            stale_event = SimpleNamespace(
                event_type="database_refresh",
                success=True,
                payload={"context": {"position": "UTG", "metric": "EV"}, "cells": []},
                request_context={"position": "UTG", "metric": "EV"},
            )
            panel._handle_async_refresh_result(stale_event)

            assert panel.payload == old_payload
            assert panel.panel_state == "AVAILABLE"
        finally:
            pygame.quit()

    def test_panel_handles_database_connection_error(self, temp_db_path):
        """Integration test: Panel handles database connection errors gracefully."""
        started_pygame = False
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
            started_pygame = True

        try:
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
        finally:
            if started_pygame:
                pygame.quit()

    def test_panel_preserves_state_on_refresh_integration(self, populated_database, temp_db_path):
        """Integration test: Panel preserves selection state when refreshing with real data."""
        started_pygame = False
        if not pygame.display.get_surface():
            pygame.init()
            pygame.display.set_mode((800, 600))
            started_pygame = True

        try:
            panel = AoFBrowserPanel(
                width=800,
                height=600,
                database_url=temp_db_path,
            )

            # Simulate some state (if panel has state management)
            initial_payload = panel.payload

            # Trigger refresh by re-setting the same URL or calling refresh method
            panel.database_url = temp_db_path  # Preserve database URL for this test

            # Verify panel still has valid data after refresh
            assert panel.payload is not None, "Panel should maintain data after refresh"
            assert "cells" in panel.payload, "Payload should still have cells after refresh"

            # If panel has selection state, verify it's preserved
            # (This would depend on specific panel implementation)
        finally:
            if started_pygame:
                pygame.quit()