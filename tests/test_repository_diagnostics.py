import os
import tempfile

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.analytics_repository import AnalyticsRepository
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.matrix_sweep_contract import build_run_parameters
from hopilot.gto.precompute_job_repository import PrecomputeJobRepository
from hopilot.gto.repository_errors import (
    AnalyticsRepositoryError,
    GameStateRepositoryError,
    PrecomputeJobRepositoryError,
    SimulationRepositoryError,
)
from hopilot.gto.simulation_repository import SimulationRepository


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


def test_game_state_repository_raises_domain_error_when_tables_missing(test_db_url):
    connection = DatabaseConnection(test_db_url)
    connection.drop_tables()

    repo = GameStateRepository(connection)
    with pytest.raises(GameStateRepositoryError) as exc_info:
        repo.create_game_state({"pot_size": 100.0, "board_cards_str": "AsKsQd"})

    assert "create_game_state" in str(exc_info.value)


def test_simulation_repository_raises_domain_error_when_tables_missing(test_db_url):
    connection = DatabaseConnection(test_db_url)
    connection.drop_tables()

    repo = SimulationRepository(connection)
    parameters = build_run_parameters(
        {
            "selected_position": "UTG",
            "hero_action": "all_in",
            "position_actions": {"UTG": "all_in", "BB": "call"},
            "active_players": ["UTG", "BB"],
            "num_opponents": 1,
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "sims_per_combo": 1,
            "matrix_size": "13x13",
            "game_type": "nlhe",
            "run_kind": "matrix_sweep",
        },
        raw_game_state_id_start=1,
    )

    with pytest.raises(SimulationRepositoryError) as exc_info:
        repo.create_matrix_sweep_simulation(parameters)

    assert "create_matrix_sweep_simulation" in str(exc_info.value)


def test_precompute_job_repository_raises_domain_error_when_tables_missing(test_db_url):
    connection = DatabaseConnection(test_db_url)
    connection.drop_tables()

    repo = PrecomputeJobRepository(connection)
    with pytest.raises(PrecomputeJobRepositoryError) as exc_info:
        repo.create_precompute_job_session("diag-fingerprint", 1)

    assert "create_precompute_job_session" in str(exc_info.value)


def test_analytics_repository_raises_domain_error_when_tables_missing(test_db_url):
    connection = DatabaseConnection(test_db_url)
    connection.drop_tables()

    repo = AnalyticsRepository(connection)
    with pytest.raises(AnalyticsRepositoryError) as exc_info:
        repo.get_simulation_summary()

    assert "get_simulation_summary" in str(exc_info.value)
