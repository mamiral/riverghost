import os
import sys
import tempfile
from datetime import datetime, timezone

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.aof_hand_matrix import build_matrix_keys
from hopilot.gto.data_model import PositionContext, ActionContext, MetricType
from hopilot.models import Simulation, HandMatrix, MatrixCell, AggregatedMetric


def _build_run_db(db_url: str):
    provider = BrowserDatabaseProvider(database_url=db_url)
    with provider.database_repository.connection.session_scope() as session:
        simulation = Simulation(
            name="migration_test_run",
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
                "run_kind": "matrix_sweep",
            },
            start_timestamp=datetime.now(timezone.utc),
            end_timestamp=datetime.now(timezone.utc),
        )
        session.add(simulation)
        session.flush()

        matrix = HandMatrix(simulation_id=simulation.id, matrix_size="13x13")
        session.add(matrix)
        session.flush()

        keys = build_matrix_keys()
        for row in range(13):
            for col in range(13):
                hand_key = keys[row][col]
                cell = MatrixCell(matrix_id=matrix.id, row_index=row, col_index=col, hand_combination=hand_key)
                session.add(cell)
                session.flush()
                session.add(AggregatedMetric(
                    cell_id=cell.id,
                    equity=0.5,
                    ev=0.6,
                    convergence_status="AVAILABLE",
                    last_updated=datetime.now(timezone.utc),
                ))

        session.commit()

    return provider


def test_browser_provider_uses_split_repositories(tmp_path):
    db_path = tmp_path / 'browser_provider_migration.db'
    db_url = f"sqlite:///{db_path}"

    provider = BrowserDatabaseProvider(database_url=db_url)

    assert hasattr(provider, 'simulation_repository')
    assert hasattr(provider, 'analytics_repository')
    assert provider.simulation_repository is not None
    assert provider.analytics_repository is not None
    assert hasattr(provider, 'database_repository')
    assert hasattr(provider.database_repository, 'connection')
    assert provider.database_repository.connection is provider.db_connection

    result = provider.database_repository.get_strategy_matrix(
        PositionContext.UTG(),
        ActionContext.ALL_IN(),
        MetricType.EQUITY(),
    )
    assert isinstance(result, dict)


def test_browser_provider_get_matrix_payload_with_migrated_database(tmp_path):
    db_path = tmp_path / 'browser_provider_payload.db'
    db_url = f"sqlite:///{db_path}"
    provider = _build_run_db(db_url)

    payload = provider.get_matrix_payload(
        position="UTG",
        metric="EV",
        position_actions={"UTG": "FOLD", "BTN": "ALL_IN"},
    )

    assert isinstance(payload, dict)
    assert payload["status"] == "AVAILABLE"
    assert isinstance(payload["cells"], list)
    assert len(payload["cells"]) == 169
    assert all("hand_key" in cell for cell in payload["cells"])
    assert all("value" in cell for cell in payload["cells"])
