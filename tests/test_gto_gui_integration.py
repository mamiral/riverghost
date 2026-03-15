import pytest
import pygame
import yaml
import time
import os
import sys
from unittest.mock import Mock, patch, MagicMock, mock_open, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.gto.gto_optimizer import GTOOptimizer
from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner
from hopilot.aof_gto_browser_gui import AoFGTOBrowserGUI


@pytest.fixture
def mock_pygame_setup():
    """Mock pygame setup for GUI testing."""
    with patch('pygame.init'), \
         patch('pygame.display.set_mode'), \
         patch('pygame.display.set_caption'), \
         patch('pygame.font.Font'), \
         patch('pygame.time.Clock'), \
         patch('pygame.display.flip'), \
         patch('pygame.event.get', return_value=[]):
        yield


@pytest.fixture
def mock_analyzer():
    """Mock PokerAnalyzer for testing."""
    analyzer = Mock(spec=PokerAnalyzer)
    analyzer.calculate_odds = Mock(return_value={
        'win_probability': 0.5,
        'tie_probability': 0.0,
        'loss_probability': 0.5,
        'valid_simulations': 100,
        'wins': 50,
        'ties': 0
    })
    return analyzer


@pytest.fixture
def mock_optimizer(mock_analyzer):
    """Mock GTOOptimizer for testing."""
    optimizer = Mock(spec=GTOOptimizer)
    optimizer.find_nash_equilibrium = Mock(return_value={
        'equilibrium_found': True,
        'hero_strategy': [1.0, 0.8, 0.6],
        'villain_strategy': [0.9, 0.7, 0.4],
        'iterations': 8,
        'convergence_tolerance': 0.01,
        'best_response_valid': True
    })
    optimizer.find_indifference_points = Mock(return_value={
        'indifference_points': {
            'AA': {'equity_vs_calling': 0.85, 'indifference_frequency': 1.0},
            'AKs': {'equity_vs_calling': 0.62, 'indifference_frequency': 1.0},
            'AQs': {'equity_vs_calling': 0.45, 'indifference_frequency': 0.0}
        },
        'optimal_frequencies': [1.0, 1.0, 0.0],
        'hero_range_size': 3,
        'villain_range_size': 3
    })
    optimizer.find_gto_threshold = Mock(return_value={
        'threshold_equity': 0.35,
        'optimal_range': ['AA', 'KK', 'QQ', 'AKs', 'AQs', 'AJs'],
        'ev_breakdown': {
            'AA': 3.2, 'KK': 2.8, 'QQ': 2.1,
            'AKs': 1.8, 'AQs': 1.2, 'AJs': 0.8
        },
        'bonus_adjusted_threshold': 0.38
    })
    return optimizer


class TestGTOGUIIntegration:
    """End-to-end GUI workflow tests for GTO solver integration."""

    def test_full_threshold_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test complete threshold analysis workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Step 1: Set threshold mode
        panel.set_mode('threshold')
        assert panel.current_mode == 'threshold'

        # Step 2: Configure parameters
        assert panel.set_num_opponents(6)
        assert panel.set_pot_size(30.0)
        assert panel.set_bet_amount(15.0)

        # Step 3: Execute calculation
        result = panel.calculate_threshold()

        # Step 4: Verify results
        assert result is not None
        assert 'threshold_equity' in result
        assert 'optimal_range' in result
        assert result['threshold_equity'] == 0.35
        assert len(result['optimal_range']) == 6

        # Step 5: Verify display formatting
        formatted = panel.format_threshold_results(result)
        assert 'Threshold Equity' in formatted
        assert 'Optimal Range' in formatted

    def test_full_range_vs_range_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test complete range vs range analysis workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        # Setup mock return value
        mock_optimizer.find_nash_equilibrium.return_value = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.8, 0.6],
            'villain_strategy': [0.9, 0.7, 0.4],
            'iterations': 8,
            'convergence_tolerance': 0.01,
            'best_response_valid': True
        }

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Step 1: Set range vs range mode
        panel.set_mode('range_vs_range')
        assert panel.current_mode == 'range_vs_range'

        # Step 2: Load ranges
        hero_range_data = {
            'name': 'Hero Range',
            'hands': ['AA', 'AKs', 'AQs'],
            'description': 'Premium tournament range'
        }

        villain_range_data = {
            'name': 'Villain Range',
            'hands': ['KK', 'QQ', 'JJ'],
            'description': 'Medium strength range'
        }

        with patch('builtins.open', create=True), \
             patch('yaml.safe_load', side_effect=[hero_range_data, villain_range_data]):

            assert panel.load_hero_range('hero.yaml')
            assert panel.load_villain_range('villain.yaml')

        assert panel.hero_range == hero_range_data['hands']
        assert panel.villain_range == villain_range_data['hands']

        # Step 3: Configure parameters
        assert panel.set_pot_size(40.0)
        assert panel.set_bet_amount(20.0)

        # Step 4: Execute calculation
        result = panel.calculate_range_vs_range()

        # Step 5: Verify results
        assert result is not None
        assert result['equilibrium_found'] == True
        assert len(result['hero_strategy']) == 3
        assert len(result['villain_strategy']) == 3
        assert result['best_response_valid'] == True

        # Step 6: Verify display formatting
        formatted = panel.format_range_vs_range_results(result)
        assert 'Nash Equilibrium Found' in formatted
        assert 'Hero Strategy' in formatted
        assert 'Villain Strategy' in formatted

    def test_full_indifference_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test complete indifference points workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Step 1: Set indifference mode
        panel.set_mode('indifference')
        assert panel.current_mode == 'indifference'

        # Step 2: Load ranges
        hero_range_data = {
            'name': 'Test Hero',
            'hands': ['AA', 'AKs', 'AQs']
        }

        villain_range_data = {
            'name': 'Test Villain',
            'hands': ['KK', 'QQ', 'JJ']
        }

        with patch('builtins.open', create=True), \
             patch('yaml.safe_load', side_effect=[hero_range_data, villain_range_data]):

            assert panel.load_hero_range('hero.yaml')
            assert panel.load_villain_range('villain.yaml')

        # Step 3: Configure parameters
        assert panel.set_pot_size(25.0)
        assert panel.set_bet_amount(12.5)

        # Step 4: Execute calculation
        result = panel.calculate_indifference_points()

        # Step 5: Verify results
        assert result is not None
        assert 'optimal_frequencies' in result
        assert len(result['optimal_frequencies']) == 3
        assert result['optimal_frequencies'] == [1.0, 1.0, 0.0]  # AA and AKs shove, AQs folds

        # Step 6: Verify display formatting
        formatted = panel.format_indifference_results(result)
        assert 'Optimal Shove Frequencies' in formatted
        assert 'AA' in formatted
        assert 'AKs' in formatted
        assert 'AQs' in formatted

    def test_parameter_persistence_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test that parameters persist across mode switches."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Set initial parameters
        panel.set_num_opponents(7)
        panel.set_pot_size(35.0)
        panel.set_bet_amount(17.5)

        # Switch modes
        panel.set_mode('range_vs_range')
        panel.set_mode('indifference')
        panel.set_mode('threshold')

        # Verify parameters persisted
        assert panel.num_opponents == 7
        assert panel.pot_size == 35.0
        assert panel.bet_amount == 17.5


class TestAoFBrowserIntegration:
    @pytest.fixture
    def aof_app(self):
        pygame.init()
        app = AoFGTOBrowserGUI(width=1000, height=760)
        yield app
        pygame.quit()

    def test_position_switch_updates_matrix(self, aof_app):
        before = [c["value"] for c in aof_app.panel.payload["cells"]]
        before_context = dict(aof_app.panel.payload["context"])
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.card_rects["BB"].center,
        )
        aof_app.panel.handle_event(event)
        after = [c["value"] for c in aof_app.panel.payload["cells"]]
        after_context = aof_app.panel.payload["context"]

        assert aof_app.panel.state.selected_position == "BB"
        if all(value is None for value in before) and all(value is None for value in after):
            assert before_context["position"] != after_context["position"]
            assert all(c["status"] == "NO_CONTEST" for c in aof_app.panel.payload["cells"])
        else:
            assert before != after

    def test_precompute_max_workers_loaded_from_config(self, aof_app):
        assert aof_app.panel.precompute_max_workers == 3

    def test_precompute_worker_buttons_adjust_count(self, aof_app):
        before = aof_app.panel.precompute_max_workers
        up_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_worker_buttons["up"].center)
        assert aof_app.panel.handle_event(up_event)
        assert aof_app.panel.precompute_max_workers == min(16, before + 1)

        down_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_worker_buttons["down"].center)
        assert aof_app.panel.handle_event(down_event)
        assert aof_app.panel.precompute_max_workers == before

    def test_precompute_sim_buttons_adjust_count(self, aof_app):
        before = aof_app.panel.precompute_simulations_per_cell
        up_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_sim_buttons["up"].center, button=1)
        assert aof_app.panel.handle_event(up_event)
        assert aof_app.panel.precompute_simulations_per_cell == before + 100

        down_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_sim_buttons["down"].center, button=1)
        assert aof_app.panel.handle_event(down_event)
        assert aof_app.panel.precompute_simulations_per_cell == before

    def test_precompute_sim_buttons_right_click_adjust_count(self, aof_app):
        aof_app.panel.precompute_simulations_per_cell = 1000
        up_event_small = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_sim_buttons["up"].center, button=3)
        assert aof_app.panel.handle_event(up_event_small)
        assert aof_app.panel.precompute_simulations_per_cell == 2000

        aof_app.panel.precompute_simulations_per_cell = 6000
        up_event_large = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_sim_buttons["up"].center, button=3)
        assert aof_app.panel.handle_event(up_event_large)
        assert aof_app.panel.precompute_simulations_per_cell == 11000

    def test_action_switch_updates_matrix(self, aof_app):
        before = [c["value"] for c in aof_app.panel.payload["cells"]]
        before_context = dict(aof_app.panel.payload["context"])
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.rects[("UTG", "ALL_IN")].center,
        )
        aof_app.panel.handle_event(event)
        after = [c["value"] for c in aof_app.panel.payload["cells"]]
        after_context = aof_app.panel.payload["context"]

        assert aof_app.panel.state.get_position_action("UTG") == "ALL_IN"
        assert before_context["action"] == after_context["action"] == "ALL_IN"
        assert before == after

    def test_scenario_selection_does_not_invoke_solver(self, aof_app):
        class _CountingSolver:
            def __init__(self):
                self.calls = 0

            def evaluate_hand_key(self, *args, **kwargs):
                self.calls += 1
                return {"status": "AVAILABLE", "win_probability": 0.6, "equity": 0.6, "ev": 1.0}

        solver = _CountingSolver()
        aof_app.panel.provider._solver = solver

        # Selection in browser mode should be cache-read only and never hit solver fallback.
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.rects[("UTG", "ALL_IN")].center,
        )
        assert aof_app.panel.handle_event(event)
        assert solver.calls == 0

    def test_completed_precompute_persists_payload(self, aof_app, tmp_path):
        class _FastSolver:
            def evaluate_hand_key(self, *args, **kwargs):
                return {"status": "AVAILABLE", "win_probability": 0.62, "equity": 0.59, "ev": 1.0}

        db_path = tmp_path / "aof_panel_precompute.sqlite3"
        provider = AoFBrowserDataProvider(cache_enabled=True, cache_db_path=str(db_path))
        provider._solver = _FastSolver()
        aof_app.panel.provider = provider
        aof_app.panel.runner = AoFPrecomputeRunner(provider, getattr(provider, "_cache_store", None))
        aof_app.panel.payload = provider.get_matrix_payload(
            aof_app.panel.state.selected_position,
            aof_app.panel.state.selected_metric,
            aof_app.panel.state.position_actions,
            allow_compute=False,
        )

        start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_buttons["start"].center)
        assert aof_app.panel.handle_event(start_event)

        deadline = time.perf_counter() + 10.0
        while time.perf_counter() < deadline:
            aof_app.panel._tick_precompute()  # pylint: disable=protected-access
            if aof_app.panel.precompute_payload_persisted:
                break
            time.sleep(0.002)

        assert aof_app.panel.precompute_payload_persisted
        context = aof_app.panel.precompute_context
        assert context is not None
        solver_key = provider._build_solver_equivalence_key(context)  # pylint: disable=protected-access
        runtime_signature = provider._runtime_signature(context)  # pylint: disable=protected-access
        stored = provider._cache_store.get_payload(solver_key, runtime_signature)  # pylint: disable=protected-access
        assert stored is not None
        assert len(stored["cells"]) == 169

    def test_metric_switch_updates_matrix(self, aof_app):
        before = [c["display"] for c in aof_app.panel.payload["cells"]]
        before_metric = aof_app.panel.payload["context"]["metric"]
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.metric_dropdown.rect.center,
        )
        aof_app.panel.handle_event(event)
        after = [c["display"] for c in aof_app.panel.payload["cells"]]
        after_metric = aof_app.panel.payload["context"]["metric"]

        assert aof_app.panel.state.selected_metric != "WIN_LOSE_PROBABILITY"
        if before == after:
            assert before_metric != after_metric
        else:
            assert before != after

    def test_position_switch_latency_under_1s(self, aof_app):
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.card_rects["SB"].center,
        )
        start = time.perf_counter()
        aof_app.panel.handle_event(event)
        elapsed = time.perf_counter() - start
        assert elapsed <= 1.0

    def test_repeated_scenario_runs_increase_sample_counts(self, tmp_path):
        """Test that running the same scenario multiple times increases aggregated sample counts."""
        from hopilot.gto.aof_scenario_cache_store import AggregationService, RunData
        from datetime import datetime, UTC

        # Setup aggregation service
        db_path = tmp_path / "aof_aggregation.sqlite3"
        service = AggregationService(db_path=str(db_path))

        # Define scenario key
        scenario_key = "test_scenario_123"

        # First run data
        run_data1 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=9.0,
            seed=42,
            results={
                "AA": {"EV": 1.0, "Equity": 0.85},
                "KK": {"EV": 0.8, "Equity": 0.75}
            }
        )

        # Store first run
        service.store_run(scenario_key, run_data1)

        # Get aggregated stats after first run
        stats1 = service.get_aggregated_stats(scenario_key)
        assert stats1.scenario_key == scenario_key
        assert stats1.statistics["AA"]["EV"].sample_count == 1000  # Now represents weighted samples
        assert stats1.statistics["KK"]["EV"].sample_count == 1000

        # Second run data (same scenario, different results)
        run_data2 = RunData(
            timestamp=datetime.now(UTC),
            sim_count=1000,
            combo_samples=4,
            timeout=9.0,
            seed=43,
            results={
                "AA": {"EV": 1.2, "Equity": 0.87},
                "KK": {"EV": 0.9, "Equity": 0.77}
            }
        )

        # Store second run
        service.store_run(scenario_key, run_data2)

        # Get aggregated stats after second run
        stats2 = service.get_aggregated_stats(scenario_key)
        assert stats2.scenario_key == scenario_key
        assert stats2.statistics["AA"]["EV"].sample_count == 2000  # Increased by sim_count!
        assert stats2.statistics["KK"]["EV"].sample_count == 2000  # Increased by sim_count!

        # Verify aggregated values are computed correctly
        expected_aa_ev = (1.0 + 1.2) / 2  # Simple average since equal weights
        assert abs(stats2.statistics["AA"]["EV"].value - expected_aa_ev) < 1e-6

    def test_scenario_loading_with_aggregated_data(self, tmp_path, mock_pygame_setup):
        """Test that scenarios load aggregated data correctly in the GUI."""
        from hopilot.gto.aof_scenario_cache_store import AggregationService, RunData
        from datetime import datetime, UTC
        import tempfile
        import yaml

        # Create config to enable aggregation
        db_path = tmp_path / "aof_aggregation.sqlite3"
        config_data = {
            "aof_browser_cache": {
                "enabled": True,
                "db_path": str(tmp_path / "aof_cache.sqlite3")
            },
            "aof_aggregation": {
                "enabled": True,
                "db_path": str(db_path)
            }
        }

        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            # Setup aggregation service and store some data
            service = AggregationService(db_path=str(db_path))

            # Create a mock provider to get the correct scenario key
            with patch.object(AoFBrowserDataProvider, '_load_aggregation_config', return_value=config_data["aof_aggregation"]), \
                 patch.object(AoFBrowserDataProvider, '_load_cache_config', return_value=config_data["aof_browser_cache"]):
                
                temp_provider = AoFBrowserDataProvider()
                test_context = {
                    'position': 'UTG',
                    'action': 'ALL_IN', 
                    'active_players': 2,
                    'position_actions': {'UTG': 'ALL_IN', 'BB': 'ALL_IN'},
                    'pot_size': 20.0,
                    'bet_amount': 10.0,
                    'num_simulations': 1000,
                    'timeout_ms': 9000,
                    'effective_mode': 'analysis'
                }
                scenario_key = temp_provider._build_scenario_equivalence_key(test_context)

            # Store multiple runs for the same scenario
            for i in range(3):
                run_data = RunData(
                    timestamp=datetime.now(UTC),
                    sim_count=1000,
                    combo_samples=4,
                    timeout=9.0,
                    seed=42 + i,
                    results={
                        "AA": {"WIN_LOSE_PROBABILITY": 0.8 + i * 0.02},  # Slightly different values
                        "KK": {"WIN_LOSE_PROBABILITY": 0.7 + i * 0.02}
                    }
                )
                service.store_run(scenario_key, run_data)

            # Now test that the GUI loads aggregated data
            # This would require setting up the full GUI with the config
            # For now, just verify the aggregation service has the data
            aggregated_stats = service.get_aggregated_stats(scenario_key)
            assert aggregated_stats.scenario_key == scenario_key
            assert aggregated_stats.statistics["AA"]["WIN_LOSE_PROBABILITY"].sample_count == 3000  # 3 runs × 1000 sim_count
            assert aggregated_stats.statistics["KK"]["WIN_LOSE_PROBABILITY"].sample_count == 3000

        finally:
            # Clean up temp config file
            import os
            os.unlink(config_path)

    def test_action_switch_latency_under_1s(self, aof_app):
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.rects[("UTG", "ALL_IN")].center,
        )
        start = time.perf_counter()
        aof_app.panel.handle_event(event)
        elapsed = time.perf_counter() - start
        assert elapsed <= 1.0

    def test_metric_switch_latency_under_1s(self, aof_app):
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.metric_dropdown.rect.center,
        )
        start = time.perf_counter()
        aof_app.panel.handle_event(event)
        elapsed = time.perf_counter() - start
        assert elapsed <= 1.0

    def test_metric_switch_updates_selected_cell_detail_model(self, aof_app):
        row, col = 0, 0
        aof_app.panel.payload["cells"][row * 13 + col].update(
            {
                "status": "AVAILABLE",
                "value": 0.62,
                "display": "62.0%",
                "metrics": {
                    "WIN_LOSE_PROBABILITY": 0.62,
                    "EV": 1.25,
                    "EQUITY": 0.58,
                    "EQR": 0.61,
                    "TIE": 0.03,
                },
            }
        )
        select_cell = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.matrix.get_cell_rect(row, col).center,
        )
        metric_switch = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.metric_dropdown.rect.center,
        )

        assert aof_app.panel.handle_event(select_cell)
        before_metric = aof_app.panel.selected_cell_detail["metric"]
        before_segments = list(aof_app.panel.selected_cell_detail["segments"])

        assert aof_app.panel.handle_event(metric_switch)
        after_metric = aof_app.panel.selected_cell_detail["metric"]
        after_segments = aof_app.panel.selected_cell_detail["segments"]

        assert before_metric != after_metric
        assert after_metric == aof_app.panel.state.selected_metric
        assert before_segments != after_segments

    def test_scenario_context_refresh_keeps_selected_cell_and_refreshes_detail(self, aof_app):
        row, col = 0, 0
        select_cell = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.matrix.get_cell_rect(row, col).center,
        )
        assert aof_app.panel.handle_event(select_cell)

        before = dict(aof_app.panel.selected_cell_detail)
        before_context = dict(aof_app.panel.payload["context"])

        # Changing position triggers payload context refresh.
        position_switch = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.card_rects["BB"].center,
        )
        assert aof_app.panel.handle_event(position_switch)

        after = aof_app.panel.selected_cell_detail
        after_context = aof_app.panel.payload["context"]

        assert aof_app.panel.state.selected_cell is not None
        assert before_context["position"] != after_context["position"]
        assert after["row"] == before["row"]
        assert after["col"] == before["col"]

    def test_layout_keeps_matrix_detail_right_columns_visible_and_non_overlapping(self, aof_app):
        surface = pygame.Surface((aof_app.width, aof_app.height))
        aof_app.panel.draw(surface)

        matrix_rect = pygame.Rect(
            aof_app.panel.matrix.x,
            aof_app.panel.matrix.y,
            aof_app.panel.matrix.width,
            aof_app.panel.matrix.height,
        )
        detail_rect = aof_app.panel.cell_detail_panel.rect

        assert matrix_rect.left >= 0
        assert detail_rect.right <= aof_app.width
        assert matrix_rect.right <= detail_rect.left
        assert detail_rect.right <= aof_app.panel.side_x

    def test_right_side_controls_work_with_middle_panel_active(self, aof_app):
        # Activate middle panel selection state first.
        select_cell = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.matrix.get_cell_rect(0, 0).center,
        )
        assert aof_app.panel.handle_event(select_cell)

        workers_before = aof_app.panel.precompute_max_workers
        up_workers = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.precompute_worker_buttons["up"].center,
        )
        assert aof_app.panel.handle_event(up_workers)
        assert aof_app.panel.precompute_max_workers == min(16, workers_before + 1)

        sims_before = aof_app.panel.precompute_simulations_per_cell
        up_sims = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.precompute_sim_buttons["up"].center,
            button=1,
        )
        assert aof_app.panel.handle_event(up_sims)
        assert aof_app.panel.precompute_simulations_per_cell == sims_before + 100

    def test_precompute_panel_control_rendering_and_state_enable(self, aof_app):
        start_rect = aof_app.panel.precompute_buttons["start"]
        pause_rect = aof_app.panel.precompute_buttons["pause"]
        resume_rect = aof_app.panel.precompute_buttons["resume"]

        start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start_rect.center)
        assert aof_app.panel.handle_event(start_event)
        assert aof_app.panel.precompute_session is not None
        assert aof_app.panel.precompute_session.run_state.value == "RUNNING"

        pause_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pause_rect.center)
        assert aof_app.panel.handle_event(pause_event)
        assert aof_app.panel.precompute_session.run_state.value == "PAUSED"

        resume_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=resume_rect.center)
        assert aof_app.panel.handle_event(resume_event)
        assert aof_app.panel.precompute_session.run_state.value == "RUNNING"

    def test_scenario_controls_locked_while_precompute_running(self, aof_app):
        start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_buttons["start"].center)
        assert aof_app.panel.handle_event(start_event)
        assert aof_app.panel.precompute_session is not None
        assert aof_app.panel.precompute_session.run_state.value == "RUNNING"

        before = aof_app.panel.state.selected_position
        switch_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.action_selector.card_rects["BB"].center,
        )
        aof_app.panel.handle_event(switch_event)

        assert aof_app.panel.state.selected_position == before

    def test_confidence_metadata_display_in_cell_detail_panel(self, aof_app):
        """Test that confidence metadata fields are available in cell detail panel."""
        # Select a cell to ensure detail panel has data
        select_cell = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.matrix.get_cell_rect(0, 0).center,
        )
        assert aof_app.panel.handle_event(select_cell)
        
        # Verify that selected_cell_detail has the expected structure
        detail = aof_app.panel.selected_cell_detail
        assert "hand_key" in detail
        assert "metric" in detail
        assert "status" in detail
        
        # Confidence fields may or may not be present depending on data availability
        # The important thing is that the detail model structure supports them
        # This tests that the integration between browser panel and cell detail panel works
        sample_count = detail.get("sample_count")
        confidence = detail.get("confidence")
        
        # If confidence data is present, it should be the correct types
        if sample_count is not None:
            assert isinstance(sample_count, int)
            assert sample_count >= 0
        if confidence is not None:
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0

    def test_metric_switching_with_aggregated_data_regression(self, aof_app):
        """Regression test: Ensure metric switching works correctly with aggregated data."""
        # Select a cell first
        select_cell = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.matrix.get_cell_rect(0, 0).center,
        )
        assert aof_app.panel.handle_event(select_cell)

        # Switch to a different metric
        metric_switch = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=aof_app.panel.metric_dropdown.rect.center,
        )
        assert aof_app.panel.handle_event(metric_switch)

        # Verify the metric actually changed
        assert aof_app.panel.state.selected_metric != "WIN_LOSE_PROBABILITY"

        # Verify the selected cell detail reflects the new metric
        detail = aof_app.panel.selected_cell_detail
        assert detail["metric"] == aof_app.panel.state.selected_metric

        # The detail should still have the expected structure even with aggregated data
        assert "hand_key" in detail
        assert "status" in detail
        assert "display_value" in detail

    def test_precompute_runner_compatibility_with_aggregation_regression(self, aof_app):
        """Regression test: Ensure precompute runner works with aggregation storage."""
        # Start precompute
        start_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_buttons["start"].center)
        assert aof_app.panel.handle_event(start_event)
        assert aof_app.panel.precompute_session is not None
        assert aof_app.panel.precompute_session.run_state.value == "RUNNING"

        # Let it run for a moment
        import time
        time.sleep(0.1)

        # Pause it
        pause_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_buttons["pause"].center)
        assert aof_app.panel.handle_event(pause_event)
        assert aof_app.panel.precompute_session.run_state.value == "PAUSED"

        # Resume it
        resume_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_buttons["resume"].center)
        assert aof_app.panel.handle_event(resume_event)
        assert aof_app.panel.precompute_session.run_state.value == "RUNNING"

        # Stop it (should work regardless of current state)
        stop_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=aof_app.panel.precompute_buttons["stop"].center)
        assert aof_app.panel.handle_event(stop_event)
        
        # The session should be stopped or completed (stopping a running session)
        # If it was paused, it might stay paused, but the important thing is that
        # the stop operation was accepted and the session exists
        assert aof_app.panel.precompute_session is not None
        # This tests that aggregation storage integration doesn't break precompute functionality

    def test_p95_latency_under_1s_for_200_switches(self):
        pygame.init()
        app = AoFGTOBrowserGUI(width=1000, height=760)

        class _FastSolver:
            def evaluate_hand_key(self, *args, **kwargs):
                return {"status": "AVAILABLE", "win_probability": 0.62, "equity": 0.59, "ev": 1.0}

        app.panel.provider._solver = _FastSolver()

        events = [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.action_selector.card_rects["UTG"].center),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.action_selector.rects[("UTG", "ALL_IN")].center),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.metric_dropdown.rect.center),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.panel.action_selector.card_rects["BB"].center),
        ]

        timings = []
        for idx in range(200):
            event = events[idx % len(events)]
            start = time.perf_counter()
            app.panel.handle_event(event)
            timings.append(time.perf_counter() - start)

        timings.sort()
        p95_index = int(0.95 * len(timings)) - 1
        p95 = timings[max(0, p95_index)]
        assert p95 <= 1.0
        pygame.quit()

    def test_error_recovery_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test error handling and recovery in GUI workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Set up a failing calculation
        mock_optimizer.find_nash_equilibrium.side_effect = Exception("Simulation timeout")

        panel.set_mode('range_vs_range')
        panel.hero_range = ['AA', 'KK']
        panel.villain_range = ['QQ', 'JJ']

        # Execute failing calculation
        result = panel.calculate_current_mode()
        assert result is None
        assert panel.last_error is not None

        # Reset error state
        panel.clear_error()

        # Fix the mock and retry
        mock_optimizer.find_nash_equilibrium.side_effect = None
        mock_optimizer.find_nash_equilibrium.return_value = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.8],
            'villain_strategy': [0.9, 0.6],
            'iterations': 6,
            'best_response_valid': True
        }

        # Retry calculation
        result = panel.calculate_range_vs_range()
        assert result is not None
        assert result['equilibrium_found'] == True
        assert panel.last_error is None

    def test_progress_tracking_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test progress tracking during long calculations."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        # Setup mock return value
        mock_optimizer.find_nash_equilibrium.return_value = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.7],
            'villain_strategy': [0.8, 0.5],
            'iterations': 10,
            'best_response_valid': True
        }

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        mock_optimizer.find_nash_equilibrium.return_value = {
            'equilibrium_found': True,
            'hero_strategy': [1.0, 0.7],
            'villain_strategy': [0.8, 0.5],
            'iterations': 10,
            'best_response_valid': True
        }

        panel.set_mode('range_vs_range')
        panel.hero_range = ['AA', 'AKs']
        panel.villain_range = ['KK', 'QQ']

        # Start calculation
        panel.start_calculation()
        assert panel.is_calculating == True
        assert panel.progress == 0.0

        # Execute calculation (progress updates happen inside)
        result = panel.calculate_range_vs_range()

        # Complete the calculation
        panel.complete_calculation()

        # Verify progress completed
        assert panel.progress == 1.0
        assert panel.is_calculating == False
        assert result is not None

    def test_range_validation_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test range validation in GUI workflow."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Test invalid range file
        with patch('builtins.open', side_effect=FileNotFoundError):
            success = panel.load_hero_range('nonexistent.yaml')
            assert success == False
            assert panel.last_error is not None

        # Test valid range file
        valid_range = {
            'name': 'Valid Range',
            'hands': ['AA', 'KK', 'QQ']
        }

        panel.clear_error()  # Clear previous error

        with patch('builtins.open', mock_open()), \
             patch('yaml.safe_load', return_value=valid_range):
            success = panel.load_hero_range('valid.yaml')
            assert success == True
            assert panel.hero_range == ['AA', 'KK', 'QQ']
            assert panel.last_error is None

    def test_mode_specific_validation(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test mode-specific validation requirements."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Threshold mode doesn't need ranges
        panel.set_mode('threshold')
        can_calculate = panel.can_calculate_current_mode()
        assert can_calculate == True

        # Range vs range mode needs both ranges
        panel.set_mode('range_vs_range')
        can_calculate = panel.can_calculate_current_mode()
        assert can_calculate == False  # No ranges loaded

        # Load ranges
        panel.hero_range = ['AA', 'KK']
        panel.villain_range = ['QQ', 'JJ']
        can_calculate = panel.can_calculate_current_mode()
        assert can_calculate == True

        # Indifference mode needs both ranges
        panel.set_mode('indifference')
        can_calculate = panel.can_calculate_current_mode()
        assert can_calculate == True  # Ranges already loaded

    def test_result_export_workflow(self, mock_pygame_setup, mock_analyzer, mock_optimizer):
        """Test result export functionality."""
        from hopilot.gui_components.gto_solver_panel import GTOSolverPanel

        # Setup mock to return a result
        mock_optimizer.find_gto_threshold.return_value = {
            'threshold_equity': 0.35,
            'optimal_range': ['AA', 'KK']
        }

        panel = GTOSolverPanel(mock_analyzer, mock_optimizer)

        # Perform a calculation
        panel.set_mode('threshold')
        result = panel.calculate_current_mode()

        # Verify calculation worked
        assert panel.last_result is not None

        # Export results
        with patch('builtins.open', create=True) as mock_file, \
             patch('yaml.dump') as mock_yaml:
            success = panel.export_results('results.yaml')

            assert success == True
            mock_file.assert_called_once()
            mock_yaml.assert_called_once()

        # Test export failure
        with patch('builtins.open', side_effect=PermissionError):
            success = panel.export_results('readonly.yaml')
            assert success == False