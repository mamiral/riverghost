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

        # Plot area (leaving space for labels, title, and statistics)
        self.plot_x = x + 60
        self.plot_y = y + 70  # Moved down to make room for stats
        self.plot_width = width - 80
        self.plot_height = height - 120  # Reduced to make room for stats

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
        self.metric = ""
        self.last_set_time = 0
        self.set_call_count = 0

        # Interaction state
        self.hovered_point = None
        self.selected_range = None

    def set_bounds(self, x: int, y: int, width: int, height: int):
        """Update panel position and size."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        # Recalculate plot area
        self.plot_x = x + 60
        self.plot_y = y + 70  # Moved down to make room for stats
        self.plot_width = width - 80
        self.plot_height = height - 120  # Reduced to make room for stats

    def set_convergence_data(self, data: List[Dict[str, Any]], position: str, action: str, metric: str = ""):
        """
        Set convergence data to display.

        Args:
            data: List of convergence points with sample_count, equity, timestamp
            position: Player position (for display)
            action: Player action (for display)
            metric: Metric being displayed (WIN_LOSE_PROBABILITY, EQUITY, EV, EQR)
        """
        import time
        self.set_call_count += 1
        self.convergence_data = data.copy()
        self.position = position
        self.action = action
        self.metric = metric
        self.last_set_time = time.time()

        logger.debug(f"Set convergence data: {len(data)} points for {position}/{action} metric={metric}")

    def draw(self, screen: pygame.Surface):
        """Draw the convergence panel."""
        # Render debug info showing panel state
        if not self.convergence_data:
            self.draw_no_data_state(screen)
        else:
            self.draw_with_data(screen)
    
    def draw_no_data_state(self, screen: pygame.Surface):
        """Render the panel when no convergence data is available."""
        # Background
        pygame.draw.rect(screen, self.bg_color, (self.x, self.y, self.width, self.height), border_radius=6)
        pygame.draw.rect(screen, self.grid_color, (self.x, self.y, self.width, self.height), 1, border_radius=6)

        # Title
        metric_str = f" - {self.metric}" if self.metric else ""
        title_text = f"Convergence Analysis{metric_str} - {self.position} {self.action}"
        title = self.title_font.render(title_text, True, self.title_color)
        title_x = self.x + (self.width - title.get_width()) // 2
        screen.blit(title, (title_x, self.y + 8))

        # No data message
        no_data_text = self.label_font.render("No convergence data available", True, self.text_color)
        text_x = self.x + (self.width - no_data_text.get_width()) // 2
        text_y = self.y + (self.height - no_data_text.get_height()) // 2
        screen.blit(no_data_text, (text_x, text_y))
    
    def draw_with_data(self, screen: pygame.Surface):
        """Render the panel with convergence data."""
        # Background
        pygame.draw.rect(screen, self.bg_color, (self.x, self.y, self.width, self.height), border_radius=6)
        pygame.draw.rect(screen, self.grid_color, (self.x, self.y, self.width, self.height), 1, border_radius=6)

        # Title
        metric_str = f" - {self.metric}" if self.metric else ""
        title_text = f"Convergence Analysis{metric_str} - {self.position} {self.action}"
        title = self.title_font.render(title_text, True, self.title_color)
        title_x = self.x + (self.width - title.get_width()) // 2
        screen.blit(title, (title_x, self.y + 8))

        # Extract data for plotting
        x_data = [point["sample_count"] for point in self.convergence_data]
        y_data = [point["equity"] for point in self.convergence_data]

        # Calculate plot bounds
        if x_data and y_data:
            x_min, x_max = min(x_data), max(x_data)
            y_min, y_max = min(y_data), max(y_data)

            # Add padding only on the left and bottom, not on the right/top
            # This allows X-axis to clearly show the max sample count
            x_padding = max(1, (x_max - x_min) * 0.05) if x_max > x_min else 1
            y_padding = max(0.001, (y_max - y_min) * 0.05) if y_max > y_min else 0.001

            x_min = max(0, x_min - x_padding)
            y_min = max(0, y_min - y_padding)
            y_max += y_padding

            # Draw grid and axes
            self._draw_grid_and_axes(screen, x_min, x_max, y_min, y_max)

            # Draw data line
            self._draw_convergence_line(screen, x_data, y_data, x_min, x_max, y_min, y_max)

            # Draw statistical analysis
            self._draw_statistics(screen, x_data, y_data)

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
        for i, (x_pixel, y_pixel) in enumerate(points):
            color = self.point_color
            radius = 3

            # Highlight hovered point
            if self.hovered_point == i:
                color = (255, 255, 0)  # Yellow for hover
                radius = 5

            pygame.draw.circle(screen, color, (x_pixel, y_pixel), radius)

    def _draw_axis_labels(self, screen: pygame.Surface, x_max: float, y_max: float):
        """Draw axis labels."""
        # X-axis label
        x_label = self.label_font.render("Simulations", True, self.text_color)
        x_label_x = self.plot_x + (self.plot_width - x_label.get_width()) // 2
        x_label_y = self.y + self.height - 20
        screen.blit(x_label, (x_label_x, x_label_y))

        # Y-axis label (rotated)
        # Y-axis label (rotated) - use metric name or default
        metric_label = self.metric if self.metric else "Value"
        y_label = self.label_font.render(metric_label, True, self.text_color)
        # For simplicity, we'll place it horizontally above the plot
        y_label_x = self.x + 10
        y_label_y = self.plot_y - 25
        screen.blit(y_label, (y_label_x, y_label_y))

    def _draw_statistics(self, screen: pygame.Surface, x_data: List[float], y_data: List[float]):
        """Draw statistical analysis information."""
        if not x_data or not y_data:
            return

        # Calculate statistics
        final_value = y_data[-1] if y_data else 0.0
        initial_value = y_data[0] if y_data else 0.0
        total_samples = x_data[-1] if x_data else 0

        # Calculate convergence metrics
        if len(y_data) >= 2:
            # Simple convergence rate (change per sample)
            convergence_rate = abs(final_value - initial_value) / len(y_data)
        else:
            convergence_rate = 0.0

        # Calculate standard deviation of last half of data (stability measure)
        if len(y_data) >= 4:
            recent_data = y_data[len(y_data)//2:]
            mean = sum(recent_data) / len(recent_data)
            variance = sum((x - mean) ** 2 for x in recent_data) / len(recent_data)
            std_dev = variance ** 0.5
        else:
            std_dev = 0.0

        # Display statistics
        stats_y = self.y + 25  # Below title
        stats_x = self.x + 10

        # Final value
        final_text = f"Final: {final_value:.4f}"
        final_render = self.label_font.render(final_text, True, self.text_color)
        screen.blit(final_render, (stats_x, stats_y))

        # Total samples
        samples_text = f"Samples: {int(total_samples)}"
        samples_render = self.label_font.render(samples_text, True, self.text_color)
        screen.blit(samples_render, (stats_x + 120, stats_y))

        # Convergence rate
        rate_text = f"Rate: {convergence_rate:.6f}"
        rate_render = self.label_font.render(rate_text, True, self.text_color)
        screen.blit(rate_render, (stats_x, stats_y + 15))

        # Stability (standard deviation)
        stability_text = f"Stability: {std_dev:.6f}"
        stability_render = self.label_font.render(stability_text, True, self.text_color)
        screen.blit(stability_render, (stats_x + 120, stats_y + 15))

        # Convergence status
        if std_dev < 0.01 and len(y_data) >= 5:
            status_text = "CONVERGED"
            status_color = (0, 255, 0)  # Green
        elif std_dev < 0.05:
            status_text = "CONVERGING"
            status_color = (255, 255, 0)  # Yellow
        else:
            status_text = "UNSTABLE"
            status_color = (255, 0, 0)  # Red

        status_render = self.label_font.render(status_text, True, status_color)
        screen.blit(status_render, (self.x + self.width - status_render.get_width() - 10, stats_y))

    def handle_mouse_motion(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle mouse motion for data exploration."""
        if not self.convergence_data:
            return False

        # Check if mouse is over plot area
        if (self.plot_x <= mouse_x <= self.plot_x + self.plot_width and
            self.plot_y <= mouse_y <= self.plot_y + self.plot_height):

            # Find closest data point
            x_data = [point["sample_count"] for point in self.convergence_data]
            y_data = [point["equity"] for point in self.convergence_data]

            if x_data and y_data:
                x_min, x_max = min(x_data), max(x_data)
                y_min, y_max = min(y_data), max(y_data)

                # Convert mouse position to data coordinates
                x_ratio = (mouse_x - self.plot_x) / self.plot_width
                y_ratio = 1.0 - (mouse_y - self.plot_y) / self.plot_height

                data_x = x_min + (x_max - x_min) * x_ratio
                data_y = y_min + (y_max - y_min) * y_ratio

                # Find closest point
                min_distance = float('inf')
                closest_idx = -1

                for i, (x_val, y_val) in enumerate(zip(x_data, y_data)):
                    distance = ((x_val - data_x) / (x_max - x_min)) ** 2 + ((y_val - data_y) / (y_max - y_min)) ** 2
                    if distance < min_distance:
                        min_distance = distance
                        closest_idx = i

                if min_distance < 0.01:  # Close enough to highlight
                    self.hovered_point = closest_idx
                    return True

        self.hovered_point = None
        return False

    def handle_mouse_click(self, mouse_x: int, mouse_y: int, button: int) -> bool:
        """Handle mouse clicks for data exploration."""
        if button == 1 and self.hovered_point is not None:  # Left click on hovered point
            # Could implement point selection or detail view
            return True
        return False

    def get_tooltip_text(self) -> Optional[str]:
        """Get tooltip text for currently hovered point."""
        if self.hovered_point is not None and self.convergence_data:
            point = self.convergence_data[self.hovered_point]
            sample_count = point["sample_count"]
            equity = point["equity"]
            timestamp = point.get("timestamp", "N/A")

            return f"Samples: {sample_count}, Value: {equity:.4f}, Time: {timestamp}"
        return None