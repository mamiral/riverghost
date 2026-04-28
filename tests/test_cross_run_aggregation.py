import sys
import os
from datetime import datetime, timezone, timedelta

# Add the python directory to path so hopilot modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider, STATUS_AVAILABLE
from hopilot.gto.aof_hand_matrix import build_matrix_keys
from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric


def test_cross_run_matrix_summary_weights_by_sample_count(db_fixture):
    provider = BrowserDatabaseProvider(database_url=db_fixture.database_url)
    repo = provider.database_repository

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
        "run_kind": "matrix_sweep",
    }

    with repo.connection.session_scope() as session:
        # Older run with lower sample count and lower cell values
        older = Simulation(
            name="older_run",
            parameters=base_params,
            start_timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
            end_timestamp=datetime.now(timezone.utc) - timedelta(minutes=9),
        )
        session.add(older)
        session.flush()

        older_matrix = HandMatrix(simulation_id=older.id, matrix_size="13x13")
        session.add(older_matrix)
        session.flush()

        keys = build_matrix_keys()
        for row in range(13):
            for col in range(13):
                hand_key = keys[row][col]
                cell = MatrixCell(
                    matrix_id=older_matrix.id,
                    row_index=row,
                    col_index=col,
                    hand_combination=hand_key,
                )
                session.add(cell)
                session.flush()
                session.add(
                    AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.25,
                        ev=0.25,
                        sample_count=100,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc),
                    )
                )

        # Newer run with higher sample count and higher cell values
        newer = Simulation(
            name="newer_run",
            parameters=base_params,
            start_timestamp=datetime.now(timezone.utc) - timedelta(minutes=4),
            end_timestamp=datetime.now(timezone.utc) - timedelta(minutes=3),
        )
        session.add(newer)
        session.flush()

        newer_matrix = HandMatrix(simulation_id=newer.id, matrix_size="13x13")
        session.add(newer_matrix)
        session.flush()

        for row in range(13):
            for col in range(13):
                hand_key = keys[row][col]
                cell = MatrixCell(
                    matrix_id=newer_matrix.id,
                    row_index=row,
                    col_index=col,
                    hand_combination=hand_key,
                )
                session.add(cell)
                session.flush()
                session.add(
                    AggregatedMetric(
                        cell_id=cell.id,
                        equity=0.75,
                        ev=0.75,
                        sample_count=300,
                        convergence_status="AVAILABLE",
                        last_updated=datetime.now(timezone.utc),
                    )
                )

        session.commit()

    payload = provider.get_matrix_payload(
        position="UTG",
        metric="EQUITY",
        position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
    )

    aa_cell = next((cell for cell in payload["cells"] if cell.get("hand_key") == "AA"), None)
    assert aa_cell is not None, "AA cell should be present in merged payload"
    assert payload["status"] == STATUS_AVAILABLE
    assert aa_cell["sample_count"] == 400
    assert abs(aa_cell["value"] - 0.625) < 1e-6, f"Merged value should be weighted by sample_count, got {aa_cell['value']}"
