import os
import tempfile
from datetime import datetime, timezone

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.matrix_sweep_contract import build_run_parameters
from hopilot.gto.precompute_job_repository import PrecomputeJobRepository
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.models import (
    AggregatedMetric,
    GameState,
    HandMatrix,
    MatrixCell,
    Player,
    Simulation,
)


class TestDatabaseRepositoryPrecomputePersistence:
    @pytest.fixture(scope="function")
    def test_db(self):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        db_url = f"sqlite:///{db_path}"

        conn = DatabaseConnection(db_url)
        conn.create_tables()
        yield conn

        try:
            conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception:
            pass

    def test_precompute_job_session_and_scenario_link_persistence(self, test_db):
        repo = PrecomputeJobRepository(test_db)

        job_session_id = repo.create_precompute_job_session(
            scenario_fingerprint="test-fingerprint",
            requested_scenarios=2,
        )
        assert job_session_id > 0

        session = repo.get_precompute_job_session(job_session_id)
        assert session is not None
        assert session.run_state == "RUNNING"
        assert session.requested_scenarios == 2
        assert session.completed_scenarios == 0
        assert session.failed_scenarios == 0

        scenario_link_id = repo.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=0,
            scenario_key="UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
            scenario_contract={"selected_position": "UTG"},
            status="PENDING",
        )
        assert scenario_link_id > 0

        links = repo.get_scenario_run_links_for_job(job_session_id)
        assert len(links) == 1
        assert links[0].scenario_index == 0
        assert links[0].status == "PENDING"

        repo.update_scenario_run_link(
            scenario_link_id,
            status="RUNNING",
        )
        updated_link = repo.get_scenario_run_link(scenario_link_id)
        assert updated_link is not None
        assert updated_link.status == "RUNNING"

        repo.update_precompute_job_session(
            job_session_id,
            completed_scenarios=1,
            failed_scenarios=0,
        )
        session = repo.get_precompute_job_session(job_session_id)
        assert session.completed_scenarios == 1
        assert session.failed_scenarios == 0

    def test_get_scenario_run_links_for_job_returns_ordered_links(self, test_db):
        repo = PrecomputeJobRepository(test_db)

        job_session_id = repo.create_precompute_job_session(
            scenario_fingerprint="ordered-fingerprint",
            requested_scenarios=3,
        )

        repo.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=2,
            scenario_key="third",
            scenario_contract={"selected_position": "BTN"},
            status="PENDING",
        )
        repo.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=0,
            scenario_key="first",
            scenario_contract={"selected_position": "UTG"},
            status="PENDING",
        )
        repo.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=1,
            scenario_key="second",
            scenario_contract={"selected_position": "MP"},
            status="PENDING",
        )

        links = repo.get_scenario_run_links_for_job(job_session_id)
        assert [link.scenario_key for link in links] == ["first", "second", "third"]

    def test_list_matrix_sweep_runs_by_contract_returns_matching_runs(self, test_db):
        sim_repo = SimulationRepository(test_db)
        scenario_contract = {
            "selected_position": "UTG",
            "hero_action": "FOLD",
            "position_actions": {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
            "active_players": ["BTN"],
            "num_opponents": 1,
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "sims_per_combo": 120,
            "matrix_size": "13x13",
            "game_type": "cash",
            "run_kind": "matrix_sweep",
            "raw_game_state_id_start": 1,
            "raw_game_state_id_end": 2,
        }
        parameters = build_run_parameters(scenario_contract, raw_game_state_id_start=1)

        with test_db.session_scope() as session:
            simulation = Simulation(
                name="list-matching-run",
                parameters=parameters,
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc),
            )
            session.add(simulation)
            session.flush()
            simulation_id = simulation.id

        matrix_id = sim_repo.get_or_create_hand_matrix_for_simulation(simulation_id)
        with test_db.session_scope() as session:
            cell = MatrixCell(
                matrix_id=matrix_id,
                row_index=0,
                col_index=0,
                hand_combination="AA vs KK",
            )
            session.add(cell)
            session.flush()

            session.add(AggregatedMetric(
                cell_id=cell.id,
                equity=0.42,
                jackpot_adjusted_ev=0.42,
                convergence_status="AVAILABLE",
                last_updated=datetime.now(timezone.utc),
            ))

        result = sim_repo.list_matrix_sweep_runs_by_contract(scenario_contract)
        assert len(result) == 1
        assert result[0].id == simulation.id

    def test_resolve_scenario_run_selection_returns_none_for_ambiguous_matches(self, test_db):
        sim_repo = SimulationRepository(test_db)
        scenario_contract = {
            "selected_position": "UTG",
            "hero_action": "FOLD",
            "position_actions": {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
            "active_players": ["BTN"],
            "num_opponents": 1,
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "sims_per_combo": 120,
            "matrix_size": "13x13",
            "game_type": "cash",
            "run_kind": "matrix_sweep",
            "raw_game_state_id_start": 1,
            "raw_game_state_id_end": 2,
        }
        parameters = build_run_parameters(scenario_contract, raw_game_state_id_start=1)

        simulation_ids = []
        with test_db.session_scope() as session:
            for idx in range(2):
                simulation = Simulation(
                    name=f"ambiguous-run-{idx}",
                    parameters=parameters,
                    start_timestamp=datetime.now(timezone.utc),
                    end_timestamp=datetime.now(timezone.utc),
                )
                session.add(simulation)
                session.flush()
                simulation_ids.append(simulation.id)

        for idx, simulation_id in enumerate(simulation_ids):
            matrix_id = sim_repo.get_or_create_hand_matrix_for_simulation(simulation_id)
            with test_db.session_scope() as session:
                cell = MatrixCell(
                    matrix_id=matrix_id,
                    row_index=0,
                    col_index=0,
                    hand_combination="AA vs KK",
                )
                session.add(cell)
                session.flush()
                session.add(AggregatedMetric(
                    cell_id=cell.id,
                    equity=0.5 + 0.01 * idx,
                    jackpot_adjusted_ev=0.5 + 0.01 * idx,
                    convergence_status="AVAILABLE",
                    last_updated=datetime.now(timezone.utc),
                ))

        # Inline resolve_scenario_run_selection: select from matches using explicit_run_id
        matches = sim_repo.list_matrix_sweep_runs_by_contract(scenario_contract)
        selected = None if len(matches) != 1 else matches[0]
        assert selected is None
        assert len(matches) == 2

        explicit_run_id = matches[0].id
        explicit_selected = next((run for run in matches if run.id == explicit_run_id), None)
        assert explicit_selected is not None
        assert explicit_selected.id == matches[0].id
        assert len(matches) == 2

    def test_get_run_raw_projection_returns_hero_hole_cards_and_ascending_order(self, test_db):
        gs_repo = GameStateRepository(test_db)
        with test_db.session_scope() as session:
            game_state_1 = GameState(
                timestamp=datetime.now(timezone.utc),
                round="preflop",
                pot_size=20.0,
                board_cards_str="As,Ks,Qd",
                outcome="hero_win",
            )
            session.add(game_state_1)
            session.flush()
            session.add(Player(
                game_state_id=game_state_1.id,
                position="UTG",
                hole_cards="AsAh",
                stack_size=100.0,
                is_hero=True,
            ))
            session.add(Player(
                game_state_id=game_state_1.id,
                position="BTN",
                hole_cards="KdKh",
                stack_size=100.0,
                is_hero=False,
            ))

            game_state_2 = GameState(
                timestamp=datetime.now(timezone.utc),
                round="preflop",
                pot_size=30.0,
                board_cards_str="",
                outcome="villain_win",
            )
            session.add(game_state_2)
            session.flush()
            session.add(Player(
                game_state_id=game_state_2.id,
                position="UTG",
                hole_cards="QsQh",
                stack_size=100.0,
                is_hero=True,
            ))
            session.add(Player(
                game_state_id=game_state_2.id,
                position="BTN",
                hole_cards="JhJd",
                stack_size=100.0,
                is_hero=False,
            ))

        projection = gs_repo.get_run_raw_projection(game_state_1.id, game_state_2.id)
        assert len(projection) == 2
        assert projection[0]["game_state_id"] == game_state_1.id
        assert projection[0]["hero_hole_cards"] == "AsAh"
        assert projection[1]["game_state_id"] == game_state_2.id
