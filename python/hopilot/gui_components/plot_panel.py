import pygame
import math
from typing import List, Tuple, Optional


class PlotPanel:
    """
    Reusable 2D plot GUI component for pygame applications.
    Supports line plots with automatic scaling and grid.
    """

    def __init__(self, screen: pygame.Surface, x: int, y: int, width: int, height: int,
                 title: str = "", xlabel: str = "", ylabel: str = ""):
        self.screen = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel

        # Plot area (leaving space for labels)
        self.plot_x = x + 60
        self.plot_y = y + 40
        self.plot_width = width - 80
        self.plot_height = height - 80

        # Colors
        self.bg_color = (30, 30, 30)
        self.grid_color = (60, 60, 60)
        self.axis_color = (200, 200, 200)
        self.line_color = (0, 255, 0)
        self.text_color = (255, 255, 255)

        # Fonts
        self.title_font = pygame.font.SysFont("arial", 16, bold=True)
        self.label_font = pygame.font.SysFont("arial", 12)
        self.axis_font = pygame.font.SysFont("arial", 10)

        # Data
        self.data_x: List[float] = []
        self.data_y: List[float] = []
        self.data_label = ""

    def set_data(self, x_data: List[float], y_data: List[float], label: str = ""):
        """Set the data to plot."""
        self.data_x = x_data.copy()
        self.data_y = y_data.copy()
        self.data_label = label

    def add_data_point(self, x: float, y: float):
        """Add a single data point to the plot."""
        self.data_x.append(x)
        self.data_y.append(y)

    def clear_data(self):
        """Clear all data."""
        self.data_x.clear()
        self.data_y.clear()

    def _get_data_bounds(self) -> Tuple[float, float, float, float]:
        """Get the bounds of the data (min_x, max_x, min_y, max_y)."""
        if not self.data_x or not self.data_y:
            return 0, 1, 0, 1

        min_x = min(self.data_x)
        max_x = max(self.data_x)
        min_y = min(self.data_y)
        max_y = max(self.data_y)

        # Add some padding
        x_padding = (max_x - min_x) * 0.05 if max_x != min_x else 0.1
        y_padding = (max_y - min_y) * 0.05 if max_y != min_y else 0.1

        return min_x - x_padding, max_x + x_padding, min_y - y_padding, max_y + y_padding

    def _screen_to_data(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Convert screen coordinates to data coordinates."""
        min_x, max_x, min_y, max_y = self._get_data_bounds()

        data_x = min_x + (screen_x - self.plot_x) / self.plot_width * (max_x - min_x)
        data_y = max_y - (screen_y - self.plot_y) / self.plot_height * (max_y - min_y)

        return data_x, data_y

    def _data_to_screen(self, data_x: float, data_y: float) -> Tuple[int, int]:
        """Convert data coordinates to screen coordinates."""
        min_x, max_x, min_y, max_y = self._get_data_bounds()

        if max_x == min_x:
            screen_x = self.plot_x + self.plot_width // 2
        else:
            screen_x = self.plot_x + int((data_x - min_x) / (max_x - min_x) * self.plot_width)

        if max_y == min_y:
            screen_y = self.plot_y + self.plot_height // 2
        else:
            screen_y = self.plot_y + int((max_y - data_y) / (max_y - min_y) * self.plot_height)

        return screen_x, screen_y

    def draw(self):
        """Draw the plot panel."""
        # Background
        pygame.draw.rect(self.screen, self.bg_color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, self.axis_color, (self.x, self.y, self.width, self.height), 1)

        # Title
        if self.title:
            title_surf = self.title_font.render(self.title, True, self.text_color)
            title_x = self.x + (self.width - title_surf.get_width()) // 2
            self.screen.blit(title_surf, (title_x, self.y + 5))

        # X label
        if self.xlabel:
            xlabel_surf = self.label_font.render(self.xlabel, True, self.text_color)
            xlabel_x = self.x + (self.width - xlabel_surf.get_width()) // 2
            self.screen.blit(xlabel_surf, (xlabel_x, self.y + self.height - 20))

        # Y label
        if self.ylabel:
            ylabel_surf = self.label_font.render(self.ylabel, True, self.text_color)
            ylabel_surf = pygame.transform.rotate(ylabel_surf, 90)
            ylabel_x = self.x + 5
            ylabel_y = self.y + (self.height + ylabel_surf.get_width()) // 2
            self.screen.blit(ylabel_surf, (ylabel_x, ylabel_y))

        # Plot area background
        pygame.draw.rect(self.screen, (20, 20, 20), (self.plot_x, self.plot_y, self.plot_width, self.plot_height))
        pygame.draw.rect(self.screen, self.grid_color, (self.plot_x, self.plot_y, self.plot_width, self.plot_height), 1)

        # Draw grid and axes
        self._draw_grid()

        # Draw data
        if self.data_x and self.data_y:
            self._draw_data()

    def _draw_grid(self):
        """Draw grid lines and axis labels."""
        min_x, max_x, min_y, max_y = self._get_data_bounds()

        # Vertical grid lines (X axis)
        for i in range(6):
            x_val = min_x + (max_x - min_x) * i / 5
            screen_x = self.plot_x + int(self.plot_width * i / 5)

            # Grid line
            pygame.draw.line(self.screen, self.grid_color,
                           (screen_x, self.plot_y), (screen_x, self.plot_y + self.plot_height), 1)

            # Label
            label = f"{x_val:.0f}" if x_val >= 1000 else f"{x_val:.1f}"
            label_surf = self.axis_font.render(label, True, self.text_color)
            self.screen.blit(label_surf, (screen_x - label_surf.get_width()//2, self.plot_y + self.plot_height + 2))

        # Horizontal grid lines (Y axis)
        for i in range(6):
            y_val = min_y + (max_y - min_y) * i / 5
            screen_y = self.plot_y + self.plot_height - int(self.plot_height * i / 5)

            # Grid line
            pygame.draw.line(self.screen, self.grid_color,
                           (self.plot_x, screen_y), (self.plot_x + self.plot_width, screen_y), 1)

            # Label
            label = f"{y_val:.3f}"
            label_surf = self.axis_font.render(label, True, self.text_color)
            self.screen.blit(label_surf, (self.plot_x - label_surf.get_width() - 2, screen_y - label_surf.get_height()//2))

    def _draw_data(self):
        """Draw the data as a line plot."""
        if len(self.data_x) < 2:
            return

        # Draw line segments
        points = []
        for i in range(len(self.data_x)):
            screen_x, screen_y = self._data_to_screen(self.data_x[i], self.data_y[i])
            # Clamp to plot area
            screen_x = max(self.plot_x, min(self.plot_x + self.plot_width, screen_x))
            screen_y = max(self.plot_y, min(self.plot_y + self.plot_height, screen_y))
            points.append((screen_x, screen_y))

        # Draw the line
        if len(points) >= 2:
            pygame.draw.lines(self.screen, self.line_color, False, points, 2)

        # Draw data points
        for point in points:
            pygame.draw.circle(self.screen, self.line_color, point, 3)
            pygame.draw.circle(self.screen, (255, 255, 255), point, 1)

        # Draw data label if provided
        if self.data_label and points:
            label_surf = self.label_font.render(self.data_label, True, self.line_color)
            self.screen.blit(label_surf, (points[-1][0] + 5, points[-1][1] - 10))


class ConvergencePlot(PlotPanel):
    """
    Specialized plot for showing Monte Carlo simulation convergence.
    Shows win probability vs simulation count.
    """

    def __init__(self, screen: pygame.Surface, x: int, y: int, width: int = 300, height: int = 200):
        super().__init__(screen, x, y, width, height,
                        title="Simulation Convergence",
                        xlabel="Simulations",
                        ylabel="Win Probability")

    def update_convergence_data(self, simulation_counts: List[int], win_probabilities: List[float]):
        """Update the convergence plot with new data."""
        self.set_data([float(x) for x in simulation_counts], win_probabilities,
                     f"Final: {win_probabilities[-1]:.3f}" if win_probabilities else "")

    def add_convergence_point(self, simulation_count: int, win_probability: float):
        """Add a single convergence data point."""
        self.add_data_point(float(simulation_count), win_probability)
        if self.data_x:
            self.data_label = f"Current: {win_probability:.3f}"