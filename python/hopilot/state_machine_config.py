# State Machine Configuration for GuiRunState Refactor
# Feature: 001-gui-state-refactor

from typing import List, Dict, Any
from hopilot.logging_config import get_logger

# Get logger for state machine
state_machine_logger = get_logger(__name__)

# State constants for type safety
class SimulationState:
    IDLE = 'idle'
    RUNNING = 'running'
    PAUSED = 'paused'
    STOPPING = 'stopping'
    COMPLETED = 'completed'
    FAILED = 'failed'

# Trigger constants for type safety
class SimulationTrigger:
    START_SIMULATION = 'start_simulation'
    PAUSE_SIMULATION = 'pause_simulation'
    RESUME_SIMULATION = 'resume_simulation'
    STOP_SIMULATION = 'stop_simulation'
    COMPLETE_SIMULATION = 'complete_simulation'
    FAIL_SIMULATION = 'fail_simulation'
    RESET_SIMULATION = 'reset_simulation'

# State definitions
SIMULATION_STATES = [
    SimulationState.IDLE,
    SimulationState.RUNNING,
    SimulationState.PAUSED,
    SimulationState.STOPPING,
    SimulationState.COMPLETED,
    SimulationState.FAILED
]

# Transition definitions
SIMULATION_TRANSITIONS = [
    # Start simulation
    {
        'trigger': SimulationTrigger.START_SIMULATION,
        'source': SimulationState.IDLE,
        'dest': SimulationState.RUNNING,
        'prepare': 'validate_scenario',
        'conditions': 'has_valid_config',
        'before': 'prepare_resources',
        'after': 'notify_simulation_started'
    },
    # Pause simulation
    {
        'trigger': SimulationTrigger.PAUSE_SIMULATION,
        'source': SimulationState.RUNNING,
        'dest': SimulationState.PAUSED,
        'after': 'cancel_pending_work'
    },
    # Resume simulation
    {
        'trigger': SimulationTrigger.RESUME_SIMULATION,
        'source': SimulationState.PAUSED,
        'dest': SimulationState.RUNNING,
        'conditions': 'context_matches',
        'after': 'restart_workers'
    },
    # Stop simulation
    {
        'trigger': SimulationTrigger.STOP_SIMULATION,
        'source': [SimulationState.RUNNING, SimulationState.PAUSED],
        'dest': SimulationState.STOPPING,
        'after': 'initiate_shutdown'
    },
    # Complete simulation
    {
        'trigger': SimulationTrigger.COMPLETE_SIMULATION,
        'source': SimulationState.STOPPING,
        'dest': SimulationState.COMPLETED,
        'conditions': 'all_work_done'
    },
    # Fail simulation
    {
        'trigger': SimulationTrigger.FAIL_SIMULATION,
        'source': SimulationState.RUNNING,
        'dest': SimulationState.FAILED,
        'after': 'cleanup_on_error'
    },
    # Reset simulation
    {
        'trigger': SimulationTrigger.RESET_SIMULATION,
        'source': [SimulationState.COMPLETED, SimulationState.FAILED],
        'dest': SimulationState.IDLE,
        'before': 'clear_session_data'
    }
]

# State machine configuration
STATE_MACHINE_CONFIG = {
    'states': SIMULATION_STATES,
    'transitions': SIMULATION_TRANSITIONS,
    'initial': SimulationState.IDLE,
    'send_event': True,      # Pass event data to callbacks
    'queued': True,          # Sequential event processing
    'auto_transitions': False,  # Don't add automatic transitions
    'ignore_invalid_triggers': False  # Strict validation
}