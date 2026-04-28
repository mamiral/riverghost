#!/usr/bin/env python3
"""
Comprehensive Analytical Query Integration Tests.

This module tests the complete analytical query pipeline including:
- Game replay queries
- Convergence analysis queries
- Jackpot frequency analysis queries

Tests verify that all queries work together and produce consistent results.
"""

import pytest
import sys
import os
import shutil
import tempfile
from datetime import datetime, timezone

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.game_replay_queries import GameReplayQueryEngine
from hopilot.gto.convergence_analysis_queries import ConvergenceAnalysisQueries
from hopilot.gto.jackpot_frequency_queries import JackpotFrequencyQueries
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.matrix_cells_derivation import MatrixCellsDerivationEngine
from hopilot.gto.replay_query_service import ReplayQueryService
from hopilot.gto.query_builder import PredefinedQueries
from hopilot.models import (
    AggregatedMetric,
    GameState,
    HandMatrix,
    MatrixCell,
    Player,
    Simulation,
)


@pytest.fixture
def comprehensive_test_db():
    """Create a comprehensive test database with all analytical data."""
    temp_dir = tempfile.mkdtemp(prefix='comprehensive_test_db_', dir=os.path.dirname(__file__))
    db_path = os.path.join(temp_dir, 'comprehensive_test.db')
    db_url = f'sqlite:///{db_path}'

    if os.path.exists(db_path):
        os.remove(db_path)
    conn = DatabaseConnection(db_url)
    conn.create_tables()

    repo = DatabaseRepository(db_url)
    derivation_engine = MatrixCellsDerivationEngine(db_url)

    # Create simulation and matrix
    sim_params = '{"num_simulations": 10000, "matrix_size": "13x13", "game_type": "NLHE"}'
    sim_id = repo.create_simulation(sim_params)
    matrix_id = repo.create_hand_matrix(sim_id)

    # Create multiple MatrixCells for comprehensive testing
    cells_data = []
    hand_combinations = ["AA vs AK", "KK vs QQ", "AK vs AQ"]

    for i, hand_combo in enumerate(hand_combinations):
        cell_id = derivation_engine._ensure_matrix_cell_exists(matrix_id, i, 0, hand_combo)
        cells_data.append((i, 0, cell_id, hand_combo))

    # Create comprehensive game data
    total_games = 3000  # 1000 games per hand combination
    jackpot_games = 0
    sample_game_state_id = None
    sample_outcome = None

    for game_idx in range(total_games):
        cell_idx = game_idx // 1000  # Rotate through hand combinations
        row_idx, col_idx, cell_id, hand_combo = cells_data[cell_idx]

        # Create game state with varying outcomes
        outcome_patterns = ['win', 'loss', 'win', 'win', 'loss']  # 60% win rate
        outcome = outcome_patterns[game_idx % 5]

        gs_data = {
            'pot_size': 1000 + (game_idx % 500),  # Vary pot sizes
            'board_cards_str': 'As,Ks,Qs,Js,Ts',
            'round': 'preflop',
            'outcome': outcome
        }
        gs_id = repo.create_game_state(gs_data)
        if game_idx == 0:
            sample_game_state_id = gs_id
            sample_outcome = outcome

        # Create players
        for player_idx in range(2):  # Hero and villain
            player_data = {
                'game_state_id': gs_id,
                'position': 'hero' if player_idx == 0 else 'villain',
                'hole_cards': 'AsAh' if player_idx == 0 else 'AsKd',
                'stack_size': 10000,
                'is_hero': player_idx == 0
            }
            player_id = repo.create_player(player_data)

            # Create some bets
            if game_idx % 3 == 0:  # Some games have bets
                bet_data = {
                    'game_state_id': gs_id,
                    'player_id': player_id,
                    'amount': 100 + (game_idx % 200),
                    'action_type': 'raise',
                    'round': 'preflop'
                }
                repo.create_bet(bet_data)

            # Create jackpots for some games
            if game_idx % 30 == 0:  # ~3% jackpot rate
                jackpot_data = {
                    'game_state_id': gs_id,
                    'player_id': player_id,
                    'jackpot_type': 'ROYAL_FLUSH' if game_idx % 60 == 0 else 'STRAIGHT_FLUSH',
                    'payout_amount': 5000 if game_idx % 60 == 0 else 1000,
                    'qualifying_cards': ['As', 'Ks', 'Qs', 'Js', 'Ts'] if game_idx % 60 == 0 else ['As', 'Ks', 'Qs', 'Js', '9s'],
                    'payout_multiplier': 500 if game_idx % 60 == 0 else 100
                }
                repo.create_jackpot(jackpot_data)
                jackpot_games += 1

    yield db_url, matrix_id, cells_data, total_games, jackpot_games, sample_game_state_id, sample_outcome

    # Cleanup
    try:
        repo.connection.close()
        repo.aggregation_engine.db_connection.close()
        conn.close()
    except Exception:
        pass

    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


def _create_raw_run(
    repo: DatabaseRepository,
    run_name: str,
    parameters: dict,
    game_state_rows: list[dict],
):
    with repo.connection.session_scope() as session:
        simulation = Simulation(
            name=run_name,
            parameters=dict(parameters),
            start_timestamp=datetime.now(timezone.utc),
            end_timestamp=datetime.now(timezone.utc),
        )
        session.add(simulation)
        session.flush()

        created_states = []
        for row in game_state_rows:
            game_state = GameState(
                timestamp=datetime.now(timezone.utc),
                round='preflop',
                pot_size=row.get('pot_size', 20.0),
                board_cards_str=row.get('board_cards_str', ''),
                outcome=row.get('outcome'),
            )
            session.add(game_state)
            session.flush()

            for player_data in row.get('players', []):
                session.add(Player(
                    game_state_id=game_state.id,
                    position=player_data['position'],
                    hole_cards=player_data['hole_cards'],
                    stack_size=player_data.get('stack_size', 100.0),
                    is_hero=player_data.get('is_hero', False),
                ))

            created_states.append(game_state)

        if created_states:
            simulation.parameters['raw_game_state_id_start'] = created_states[0].id
            simulation.parameters['raw_game_state_id_end'] = created_states[-1].id
        else:
            simulation.parameters['raw_game_state_id_start'] = None
            simulation.parameters['raw_game_state_id_end'] = None

        session.add(simulation)
        session.commit()

        return simulation, created_states


class TestAnalyticalQueryIntegration:
    """Comprehensive integration tests for all analytical queries."""

    def test_complete_analytical_pipeline(self, comprehensive_test_db):
        """Test the complete analytical query pipeline from data to insights."""
        db_url, matrix_id, cells_data, total_games, jackpot_games, sample_game_state_id, sample_outcome = comprehensive_test_db

        # Initialize all query engines
        replay_engine = GameReplayQueryEngine(db_url)
        conv_engine = ConvergenceAnalysisQueries(db_url)
        jackpot_engine = JackpotFrequencyQueries(db_url)

        # Test 1: Game Replay - Get a sample game
        replay_result = replay_engine.replay_game_sequence(sample_game_state_id, include_player_details=True)

        assert replay_result is not None
        assert replay_result['game_state_id'] == sample_game_state_id
        assert 'sequence' in replay_result
        assert replay_result['final_outcome'] == sample_outcome
        assert replay_result['hand_combination'] is not None

        # Guard: analytical pipeline should operate from raw GameState rows, not legacy board_cards_id or cell_id.
        repo = DatabaseRepository(db_url)
        raw_state = repo.get_game_state(sample_game_state_id)
        assert raw_state is not None
        assert raw_state['board_cards_str'] == 'As,Ks,Qs,Js,Ts'
        assert 'board_cards_id' not in raw_state
        assert 'cell_id' not in raw_state

        # Test 2: Convergence Analysis - Get equity convergence
        conv_result = conv_engine.get_equity_convergence_series(
            matrix_id, 0, 0, sample_intervals=[500, 1000, 2000]
        )

        assert conv_result is not None
        assert conv_result['matrix_id'] == matrix_id
        assert conv_result['row_idx'] == 0
        assert conv_result['col_idx'] == 0
        assert len(conv_result['convergence_series']) >= 2

        # Verify equity values are reasonable
        for point in conv_result['convergence_series']:
            assert 0.0 <= point['equity'] <= 1.0
            assert point['sample_count'] in [500, 1000, 2000]

        # Test 3: Convergence Statistics
        conv_stats = conv_engine.get_convergence_statistics(matrix_id, min_samples=500)

        assert conv_stats is not None
        assert conv_stats['matrix_id'] == matrix_id
        assert conv_stats['cells_analyzed'] >= 1
        assert 'convergence_data' in conv_stats

        # Test 4: Jackpot Frequency Analysis
        jackpot_freq = jackpot_engine.get_jackpot_frequency_analysis(matrix_id)

        assert jackpot_freq is not None
        assert jackpot_freq['total_games'] == total_games
        assert jackpot_freq['total_jackpots'] == jackpot_games
        assert 'jackpot_types' in jackpot_freq

        # Test 5: Jackpot EV Impact by Hand
        jackpot_ev = jackpot_engine.get_jackpot_ev_impact_by_hand(matrix_id)

        assert jackpot_ev is not None
        assert jackpot_ev['matrix_id'] == matrix_id
        assert len(jackpot_ev['hand_analysis']) >= 1

        # Test 6: Cross-query consistency checks
        # Verify that jackpot frequency from frequency analysis matches EV analysis
        if jackpot_freq['jackpot_types']:
            total_freq_jackpots = sum(jt['count'] for jt in jackpot_freq['jackpot_types'].values())
            total_ev_jackpots = sum(h['total_jackpots'] for h in jackpot_ev['hand_analysis'])

            assert total_freq_jackpots == total_ev_jackpots

        # Verify convergence data makes sense
        if conv_stats['convergence_data']:
            for cell_data in conv_stats['convergence_data']:
                assert 'initial_equity' in cell_data
                assert 'final_equity' in cell_data
                assert 'equity_change' in cell_data
                # Equity change should be reasonable (not all identical)
                assert isinstance(cell_data['equity_change'], (int, float))

        # Guard: analytical pipeline should operate from raw GameState rows, not legacy board_cards_id or cell_id.
        raw_state = repo.get_game_state(sample_game_state_id)
        assert raw_state is not None
        assert raw_state['board_cards_str'] == 'As,Ks,Qs,Js,Ts'
        assert 'board_cards_id' not in raw_state
        assert 'cell_id' not in raw_state

    def test_query_raw_run_scopes_by_simulation_and_hand_matrix_boundary(self):
        """Verify raw GameState rows are returned only for the selected run boundary."""
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test_db_raw_run')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        db_path = os.path.join(temp_dir, 'test.db')
        db_url = f'sqlite:///{db_path}'

        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            conn = DatabaseConnection(db_url)
            conn.create_tables()
            repo = DatabaseRepository(db_url)
            service = ReplayQueryService(repo)

            parameters = {
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
            }

            simulation, game_states = _create_raw_run(
                repo,
                run_name="raw_run_boundary",
                parameters=parameters,
                game_state_rows=[
                    {
                        'round': 'preflop',
                        'pot_size': 20.0,
                        'board_cards_str': 'AsAh,KsKd,QhJh',
                        'outcome': 'hero_win',
                        'players': [
                            {'position': 'UTG', 'hole_cards': 'AsAh', 'stack_size': 100.0, 'is_hero': True},
                            {'position': 'BTN', 'hole_cards': 'KdKh', 'stack_size': 100.0, 'is_hero': False},
                        ],
                    },
                    {
                        'round': 'flop',
                        'pot_size': 30.0,
                        'board_cards_str': 'AsAh,KsKd,QhJh,Ts9s',
                        'outcome': 'hero_loss',
                        'players': [
                            {'position': 'UTG', 'hole_cards': 'AsAh', 'stack_size': 100.0, 'is_hero': True},
                            {'position': 'BTN', 'hole_cards': 'KdKh', 'stack_size': 100.0, 'is_hero': False},
                        ],
                    },
                ],
            )

            assert simulation.parameters['raw_game_state_id_start'] is not None
            assert simulation.parameters['raw_game_state_id_end'] is not None

            raw_result = service.query_raw_run(simulation_id=simulation.id)
            assert raw_result['status'] == 'AVAILABLE'
            assert len(raw_result['game_states']) == 2
            assert [row['game_state_id'] for row in raw_result['game_states']] == [state.id for state in game_states]
            assert raw_result['matched_runs'][0]['simulation_id'] == simulation.id

            matrix_id = repo.get_or_create_hand_matrix_for_simulation(simulation.id)
            matrix_result = service.query_raw_run(hand_matrix_id=matrix_id)
            assert matrix_result['status'] == 'AVAILABLE'
            assert matrix_result['matched_runs'][0]['simulation_id'] == simulation.id
            assert len(matrix_result['game_states']) == 2

        finally:
            try:
                if 'conn' in locals():
                    conn.close()
                if os.path.exists(db_path):
                    os.remove(db_path)
                os.rmdir(temp_dir)
            except Exception:
                pass

    def test_query_raw_run_exact_scenario_contract_unique_match(self):
        """Verify exact scenario-contract raw run selection returns only the unique matching run."""
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test_db_raw_run_contract')
        os.makedirs(temp_dir, exist_ok=True)
        db_path = os.path.join(temp_dir, 'test.db')
        db_url = f'sqlite:///{db_path}'

        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            conn = DatabaseConnection(db_url)
            conn.create_tables()
            repo = DatabaseRepository(db_url)
            service = ReplayQueryService(repo)

            parameters = {
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
            }

            simulation, game_states = _create_raw_run(
                repo,
                run_name="raw_run_contract",
                parameters=parameters,
                game_state_rows=[
                    {
                        'round': 'preflop',
                        'pot_size': 20.0,
                        'board_cards_str': 'AsAh,KsKd',
                        'outcome': 'hero_win',
                        'players': [
                            {'position': 'UTG', 'hole_cards': 'AsAh', 'stack_size': 100.0, 'is_hero': True},
                            {'position': 'BTN', 'hole_cards': 'KdKh', 'stack_size': 100.0, 'is_hero': False},
                        ],
                    }
                ],
            )

            matrix_id = repo.get_or_create_hand_matrix_for_simulation(simulation.id)
            with repo.connection.session_scope() as session:
                cell = MatrixCell(matrix_id=matrix_id, row_index=0, col_index=0, hand_combination="AA vs KK")
                session.add(cell)
                session.flush()
                session.add(AggregatedMetric(
                    cell_id=cell.id,
                    equity=0.55,
                    jackpot_adjusted_ev=0.55,
                    convergence_status="AVAILABLE",
                    last_updated=datetime.now(timezone.utc),
                ))
                session.commit()

            scenario_contract = dict(parameters)
            scenario_contract["raw_game_state_id_start"] = simulation.parameters["raw_game_state_id_start"]
            scenario_contract["raw_game_state_id_end"] = simulation.parameters["raw_game_state_id_end"]

            raw_result = service.query_raw_run(scenario_contract=scenario_contract)
            assert raw_result['status'] == 'AVAILABLE'
            assert len(raw_result['game_states']) == 1
            assert raw_result['matched_runs'][0]['simulation_id'] == simulation.id

        finally:
            try:
                if 'conn' in locals():
                    conn.close()
                if os.path.exists(db_path):
                    os.remove(db_path)
                os.rmdir(temp_dir)
            except Exception:
                pass

    def test_query_raw_run_with_missing_boundaries_returns_empty_scope(self):
        """Verify missing raw boundaries produce EMPTY_SCOPE instead of bad data."""
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test_db_raw_run_empty')
        os.makedirs(temp_dir, exist_ok=True)
        db_path = os.path.join(temp_dir, 'test.db')
        db_url = f'sqlite:///{db_path}'

        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            conn = DatabaseConnection(db_url)
            conn.create_tables()
            repo = DatabaseRepository(db_url)
            service = ReplayQueryService(repo)

            parameters = {
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
                "raw_game_state_id_start": None,
                "raw_game_state_id_end": None,
            }

            with repo.connection.session_scope() as session:
                simulation = Simulation(
                    name="raw_run_missing_boundaries",
                    parameters=dict(parameters),
                    start_timestamp=datetime.now(timezone.utc),
                    end_timestamp=datetime.now(timezone.utc),
                )
                session.add(simulation)
                session.flush()
                simulation_id = simulation.id
                session.commit()

            raw_result = service.query_raw_run(simulation_id=simulation_id)
            assert raw_result['status'] == 'EMPTY_SCOPE'
            assert raw_result['game_states'] == []
            assert raw_result['matched_runs'][0]['simulation_id'] == simulation_id

        finally:
            try:
                if 'conn' in locals():
                    conn.close()
                if os.path.exists(db_path):
                    os.remove(db_path)
                os.rmdir(temp_dir)
            except Exception:
                pass

    def test_analytical_query_performance_under_load(self, comprehensive_test_db):
        """Test that analytical queries perform well under load."""
        import time

        db_url, matrix_id, cells_data, total_games, jackpot_games, _sample_game_state_id, _sample_outcome = comprehensive_test_db

        conv_engine = ConvergenceAnalysisQueries(db_url)
        jackpot_engine = JackpotFrequencyQueries(db_url)

        # Test convergence analysis performance
        start_time = time.time()
        result = conv_engine.get_convergence_statistics(matrix_id, min_samples=500)
        conv_time = time.time() - start_time

        assert conv_time < 5.0, f"Convergence analysis too slow: {conv_time:.2f}s"

        # Test jackpot analysis performance
        start_time = time.time()
        result = jackpot_engine.get_jackpot_frequency_analysis(matrix_id)
        jackpot_time = time.time() - start_time

        assert jackpot_time < 2.0, f"Jackpot analysis too slow: {jackpot_time:.2f}s"

        # Test temporal analysis performance
        start_time = time.time()
        result = jackpot_engine.get_jackpot_temporal_analysis(matrix_id)
        temporal_time = time.time() - start_time

        assert temporal_time < 3.0, f"Temporal analysis too slow: {temporal_time:.2f}s"

    def test_analytical_query_data_consistency(self, comprehensive_test_db):
        """Test that analytical queries produce consistent and valid data."""
        db_url, matrix_id, cells_data, total_games, jackpot_games, _sample_game_state_id, _sample_outcome = comprehensive_test_db

        conv_engine = ConvergenceAnalysisQueries(db_url)
        jackpot_engine = JackpotFrequencyQueries(db_url)

        # Get convergence data
        conv_result = conv_engine.get_equity_convergence_series(matrix_id, 0, 0, [500, 1000, 1500])

        # Get jackpot data
        jackpot_result = jackpot_engine.get_jackpot_frequency_analysis(matrix_id)

        # Verify data types and ranges
        if conv_result:
            for point in conv_result['convergence_series']:
                assert isinstance(point['equity'], (int, float))
                assert 0.0 <= point['equity'] <= 1.0
                assert isinstance(point['sample_count'], int)
                assert point['sample_count'] > 0

        if jackpot_result:
            assert isinstance(jackpot_result['overall_frequency'], (int, float))
            assert 0.0 <= jackpot_result['overall_frequency'] <= 1.0
            assert isinstance(jackpot_result['total_ev_impact'], (int, float))
            assert jackpot_result['total_ev_impact'] >= 0

            for jt_data in jackpot_result['jackpot_types'].values():
                assert isinstance(jt_data['frequency'], (int, float))
                assert 0.0 <= jt_data['frequency'] <= 1.0
                assert isinstance(jt_data['ev_impact'], (int, float))
                assert jt_data['ev_impact'] >= 0

    def test_analytical_query_error_handling(self, comprehensive_test_db):
        """Test error handling in analytical queries."""
        db_url, matrix_id, cells_data, total_games, jackpot_games, _sample_game_state_id, _sample_outcome = comprehensive_test_db

        conv_engine = ConvergenceAnalysisQueries(db_url)
        jackpot_engine = JackpotFrequencyQueries(db_url)

        # Test with non-existent matrix
        result = conv_engine.get_equity_convergence_series(99999, 0, 0)
        assert result is None

        result = jackpot_engine.get_jackpot_frequency_analysis(99999)
        assert result == {}  # Should return empty dict for insufficient data

        # Test with invalid parameters
        result = conv_engine.get_convergence_statistics(matrix_id, min_samples=50000)  # More than available
        assert result is None or result['cells_analyzed'] == 0

    def test_analytical_query_mathematical_correctness(self, comprehensive_test_db):
        """Test mathematical correctness of analytical calculations."""
        db_url, matrix_id, cells_data, total_games, jackpot_games, _sample_game_state_id, _sample_outcome = comprehensive_test_db

        jackpot_engine = JackpotFrequencyQueries(db_url)

        # Test jackpot EV calculations
        freq_result = jackpot_engine.get_jackpot_frequency_analysis(matrix_id)
        ev_result = jackpot_engine.get_jackpot_ev_impact_by_hand(matrix_id)

        if freq_result and ev_result:
            # Verify EV impact calculations
            for jt_name, jt_data in freq_result['jackpot_types'].items():
                expected_ev = jt_data['frequency'] * jt_data['avg_payout']
                assert abs(jt_data['ev_impact'] - expected_ev) < 0.001

            # Verify total EV impact
            total_calculated_ev = sum(jt_data['ev_impact'] for jt_data in freq_result['jackpot_types'].values())
            assert abs(freq_result['total_ev_impact'] - total_calculated_ev) < 0.001

            # Verify frequency calculations
            expected_overall_freq = freq_result['total_jackpots'] / freq_result['total_games']
            assert abs(freq_result['overall_frequency'] - expected_overall_freq) < 0.001

    def test_analytical_query_integration_workflow(self, comprehensive_test_db):
        """Test a complete analytical workflow from data to insights."""
        db_url, matrix_id, cells_data, total_games, jackpot_games, _sample_game_state_id, _sample_outcome = comprehensive_test_db

        # Step 1: Analyze convergence
        conv_engine = ConvergenceAnalysisQueries(db_url)
        conv_series = conv_engine.get_equity_convergence_series(matrix_id, 0, 0, [1000, 2000])
        conv_stats = conv_engine.get_convergence_statistics(matrix_id, min_samples=500)

        # Step 2: Analyze jackpot impact
        jackpot_engine = JackpotFrequencyQueries(db_url)
        jackpot_freq = jackpot_engine.get_jackpot_frequency_analysis(matrix_id)
        jackpot_ev = jackpot_engine.get_jackpot_ev_impact_by_hand(matrix_id)

        # Step 3: Verify workflow produces actionable insights
        insights = {
            'has_convergence_data': conv_series is not None and len(conv_series['convergence_series']) > 0,
            'has_jackpot_data': bool(jackpot_freq.get('jackpot_types')),
            'total_games_analyzed': total_games,
            'jackpot_rate': jackpot_freq.get('overall_frequency', 0) if jackpot_freq else 0,
            'cells_with_convergence': conv_stats['cells_analyzed'] if conv_stats else 0,
            'timestamp': datetime.now().isoformat()
        }

        # Verify all expected insights are present
        assert insights['has_convergence_data']
        assert insights['total_games_analyzed'] == total_games
        assert isinstance(insights['jackpot_rate'], (int, float))
        assert insights['jackpot_rate'] >= 0
        assert insights['cells_with_convergence'] >= 0

        print(f"Analytical workflow completed successfully: {insights}")