"""
Observer pattern implementation for convergence tracking events.

Provides the foundation for decoupling convergence data producers from consumers,
enabling real-time GUI updates and database storage during aggregation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Protocol

from hopilot.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ConvergenceData:
    """
    Data structure for convergence update events.

    Contains all the information needed to track convergence progress
    for a specific matrix cell during aggregation.
    """
    cell_id: int
    simulation_id: int
    sample_count: int
    equity: float
    win_probability: float
    ev: float
    timestamp: str


class ConvergenceObserver(Protocol):
    """
    Protocol for convergence event observers.

    Defines the interface that all convergence observers must implement.
    """

    def on_convergence_update(self, data: ConvergenceData) -> None:
        """
        Handle a convergence update event.

        Args:
            data: Convergence data for the update
        """
        ...


class ConvergenceEventEmitter:
    """
    Event emitter for convergence tracking.

    Manages a list of observers and notifies them of convergence updates
    during matrix cell aggregation.
    """

    def __init__(self) -> None:
        """Initialize with empty observer list."""
        self._observers: List[ConvergenceObserver] = []

    def attach(self, observer: ConvergenceObserver) -> None:
        """
        Attach an observer to receive convergence events.

        Args:
            observer: Observer to attach
        """
        if observer not in self._observers:
            self._observers.append(observer)
            logger.debug(f"Attached convergence observer: {type(observer).__name__}")

    def detach(self, observer: ConvergenceObserver) -> None:
        """
        Detach an observer from receiving convergence events.

        Args:
            observer: Observer to detach
        """
        try:
            self._observers.remove(observer)
            logger.debug(f"Detached convergence observer: {type(observer).__name__}")
        except ValueError:
            logger.warning(f"Observer {type(observer).__name__} not found in observer list")

    def emit_convergence_update(self, data: ConvergenceData) -> None:
        """
        Emit a convergence update to all attached observers.

        Args:
            data: Convergence data to emit
        """
        logger.debug(f"Emitting convergence update for cell {data.cell_id}, sample_count {data.sample_count}")
        for observer in self._observers:
            try:
                observer.on_convergence_update(data)
            except Exception as e:
                logger.error(f"Error in convergence observer {type(observer).__name__}: {e}")