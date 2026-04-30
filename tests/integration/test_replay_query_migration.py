import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))

from hopilot.database import DatabaseConnection

from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.replay_query_service import ReplayQueryService
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.models import (
    AggregatedMetric,
    GameState,
    HandMatrix,
    MatrixCell,
    Player,
    Simulation,
)


def _seed_raw_run_with_aggregation(conn: DatabaseConnection, run_name: str, parameters: dict):
    with conn.session_scope() as session:
        simulation = Simulation(
            name=run_name,
            parameters=dict(parameters),
            start_timestamp=datetime.now(timezone.utc),
            end_timestamp=datetime.now(timezone.utc),
        )
        session.add(simulation)
        session.flush()

        game_state = GameState(
            timestamp=datetime.now(timezone.utc),
            round='preflop',
            pot_size=20.0,
            board_cards_str='AsAh,KsKh,QhJh',
            outcome='hero_win',
        )
        session.add(game_state)
        session.flush()

        session.add(Player(
            game_state_id=game_state.id,
            position='UTG',
            hole_cards='AsAh',
            stack_size=100.0,
            is_hero=True,
        ))
        session.add(Player(
            game_state_id=game_state.id,
            position='BTN',
            hole_cards='KdKh',
            stack_size=100.0,
            is_hero=False,
        ))

        simulation.parameters['raw_game_state_id_start'] = game_state.id
        simulation.parameters['raw_game_state_id_end'] = game_state.id

        matrix = HandMatrix(simulation_id=simulation.id, matrix_size='13x13')
        session.add(matrix)
        session.flush()

        cell = MatrixCell(
            matrix_id=matrix.id,
            row_index=0,
            col_index=0,
            hand_combination='AA vs KK',
        )
        session.add(cell)
        session.flush()

        session.add(AggregatedMetric(
            cell_id=cell.id,
            equity=0.55,
            jackpot_adjusted_ev=0.55,
            convergence_status='AVAILABLE',
            last_updated=datetime.now(timezone.utc),
        ))

        session.commit()

        return simulation, matrix


class TestReplayQueryMigration:
    def test_ambiguous_exact_contract_disambiguation(self):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.db')
        db_url = f'sqlite:///{db_path}'

        try:
            conn = DatabaseConnection(db_url)
            conn.create_tables()

            service = ReplayQueryService(
                db_connection=conn,
                simulation_repository=SimulationRepository(conn),
                game_state_repository=GameStateRepository(conn),
            )

            scenario_contract = {
                'selected_position': 'UTG',
                'hero_action': 'FOLD',
                'position_actions': {'UTG': 'FOLD', 'BTN': 'ALL_IN', 'SB': 'FOLD', 'BB': 'FOLD'},
                'active_players': ['BTN'],
                'num_opponents': 1,
                'pot_size': 20.0,
                'bet_amount': 10.0,
                'sims_per_combo': 120,
                'num_simulations': 120,
                'matrix_size': '13x13',
                'game_type': 'cash',
                'run_kind': 'matrix_sweep',
                'raw_game_state_id_start': None,
                'raw_game_state_id_end': None,
            }

            _seed_raw_run_with_aggregation(conn, 'raw_run_1', scenario_contract)
            _seed_raw_run_with_aggregation(conn, 'raw_run_2', scenario_contract)

            result = service.query_raw_run(scenario_contract=scenario_contract)

            assert result['status'] == 'DISAMBIGUATION_REQUIRED'
            assert result['game_states'] == []
            assert len(result['matched_runs']) == 2
            assert all('simulation_id' in run for run in result['matched_runs'])
        finally:
            try:
                conn.close()
            except Exception:
                pass
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_explicit_run_selection_success_path(self):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.db')
        db_url = f'sqlite:///{db_path}'

        try:
            conn = DatabaseConnection(db_url)
            conn.create_tables()

            service = ReplayQueryService(
                db_connection=conn,
                simulation_repository=SimulationRepository(conn),
                game_state_repository=GameStateRepository(conn),
            )

            scenario_contract = {
                'selected_position': 'UTG',
                'hero_action': 'FOLD',
                'position_actions': {'UTG': 'FOLD', 'BTN': 'ALL_IN', 'SB': 'FOLD', 'BB': 'FOLD'},
                'active_players': ['BTN'],
                'num_opponents': 1,
                'pot_size': 20.0,
                'bet_amount': 10.0,
                'sims_per_combo': 120,
                'num_simulations': 120,
                'matrix_size': '13x13',
                'game_type': 'cash',
                'run_kind': 'matrix_sweep',
                'raw_game_state_id_start': None,
                'raw_game_state_id_end': None,
            }

            simulation_a, _ = _seed_raw_run_with_aggregation(conn, 'raw_run_3', scenario_contract)
            simulation_b, _ = _seed_raw_run_with_aggregation(conn, 'raw_run_4', scenario_contract)

            assert simulation_a.id != simulation_b.id

            result = service.query_raw_run(
                scenario_contract=scenario_contract,
                explicit_run_id=simulation_b.id,
            )

            assert result['status'] == 'AVAILABLE'
            assert len(result['game_states']) == 1
            assert result['matched_runs'][0]['simulation_id'] == simulation_b.id
        finally:
            try:
                conn.close()
            except Exception:
                pass
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summary_to_raw_linking_preserves_raw_query_shape(self):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.db')
        db_url = f'sqlite:///{db_path}'

        try:
            conn = DatabaseConnection(db_url)
            conn.create_tables()

            service = ReplayQueryService(
                db_connection=conn,
                simulation_repository=SimulationRepository(conn),
                game_state_repository=GameStateRepository(conn),
            )

            scenario_contract = {
                'selected_position': 'UTG',
                'hero_action': 'FOLD',
                'position_actions': {'UTG': 'FOLD', 'BTN': 'ALL_IN', 'SB': 'FOLD', 'BB': 'FOLD'},
                'active_players': ['BTN'],
                'num_opponents': 1,
                'pot_size': 20.0,
                'bet_amount': 10.0,
                'sims_per_combo': 120,
                'num_simulations': 120,
                'matrix_size': '13x13',
                'game_type': 'cash',
                'run_kind': 'matrix_sweep',
                'raw_game_state_id_start': None,
                'raw_game_state_id_end': None,
            }

            simulation, _ = _seed_raw_run_with_aggregation(conn, 'raw_run_5', scenario_contract)
            summary = SimulationRepository(conn).get_matrix_sweep_summary(simulation.id)

            direct_result = service.query_raw_run(simulation_id=simulation.id)
            summary_result = service.query_raw_run_from_summary(summary)

            assert summary_result['status'] == direct_result['status']
            assert summary_result['matched_runs'] == direct_result['matched_runs']
            assert summary_result['game_states'] == direct_result['game_states']
        finally:
            try:
                conn.close()
            except Exception:
                pass
            shutil.rmtree(temp_dir, ignore_errors=True)
