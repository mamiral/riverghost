import os
import tempfile
from datetime import datetime, timezone

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.precompute_job_repository import PrecomputeJobRepository
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.gto.analytics_repository import AnalyticsRepository
from hopilot.gto.matrix_sweep_contract import build_run_parameters
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


def test_domain_split_repositories_can_be_instantiated(test_db_url):
    game_state_repo = GameStateRepository(DatabaseConnection(test_db_url))
    simulation_repo = SimulationRepository(DatabaseConnection(test_db_url))
    job_repo = PrecomputeJobRepository(DatabaseConnection(test_db_url))
    analytics_repo = AnalyticsRepository(DatabaseConnection(test_db_url))

    assert game_state_repo is not None
    assert simulation_repo is not None
    assert job_repo is not None
    assert analytics_repo is not None


def test_game_state_repository_can_create_and_fetch_a_game_state(test_db_url):
    connection = DatabaseConnection(test_db_url)
    repo = GameStateRepository(connection)

    payload = {
        "pot_size": 100.0,
        "board_cards_str": "As,Ks,Qd",
        "round": "preflop",
        "outcome": "hero_win",
        "players": [
            {
                "position": "UTG",
                "hole_cards": "AsAh",
                "stack_size": 150.0,
                "is_hero": True,
            },
            {
                "position": "BTN",
                "hole_cards": "KdKh",
                "stack_size": 200.0,
                "is_hero": False,
            },
        ],
    }

    game_state_id = repo.create_game_state(payload)
    assert game_state_id > 0

    saved = repo.get_game_state(game_state_id)
    assert saved is not None
    assert saved["id"] == game_state_id
    assert len(saved["players"]) == 2
    assert saved["players"][0]["hole_cards"] == "AsAh"


def test_precompute_job_repository_can_track_job_and_links(test_db_url):
    connection = DatabaseConnection(test_db_url)
    repo = PrecomputeJobRepository(connection)

    job_id = repo.create_precompute_job_session("fingerprint", 2)
    assert job_id > 0

    link_id = repo.create_scenario_run_link(
        job_session_id=job_id,
        scenario_index=0,
        scenario_key="UTG:ALL_IN",
        scenario_contract={"selected_position": "UTG"},
        status="PENDING",
    )
    assert link_id > 0

    links = repo.get_scenario_run_links_for_job(job_id)
    assert len(links) == 1
    assert links[0].scenario_index == 0


def test_simulation_repository_can_create_simulation_and_matrix(test_db_url):
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

    matrix_id = repo.create_hand_matrix(simulation_id)
    assert matrix_id > 0

    assert repo.get_latest_game_state_id() == 0
    assert repo.get_max_simulation_id() == simulation_id


def test_analytics_repository_can_return_simulation_summary(test_db_url):
    connection = DatabaseConnection(test_db_url)
    analytics_repo = AnalyticsRepository(connection)

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
        cell = MatrixCell(matrix_id=matrix.id, row_index=0, col_index=0, hand_combination="AA")
        session.add(cell)
        session.flush()
        session.add(AggregatedMetric(
            cell_id=cell.id,
            equity=0.5,
            jackpot_adjusted_ev=0.1,
            convergence_status="CONVERGED",
            last_updated=datetime.now(timezone.utc),
        ))

    summary = analytics_repo.get_simulation_summary()
    assert isinstance(summary, list)
    assert len(summary) == 1
    assert summary[0]["simulation_id"] == simulation.id
