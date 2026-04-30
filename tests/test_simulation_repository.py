import os
import tempfile
from datetime import datetime, timezone

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.matrix_sweep_contract import build_run_parameters
from hopilot.models import Simulation


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


def test_simulation_repository_creates_matrix_sweep_simulation(test_db_url):
    connection = DatabaseConnection(test_db_url)
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

    simulation_id = repo.create_matrix_sweep_simulation(parameters)
    assert simulation_id > 0

    assert repo.get_max_simulation_id() == simulation_id
    assert repo.get_latest_game_state_id() == 0
    assert repo.get_simulation_record(simulation_id) is not None


def test_simulation_repository_updates_matrix_sweep_simulation(test_db_url):
    connection = DatabaseConnection(test_db_url)
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

    simulation_id = repo.create_matrix_sweep_simulation(parameters)
    repo.update_matrix_sweep_simulation(simulation_id, parameters={**parameters, "status": "running"})

    simulation = repo.get_simulation_record(simulation_id)
    assert simulation is not None
    assert simulation.parameters.get("status") == "running"
