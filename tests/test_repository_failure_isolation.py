import os
import tempfile

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.analytics_repository import AnalyticsRepository
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.precompute_job_repository import PrecomputeJobRepository
from hopilot.gto.matrix_sweep_contract import build_run_parameters
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


def test_game_state_failure_does_not_block_other_domains(test_db_url):
    connection = DatabaseConnection(test_db_url)
    game_state_repo = GameStateRepository(connection)
    simulation_repo = SimulationRepository(connection)
    precompute_repo = PrecomputeJobRepository(connection)
    analytics_repo = AnalyticsRepository(connection)

    with pytest.raises(ValueError):
        game_state_repo.create_game_state({"pot_size": 100.0})

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
    simulation_id = simulation_repo.create_matrix_sweep_simulation(parameters)
    assert simulation_id > 0

    job_id = precompute_repo.create_precompute_job_session("fingerprint-isolation", 1)
    assert job_id > 0

    summary = analytics_repo.get_simulation_summary()
    assert isinstance(summary, list)
