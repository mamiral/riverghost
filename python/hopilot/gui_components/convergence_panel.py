"""
Convergence visualization panel for AoF GTO browser.

Displays convergence analysis showing how equity values stabilize
over increasing numbers of simulations.
"""

import pygame
from typing import List, Dict, Any, Optional

from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class ConvergencePanel:
    """
    Panel for visualizing convergence analysis data.

    Shows a line plot of average equity vs number of simulations
    to demonstrate how GTO solutions converge over time.
    """

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # Plot area (leaving space for labels and title)
        self.plot_x = x + 60
        self.plot_y = y + 50
        self.plot_width = width - 80
        self.plot_height = height - 90

        # Colors
        self.bg_color = (25, 25, 25)
        self.grid_color = (50, 50, 50)
        self.axis_color = (180, 180, 180)
        self.line_color = (0, 255, 0)
        self.point_color = (100, 255, 100)
        self.text_color = (220, 220, 220)
        self.title_color = (255, 255, 255)

        # Fonts
        self.title_font = pygame.font.SysFont("arial", 14, bold=True)
        self.label_font = pygame.font.SysFont("arial", 11)
        self.axis_font = pygame.font.SysFont("arial", 9)

        # Data
        self.convergence_data: List[Dict[str, Any]] = []
        self.position = ""
        self.action = ""

    def set_convergence_data(self, data: List[Dict[str, Any]], position: str, action: str):
        """
        Set convergence data to display.

        Args:
            data: List of convergence points with num_simulations, average_equity, timestamp
            position: Player position (for display)
            action: Player action (for display)
        """
        self.convergence_data = data.copy()
        self.position = position
        self.action = action

        logger.debug(f"Set convergence data: {len(data)} points for {position}/{action}")

    def draw(self, screen: pygame.Surface):
        """Draw the convergence panel."""
        # Background
        pygame.draw.rect(screen, self.bg_color, (self.x, self.y, self.width, self.height), border_radius=6)
        pygame.draw.rect(screen, self.grid_color, (self.x, self.y, self.width, self.height), 1, border_radius=6)

        # Title
        title_text = f"Convergence Analysis - {self.position} {self.action}"
        title = self.title_font.render(title_text, True, self.title_color)
        title_x = self.x + (self.width - title.get_width()) // 2
        screen.blit(title, (title_x, self.y + 8))

        # Check if we have data
        if not self.convergence_data:
            no_data_text = self.label_font.render("No convergence data available", True, self.text_color)
            text_x = self.x + (self.width - no_data_text.get_width()) // 2
            text_y = self.y + (self.height - no_data_text.get_height()) // 2
            screen.blit(no_data_text, (text_x, text_y))
            return

        # Extract data for plotting
        x_data = [point["num_simulations"] for point in self.convergence_data]
        y_data = [point["average_equity"] for point in self.convergence_data]

        # Calculate plot bounds
        if x_data and y_data:
            x_min, x_max = min(x_data), max(x_data)
            y_min, y_max = min(y_data), max(y_data)

            # Add some padding
            x_padding = max(1, (x_max - x_min) * 0.05)
            y_padding = max(0.001, (y_max - y_min) * 0.05)

            x_min = max(0, x_min - x_padding)
            x_max += x_padding
            y_min = max(0, y_min - y_padding)
            y_max += y_padding

            # Draw grid and axes
            self._draw_grid_and_axes(screen, x_min, x_max, y_min, y_max)

            # Draw data line
            self._draw_convergence_line(screen, x_data, y_data, x_min, x_max, y_min, y_max)

            # Draw axis labels
            self._draw_axis_labels(screen, x_max, y_max)

    def _draw_grid_and_axes(self, screen: pygame.Surface, x_min: float, x_max: float, y_min: float, y_max: float):
        """Draw grid lines and axis labels."""
        # Vertical grid lines (simulations)
        for i in range(6):
            x_ratio = i / 5.0
            x_val = x_min + (x_max - x_min) * x_ratio
            x_pixel = self.plot_x + int(self.plot_width * x_ratio)

            # Grid line
            pygame.draw.line(screen, self.grid_color, (x_pixel, self.plot_y),
                           (x_pixel, self.plot_y + self.plot_height), 1)

            # Label
            label = self.axis_font.render(f"{int(x_val)}", True, self.axis_color)
            screen.blit(label, (x_pixel - label.get_width() // 2, self.plot_y + self.plot_height + 2))

        # Horizontal grid lines (equity)
        for i in range(6):
            y_ratio = i / 5.0
            y_val = y_min + (y_max - y_min) * y_ratio
            y_pixel = self.plot_y + self.plot_height - int(self.plot_height * y_ratio)

            # Grid line
            pygame.draw.line(screen, self.grid_color, (self.plot_x, y_pixel),
                           (self.plot_x + self.plot_width, y_pixel), 1)

            # Label
            label = self.axis_font.render(f"{y_val:.3f}", True, self.axis_color)
            screen.blit(label, (self.plot_x - label.get_width() - 2, y_pixel - label.get_height() // 2))

    def _draw_convergence_line(self, screen: pygame.Surface, x_data: List[float], y_data: List[float],
                              x_min: float, x_max: float, y_min: float, y_max: float):
        """Draw the convergence line plot."""
        points = []

        for x_val, y_val in zip(x_data, y_data):
            # Convert to pixel coordinates
            x_ratio = (x_val - x_min) / (x_max - x_min) if x_max > x_min else 0
            y_ratio = (y_val - y_min) / (y_max - y_min) if y_max > y_min else 0

            x_pixel = self.plot_x + int(self.plot_width * x_ratio)
            y_pixel = self.plot_y + self.plot_height - int(self.plot_height * y_ratio)

            points.append((x_pixel, y_pixel))

        # Draw line
        if len(points) > 1:
            pygame.draw.lines(screen, self.line_color, False, points, 2)

        # Draw points
        for x_pixel, y_pixel in points:
            pygame.draw.circle(screen, self.point_color, (x_pixel, y_pixel), 3)

    def _draw_axis_labels(self, screen: pygame.Surface, x_max: float, y_max: float):
        """Draw axis labels."""
        # X-axis label
        x_label = self.label_font.render("Simulations", True, self.text_color)
        x_label_x = self.plot_x + (self.plot_width - x_label.get_width()) // 2
        x_label_y = self.y + self.height - 20
        screen.blit(x_label, (x_label_x, x_label_y))

        # Y-axis label (rotated)
        y_label = self.label_font.render("Average Equity", True, self.text_color)
        # For simplicity, we'll place it horizontally above the plot
        y_label_x = self.x + 10
        y_label_y = self.plot_y - 25
        screen.blit(y_label, (y_label_x, y_label_y))