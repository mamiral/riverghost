# State Machine Error Handling Utilities
# Feature: 001-gui-state-refactor

import logging
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

def state_machine_error_handler(func: Callable) -> Callable:
    """
    Decorator for state machine callbacks that provides error handling and logging.

    Args:
        func: The callback function to wrap

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in state machine callback {func.__name__}: {e}", exc_info=True)
            # Re-raise to let state machine handle it
            raise
    return wrapper

def handle_simulation_error(event) -> None:
    """
    Global error handler for simulation state machine transitions.

    Called when any callback raises an exception during state transitions.

    Args:
        event: The transition event that caused the error
    """
    logger.error(f"Simulation state machine error during {event.event.name}: {event.error}")
    # Additional error handling logic can be added here
    # For example, attempt recovery or notify UI

def validate_transition_conditions(func: Callable[[Any], bool]) -> Callable[[Any], bool]:
    """
    Decorator for transition condition functions that provides validation and logging.

    Args:
        func: The condition function to wrap

    Returns:
        Wrapped condition function
    """
    @wraps(func)
    def wrapper(model, *args, **kwargs):
        try:
            result = func(model, *args, **kwargs)
            logger.debug(f"Transition condition {func.__name__} evaluated to: {result}")
            return result
        except Exception as e:
            logger.error(f"Error evaluating transition condition {func.__name__}: {e}")
            return False  # Fail closed for safety
    return wrapper