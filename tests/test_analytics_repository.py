import os
import tempfile
from datetime import datetime, timezone

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.aof_hand_matrix import iter_canonical_matrix_cells
from hopilot.gto.analytics_repository import AnalyticsRepository
from hopilot.models import AggregatedMetric, HandMatrix, MatrixCell, Simulation


@pytest.fixture(scope="function")
def test_db_url():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    db_url = f"sqlite:///{db_path}"
    connection = DatabaseConnection(db_url)
    connection.create_tables()
    connection.close()
    yield db_url
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass


def test_analytics_repository_returns_summary(test_db_url):
    connection = DatabaseConnection(test_db_url)
    repo = AnalyticsRepository(connection)

    with connection.session_scope() as session:
        simulation = Simulation(
            name="analytics-run",
            start_timestamp=datetime.now(timezone.utc),
            end_timestamp=datetime.now(timezone.utc),
            parameters={"num_simulations": 1, "matrix_size": "13x13", "game_type": "nlhe"},
        )
        session.add(simulation)
        session.flush()

        matrix = HandMatrix(simulation_id=simulation.id, matrix_size="13x13")
        session.add(matrix)
        session.flush()

        canonical = iter_canonical_matrix_cells()[0]
        cell = MatrixCell(matrix_id=matrix.id, row_index=canonical[0], col_index=canonical[1], hand_combination=canonical[2])
        session.add(cell)
        session.flush()

        session.add(AggregatedMetric(
            cell_id=cell.id,
            equity=0.5,
            jackpot_adjusted_ev=0.2,
            convergence_status="CONVERGED",
            last_updated=datetime.now(timezone.utc),
        ))

    summary = repo.get_simulation_summary()
    assert isinstance(summary, list)
    assert len(summary) == 1
    assert summary[0]["simulation_id"] == simulation.id
    assert summary[0]["avg_equity"] == 0.5
