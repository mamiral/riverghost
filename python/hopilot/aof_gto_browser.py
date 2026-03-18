# AOF GTO Browser - GUI Application with State Machine
# Feature: 001-gui-state-refactor

import pygame
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any

from transitions.extensions import LockedMachine as Machine

from hopilot.logging_config import get_logger
from hopilot.state_machine_config import (
    STATE_MACHINE_CONFIG,
    SimulationState,
    SimulationTrigger,
    state_machine_logger
)
from hopilot.state_machine_utils import handle_simulation_error
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiPrecomputeRunSession


class GuiApplication:
    """
    Main GUI application for AOF GTO Browser with state machine control.

    This class manages the simulation lifecycle using a robust state machine
    implemented with the transitions library.
    """

    def __init__(self, width: int = 1200, height: int = 800):
        self.logger = get_logger(__name__)
        self.logger.info("Initializing AOF GTO Browser GUI Application")

        # Initialize Pygame
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("HoPilot - AOF GTO Browser")
        self.clock = pygame.time.Clock()

        # Simulation components
        self.executor: Optional[ThreadPoolExecutor] = None
        self.session: Optional[GuiPrecomputeRunSession] = None
        self.runner: Optional[AoFPrecomputeRunner] = None

        # UI Components
        self.start_button: Optional[pygame.Rect] = None
        self.pause_button: Optional[pygame.Rect] = None
        self.resume_button: Optional[pygame.Rect] = None
        self.stop_button: Optional[pygame.Rect] = None
        self.font = pygame.font.SysFont("arial", 24)

        # Error handling
        self.last_error: Optional[str] = None

        # Initialize state machine
        self._init_state_machine()

        self.logger.info("AOF GTO Browser GUI Application initialized")

    def _init_state_machine(self):
        """Initialize the state machine using transitions library."""
        self.logger.info("Initializing state machine")

        # Create the LockedMachine for thread-safe operations
        self.machine = Machine(
            model=self,
            **STATE_MACHINE_CONFIG,
            on_exception=self.handle_simulation_error
        )

        self.logger.info("State machine initialized successfully")

    def run(self):
        """Main application loop."""
        running = True
        while running:
            for event in pygame.event.get():
                running = self._handle_event(event)
            self._draw()
            self.clock.tick(30)

        pygame.quit()
        sys.exit()

    def _handle_event(self, event) -> bool:
        """Handle pygame events."""
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mouse_click(event.pos)

        return True

    def _handle_mouse_click(self, pos: tuple[int, int]) -> bool:
        """Handle mouse click events on buttons."""
        if self.start_button and self.start_button.collidepoint(pos):
            self._on_start_clicked()
        elif self.pause_button and self.pause_button.collidepoint(pos):
            self._on_pause_clicked()
        elif self.resume_button and self.resume_button.collidepoint(pos):
            self._on_resume_clicked()
        elif self.stop_button and self.stop_button.collidepoint(pos):
            self._on_stop_clicked()

        return True

    def _on_start_clicked(self):
        """Handle start button click."""
        try:
            self.machine.start_simulation()
        except Exception as e:
            self.logger.error(f"Failed to start simulation: {e}")

    def _on_pause_clicked(self):
        """Handle pause button click."""
        try:
            self.machine.pause_simulation()
        except Exception as e:
            self.logger.error(f"Failed to pause simulation: {e}")

    def _on_resume_clicked(self):
        """Handle resume button click."""
        try:
            self.machine.resume_simulation()
        except Exception as e:
            self.logger.error(f"Failed to resume simulation: {e}")

    def _on_stop_clicked(self):
        """Handle stop button click."""
        try:
            self.machine.stop_simulation()
        except Exception as e:
            self.logger.error(f"Failed to stop simulation: {e}")

    def _draw(self):
        """Draw the GUI."""
        self.screen.fill((27, 40, 34))  # Dark green background

        # Draw buttons
        self._draw_buttons()

        # Draw status
        self._draw_status()

        pygame.display.flip()

    def _draw_buttons(self):
        """Draw control buttons based on current state."""
        button_y = 50
        button_height = 40
        button_width = 100
        spacing = 20

        # Start button
        if self.may_start_simulation():
            self.start_button = pygame.Rect(50, button_y, button_width, button_height)
            pygame.draw.rect(self.screen, (0, 255, 0), self.start_button)
            text = self.font.render("START", True, (0, 0, 0))
            self.screen.blit(text, (60, button_y + 10))
        else:
            self.start_button = None

        # Pause button
        if self.may_pause_simulation():
            self.pause_button = pygame.Rect(170, button_y, button_width, button_height)
            pygame.draw.rect(self.screen, (255, 255, 0), self.pause_button)
            text = self.font.render("PAUSE", True, (0, 0, 0))
            self.screen.blit(text, (180, button_y + 10))
        else:
            self.pause_button = None

        # Resume button
        if self.may_resume_simulation():
            self.resume_button = pygame.Rect(290, button_y, button_width, button_height)
            pygame.draw.rect(self.screen, (0, 255, 255), self.resume_button)
            text = self.font.render("RESUME", True, (0, 0, 0))
            self.screen.blit(text, (295, button_y + 10))
        else:
            self.resume_button = None

        # Stop button
        if self.may_stop_simulation():
            self.stop_button = pygame.Rect(410, button_y, button_width, button_height)
            pygame.draw.rect(self.screen, (255, 0, 0), self.stop_button)
            text = self.font.render("STOP", True, (255, 255, 255))
            self.screen.blit(text, (425, button_y + 10))
        else:
            self.stop_button = None

    def _draw_status(self):
        """Draw current status information."""
        status_text = f"State: {self.state}"
        text = self.font.render(status_text, True, (255, 255, 255))
        self.screen.blit(text, (50, 120))

        # Show error message if in failed state
        if self.is_failed() and self.last_error:
            error_text = f"Error: {self.last_error}"
            error_surface = self.font.render(error_text, True, (255, 0, 0))
            self.screen.blit(error_surface, (50, 150))

    def handle_simulation_error(self, event):
        """Handle simulation errors and update UI."""
        self.last_error = str(event.error) if event.error else "Unknown error"
        self.logger.error(f"Simulation error: {self.last_error}")
        # Call global handler
        handle_simulation_error(event)

    def validate_scenario(self, event):
        """Prepare callback: validate scenario before starting."""
        self.logger.info("Validating scenario configuration")
        # TODO: Implement scenario validation
        return True

    def has_valid_config(self, event):
        """Condition: check if configuration is valid."""
        # TODO: Implement config validation
        return True

    def prepare_resources(self, event):
        """Before callback: prepare resources for simulation."""
        self.logger.info("Preparing simulation resources")
        # TODO: Initialize ThreadPoolExecutor, session, etc.

    def notify_simulation_started(self, event):
        """After callback: notify that simulation has started."""
        self.logger.info("Simulation started successfully")

    def cancel_pending_work(self, event):
        """After callback: cancel pending work on pause."""
        self.logger.info("Cancelling pending simulation work")

    def context_matches(self, event):
        """Condition: check if resume context matches."""
        # TODO: Implement context validation
        return True

    def restart_workers(self, event):
        """After callback: restart workers on resume."""
        self.logger.info("Restarting simulation workers")

    def initiate_shutdown(self, event):
        """After callback: initiate graceful shutdown."""
        self.logger.info("Initiating simulation shutdown")

    def all_work_done(self, event):
        """Condition: check if all work is completed."""
        # TODO: Implement completion check
        return True

    def cleanup_on_error(self, event):
        """After callback: cleanup on error."""
        self.logger.error("Cleaning up after simulation error")

    def clear_session_data(self, event):
        """Before callback: clear session data on reset."""
        self.logger.info("Clearing session data")


if __name__ == "__main__":
    app = GuiApplication()
    app.run()