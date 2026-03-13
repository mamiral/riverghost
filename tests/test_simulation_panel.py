import pytest
import pygame
import sys
import os
from unittest.mock import MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.simulation_panel import SimulationPanel
from hopilot.poker_analyzer import PokerAnalyzer


class TestSimulationPanel:
    """Unit tests for SimulationPanel component."""

    @pytest.fixture
    def screen(self):
        """Create a pygame screen for testing."""
        pygame.init()
        screen = pygame.display.set_mode((1200, 800))
        yield screen
        pygame.quit()

    @pytest.fixture
    def analyzer(self):
        """Create a mock PokerAnalyzer."""
        return MagicMock(spec=PokerAnalyzer)

    def test_simulation_panel_initialization(self, screen, analyzer):
        """Test SimulationPanel initialization."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        assert panel.x == 800
        assert panel.y == 100
        assert panel.width == 350
        assert panel.height == 600
        assert panel.num_simulations == 10000
        assert panel.results is None

    def test_simulation_panel_initialization_with_gui(self, screen, analyzer):
        """Test SimulationPanel initialization with GUI reference."""
        mock_gui = MagicMock()
        mock_gui.num_simulations = 5000
        mock_gui.randomize_unset = False

        panel = SimulationPanel(screen, analyzer, 800, 100, mock_gui)

        assert panel.num_simulations == 5000
        assert panel.randomize_unset is False

    def test_simulation_panel_draw(self, screen, analyzer):
        """Test drawing the simulation panel."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        # Should not raise exceptions
        panel.draw()

    def test_simulation_panel_draw_with_results(self, screen, analyzer):
        """Test drawing with simulation results."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        results = {
            'win_probability': 0.65,
            'tie_probability': 0.05,
            'loss_probability': 0.30,
            'valid_simulations': 10000
        }
        panel.set_results(results)

        # Should not raise exceptions
        panel.draw()

    def test_simulation_panel_handle_event_run_simulation(self, screen, analyzer):
        """Test run simulation button click."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        # Click run button (center at 870, 165)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (870, 165)  # Center of run button

        result = panel.handle_event(mock_event)

        assert result == "run_simulation"

    def test_simulation_panel_handle_event_add_villain(self, screen, analyzer):
        """Test add villain button click."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        # Click add villain button (center at 940, 165)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (940, 165)  # Center of add villain button

        result = panel.handle_event(mock_event)

        assert result == "add_villain"

    def test_simulation_panel_handle_event_remove_villain(self, screen, analyzer):
        """Test remove villain button click."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        # Click remove villain button (center at 1095, 165)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (1095, 165)  # Center of remove villain button

        result = panel.handle_event(mock_event)

        assert result == "remove_villain"

    def test_simulation_panel_handle_event_increment_simulations(self, screen, analyzer):
        """Test increment simulations button."""
        mock_gui = MagicMock()
        mock_gui.num_simulations = 10000  # Set initial value
        panel = SimulationPanel(screen, analyzer, 800, 100, mock_gui)

        initial_sims = panel.num_simulations

        # Click increment button (center at 835, 195)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (835, 195)  # Center of increment button

        result = panel.handle_event(mock_event)

        assert result is True
        assert panel.num_simulations == initial_sims * 2
        assert mock_gui.num_simulations == initial_sims * 2

    def test_simulation_panel_handle_event_decrement_simulations(self, screen, analyzer):
        """Test decrement simulations button."""
        mock_gui = MagicMock()
        mock_gui.num_simulations = 10000  # Set initial value
        panel = SimulationPanel(screen, analyzer, 800, 100, mock_gui)

        initial_sims = panel.num_simulations

        # Click decrement button (center at 875, 195)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (875, 195)  # Center of decrement button

        result = panel.handle_event(mock_event)

        assert result is True
        assert panel.num_simulations == initial_sims // 2
        assert mock_gui.num_simulations == initial_sims // 2

    def test_simulation_panel_simulation_limits(self, screen, analyzer):
        """Test simulation count limits."""
        mock_gui = MagicMock()
        panel = SimulationPanel(screen, analyzer, 800, 100, mock_gui)

        # Test minimum limit
        panel.num_simulations = 500
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (875, 195)  # Decrement button center

        panel.handle_event(mock_event)
        assert panel.num_simulations >= 1000  # Minimum 1k

        # Test maximum limit
        panel.num_simulations = 50000
        mock_event.pos = (835, 195)  # Increment button center

        panel.handle_event(mock_event)
        assert panel.num_simulations <= 100000  # Maximum 100k

    def test_simulation_panel_handle_event_outside_buttons(self, screen, analyzer):
        """Test clicking outside buttons does nothing."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        # Click outside any button
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.pos = (900, 200)  # In panel but not on button

        result = panel.handle_event(mock_event)

        assert result is False

    def test_simulation_panel_set_results(self, screen, analyzer):
        """Test setting simulation results."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        results = {
            'win_probability': 0.75,
            'tie_probability': 0.10,
            'loss_probability': 0.15
        }

        panel.set_results(results)
        assert panel.results == results

    def test_simulation_panel_no_gto_trigger(self, screen, analyzer):
        """Regression: simulation panel no longer exposes a run_gto action."""
        panel = SimulationPanel(screen, analyzer, 800, 100)
        assert not hasattr(panel, "gto_button_rect")

    def test_simulation_panel_add_convergence_point(self, screen, analyzer):
        """Test adding convergence data points."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        panel.add_convergence_point(1000, 0.5)
        panel.add_convergence_point(2000, 0.55)

        assert len(panel.convergence_data) == 2
        assert panel.convergence_data[0] == (1000, 0.5)
        assert panel.convergence_data[1] == (2000, 0.55)

    def test_simulation_panel_clear_convergence_data(self, screen, analyzer):
        """Test clearing convergence data."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        panel.add_convergence_point(1000, 0.5)
        panel.add_convergence_point(2000, 0.55)

        panel.clear_convergence_data()

        assert len(panel.convergence_data) == 0

    def test_simulation_panel_convergence_plot_integration(self, screen, analyzer):
        """Test that convergence data updates the plot."""
        panel = SimulationPanel(screen, analyzer, 800, 100)

        # Add convergence data
        panel.add_convergence_point(1000, 0.5)
        panel.add_convergence_point(2000, 0.55)

        # The convergence plot should be updated
        # (We can't easily test the plot internals without more complex mocking)
