import pytest
import pygame
import sys
import os

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.plot_panel import PlotPanel, ConvergencePlot


class TestPlotPanel:
    """Unit tests for PlotPanel component."""

    @pytest.fixture
    def screen(self):
        """Create a pygame screen for testing."""
        pygame.init()
        screen = pygame.display.set_mode((1200, 800))
        yield screen
        pygame.quit()

    def test_plot_panel_initialization(self, screen):
        """Test PlotPanel initialization."""
        plot_panel = PlotPanel(screen, 100, 100, 400, 300, "Test Plot", "X Axis", "Y Axis")

        assert plot_panel.screen == screen
        assert plot_panel.x == 100
        assert plot_panel.y == 100
        assert plot_panel.width == 400
        assert plot_panel.height == 300
        assert plot_panel.title == "Test Plot"
        assert plot_panel.xlabel == "X Axis"
        assert plot_panel.ylabel == "Y Axis"
        assert len(plot_panel.data_x) == 0
        assert len(plot_panel.data_y) == 0
        assert plot_panel.data_label == ""

    def test_plot_panel_set_data(self, screen):
        """Test setting data on PlotPanel."""
        plot_panel = PlotPanel(screen, 100, 100, 400, 300, "Test Plot", "X Axis", "Y Axis")

        # Set some test data
        x_data = [1, 2, 3, 4, 5]
        y_data = [10, 20, 15, 25, 30]
        plot_panel.set_data(x_data, y_data, "Test Data")

        assert plot_panel.data_x == x_data
        assert plot_panel.data_y == y_data
        assert plot_panel.data_label == "Test Data"

    def test_plot_panel_empty_data(self, screen):
        """Test PlotPanel with empty data."""
        plot_panel = PlotPanel(screen, 100, 100, 400, 300, "Test Plot", "X Axis", "Y Axis")

        # Empty data should not cause issues
        plot_panel.set_data([], [], "")

        assert len(plot_panel.data_x) == 0
        assert len(plot_panel.data_y) == 0

    def test_plot_panel_drawing(self, screen):
        """Test that PlotPanel draws without errors."""
        plot_panel = PlotPanel(screen, 100, 100, 400, 300, "Test Plot", "X Axis", "Y Axis")

        # Test drawing with no data
        try:
            plot_panel.draw()
        except Exception as e:
            pytest.fail(f"PlotPanel.draw() with no data raised an exception: {e}")

        # Test drawing with data
        x_data = [1, 2, 3, 4, 5]
        y_data = [10, 20, 15, 25, 30]
        plot_panel.set_data(x_data, y_data, "Test Data")

        try:
            plot_panel.draw()
        except Exception as e:
            pytest.fail(f"PlotPanel.draw() with data raised an exception: {e}")

    def test_plot_panel_large_data(self, screen):
        """Test PlotPanel with large datasets."""
        plot_panel = PlotPanel(screen, 100, 100, 400, 300, "Large Data Plot", "Iterations", "Equity")

        # Large dataset
        x_data = list(range(1, 101))  # 1 to 100
        y_data = [0.5 + 0.01 * i for i in range(100)]  # Gradually increasing equity
        plot_panel.set_data(x_data, y_data, "Convergence Data")

        assert len(plot_panel.data_x) == 100
        assert len(plot_panel.data_y) == 100

        # Should draw without issues
        try:
            plot_panel.draw()
        except Exception as e:
            pytest.fail(f"PlotPanel.draw() with large data raised an exception: {e}")

    def test_convergence_plot_initialization(self, screen):
        """Test ConvergencePlot initialization."""
        convergence_plot = ConvergencePlot(screen, 100, 100, 400, 300)

        assert convergence_plot.title == "Simulation Convergence"
        assert convergence_plot.xlabel == "Simulations"
        assert convergence_plot.ylabel == "Win Probability"

    def test_convergence_plot_update(self, screen):
        """Test ConvergencePlot update functionality."""
        convergence_plot = ConvergencePlot(screen, 100, 100, 400, 300)

        # Simulate convergence data
        iterations = [100, 500, 1000, 2000, 5000]
        equities = [0.45, 0.48, 0.49, 0.495, 0.497]

        convergence_plot.set_data(iterations, equities, "Hero Equity")

        assert convergence_plot.data_x == iterations
        assert convergence_plot.data_y == equities

        # Test drawing
        try:
            convergence_plot.draw()
        except Exception as e:
            pytest.fail(f"ConvergencePlot.draw() raised an exception: {e}")

    def test_plot_panel_axis_labels(self, screen):
        """Test that axis labels are properly set."""
        plot_panel = PlotPanel(screen, 100, 100, 400, 300, "Custom Title", "Time", "Value")

        assert plot_panel.title == "Custom Title"
        assert plot_panel.xlabel == "Time"
        assert plot_panel.ylabel == "Value"

        # Test drawing with custom labels
        try:
            plot_panel.draw()
        except Exception as e:
            pytest.fail(f"PlotPanel.draw() with custom labels raised an exception: {e}")
