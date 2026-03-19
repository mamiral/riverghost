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

# T053: State Transition Reachability Audit
# All transitions verified as reachable and tested:
# 
# State Graph:
#   IDLE (initial) 
#     → START → RUNNING (T012, T014)
#            ↓
#          PAUSE → PAUSED (T022, T040)
#            ↓
#          RESUME → RUNNING (T023, T040) [condition: context_matches]
#            ↓
#          STOP → STOPPING (T017, T021) 
#            ↓
#          COMPLETE → COMPLETED (T018, T021) [condition: all_work_done]
#            ↓
#           RESET → IDLE (T034, T036)
#
# Error Path:
#   RUNNING → FAIL → FAILED (T026, T027)
#              ↓
#            RESET → IDLE (T037)
#
# Recovery from Error:
#   FAILED → START → RUNNING (T023)
#   COMPLETED → START → RUNNING (T012)
#
# Transitions Verified:
#   ✓ START_SIMULATION: 3 sources (IDLE, COMPLETED, FAILED) → RUNNING - Tested
#   ✓ PAUSE_SIMULATION: RUNNING → PAUSED - Tested
#   ✓ RESUME_SIMULATION: PAUSED → RUNNING - Tested  ✓ STOP_SIMULATION: 2 sources (RUNNING, PAUSED) → STOPPING - Tested
#   ✓ COMPLETE_SIMULATION: STOPPING → COMPLETED - Tested
#   ✓ FAIL_SIMULATION: RUNNING → FAILED - Tested
#   ✓ RESET_SIMULATION: 2 sources (COMPLETED, FAILED) → IDLE - Tested
#
# Total: 7 transitions, all reachable, all tested (T053 verified)

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
        'source': [SimulationState.IDLE, SimulationState.COMPLETED, SimulationState.FAILED],
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