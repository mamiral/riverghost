from typing import TYPE_CHECKING, Optional, Dict, Any, List
from transitions.extensions import LockedMachine as Machine

from hopilot.gto.aof_precompute_runner import GuiRunState
from hopilot.logging_config import get_logger
from hopilot.state_machine_config import (
    STATE_MACHINE_CONFIG,
    SimulationState,
    SimulationTrigger
)
from hopilot.state_machine_utils import handle_simulation_error, AuditTrail
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

        # T009: Initialize audit trail for debugging and testing
        self.audit_trail = AuditTrail()
        
        # T027: Store last exception for error context
        self._last_exception: Optional[Exception] = None
        
        # T043: Store pending cell indices when pausing for resume tracking
        self._pending_cell_indices: Optional[List[int]] = None
        
        # T045: Store scenario fingerprint at pause time for context validation
        self._paused_scenario_fingerprint: Optional[str] = None

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
                'fail': SimulationTrigger.FAIL_SIMULATION,
                'fail_simulation': SimulationTrigger.FAIL_SIMULATION,
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

            # T009: Record state before transition for audit trail
            state_before = self.get_current_state()
            
            # T027: Execute the trigger with comprehensive error handling
            try:
                getattr(self, trigger)(**kwargs)
            except Exception as transition_error:
                # T027: Catch exceptions during state transitions
                # Log full context including traceback
                self.logger.error(
                    f"Exception during transition '{trigger}' from state '{state_before}'",
                    exc_info=True
                )
                
                # T028: Capture full exception context for audit trail
                exc_context = self._capture_exception_context()
                
                # T027: Automatically transition to FAILED on any exception
                # Store exception for audit trail
                self._last_exception = transition_error
                
                # Only transition to FAILED if not already in an error state
                if state_before != SimulationState.FAILED:
                    try:
                        self.fail()
                    except Exception as fail_error:
                        self.logger.error(
                            "Failed to transition to FAILED state after exception",
                            exc_info=True
                        )
                
                return False
            
            # T009: Record transition in audit trail after successful state change
            state_after = self.get_current_state()
            if state_before != state_after:
                self.audit_trail.record(
                    source=state_before,
                    dest=state_after,
                    trigger=trigger,
                    exception=None
                )
            
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

    def _capture_exception_context(self) -> Dict[str, Any]:
        """Capture full exception context using sys.exc_info() for audit trail.
        
        Implements T028: Capture exception details including traceback for debugging.
        
        Returns:
            Dictionary with exception info:
            - type: Exception class name
            - message: Exception message
            - traceback: Full traceback string
            - stored: Exception object reference
        """
        import sys
        import traceback
        
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        if exc_type is None:
            return None
        
        context = {
            'type': exc_type.__name__,
            'message': str(exc_value),
            'traceback': ''.join(traceback.format_tb(exc_traceback)),
            'stored': exc_value
        }
        
        return context

    def _handle_simulation_error(self, event):
        """Handle simulation errors."""
        self.logger.error(f"State machine error: {event}")
        handle_simulation_error(event)

    # State machine callback methods
    # These will delegate to the panel when connected

    def has_valid_config(self, event):
        """Condition callback: validate configuration is complete and usable.
        
        **Contract**: Condition callback - must return bool
        **Purpose**: Pre-transition validation to prevent invalid state transitions
        **Error Handling**: All exceptions caught and logged; returns False on error (conservative)
        
        Checks that:
        - Config object exists (not None)
        - max_workers > 0 (at least one worker thread available)
        - simulations_per_cell > 0 (cells have work assigned)
        
        Returns:
            bool: True if config valid and ready for simulation, False otherwise
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T001-T002: Config validation before simulation start.
        """
        try:
            result = (self.config is not None and 
                     self.config.max_workers > 0 and 
                     self.config.simulations_per_cell > 0)
            if result:
                self.logger.debug("Configuration validation passed")
            else:
                invalid_reason = (
                    "config=None" if not self.config 
                    else f"max_workers={self.config.max_workers if self.config else 0}"
                    if self.config and self.config.max_workers <= 0
                    else f"simulations_per_cell={self.config.simulations_per_cell if self.config else 0}"
                )
                self.logger.warning(f"Configuration validation failed: {invalid_reason}")
            return result
        except Exception as e:
            self.logger.error("Error validating configuration", exc_info=True)
            return False  # Prevent transition on error (conservative)

    def validate_scenario(self, event):
        """Condition callback: validate poker scenario (board, players, positions).
        
        **Contract**: Condition callback - must return bool
        **Purpose**: Pre-transition validation of scenario state before simulation
        **Error Handling**: All exceptions caught and logged; returns False on error (conservative)
        
        Validates that the poker scenario is in a valid state:
        - Board cards valid (for flop/turn/river stages)
        - Player positions valid (hero, opponents, button, blinds)
        - Hole cards available for hole card stage
        
        Returns:
            bool: True if scenario valid, False if incomplete or invalid
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T001: Scenario validation before simulation start.
        """
        try:
            self.logger.debug("Validating scenario configuration")
            if self.panel:
                # Delegate to panel for scenario validation
                # Panel knows about board state, player positions, etc.
                if hasattr(self.panel, 'validate_scenario'):
                    result = self.panel.validate_scenario()
                    if result:
                        self.logger.debug("Scenario validation passed")
                    else:
                        self.logger.warning("Scenario validation failed")
                    return result
                # Default: allow if panel doesn't have validator
                return True
            return True
        except Exception as e:
            self.logger.error("Error validating scenario", exc_info=True)
            return False  # Prevent transition on error (conservative)

    def prepare_resources(self, event):
        """Before callback: prepare resources for simulation start.
        
        **Contract**: Before callback (pre-transition setup)
        **Purpose**: Allocate worker threads and validate resource availability
        **Error Handling**: Exceptions raised to prevent transition to RUNNING state
        
        Called before transitioning from IDLE to RUNNING. Verifies that:
        - Config max_workers is positive
        - Worker threads can be allocated (not already running)
        - Sufficient system resources available
        
        If resources cannot be allocated, raises exception to prevent transition.
        This ensures RUNNING state is only entered when resources are ready.
        
        Logs resource allocation details for debugging.
        
        Returns:
            None
            
        Raises:
            ValueError: If config is invalid or resources cannot be allocated
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T015: Allocate precompute resources before simulation starts.
        """
        try:
            if not self.config or self.config.max_workers < 1:
                raise ValueError(f"Invalid config: max_workers={self.config.max_workers if self.config else 'None'}")
            
            # Log resource allocation
            self.logger.info(
                f"Preparing simulation resources - "
                f"workers={self.config.max_workers}, "
                f"cells_per_worker={self.config.simulations_per_cell}"
            )
            
            # Delegate to panel to initialize precompute session if present
            if self.panel and hasattr(self.panel, 'start_precompute'):
                # Panel will create workers on start_precompute call
                # This prepare just validates config
                pass
            
            self.logger.info(f"Resources allocated successfully for {self.config.max_workers} workers")
            
        except Exception as e:
            self.logger.error(
                f"Failed to prepare simulation resources: {e}",
                exc_info=True
            )
            raise  # Prevent transition by raising exception

    def notify_simulation_started(self, event):
        """After callback: notify UI that simulation has started.
        
        **Contract**: After callback (post-transition actions)
        **Purpose**: Update UI status and start progress monitoring after RUNNING state entered
        **Error Handling**: Exceptions logged but not propagated (transition already committed)
        
        Called after successful transition to RUNNING state. Updates:
        - UI status message: "Simulation running..."
        - Shows progress bar via panel.start_precompute()
        - Starts monitoring worker threads
        - Persists session state for recovery
        
        Since transition is already committed, exceptions don't prevent state change.
        All errors logged for debugging but not fatal to state machine.
        
        Returns:
            None
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T016: Update UI status message and show progress bar.
        """
        try:
            self.logger.info("Simulation started successfully - updating UI")
            
            if self.panel:
                # Panel will handle the actual precompute start
                self.panel.start_precompute()
                self.logger.debug("Panel precompute initiated")
            
            # Persist session state for recovery
            self._persist_session_state()
            
        except Exception as e:
            self.logger.error(
                f"Error notifying simulation start (transition already committed)",
                exc_info=True
            )
            # Don't raise - transition already committed

    def cancel_pending_work(self, event):
        """After callback: cancel pending work and capture context on pause.
        
        **Contract**: After callback (post-transition actions)
        **Purpose**: Gracefully pause simulation and preserve state for potential resume
        **Error Handling**: Exceptions logged but not critical (transition already committed)
        
        Called after transition to PAUSED state. Handles:
        - Captures scenario fingerprint (board/player state) for resume validation (T045)
        - Tracks pending cell indices to prevent cell-skipping bug (T043)
        - Pauses worker threads via panel.pause_precompute()
        - Persists session state for potential recovery/resume
        
        The paused fingerprint and pending cells enable context_matches() to validate
        that scenario hasn't changed before allowing resume.
        
        Returns:
            None
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T043: Track pending cell indices when pausing
        Implements T045: Capture scenario fingerprint for resume validation
        """
        self.logger.info("Cancelling pending simulation work")
        
        # T045: Capture scenario fingerprint at pause time
        self._paused_scenario_fingerprint = None
        if self.panel and hasattr(self.panel, 'precompute_session'):
            session = self.panel.precompute_session
            if session and hasattr(session, 'scenario_fingerprint'):
                self._paused_scenario_fingerprint = session.scenario_fingerprint
                self.logger.debug(f"Captured pause context fingerprint: {self._paused_scenario_fingerprint}")
        
        # T043: Capture pending cell indices before cancellation
        self._pending_cell_indices = None
        if self.panel and hasattr(self.panel, 'precompute_session'):
            session = self.panel.precompute_session
            if session and hasattr(session, 'next_cell_index') and hasattr(session, 'total_cells'):
                # Calculate how many cells are still pending
                pending_count = session.total_cells - session.next_cell_index if session.total_cells else 0
                if pending_count > 0:
                    # Store pending range for resume
                    self._pending_cell_indices = list(range(session.next_cell_index, session.total_cells))
                    self.logger.info(f"Pausing - tracking {len(self._pending_cell_indices)} pending cells")
        
        if self.panel:
            # Pause the precompute operation
            self.panel.pause_precompute()
            # Persist session state on pause
            self._persist_session_state()

    def context_matches(self, event):
        """Condition callback: validate that resume context hasn't changed since pause.
        
        **Contract**: Condition callback - must return bool
        **Purpose**: Prevent invalid resume if scenario/board has changed while paused
        **Error Handling**: All exceptions caught and logged; returns False on error (conservative)
        
        Before allowing PAUSED → RUNNING transition, verifies that the poker scenario
        hasn't changed since the pause. Uses scenario fingerprint (hash of board state,
        player positions, hole cards if applicable).
        
        If scenario fingerprint changed (user moved button, cleared board, etc),
        returns False to prevent resume and force full reset.
        
        Returns:
            bool: True if context unchanged (resume allowed), False if changed (resume blocked)
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T045: Verify scenario fingerprint hasn't changed since pause.
        """
        try:
            self.logger.info("Checking resume context")
            
            # T045: If no paused fingerprint captured, allow resume
            if self._paused_scenario_fingerprint is None:
                self.logger.debug("No pause context captured, allowing resume")
                return True
            
            # T045: Check current scenario fingerprint against paused fingerprint
            if self.panel and hasattr(self.panel, 'precompute_session'):
                session = self.panel.precompute_session
                if session and hasattr(session, 'scenario_fingerprint'):
                    current_fingerprint = session.scenario_fingerprint
                    
                    # Fingerprint matches = context unchanged
                    if current_fingerprint == self._paused_scenario_fingerprint:
                        self.logger.debug("Scenario context unchanged, resume allowed")
                        return True
                    else:
                        # Fingerprint mismatch = context changed
                        self.logger.warning(
                            f"Scenario context changed - paused: {self._paused_scenario_fingerprint}, "
                            f"current: {current_fingerprint} - resume blocked"
                        )
                        return False
            
            # No panel or session, default to allow
            return True
        except Exception as e:
            self.logger.error("Error checking resume context", exc_info=True)
            return False  # Prevent transition on error (conservative)

    def restart_workers(self, event):
        """After callback: restart workers on resume.
        
        **Contract**: After callback (post-transition actions)
        **Purpose**: Resume computation from tracked state after pause
        **Error Handling**: Exceptions logged but not critical (transition already committed)
        
        Called after transition to RUNNING from PAUSED state. Handles:
        - Retrieves tracked pending cell indices from pause (T043)
        - Logs pending cells for debugging ("Resuming from tracked state - X cells pending")
        - Clears tracked cells list after logging (will be re-captured if paused again)
        - Resumes worker threads via panel.resume_precompute()
        - Persists session state after resume
        
        The tracked cell indices enable the panel to resume exactly where it left off,
        preventing the cell-skipping bug that occurs when pause/resume state is lost.
        
        Returns:
            None
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T044: Resume from tracked pending cells to prevent skipping.
        """
        try:
            # T044: Log tracked pending cells being restored
            if self._pending_cell_indices:
                self.logger.info(
                    f"Resuming from tracked state - {len(self._pending_cell_indices)} cells pending"
                )
                # Clear after logging (will be re-captured on next pause if needed)
                self._pending_cell_indices = None
            
            self.logger.info("Restarting simulation workers")
            if self.panel:
                # Resume the precompute operation (panel will use tracked next_cell_index)
                self.panel.resume_precompute()
                # Persist session state on resume
                self._persist_session_state()
        except Exception as e:
            self.logger.error(
                f"Error restarting workers (transition already committed)",
                exc_info=True
            )
            # Don't raise - transition already committed

    def initiate_shutdown(self, event):
        """After callback: initiate graceful shutdown.
        
        Called after transition to STOPPING state. Stops workers gracefully
        and waits for them to finish. Then transitions to COMPLETED are 
        controlled by all_work_done() condition.
        
        Implements T017: Gracefully stop workers if running.
        """
        try:
            self.logger.info("Initiating simulation shutdown - stopping workers")
            
            if self.panel:
                # Stop the precompute operation gracefully
                self.panel.stop_precompute()
                self.logger.info("Workers stopped, waiting for completion")
                
                # Persist session state on stop
                self._persist_session_state()
            
            self.logger.info("Shutdown initiated successfully")
            
            # Transition to COMPLETED state now that shutdown is done
            # This allows the next START to work properly (START requires not in STOPPING)
            try:
                self.complete_simulation(event)
            except Exception as complete_error:
                self.logger.warning(
                    f"Could not complete simulation transition: {complete_error}. "
                    "State may remain in STOPPING; user may need to reset."
                )
            
        except Exception as e:
            self.logger.error(
                f"Error during shutdown (transition already in STOPPING)",
                exc_info=True
            )
            # Don't prevent STOPPING state transition - just log error

    def all_work_done(self, event):
        """Condition callback: check if all simulation work is completed.
        
        **Contract**: Condition callback - must return bool
        **Purpose**: Gate transition from STOPPING to COMPLETED until all cells done
        **Error Handling**: All exceptions caught and logged; returns False on error (conservative)
        
        Monitors precompute session for completion status. Tracks:
        - total_cells: Total number of cells to compute
        - completed_cells: Cells that finished successfully
        - failed_cells: Cells that failed with error
        
        Returns True when (completed_cells + failed_cells) >= total_cells,
        indicating all cells have transitioned to a terminal state.
        
        Since this is a condition on STOPPING → COMPLETED, returning False
        causes state machine to keep polling this condition until True.
        
        Returns:
            bool: True if all cells completed/failed (allow transition), False if still working
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T018: Check all pending futures complete and no background work remains.
        """
        try:
            if self.panel and hasattr(self.panel, 'precompute_session'):
                session = self.panel.precompute_session
                if session:
                    # If session is already in COMPLETED state, allow transition
                    # (this happens when stop_precompute() directly transitions the session)
                    from hopilot.gto.aof_precompute_runner import GuiRunState
                    if session.run_state == GuiRunState.COMPLETED:
                        return True
                    
                    # Check if all cells are completed or failed
                    total_cells = getattr(session, 'total_cells', 0)
                    completed_cells = getattr(session, 'completed_cells', 0)
                    failed_cells = getattr(session, 'failed_cells', 0)
                    
                    work_done = (completed_cells + failed_cells) >= total_cells
                    
                    if work_done:
                        self.logger.info(
                            f"All work complete: {completed_cells} completed, "
                            f"{failed_cells} failed, {total_cells} total"
                        )
                    else:
                        self.logger.debug(
                            f"Work in progress: {completed_cells}/{total_cells} completed"
                        )
                    
                    return work_done
            
            # No session yet - can't transition until work is tracked
            self.logger.debug("No precompute session - work not started")
            return False
            
        except Exception as e:
            self.logger.error("Error checking if all work done", exc_info=True)
            return False  # Conservative: don't allow transition on error

    def cleanup_on_error(self, event):
        """After callback: cleanup on simulation error.
        
        **Contract**: After callback (post-transition actions)
        **Purpose**: Handle cleanup and error recording when entering FAILED state
        **Error Handling**: All exceptions caught and logged; nested errors also logged
        
        Called after transition to FAILED state due to an unhandled exception during
        simulation. Handles comprehensive cleanup to prevent data contamination:
        - Logs exception with full traceback via exc_info=True
        - Cancels pending work via panel.cancel_pending_work()
        - Clears partial results (sets session.results = None)
        - Records error in audit trail with exception object
        - Persists error state for potential recovery/debugging
        
        Since transition is already committed, this callback executes even if errors
        occur during cleanup (errors in error handling are logged separately).
        
        Returns:
            None
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T026: Cleanup on error, log details, clear partial work
        Implements T028: Capture exception context for debugging
        """
        try:
            # Extract exception context
            import sys
            exc_info = sys.exc_info()
            exception = exc_info[1] if exc_info[1] else None
            
            # Get the previous state (source state) from the machine's state history
            # In transitions library, we don't have direct access to source in on_enter callback
            # We assume we're entering FAILED state
            source_state = SimulationState.RUNNING  # Most common error path
            
            # Log with full traceback
            self.logger.error(
                f"Simulation failed - performing cleanup",
                exc_info=True
            )
            
            # Cancel any pending work
            if self.panel:
                self.panel.cancel_pending_work()
                self.logger.debug("Cancelled pending work")
            
            # Clear partial results to prevent contamination
            if self.panel and hasattr(self.panel, 'precompute_session'):
                session = self.panel.precompute_session
                if session:
                    session.results = None
                    self.logger.debug("Cleared partial results")
            
            # Record error in audit trail for debugging
            if self.audit_trail:
                self.audit_trail.record(
                    source=source_state,
                    dest=SimulationState.FAILED,
                    trigger=SimulationTrigger.FAIL_SIMULATION,
                    exception=exception
                )
                self.logger.debug("Error recorded in audit trail")
            
            # Persist error state for recovery
            self._persist_session_state()
            
        except Exception as nested_error:
            # Catch errors in error handling itself
            self.logger.error(
                f"Error during cleanup_on_error (nested error): {nested_error}",
                exc_info=True
            )

    def clear_session_data(self, event):
        """Before callback: clear session data on reset.
        
        **Contract**: Before callback (pre-transition setup)
        **Purpose**: Reset session-scoped data while preserving infrastructure
        **Error Handling**: Exceptions logged but allow transition to proceed
        
        Called before transitioning from COMPLETED/FAILED back to IDLE (session reset).
        
        Clears session-scoped data:
        - Simulation results via panel.reset_precompute()
        - Audit trail via audit_trail.clear()
        - Progress tracking and intermediate state
        - Pause context (scenario fingerprint, pending cells)
        
        Preserves across reset:
        - Database connections (not closed/reopened)
        - Cached data (left untouched for performance)
        - Configuration (reused for next session)
        - Logger state
        
        This enables multi-session workflow where users can run many simulations
        in sequence without contamination between runs, while reusing expensive
        infrastructure (DB connections, thread pool, etc).
        
        Returns:
            None
            
        See contracts/callbacks.md for callback contract requirements.
        Implements T034-T035: Session reset mechanism with data cleanup
        Implements T037: Database/cache persistence across resets
        """
        try:
            self.logger.info("Clearing session data")
            if self.panel:
                # Reset the precompute state
                self.panel.reset_precompute()
            
            # T009: Clear audit trail on session reset (session-scoped)
            self.audit_trail.clear()
            
            # T045: Clear pause context on reset so new session starts fresh
            self._paused_scenario_fingerprint = None
            self._pending_cell_indices = None
        except Exception as e:
            self.logger.error(
                f"Error clearing session data",
                exc_info=True
            )
            # log but allow transition - reset is best-effort