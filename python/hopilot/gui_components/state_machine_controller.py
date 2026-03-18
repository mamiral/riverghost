from typing import TYPE_CHECKING, Optional, Dict, Any
from transitions.extensions import LockedMachine as Machine

from hopilot.gto.aof_precompute_runner import GuiRunState
from hopilot.logging_config import get_logger
from hopilot.state_machine_config import (
    STATE_MACHINE_CONFIG,
    SimulationState,
    SimulationTrigger
)
from hopilot.state_machine_utils import handle_simulation_error
from .precompute_config import PrecomputeConfig


if TYPE_CHECKING:
    from .aof_browser_panel import AoFBrowserPanel


class StateMachineController:
    """
    Controller for managing precompute operations through a state machine.

    This class provides a clean interface for triggering state machine events
    and delegates execution to the attached AoFBrowserPanel.
    """

    def __init__(self, panel: Optional['AoFBrowserPanel'] = None, config: Optional[PrecomputeConfig] = None):
        """
        Initialize the state machine controller.

        Args:
            panel: The AoFBrowserPanel to control (can be set later)
            config: Configuration for precompute operations
        """
        self.logger = get_logger(__name__)
        self.panel = panel
        self.config = config or PrecomputeConfig()
        self.state: str = SimulationState.IDLE

        # Initialize state machine
        self._init_state_machine()

        self.logger.info("StateMachineController initialized")

    def _init_state_machine(self):
        """Initialize the state machine with LockedMachine for thread safety."""
        self.logger.info("Initializing state machine")

        # Create the LockedMachine for thread-safe operations
        self.machine = Machine(
            model=self,
            **STATE_MACHINE_CONFIG,
            on_exception=self._handle_simulation_error
        )

        self.logger.info("State machine initialized successfully")

    def trigger_event(self, event: str, **kwargs) -> bool:
        """
        Trigger a state machine event.

        Args:
            event: Event name ('start', 'pause', 'resume', 'stop', 'reset')
            **kwargs: Additional event parameters

        Returns:
            True if event was accepted and processed, False otherwise
        """
        try:
            # Map string events to state machine triggers
            trigger_map = {
                'start': SimulationTrigger.START_SIMULATION,
                'pause': SimulationTrigger.PAUSE_SIMULATION,
                'resume': SimulationTrigger.RESUME_SIMULATION,
                'stop': SimulationTrigger.STOP_SIMULATION,
                'reset': SimulationTrigger.RESET_SIMULATION
            }

            if event not in trigger_map:
                self.logger.warning(f"Unknown event: {event}")
                return False

            trigger = trigger_map[event]

            # Check if trigger is valid for current state
            current_state = self.get_current_state()
            valid_triggers = self.machine.get_triggers(current_state)
            if trigger not in valid_triggers:
                self.logger.warning(f"Invalid trigger '{trigger}' for current state '{current_state}'")
                return False

            # Execute the trigger
            getattr(self, trigger)(**kwargs)
            return True

        except Exception as e:
            self.logger.error(f"Failed to trigger event '{event}': {e}")
            return False

    def get_current_state(self) -> str:
        """Get the current state machine state."""
        return self.state

    def get_status_info(self) -> Dict[str, Any]:
        """
        Get comprehensive status information.

        Returns:
            Dictionary containing state and capability information
        """
        current_state = self.get_current_state()
        valid_triggers = self.machine.get_triggers(current_state)
        return {
            'state': current_state,
            'can_start': SimulationTrigger.START_SIMULATION in valid_triggers,
            'can_pause': SimulationTrigger.PAUSE_SIMULATION in valid_triggers,
            'can_resume': SimulationTrigger.RESUME_SIMULATION in valid_triggers,
            'can_stop': SimulationTrigger.STOP_SIMULATION in valid_triggers,
            'can_reset': SimulationTrigger.RESET_SIMULATION in valid_triggers,
            'progress': self._get_progress_info() if self.panel else None
        }

    def _get_progress_info(self) -> Dict[str, Any]:
        """Get progress information from the panel."""
        if not self.panel:
            return {}
        
        # Get progress info from panel's precompute session
        if hasattr(self.panel, 'precompute_session') and self.panel.precompute_session:
            session = self.panel.precompute_session
            return {
                'completed_cells': getattr(session, 'completed_cells', 0),
                'total_cells': getattr(session, 'total_cells', 0),
                'failed_cells': getattr(session, 'failed_cells', 0),
                'status': getattr(getattr(session, 'run_state', None), 'value', 'unknown')
            }
        
        return {}

    def update_config(self, config: PrecomputeConfig) -> None:
        """
        Update the configuration.

        Args:
            config: New configuration settings
        """
        self.config = config
        if self.panel:
            self.panel.update_precompute_config(config)
        self.logger.info(f"Configuration updated: {config.to_dict()}")

    def sync_with_run_state(self, run_state: GuiRunState | None) -> None:
        """Synchronize the controller with the panel's persisted or runtime session state."""
        if run_state == GuiRunState.RUNNING:
            target_state = SimulationState.RUNNING
        elif run_state == GuiRunState.PAUSED:
            target_state = SimulationState.PAUSED
        elif run_state == GuiRunState.COMPLETED:
            target_state = SimulationState.COMPLETED
        elif run_state == GuiRunState.FAILED:
            target_state = SimulationState.FAILED
        else:
            target_state = SimulationState.IDLE
        self.machine.set_state(target_state)

    def mark_completed(self) -> None:
        """Reflect a completed precompute session in the controller state."""
        self.machine.set_state(SimulationState.COMPLETED)

    def mark_failed(self) -> None:
        """Reflect a failed precompute session in the controller state."""
        self.machine.set_state(SimulationState.FAILED)

    def _persist_session_state(self) -> None:
        """Persist the current session state for recovery."""
        if self.panel and hasattr(self.panel, 'precompute_session') and self.panel.precompute_session:
            # The session checkpointing is handled automatically by the runner
            # during state transitions, but we can ensure it's up to date
            session = self.panel.precompute_session
            if hasattr(session, 'run_id') and session.run_id is not None:
                self.logger.debug(f"Session state persisted for run_id: {session.run_id}")
            else:
                self.logger.debug("Session state checkpointed (no run_id yet)")

    def _handle_simulation_error(self, event):
        """Handle simulation errors."""
        self.logger.error(f"State machine error: {event}")
        handle_simulation_error(event)

    # State machine callback methods
    # These will delegate to the panel when connected

    def has_valid_config(self, event):
        """Condition: check if configuration is valid."""
        return self.config is not None and self.config.max_workers > 0 and self.config.simulations_per_cell > 0

    def validate_scenario(self, event):
        """Prepare callback: validate scenario before starting."""
        self.logger.info("Validating scenario configuration")
        if self.panel:
            # TODO: Implement panel scenario validation
            return True
        return True

    def prepare_resources(self, event):
        """Before callback: prepare resources for simulation."""
        self.logger.info("Preparing simulation resources")
        if self.panel:
            # TODO: Delegate to panel resource preparation
            pass

    def notify_simulation_started(self, event):
        """After callback: notify that simulation has started."""
        self.logger.info("Simulation started successfully")
        if self.panel:
            self.panel.start_precompute()

    def cancel_pending_work(self, event):
        """After callback: cancel pending work on pause."""
        self.logger.info("Cancelling pending simulation work")
        if self.panel:
            # Pause the precompute operation
            self.panel.pause_precompute()
            # Persist session state on pause
            self._persist_session_state()

    def context_matches(self, event):
        """Condition: check if resume context matches."""
        self.logger.info("Checking resume context")
        if self.panel:
            # TODO: Implement context validation for resume
            return True
        return True

    def restart_workers(self, event):
        """After callback: restart workers on resume."""
        self.logger.info("Restarting simulation workers")
        if self.panel:
            # Resume the precompute operation
            self.panel.resume_precompute()
            # Persist session state on resume
            self._persist_session_state()

    def initiate_shutdown(self, event):
        """After callback: initiate graceful shutdown."""
        self.logger.info("Initiating simulation shutdown")
        if self.panel:
            # Stop the precompute operation
            self.panel.stop_precompute()
            # Persist session state on stop
            self._persist_session_state()
        self.machine.set_state(SimulationState.IDLE)

    def all_work_done(self, event):
        """Condition: check if all work is completed."""
        if self.panel and hasattr(self.panel, 'precompute_session'):
            session = self.panel.precompute_session
            if session:
                # Check if all cells are completed or failed
                total_cells = getattr(session, 'total_cells', 0)
                completed_cells = getattr(session, 'completed_cells', 0)
                failed_cells = getattr(session, 'failed_cells', 0)
                return (completed_cells + failed_cells) >= total_cells
        return False

    def cleanup_on_error(self, event):
        """After callback: cleanup on error."""
        self.logger.info("Cleaning up after simulation error")
        if self.panel:
            # Stop any running operations
            self.panel.stop_precompute()
            # Persist error state
            self._persist_session_state()

    def clear_session_data(self, event):
        """Before callback: clear session data on reset."""
        self.logger.info("Clearing session data")
        if self.panel:
            # Reset the precompute state
            self.panel.reset_precompute()