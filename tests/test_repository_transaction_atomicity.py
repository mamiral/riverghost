import os
import tempfile

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.matrix_sweep_contract import build_run_parameters
from hopilot.gto.precompute_job_repository import PrecomputeJobRepository
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.unit_of_work import UnitOfWork
from hopilot.models import PrecomputeJobSession, Simulation


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


def test_shared_unit_of_work_commits_across_domains(test_db_url):
    connection = DatabaseConnection(test_db_url)

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

    with UnitOfWork(connection) as uow:
        simulation_repo = SimulationRepository(connection, session=uow.session)
        precompute_repo = PrecomputeJobRepository(connection, session=uow.session)

        simulation_repo.create_matrix_sweep_simulation(parameters)
        precompute_repo.create_precompute_job_session("atomic-fingerprint", 2)

    with connection.session_scope() as session:
        assert session.query(Simulation).count() == 1
        assert session.query(PrecomputeJobSession).count() == 1


def test_shared_unit_of_work_rolls_back_across_domains(test_db_url):
    connection = DatabaseConnection(test_db_url)

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

    with pytest.raises(RuntimeError):
        with UnitOfWork(connection) as uow:
            simulation_repo = SimulationRepository(connection, session=uow.session)
            precompute_repo = PrecomputeJobRepository(connection, session=uow.session)

            simulation_repo.create_matrix_sweep_simulation(parameters)
            precompute_repo.create_precompute_job_session("atomic-fingerprint", 2)

            raise RuntimeError("force rollback")

    with connection.session_scope() as session:
        assert session.query(Simulation).count() == 0
        assert session.query(PrecomputeJobSession).count() == 0
